"""Unified aggregation engine producing Schema v2 output."""

import collections
import datetime as dt
import json
import pathlib
import re
from typing import List, Dict, Any, Optional

from .collectors.base import NormalizedSession, BaseCollector
from .pricing import PricingCalculator, classify_family
from .efficiency import calculate_cache_hit_rate, evaluate_cache_leak

IDLE_CAP_S = 5 * 60  # 5 minutes cap for active time calculations


def anonymize_name(index: int) -> str:
    if index < 26:
        return f"Project {chr(65 + index)}"
    return f"Project {index + 1}"


def sanitize_project_id(name: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return cleaned or "project"


class AggregationEngine:
    def __init__(self, pricing_calc: Optional[PricingCalculator] = None):
        self.pricing = pricing_calc or PricingCalculator()

    def aggregate(
        self,
        sessions: List[NormalizedSession],
        range_days: int = 30,
        anonymize: bool = False,
        cache_thresholds: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=range_days)
        # Filter sessions within time range
        valid_sessions = [s for s in sessions if s.timestamp >= since]

        # Map by project
        proj_sessions = collections.defaultdict(list)
        for s in valid_sessions:
            proj_sessions[s.project_name].append(s)

        # Sort projects by approximate cost descending
        def rough_cost(sess_list):
            return sum(self.pricing.compute_cost(s.model, s.input_tokens, s.output_tokens, s.cache_write_tokens, s.cache_read_tokens) for s in sess_list)

        sorted_proj_names = sorted(proj_sessions.keys(), key=lambda p: -rough_cost(proj_sessions[p]))

        alias_map = {}
        for idx, name in enumerate(sorted_proj_names):
            if anonymize:
                alias_map[name] = anonymize_name(idx)
            else:
                alias_map[name] = name

        days_list = [(dt.date.today() - dt.timedelta(days=i)).isoformat() for i in range(min(range_days, 30) - 1, -1, -1)]

        projects_out = []
        tools_all = collections.Counter()
        models_all = collections.defaultdict(lambda: [0, 0.0, "other"])  # model -> [tokens, cost, source]
        daily_all = collections.defaultdict(lambda: {"tokens": 0, "cost": 0.0, "sessions": set(), "bySource": collections.defaultdict(float)})
        by_source_all = collections.defaultdict(lambda: {"costUSD": 0.0, "tokens": collections.Counter(), "sessions": 0, "activeSeconds": 0.0})

        total_saved_usd = 0.0
        detected_sources = set()

        for orig_name in sorted_proj_names:
            s_list = proj_sessions[orig_name]
            p_alias = alias_map[orig_name]
            p_id = sanitize_project_id(p_alias)

            p_tokens = collections.Counter()
            p_tools = collections.Counter()
            p_models = collections.Counter()
            p_daily = collections.defaultdict(lambda: [0, 0.0])  # day -> [tokens, cost]
            p_sources = set()
            p_by_source = collections.defaultdict(float)
            last_active = None
            sess_ids = set()

            # Active hours calculation from event timestamps
            all_timestamps = []
            for s in s_list:
                p_sources.add(s.source)
                detected_sources.add(s.source)
                sess_ids.add(s.session_id)
                by_source_all[s.source]["sessions"] += 1

                p_tokens["input"] += s.input_tokens
                p_tokens["output"] += s.output_tokens
                p_tokens["cacheWrite"] += s.cache_write_tokens
                p_tokens["cacheRead"] += s.cache_read_tokens

                p_tools.update(s.tool_calls)
                tools_all.update(s.tool_calls)

                # Compute dynamic cost at export time
                c = self.pricing.compute_cost(s.model, s.input_tokens, s.output_tokens, s.cache_write_tokens, s.cache_read_tokens)
                saved = self.pricing.compute_cache_savings(s.model, s.cache_read_tokens)
                total_saved_usd += saved

                p_models[s.model] += c
                models_all[s.model][0] += (s.input_tokens + s.output_tokens + s.cache_write_tokens + s.cache_read_tokens)
                models_all[s.model][1] += c
                models_all[s.model][2] = s.source

                p_by_source[s.source] += c
                by_source_all[s.source]["costUSD"] += c
                by_source_all[s.source]["tokens"]["input"] += s.input_tokens
                by_source_all[s.source]["tokens"]["output"] += s.output_tokens
                by_source_all[s.source]["tokens"]["cacheWrite"] += s.cache_write_tokens
                by_source_all[s.source]["tokens"]["cacheRead"] += s.cache_read_tokens

                day_str = s.timestamp.astimezone().date().isoformat()
                tot_s_tokens = s.input_tokens + s.output_tokens + s.cache_write_tokens + s.cache_read_tokens
                p_daily[day_str][0] += tot_s_tokens
                p_daily[day_str][1] += c

                daily_all[day_str]["tokens"] += tot_s_tokens
                daily_all[day_str]["cost"] += c
                daily_all[day_str]["sessions"].add(s.session_id)
                daily_all[day_str]["bySource"][s.source] += c

                iso_ts = s.timestamp.isoformat()
                last_active = max(last_active or iso_ts, iso_ts)

                if s.event_timestamps:
                    all_timestamps.extend(s.event_timestamps)

            # Active hours calculation
            all_timestamps.sort()
            active_seconds = sum(min(b - a, IDLE_CAP_S) for a, b in zip(all_timestamps, all_timestamps[1:])) if len(all_timestamps) > 1 else 300
            for src in p_sources:
                by_source_all[src]["activeSeconds"] += active_seconds / len(p_sources)

            p_cost = sum(p_models.values())
            p_hit_rate = calculate_cache_hit_rate(p_tokens["input"], p_tokens["cacheWrite"], p_tokens["cacheRead"])
            top_source = max(p_by_source.keys(), key=lambda k: p_by_source[k]) if p_by_source else "claude-code"
            leak_th = (cache_thresholds or {}).get(top_source)
            has_leak, leak_reason = evaluate_cache_leak(top_source, p_cost, p_tokens["input"], p_tokens["cacheWrite"], p_tokens["cacheRead"], leak_th)

            top_model = p_models.most_common(1)[0][0] if p_models else "claude-sonnet-5-5"
            primary_fam = classify_family(top_model)

            # Compatible daily grid: [[date_str, tokens_int, cost_float], ...]
            daily_grid = [[d, p_daily[d][0], round(p_daily[d][1], 2)] for d in days_list]

            projects_out.append({
                "id": p_id,
                "name": p_alias,
                "sessions": len(sess_ids),
                "activeHours": round(active_seconds / 3600, 2),
                "tokens": {
                    "input": p_tokens["input"],
                    "output": p_tokens["output"],
                    "cacheWrite": p_tokens["cacheWrite"],
                    "cacheRead": p_tokens["cacheRead"]
                },
                "costUSD": round(p_cost, 2),
                "costSavedUSD": round(sum(self.pricing.compute_cache_savings(m, p_tokens["cacheRead"]) for m in p_models.keys()), 2),
                "cacheHitRate": p_hit_rate,
                "cacheLeak": has_leak,
                "cacheLeakReason": leak_reason,
                "toolCalls": sum(p_tools.values()),
                "topTools": p_tools.most_common(8),
                "models": {m: round(c, 2) for m, c in p_models.most_common()},
                "family": primary_fam,
                "sources": sorted(p_sources),
                "bySource": {src: round(amt, 2) for src, amt in p_by_source.items()},
                "daily": daily_grid,
                "lastActive": last_active
            })

        all_tokens = collections.Counter()
        for p in projects_out:
            all_tokens.update(p["tokens"])

        total_cost = sum(p["costUSD"] for p in projects_out)
        total_sessions = sum(p["sessions"] for p in projects_out)
        total_hours = sum(p["activeHours"] for p in projects_out)
        total_hit_rate = calculate_cache_hit_rate(all_tokens["input"], all_tokens["cacheWrite"], all_tokens["cacheRead"])

        by_source_out = {}
        for src, data in by_source_all.items():
            by_source_out[src] = {
                "costUSD": round(data["costUSD"], 2),
                "tokens": sum(data["tokens"].values()),
                "sessions": data["sessions"],
                "activeHours": round(data["activeSeconds"] / 3600, 2)
            }

        daily_out = []
        for d in days_list:
            day_data = daily_all[d]
            daily_out.append({
                "date": d,
                "tokens": day_data["tokens"],
                "costUSD": round(day_data["cost"], 2),
                "sessions": len(day_data["sessions"]),
                "bySource": {src: round(amt, 2) for src, amt in day_data["bySource"].items()}
            })

        return {
            "$schema": "./schema/v2.json",
            "version": "2.0.0",
            "mock": False,
            "generatedAt": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "rangeDays": range_days,
            "anonymized": anonymize,
            "sources": sorted(detected_sources),
            "totals": {
                "sessions": total_sessions,
                "activeHours": round(total_hours, 2),
                "tokens": dict(all_tokens),
                "costUSD": round(total_cost, 2),
                "costSavedUSD": round(total_saved_usd, 2),
                "cacheHitRate": total_hit_rate,
                "toolCalls": sum(tools_all.values()),
                "projects": len(projects_out),
                "bySource": by_source_out
            },
            "tools": tools_all.most_common(15),
            "models": [
                {"model": m, "tokens": v[0], "costUSD": round(v[1], 2), "source": v[2], "family": classify_family(m)}
                for m, v in sorted(models_all.items(), key=lambda kv: -kv[1][1])
            ],
            "daily": daily_out,
            "projects": projects_out
        }


def validate_schema_v2(payload: Dict[str, Any]) -> List[str]:
    """Pure stdlib validator verifying Schema v2 compliance without external dependencies."""
    errors = []
    required_top = ["$schema", "version", "generatedAt", "rangeDays", "anonymized", "sources", "totals", "tools", "models", "daily", "projects"]
    for k in required_top:
        if k not in payload:
            errors.append(f"Missing top-level key: {k}")

    # Check that NO absolute paths exist in the entire payload
    payload_str = json.dumps(payload)
    if re.search(r"/(?:Users|home)/[a-zA-Z0-9_-]+/", payload_str):
        errors.append("Privacy violation: Absolute user directory path detected in payload!")

    totals = payload.get("totals", {})
    for tk in ["sessions", "activeHours", "tokens", "costUSD", "costSavedUSD", "cacheHitRate", "projects"]:
        if tk not in totals:
            errors.append(f"Missing totals key: {tk}")

    for p in payload.get("projects", []):
        for pk in ["id", "name", "sessions", "tokens", "costUSD", "cacheHitRate", "daily", "sources"]:
            if pk not in p:
                errors.append(f"Project '{p.get('name')}' missing key: {pk}")
        # Verify daily format is compatible: list of 3-element tuples [date, tokens, cost]
        daily = p.get("daily", [])
        if daily and (not isinstance(daily[0], list) or len(daily[0]) != 3):
            errors.append(f"Project '{p.get('name')}' daily format must be [date, tokens, cost] array")

    return errors
