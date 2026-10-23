"""Usage MCP Server for DevCity (Agent 1).

Exposes read-only telemetry tools for Claude Code, Cursor, and any MCP client:
  - get_summary(days)
  - get_project(project_identifier, days)
  - get_daily(days)
  - top_tools(limit, days)
  - check_budget(daily_limit_usd)
  - compare_models(days)

Never returns file paths or raw transcript text.
"""

import datetime as dt
import json
import os
import pathlib
import sys
from typing import Dict, Any, List, Optional


def load_aggregated_data(json_path: Optional[pathlib.Path] = None) -> Dict[str, Any]:
    """Loads aggregated metrics from usage.json or sample-usage.json."""
    candidates = [
        json_path,
        pathlib.Path("data/usage.json"),
        pathlib.Path(__file__).resolve().parent.parent / "data" / "usage.json",
        pathlib.Path("data/sample-usage.json"),
        pathlib.Path(__file__).resolve().parent.parent / "data" / "sample-usage.json"
    ]
    for p in candidates:
        if p and p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
    return {}


# Tool implementations (pure Python functions returning dicts)
def get_summary(days: int = 30) -> Dict[str, Any]:
    data = load_aggregated_data()
    if not data or "totals" not in data:
        return {"status": "empty", "message": "No local usage data found. Run 'usage-city' or 'python3 collect.py' to generate your local metrics."}

    totals = data["totals"]
    return {
        "status": "success",
        "time_range_days": days,
        "total_spend_usd": totals.get("costUSD", 0.0),
        "cost_saved_caching_usd": totals.get("costSavedUSD", 0.0),
        "cache_hit_rate": totals.get("cacheHitRate", 0.0),
        "active_hours": totals.get("activeHours", 0.0),
        "total_sessions": totals.get("sessions", 0),
        "total_tool_calls": totals.get("toolCalls", 0),
        "total_tokens": totals.get("tokens", {}),
        "sources": data.get("sources", []),
        "by_source": totals.get("bySource", {})
    }


def get_project(project_identifier: str, days: int = 30) -> Dict[str, Any]:
    data = load_aggregated_data()
    projects = data.get("projects", [])
    if not projects:
        return {"status": "empty", "message": "No project records found."}

    target = project_identifier.lower().strip()
    match = None
    for p in projects:
        if p.get("id", "").lower() == target or p.get("name", "").lower() == target:
            match = p
            break

    if not match:
        available = [p.get("name") for p in projects[:10]]
        return {
            "status": "not_found",
            "message": f"Project '{project_identifier}' not found.",
            "available_projects": available
        }

    return {
        "status": "success",
        "project": match.get("name"),
        "spend_usd": match.get("costUSD", 0.0),
        "tokens": sum(match.get("tokens", {}).values()),
        "active_hours": match.get("activeHours", 0.0),
        "sessions": match.get("sessions", 0),
        "cache_hit_rate": match.get("cacheHitRate", 0.0),
        "cache_leak_detected": match.get("cacheLeak", False),
        "cache_leak_reason": match.get("cacheLeakReason"),
        "primary_model": list(match.get("models", {}).keys())[0] if match.get("models") else "unknown",
        "sources": match.get("sources", []),
        "top_tools": match.get("topTools", [])
    }


def get_daily(days: int = 14) -> Dict[str, Any]:
    data = load_aggregated_data()
    daily_records = data.get("daily", [])
    if not daily_records:
        return {"status": "empty", "message": "No daily records found."}

    # Slice requested recent days
    recent = daily_records[-days:] if len(daily_records) > days else daily_records
    return {
        "status": "success",
        "days_requested": days,
        "daily_totals": recent
    }


def top_tools(limit: int = 10, days: int = 30) -> Dict[str, Any]:
    data = load_aggregated_data()
    tools = data.get("tools", [])
    if not tools:
        return {"status": "empty", "message": "No tool data found."}

    formatted = [{"tool": t[0], "invocations": t[1]} for t in tools[:limit]]
    return {
        "status": "success",
        "top_tools": formatted
    }


def check_budget(daily_limit_usd: float = 10.0) -> Dict[str, Any]:
    data = load_aggregated_data()
    daily_records = data.get("daily", [])
    today_str = dt.date.today().isoformat()

    today_spend = 0.0
    for d in daily_records:
        if d.get("date") == today_str:
            today_spend = d.get("costUSD", 0.0)
            break
    if today_spend == 0.0 and daily_records:
        # Fall back to latest day recorded if today has not closed
        today_spend = daily_records[-1].get("costUSD", 0.0)
        today_str = daily_records[-1].get("date", today_str)

    rem = round(max(0.0, daily_limit_usd - today_spend), 2)
    pct = round((today_spend / daily_limit_usd * 100), 1) if daily_limit_usd > 0 else 100.0

    status = "OK"
    if today_spend >= daily_limit_usd:
        status = "EXCEEDED"
    elif pct >= 80.0:
        status = "WARNING"

    return {
        "status": status,
        "date": today_str,
        "daily_limit_usd": float(daily_limit_usd),
        "today_spend_usd": float(today_spend),
        "remaining_usd": rem,
        "percent_utilized": pct
    }


def compare_models(days: int = 30) -> Dict[str, Any]:
    data = load_aggregated_data()
    models = data.get("models", [])
    return {
        "status": "success",
        "models": models
    }


def run_mcp_server() -> int:
    """Runs the MCP server over stdio."""
    try:
        from mcp.server.fastmcp import FastMCP
        mcp = FastMCP("usage-city")

        @mcp.tool()
        def mcp_get_summary(days: int = 30) -> str:
            """Get high-level AI usage summary including total spend, tokens, hours, and cache efficiency."""
            return json.dumps(get_summary(days))

        @mcp.tool()
        def mcp_get_project(project_identifier: str, days: int = 30) -> str:
            """Get usage details, tools, and models for a specific project folder basename."""
            return json.dumps(get_project(project_identifier, days))

        @mcp.tool()
        def mcp_get_daily(days: int = 14) -> str:
            """Get recent day-by-day AI token and dollar spend trends."""
            return json.dumps(get_daily(days))

        @mcp.tool()
        def mcp_top_tools(limit: int = 10, days: int = 30) -> str:
            """Get most frequently called tools and MCP integrations."""
            return json.dumps(top_tools(limit, days))

        @mcp.tool()
        def mcp_check_budget(daily_limit_usd: float = 10.0) -> str:
            """Check today's AI spend against a daily dollar budget."""
            return json.dumps(check_budget(daily_limit_usd))

        @mcp.tool()
        def mcp_compare_models(days: int = 30) -> str:
            """Compare token distribution and costs across Claude, Gemini, and other models."""
            return json.dumps(compare_models(days))

        mcp.run(transport="stdio")
        return 0
    except ImportError:
        # Lightweight zero-dependency stdio JSON-RPC fallback
        return run_stdio_jsonrpc_fallback()


def run_stdio_jsonrpc_fallback() -> int:
    """Lightweight stdio JSON-RPC 2.0 dispatcher for environments without mcp package."""
    tools_map = {
        "get_summary": get_summary,
        "get_project": get_project,
        "get_daily": get_daily,
        "top_tools": top_tools,
        "check_budget": check_budget,
        "compare_models": compare_models
    }

    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            req = json.loads(line)
            req_id = req.get("id")
            method = req.get("method")
            params = req.get("params", {})

            if method == "initialize":
                res = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "serverInfo": {"name": "usage-city", "version": "0.2.0"},
                        "capabilities": {"tools": {}}
                    }
                }
            elif method == "tools/list":
                tools_desc = [
                    {"name": "get_summary", "description": "Get high-level AI usage summary", "inputSchema": {"type": "object", "properties": {"days": {"type": "integer"}}}},
                    {"name": "get_project", "description": "Get project usage details", "inputSchema": {"type": "object", "properties": {"project_identifier": {"type": "string"}, "days": {"type": "integer"}}, "required": ["project_identifier"]}},
                    {"name": "get_daily", "description": "Get daily spend and token trends", "inputSchema": {"type": "object", "properties": {"days": {"type": "integer"}}}},
                    {"name": "top_tools", "description": "Get top tool invocations", "inputSchema": {"type": "object", "properties": {"limit": {"type": "integer"}, "days": {"type": "integer"}}}},
                    {"name": "check_budget", "description": "Check spend against a daily dollar budget", "inputSchema": {"type": "object", "properties": {"daily_limit_usd": {"type": "number"}}, "required": ["daily_limit_usd"]}},
                    {"name": "compare_models", "description": "Compare model token distribution and spend", "inputSchema": {"type": "object", "properties": {"days": {"type": "integer"}}}}
                ]
                res = {"jsonrpc": "2.0", "id": req_id, "result": {"tools": tools_desc}}
            elif method == "tools/call":
                tname = params.get("name")
                targs = params.get("arguments", {})
                if tname in tools_map:
                    out = tools_map[tname](**targs)
                    res = {"jsonrpc": "2.0", "id": req_id, "result": {"content": [{"type": "text", "text": json.dumps(out)}]}}
                else:
                    res = {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Method {tname} not found"}}
            else:
                res = {"jsonrpc": "2.0", "id": req_id, "result": {}}

            sys.stdout.write(json.dumps(res) + "\n")
            sys.stdout.flush()
        except Exception as e:
            err = {"jsonrpc": "2.0", "id": None, "error": {"code": -32603, "message": str(e)}}
            sys.stdout.write(json.dumps(err) + "\n")
            sys.stdout.flush()

    return 0


if __name__ == "__main__":
    sys.exit(run_mcp_server())
