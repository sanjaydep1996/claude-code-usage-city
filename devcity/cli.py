"""Command line interface for DevCity (Personal AI Developer Cockpit & Companion)."""

import argparse
import datetime as dt
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
from .guide.advisor import ToolAdvisor
from .guide.playbooks import load_playbook, list_playbooks
from .guard.audit import RepoAuditor
from .guard.hooks import install_git_hook, install_claude_hook
from .prove.report import write_report_file, generate_markdown_report
from .prove.health import calculate_health_score


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="devcity",
        description="DevCity v3.0: The Local-First Companion for Software Engineering with AI (Monitor · Guide · Guard · Prove)",
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
    p.add_argument("--report", action="store_true", default=True, help="Auto-generate DEVCITY_REPORT.md after collection (default: True)")

    # Subcommands or positional action
    p.add_argument(
        "command",
        nargs="?",
        choices=["collect", "advisor", "playbook", "audit", "report", "hook", "serve", "mcp"],
        default="collect",
        help="Command to run"
    )

    # Extra arguments for subcommands
    p.add_argument("extra", nargs="*", help="Additional arguments for subcommands (e.g. playbook name, audit path)")
    p.add_argument("--task", default="api_endpoint", help="Task type for advisor (e.g. scaffold, api_endpoint, ui_component, regex_grep)")
    p.add_argument("--size", choices=["quick", "medium", "complex"], default="medium", help="Task size for advisor")
    p.add_argument("--domain", default="fullstack", help="Technical domain (frontend, backend, database, devops)")
    p.add_argument("--step", type=int, help="Specific step number for playbook")

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
    print(f"DevCity v3.0.0: Scanning AI developer activity (last {args.days} days)...")
    if not active_collectors:
        print(f"  Note: No active logs found at default paths.")
        print(f"  Checked: Claude Code ({claude_root}), Antigravity ({antigravity_root})")

    all_sessions = []
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

    val_errors = validate_schema_v2(payload)
    if val_errors:
        print(f"Validation warnings: {val_errors}", file=sys.stderr)

    out_path = pathlib.Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=1), encoding="utf-8")

    t = payload["totals"]
    total_tokens = sum(t["tokens"].values())
    leaks = [p for p in payload["projects"] if p.get("cacheLeak")]
    health = calculate_health_score(payload)

    print(f"\n📊 DevCity Observability Summary:")
    print(f"  • Projects: {t['projects']} ({', '.join(payload['sources']) if payload['sources'] else 'None'})")
    print(f"  • Sessions: {t['sessions']} · Active Hours: {t['activeHours']}h")
    print(f"  • Total Tokens: {total_tokens:,} · API Cost: ~${t['costUSD']:,.2f}")
    print(f"  • Cache Hit Rate: {round(t['cacheHitRate']*100, 1)}% (Saved: ~${t['costSavedUSD']:,.2f})")
    print(f"  • AI Health Score: {health.grade} ({health.score}/100)")
    if leaks:
        print(f"  ⚠️  Cache Leak Alerts ({len(leaks)}): {', '.join(p['name'] for p in leaks)}")

    if args.report:
        report_file = write_report_file(payload)
        print(f"  📝 Generated Value Report: {report_file}")

    if args.serve or args.command == "serve":
        port = args.serve if isinstance(args.serve, int) else 8000
        serve_dashboard(port)

    return 0


def run_advisor(args: argparse.Namespace) -> int:
    advisor = ToolAdvisor()
    task = args.task or (args.extra[0] if args.extra else "api_endpoint")
    rec = advisor.recommend(task_type=task, size=args.size, domain=args.domain)

    print(f"\n🧭 DevCity Tool & Model Advisor")
    print(f"Task: {rec.task_type} ({rec.size} / {rec.domain})")
    print(f"  • Recommended Tool:  {rec.recommended_tool}")
    print(f"  • Primary Model:     {rec.recommended_model}")
    print(f"  • Fallback / Eco:    {rec.fallback_model}")
    print(f"  • Token Budget Est:  {rec.token_budget_est} (~{rec.cost_est_usd})")
    print(f"  • Effort Tier:       {rec.effort_tier}")
    print(f"\n💡 Rationale:\n  {rec.rationale}")
    if rec.caveats:
        print(f"\n⚠️ Caveats:\n  {rec.caveats}")
    return 0


def run_playbook(args: argparse.Namespace) -> int:
    name = args.extra[0] if args.extra else "react-springboot-postgres"
    pb = load_playbook(name)
    if not pb:
        available = list_playbooks()
        print(f"Playbook '{name}' not found. Available playbooks: {', '.join(available) or 'None'}")
        return 1

    print(f"\n📖 DevCity Playbook: {pb.title}")
    if pb.overview:
        print(f"{pb.overview}\n")

    step_filter = args.step
    for s in pb.steps:
        if step_filter and s.step_number != step_filter:
            continue
        print(f"─── Step {s.step_number}: {s.title} ───")
        print(f"Goal: {s.goal}")
        print(f"Tool & Model: {s.ai_tool_model}")
        print(f"Why: {s.why}")
        if s.prompt_template:
            print(f"\nPrompt Template:\n```\n{s.prompt_template}\n```")
        if s.checklist:
            print("\nChecklist:")
            for item in s.checklist:
                print(f"  [ ] {item}")
        if s.common_mistakes:
            print(f"\nCommon Pitfalls: {s.common_mistakes}\n")
    return 0


def run_audit(args: argparse.Namespace) -> int:
    target = args.extra[0] if args.extra else "."
    auditor = RepoAuditor(pathlib.Path(target))
    res = auditor.audit()

    print(f"\n🛡️ DevCity Repo AI-Readiness Audit: {res.target_path}")
    print(f"Score: {res.score}/100 · Grade: {res.grade}")
    print(f"Stats: {res.stats.get('instruction_files', [])} | Large files: {res.stats.get('large_files_count', 0)}")

    if not res.findings:
        print("  ✅ Excellent! Repository is fully optimized for AI coding tools.")
    else:
        print(f"\nFindings ({len(res.findings)}):")
        for f in res.findings:
            icon = "❌" if f.severity == "danger" else "⚠️" if f.severity == "warning" else "ℹ️"
            print(f"  {icon} [{f.category}] {f.title}")
            print(f"     Why: {f.description}")
            print(f"     Fix: {f.remediation}")
            if f.tokens_wasted_per_prompt_est > 0:
                print(f"     Est. token waste: ~{f.tokens_wasted_per_prompt_est:,} tokens / prompt")
    return 0


def run_report(args: argparse.Namespace) -> int:
    usage_path = pathlib.Path(args.out)
    if not usage_path.exists():
        # Try sample
        usage_path = pathlib.Path("data/sample-usage.json")
    if not usage_path.exists():
        print("No usage data found. Run `devcity collect` first.")
        return 1

    payload = json.loads(usage_path.read_text(encoding="utf-8"))
    out_file = args.extra[0] if args.extra else "DEVCITY_REPORT.md"
    written = write_report_file(payload, out_file)
    print(f"Wrote executive value report to {written}")
    return 0


def run_hook(args: argparse.Namespace) -> int:
    action = args.extra[0] if args.extra else "install"
    if action == "install":
        ok1, msg1 = install_git_hook()
        print(f"  • {msg1}")
        ok2, msg2 = install_claude_hook()
        print(f"  • {msg2}")
        return 0 if (ok1 or ok2) else 1
    else:
        print(f"Unknown hook action: {action}. Use `devcity hook install`.")
        return 1


def serve_dashboard(port: int = 8000):
    print(f"\nServing DevCity 3D cockpit on http://localhost:{port} (Ctrl+C to stop)...")
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
    elif args.command == "advisor":
        return run_advisor(args)
    elif args.command == "playbook":
        return run_playbook(args)
    elif args.command == "audit":
        return run_audit(args)
    elif args.command == "report":
        return run_report(args)
    elif args.command == "hook":
        return run_hook(args)
    elif args.command == "serve":
        return serve_dashboard(args.serve or 8000)
    else:
        return run_collection(args)


if __name__ == "__main__":
    sys.exit(main())
