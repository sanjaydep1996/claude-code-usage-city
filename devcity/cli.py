"""Command line interface for DevCity."""

import argparse
import http.server
import json
import os
import pathlib
import sys
import webbrowser
from typing import List, Optional

from .pricing import PricingCalculator, load_pricing
from .cache import MetricsCache
from .collectors.claude import ClaudeCodeCollector
from .collectors.antigravity import AntigravityCollector
from .engine import AggregationEngine, validate_schema_v2


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="usage-city",
        description="DevCity: Personal AI Developer Cockpit & Observability Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--days", type=int, default=30, help="Look back N days (default: 30)")
    p.add_argument("--anonymize", action="store_true", help="Mask project names to Project A, Project B...")
    p.add_argument("--source", choices=["all", "claude", "antigravity"], default="all", help="Collect from specific source")
    p.add_argument("--root", help="Custom path for Claude Code sessions (backward compatibility)")
    p.add_argument("--claude-root", help="Custom path for Claude Code sessions")
    p.add_argument("--antigravity-root", help="Custom path for Antigravity sessions")
    p.add_argument("--out", default="data/usage.json", help="Path to write usage.json (default: data/usage.json)")
    p.add_argument("--no-cache", action="store_true", help="Bypass SQLite incremental cache")
    p.add_argument("--serve", nargs="?", const=8000, type=int, help="Serve dashboard locally on specified port (default: 8000)")
    p.add_argument("--claude-cache-threshold", type=float, default=0.75, help="Cache leak hit-rate threshold for Claude Code (default: 0.75)")
    p.add_argument("command", nargs="?", choices=["collect", "mcp", "serve"], default="collect", help="Command to run")
    return p.parse_args(args)


def run_collection(args: argparse.Namespace) -> int:
    pricing = PricingCalculator(load_pricing())
    cache = None if args.no_cache else MetricsCache()

    claude_root = pathlib.Path(args.claude_root or args.root or os.path.expanduser("~/.claude/projects"))
    antigravity_root = pathlib.Path(args.antigravity_root or os.path.expanduser("~/.gemini/antigravity/brain"))

    collectors = []
    if args.source in ("all", "claude"):
        collectors.append(ClaudeCodeCollector(root=claude_root, cache=cache))
    if args.source in ("all", "antigravity"):
        collectors.append(AntigravityCollector(root=antigravity_root, cache=cache))

    active_collectors = [c for c in collectors if c.detect()]
    print(f"DevCity v0.2.0: Scanning AI developer activity (last {args.days} days)...")
    if not active_collectors:
        print(f"  Note: No active logs found at default paths.")
        print(f"  Checked: Claude Code ({claude_root}), Antigravity ({antigravity_root})")

    all_sessions = []
    since = None  # engine will filter by range_days
    import datetime as dt
    since_dt = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=args.days)

    for c in active_collectors:
        try:
            sess = c.collect(since=since_dt, anonymize=args.anonymize)
            all_sessions.extend(sess)
            print(f"  ✓ {c.name}: {len(sess)} sessions collected")
        except Exception as e:
            print(f"  ! {c.name} error: {e}")

    engine = AggregationEngine(pricing_calc=pricing)
    thresholds = {"claude-code": args.claude_cache_threshold}
    payload = engine.aggregate(
        sessions=all_sessions,
        range_days=args.days,
        anonymize=args.anonymize,
        cache_thresholds=thresholds
    )

    # Validate output
    val_errors = validate_schema_v2(payload)
    if val_errors:
        print(f"Validation warnings: {val_errors}", file=sys.stderr)

    out_path = pathlib.Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=1), encoding="utf-8")

    t = payload["totals"]
    total_tokens = sum(t["tokens"].values())
    leaks = [p for p in payload["projects"] if p.get("cacheLeak")]

    print(f"\nWrote {out_path}:")
    print(f"  • Projects: {t['projects']} ({', '.join(payload['sources']) if payload['sources'] else 'None'})")
    print(f"  • Sessions: {t['sessions']} · Active Hours: {t['activeHours']}h")
    print(f"  • Total Tokens: {total_tokens:,} · API Cost: ~${t['costUSD']:,.2f}")
    print(f"  • Cache Hit Rate: {round(t['cacheHitRate']*100, 1)}% (Saved: ~${t['costSavedUSD']:,.2f})")
    if leaks:
        print(f"  ⚠️  Cache Leak Alerts ({len(leaks)}): {', '.join(p['name'] for p in leaks)}")

    if args.serve or args.command == "serve":
        port = args.serve if isinstance(args.serve, int) else 8000
        serve_dashboard(port)

    return 0


def serve_dashboard(port: int = 8000):
    print(f"\nServing DevCity 3D dashboard on http://localhost:{port} (Ctrl+C to stop)...")
    webbrowser.open(f"http://localhost:{port}")
    server = http.server.ThreadingHTTPServer(("", port), http.server.SimpleHTTPRequestHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    if args.command == "mcp":
        from .mcp_server import run_mcp_server
        return run_mcp_server()
    elif args.command == "serve":
        return serve_dashboard(args.serve or 8000)
    else:
        return run_collection(args)


if __name__ == "__main__":
    sys.exit(main())
