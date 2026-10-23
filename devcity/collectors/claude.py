"""Collector for Claude Code (~/.claude/projects/**/*.jsonl)."""

import collections
import datetime as dt
import json
import os
import pathlib
import re
from typing import List, Optional

from .base import BaseCollector, NormalizedSession
from ..cache import MetricsCache


def tool_label(name: str) -> str:
    m = re.match(r"mcp__([^_].*?)__(.+)", name or "")
    if m:
        return f"{m.group(1).replace('Claude_', '').replace('_', ' ')} · {m.group(2)}"
    return name or "?"


def project_basename_from_cwd(cwd: Optional[str]) -> str:
    if not cwd:
        return "unknown"
    if "scratch-workspaces" in cwd:
        return "scratch-sessions"
    p = pathlib.Path(cwd).name or cwd
    return p.strip() or "unknown"


class ClaudeCodeCollector(BaseCollector):
    id = "claude-code"
    name = "Claude Code"
    description = "Parses ~/.claude/projects/**/*.jsonl session logs."

    def __init__(self, root: Optional[pathlib.Path] = None, cache: Optional[MetricsCache] = None):
        self.root = pathlib.Path(root or os.path.expanduser("~/.claude/projects"))
        self.cache = cache

    def detect(self) -> bool:
        return self.root.exists() and any(self.root.rglob("*.jsonl"))

    def collect(self, since: dt.datetime, anonymize: bool = False) -> List[NormalizedSession]:
        if not self.root.exists():
            return []

        files = sorted(self.root.rglob("*.jsonl"))
        if not files:
            return []

        sessions_map = {}
        seen_keys = set()
        seen_tools = set()

        for f in files:
            try:
                start_offset = 0
                if self.cache:
                    start_offset = self.cache.get_file_offset(f)

                with open(f, "r", encoding="utf-8", errors="replace") as fh:
                    if start_offset > 0:
                        fh.seek(start_offset)

                    for line in fh:
                        if '"timestamp"' not in line:
                            continue
                        try:
                            d = json.loads(line)
                        except ValueError:
                            continue

                        ts = d.get("timestamp")
                        if not ts:
                            continue
                        try:
                            t = dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))
                        except Exception:
                            continue

                        if t < since:
                            continue

                        # Extract ONLY folder basename, never full path
                        proj = project_basename_from_cwd(d.get("cwd"))
                        sid = d.get("sessionId") or f.stem
                        key_sess = (proj, sid)

                        if key_sess not in sessions_map:
                            sessions_map[key_sess] = {
                                "project": proj,
                                "session_id": sid,
                                "first_time": t,
                                "timestamps": [],
                                "models": collections.Counter(),
                                "input_tokens": 0,
                                "output_tokens": 0,
                                "cache_write": 0,
                                "cache_read": 0,
                                "tools": collections.Counter(),
                            }

                        sess_data = sessions_map[key_sess]
                        sess_data["timestamps"].append(t.timestamp())

                        if d.get("type") != "assistant":
                            continue

                        msg = d.get("message") or {}
                        model = msg.get("model")
                        usage = msg.get("usage")
                        if not usage or not model or model.startswith("<"):
                            continue

                        # Extract tool calls (by tool_use id)
                        for c in msg.get("content") or []:
                            if isinstance(c, dict) and c.get("type") == "tool_use":
                                tid = c.get("id")
                                if tid not in seen_tools:
                                    seen_tools.add(tid)
                                    lbl = tool_label(c.get("name"))
                                    sess_data["tools"][lbl] += 1

                        # Deduplicate responses spanning several lines
                        req_key = (msg.get("id"), d.get("requestId"))
                        if req_key in seen_keys:
                            continue
                        seen_keys.add(req_key)

                        inp = usage.get("input_tokens") or 0
                        out = usage.get("output_tokens") or 0
                        cw = usage.get("cache_creation_input_tokens") or 0
                        cr = usage.get("cache_read_input_tokens") or 0

                        sess_data["input_tokens"] += inp
                        sess_data["output_tokens"] += out
                        sess_data["cache_write"] += cw
                        sess_data["cache_read"] += cr
                        sess_data["models"][model] += 1

                    if self.cache:
                        self.cache.update_file_offset(f, fh.tell())
            except Exception:
                continue

        results = []
        for (proj, sid), data in sessions_map.items():
            top_model = data["models"].most_common(1)[0][0] if data["models"] else "claude-sonnet-5-5"
            session = NormalizedSession(
                source=self.id,
                project_name=proj,
                session_id=sid,
                timestamp=data["first_time"],
                model=top_model,
                input_tokens=data["input_tokens"],
                output_tokens=data["output_tokens"],
                cache_write_tokens=data["cache_write"],
                cache_read_tokens=data["cache_read"],
                tool_calls=data["tools"],
                event_timestamps=sorted(data["timestamps"]),
            )
            results.append(session)

            if self.cache:
                self.cache.save_session(
                    source=self.id,
                    project_name=proj,
                    session_id=sid,
                    timestamp_iso=data["first_time"].isoformat(),
                    model=top_model,
                    input_tokens=data["input_tokens"],
                    output_tokens=data["output_tokens"],
                    cache_write_tokens=data["cache_write"],
                    cache_read_tokens=data["cache_read"],
                    tool_calls=dict(data["tools"]),
                    event_timestamps=sorted(data["timestamps"]),
                )

        return results
