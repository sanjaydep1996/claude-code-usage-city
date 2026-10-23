# DevCity · Personal AI Developer Cockpit

> Formerly *Claude Code Usage City*. Now evolving into an open-source, local-first **AI developer observability ecosystem**.

See where your AI coding time, tokens, and dollars actually go across your tools as an interactive 3D city. Every project is a building. Taller means more usage (switch between **cost**, **tokens**, **active hours**, and **prompt cache efficiency**), colour shows the main model family, and lit windows mean you worked on it in the last 3 days.

**[▶ Live Interactive Demo](https://sanjaydep1996.github.io/claude-code-usage-city/)** *(uses synthetic sample data)*

![DevCity 3D Cockpit](docs/screenshot-dark.png)

---

## What's New in v0.2

* **Multi-Tool Observability**: Out-of-the-box support for both **Claude Code** and **Google Antigravity / Gemini CLI**. Filter the 3D scene by tool or see a unified city.
* **Cache Leak Detector & Efficiency Warnings**:
  * Real-time prompt-cache hit rate telemetry.
  * Detects cache thrashing and context invalidation loops.
  * Leaky buildings pulse with an amber/red beacon on the roof and show diagnostic recovery tips in the detail panel.
* **Anonymized Social Share Card**:
  * Click **"📸 Share Card"** to generate a 1200x630 dark-glass social card of your AI city and stats.
  * Masked project names by default to protect employer and client repositories.
* **Accessible Table View**:
  * Screen-reader friendly semantic table view (`📋 Table` button or `Alt+T`) with keyboard navigation.
* **Agent 1: Usage MCP Server**:
  * Query your personal usage directly from within Claude Code or Cursor.

---

## Quickstart

No dependencies required: runs on standard Python 3.9+ and a single static HTML file with Three.js via ES modules.

```bash
git clone https://github.com/sanjaydep1996/claude-code-usage-city.git
cd claude-code-usage-city

# Index your local Claude Code & Antigravity sessions:
python3 collect.py

# Launch the dashboard:
python3 collect.py --serve
# then open http://localhost:8000
```

Without local data, the dashboard displays rich synthetic sample data. Append `?sample` to the URL to view sample data anytime.

### CLI Options

| Flag | Description |
| :--- | :--- |
| `--days 90` | Look back 90 days instead of 30 |
| `--anonymize` | Replace project folder names with "Project A", "Project B"... |
| `--source claude` | Filter collection to `claude`, `antigravity`, or `all` |
| `--serve [8000]` | Start local web server and open the browser |
| `--no-cache` | Bypass the incremental SQLite cache and re-index all files |

---

## Usage MCP Server (Agent 1)

DevCity includes a read-only Model Context Protocol (MCP) server exposing tools like `get_summary`, `get_project`, `get_daily`, `top_tools`, `check_budget`, and `compare_models`.

### In Claude Code
```bash
claude mcp add usage-city python3 -m devcity.mcp_server
```

### In Cursor (`~/.cursor/mcp.json`)
```json
{
  "mcpServers": {
    "usage-city": {
      "command": "python3",
      "args": ["-m", "devcity.mcp_server"]
    }
  }
}
```

---

## Privacy & Safety Contract

1. **Zero Text Ingestion**: Prompts, assistant replies, source code, and diffs are discarded at parse time. Only token integers, timestamps, model IDs, and tool names are retained.
2. **Zero Absolute Paths**: Only folder basenames are stored. User home directories, usernames, and git remotes are never collected.
3. **100% Local & Offline**: Zero network calls, telemetry pings, or cloud phone-home calls.
4. **Automated Privacy Tests**: `tests/test_privacy.py` continuously asserts that sensitive tokens (`sk-...`, passwords) never leak into output JSON or SQLite tables.

---

## Contributing a New Tool Collector

We welcome community collectors!
1. Check `plugins/template_collector.py` for a clean `<50` line template.
2. Implement your collector inheriting from `devcity.collectors.base.BaseCollector`.
3. Read [CONTRIBUTING.md](CONTRIBUTING.md) for privacy guidelines and test instructions.

---

## Licence

[MIT](LICENSE)
