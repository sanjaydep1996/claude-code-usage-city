# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-10-23

### Added
- **Multi-Tool Observability Cockpit ("DevCity")**:
  - Pluggable collector architecture supporting multiple AI coding tools without external dependencies.
  - **Google Antigravity / Gemini CLI Collector** (`devcity/collectors/antigravity.py`): Ingests local transcript logs (`transcript.jsonl`), extracting token usage, Gemini models, tool invocations, and workspace basenames.
  - **Claude Code Collector** (`devcity/collectors/claude.py`): Enhanced port with incremental byte-offset indexing and prompt cache tracking.
- **Cache Efficiency & Leak Detector** (`devcity/efficiency.py`):
  - Calculates prompt cache hit rates (`cacheRead / (cacheRead + input + cacheWrite)`) and estimated USD saved by caching.
  - Configurable per-source cache leak thresholds (flags Claude Code hit rates below 75% on significant spend).
  - 3D visual beacon on the roof of leaky buildings with diagnostic breakdown in detail panel.
- **Multi-Tool Selector in 3D City** (`index.html`):
  - Segmented control to filter the 3D scene by tool (`All Tools`, `Claude Code`, `Antigravity`).
  - Dynamic KPI recalculation, daily chart updates, and tool call filtering.
- **Anonymized-by-Default Social Share Card Generator**:
  - One-click HTML5 Canvas generator producing a 1200x630 dark-glass social card.
  - Default masks project names and hides fine-grained timestamps to protect client confidentiality and working hours.
  - Includes instant "Download PNG" and "Copy to Clipboard" actions.
- **Accessible Table Mode**:
  - Keyboard-accessible semantic table drawer (`Alt+T` or header button) for screen reader users and low-motion environments.
- **Agent 1: Usage MCP Server** (`devcity/mcp_server.py`):
  - Read-only Model Context Protocol (MCP) server for Claude Code and Cursor.
  - Exposes `get_summary`, `get_project`, `get_daily`, `top_tools`, `check_budget`, and `compare_models`.
  - FastMCP integration with zero-dependency stdio JSON-RPC fallback.
- **Incremental SQLite Ingestion Cache** (`devcity/cache.py`):
  - Tracks `file_size`, `mtime`, and `byte_offset` for instant incremental scans; automatically detects truncated or rotated files.
- **Privacy & Security Assertion Suite** (`tests/test_privacy.py`):
  - Automated tests asserting that secret tokens, passwords, and code snippets fed via test fixtures NEVER leak into JSON outputs or SQLite storage.
  - Zero-absolute-path guarantee: only folder basenames are stored.
- **Packaging & Community Contributor Kit**:
  - `pyproject.toml` supporting `pipx run usage-city` or `pip install usage-city`.
  - `CONTRIBUTING.md` and `plugins/template_collector.py` (<50 LOC) for adding community tools.

### Changed
- Refactored `collect.py` into a thin backward-compatible wrapper delegating to `devcity.cli`.
- Updated `pricing.json` with Gemini models (`gemini-3.8-flash`, `gemini-2.5-pro`, `gemini-2.5-flash`), effective dates, and source attribution.
- Updated `data/sample-usage.json` to Schema v2 with multi-tool session distributions, model family colors, and cache leak demo buildings.

---

## [0.1.0] - 2026-10-22

### Added
- Initial release of Claude Code Usage City.
- Python stdlib collector (`collect.py`) for reading `~/.claude/projects/**/*.jsonl`.
- Interactive Three.js 3D city dashboard (`index.html`) with height metrics (Cost, Tokens, Hours), theme toggle, detail panel, and cost chart.
- Demo sample dataset (`data/sample-usage.json`) and GitHub Pages deployment.
