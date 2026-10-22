#!/usr/bin/env python3
"""Summarise your local Claude Code sessions into data/usage.json for the Usage City dashboard.

Reads ~/.claude/projects/**/*.jsonl on THIS machine. Writes totals only: token counts, tool names,
models, timestamps per day and per project. It never copies prompts, replies, code or file contents,
and it never sends anything anywhere.

    python3 collect.py                    # last 30 days
    python3 collect.py --days 90
    python3 collect.py --anonymize        # replace project names with "Project A", "Project B", ...
    python3 collect.py --root /path/to/.claude/projects --out data/usage.json
"""
import argparse, collections, datetime as dt, json, os, pathlib, re, sys

HERE = pathlib.Path(__file__).resolve().parent
IDLE_CAP_S = 5 * 60   # gaps longer than this between events don't count as active time


def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--root", default=os.path.expanduser("~/.claude/projects"))
    p.add_argument("--days", type=int, default=30)
    p.add_argument("--out", default=str(HERE / "data" / "usage.json"))
    p.add_argument("--anonymize", action="store_true", help="hide real project names")
    return p.parse_args()


def load_pricing():
    p = json.loads((HERE / "pricing.json").read_text())
    def rates(model):
        r = p["models"].get(model) or p["fallback"]
        return (r["input"], r["output"], r.get("cacheWrite", r["input"] * 1.25), r.get("cacheRead", r["input"] * 0.1))
    return rates, p.get("fastMultiplier", 1)


def project_name(cwd):
    if not cwd: return "unknown"
    if "scratch-workspaces" in cwd: return "Scratch sessions"
    return pathlib.Path(cwd).name or cwd


def tool_label(name):
    m = re.match(r"mcp__([^_].*?)__(.+)", name or "")
    if m: return f"{m.group(1).replace('Claude_', '').replace('_', ' ')} · {m.group(2)}"
    return name or "?"


def family(model):
    for f in ("fable", "mythos", "opus", "sonnet", "haiku"):
        if f in (model or ""): return f
    return "other"


def main():
    a = parse_args()
    rates, fast_mult = load_pricing()
    since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=a.days)
    files = sorted(pathlib.Path(a.root).rglob("*.jsonl"))
    if not files: sys.exit(f"No session files under {a.root}")

    seen, seen_tools = set(), set()   # responses span several lines and forked sessions copy history; count each once
    P = collections.defaultdict(lambda: {"sessions": set(), "tokens": collections.Counter(), "cost": 0.0, "tools": collections.Counter(),
                                          "models": collections.Counter(), "daily": collections.defaultdict(lambda: [0, 0.0]), "last": None})
    sess_times = collections.defaultdict(list)   # (project, session) -> [timestamps]
    daily = collections.defaultdict(lambda: {"tokens": 0, "cost": 0.0, "sessions": set()})
    tools_all, models_all = collections.Counter(), collections.defaultdict(lambda: [0, 0.0])

    for i, f in enumerate(files):
        if i % 25 == 0 or i == len(files) - 1: print(f"\r reading {i + 1}/{len(files)}", end="", file=sys.stderr, flush=True)
        with open(f, errors="replace") as fh:
            for line in fh:
                if '"timestamp"' not in line: continue
                try: d = json.loads(line)
                except ValueError: continue
                ts = d.get("timestamp")
                if not ts: continue
                t = dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))
                if t < since: continue
                proj, sid = project_name(d.get("cwd")), d.get("sessionId") or f.stem
                sess_times[(proj, sid)].append(t.timestamp())
                if d.get("type") != "assistant": continue
                m = d.get("message") or {}
                model, u = m.get("model"), m.get("usage")
                if not u or not model or model.startswith("<"): continue
                for c in m.get("content") or []:   # tool calls: one per content block, may sit on any line of the response
                    if isinstance(c, dict) and c.get("type") == "tool_use" and c.get("id") not in seen_tools:
                        seen_tools.add(c.get("id")); lbl = tool_label(c.get("name"))
                        P[proj]["tools"][lbl] += 1; tools_all[lbl] += 1
                key = (m.get("id"), d.get("requestId"))   # usage repeats on every line of one response: count it once
                if key in seen: continue
                seen.add(key)
                ri, ro, rw, rr = rates(model)
                tk = {"input": u.get("input_tokens") or 0, "output": u.get("output_tokens") or 0,
                      "cacheWrite": u.get("cache_creation_input_tokens") or 0, "cacheRead": u.get("cache_read_input_tokens") or 0}
                cost = (tk["input"] * ri + tk["output"] * ro + tk["cacheWrite"] * rw + tk["cacheRead"] * rr) / 1e6
                if u.get("speed") == "fast": cost *= fast_mult
                total = sum(tk.values()); day = t.astimezone().date().isoformat()
                p = P[proj]
                p["sessions"].add(sid); p["tokens"].update(tk); p["cost"] += cost; p["models"][model] += cost
                p["daily"][day][0] += total; p["daily"][day][1] += cost
                p["last"] = max(p["last"] or ts, ts)
                daily[day]["tokens"] += total; daily[day]["cost"] += cost; daily[day]["sessions"].add(sid)
                models_all[model][0] += total; models_all[model][1] += cost
    print(file=sys.stderr)

    active = collections.Counter()
    for (proj, _), times in sess_times.items():
        times.sort(); active[proj] += sum(min(b - a, IDLE_CAP_S) for a, b in zip(times, times[1:]))

    names = sorted(P, key=lambda k: -P[k]["cost"])
    alias = {n: (f"Project {chr(65 + i)}" if i < 26 else f"Project {i + 1}") for i, n in enumerate(names)} if a.anonymize else {n: n for n in names}
    days = [(dt.date.today() - dt.timedelta(days=i)).isoformat() for i in range(min(a.days, 30) - 1, -1, -1)]
    r2 = lambda x: round(x, 2)

    projects = []
    for n in names:
        p = P[n]; tok = dict(p["tokens"])
        projects.append({
            "id": re.sub(r"[^a-z0-9]+", "-", alias[n].lower()).strip("-"), "name": alias[n],
            "sessions": len(p["sessions"]), "activeHours": r2(active[n] / 3600),
            "tokens": {k: tok.get(k, 0) for k in ("input", "output", "cacheWrite", "cacheRead")},
            "costUSD": r2(p["cost"]), "toolCalls": sum(p["tools"].values()),
            "topTools": p["tools"].most_common(8),
            "models": {m: r2(c) for m, c in p["models"].most_common()},
            "family": family(p["models"].most_common(1)[0][0]) if p["models"] else "other",
            "daily": [[d, p["daily"][d][0], r2(p["daily"][d][1])] for d in days],
            "lastActive": p["last"],
        })
    T = collections.Counter()
    for p in projects: T.update(p["tokens"])
    out = {
        "mock": False, "generatedAt": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "rangeDays": a.days, "anonymized": a.anonymize,
        "totals": {"sessions": sum(p["sessions"] for p in projects), "activeHours": r2(sum(p["activeHours"] for p in projects)),
                   "tokens": dict(T), "costUSD": r2(sum(p["costUSD"] for p in projects)), "toolCalls": sum(tools_all.values()),
                   "projects": len(projects)},
        "tools": tools_all.most_common(15),
        "models": [{"model": m, "tokens": v[0], "costUSD": r2(v[1])} for m, v in sorted(models_all.items(), key=lambda kv: -kv[1][1])],
        "daily": [{"date": d, "tokens": daily[d]["tokens"], "costUSD": r2(daily[d]["cost"]), "sessions": len(daily[d]["sessions"])} for d in days],
        "projects": projects,
    }
    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(a.out).write_text(json.dumps(out, indent=1))
    t = out["totals"]
    print(f"Wrote {a.out}: {t['projects']} projects, {t['sessions']} sessions, {sum(t['tokens'].values()):,} tokens, "
          f"~${t['costUSD']:,.2f} API-equivalent, {t['activeHours']} active hours")


if __name__ == "__main__":
    main()
