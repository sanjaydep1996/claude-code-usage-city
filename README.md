# DevCity · Personal AI Developer Cockpit & Companion

> **The local-first companion for software engineering with AI — from first prompt to production.**  
> Monitor your spend · Guide your tool choices · Guard against risks & leaks · Prove your AI ROI.

**[▶ Open Live Interactive Demo (Two Cities)](https://sanjaydep1996.github.io/claude-code-usage-city/)** *(runs 100% in-browser with synthetic sample data)*

![DevCity 3D Cockpit](docs/screenshot-dark.png)

---

## 🌟 The Four Pillars of DevCity

DevCity brings together everything developers and engineering teams need to use AI coding tools effectively:

| Pillar | Focus | What DevCity Provides |
| :--- | :--- | :--- |
| **🏙️ MONITOR** | Observability & Telemetry | Interactive 3D campus visualizer, session tracking, multi-tool aggregation (Claude Code + Antigravity), and prompt cache leak detection. |
| **🧭 GUIDE** | Best Practices & Architecture | Deterministic Tool & Model Advisor, production playbooks (React + Spring Boot + Postgres), prompt templates, and habit coaching. |
| **🛡️ GUARD** | Risk Prevention & Safety | Repo AI-Readiness Audit (`devcity audit`), local pre-commit secret scanner, destructive migration gates, and budget thresholds. |
| **📈 PROVE** | ROI & Executive Value | Headline savings numbers ("Prompt caching saved $242.60 this month"), Weekly AI Health Grade (A–F), and executive Markdown reports. |

---

## 🏙️ Two Cities in One Cockpit (Live Demo)

In the [Live Demo](https://sanjaydep1996.github.io/claude-code-usage-city/), use the top campus switcher to toggle between two complete 3D environments:
1. **🏙️ Observability City:** Each skyscraper represents an active project you worked on. Height reflects API spend, tokens, hours, or cache efficiency; glowing beacons highlight prompt cache leaks; click any building to enter the interior room cutaway.
2. **🏗️ Developer Builder City:** 8 specialized architect pavilions representing the 8 steps of building an enterprise full-stack feature (System Spec, DB Foundry, Backend APIs, Frontend UI, Test QA, Security Gate, Deploy Tower, ROI Citadel). Click any pavilion to get model recommendations, tested copyable prompt templates, and pre-flight checklists!

---

## 🚀 Quickstart

DevCity requires **zero dependencies** beyond Python 3.9+ and modern browser standards (Three.js via CDN). Zero npm installs, zero builds.

```bash
git clone https://github.com/sanjaydep1996/claude-code-usage-city.git devcity
cd devcity

# 1. Index your local AI developer activity (Claude Code & Antigravity):
python3 -m devcity.cli collect

# 2. Launch the 3D Cockpit:
python3 -m devcity.cli serve
# Open http://localhost:8000
```

---

## 🛠️ CLI Toolkit Commands

### 1. Tool & Model Advisor (`devcity advisor`)
Get objective, dated model recommendations and token budget estimates based on task type:
```bash
devcity advisor --task api_endpoint --size medium --domain backend
devcity advisor --task regex_grep --size quick
```

### 2. Production Playbooks (`devcity playbook`)
Step-by-step blueprints from system spec to deployment:
```bash
devcity playbook react-springboot-postgres
devcity playbook react-springboot-postgres --step 2
```

### 3. Repo AI-Readiness Audit (`devcity audit`)
Scan your workspace for token-waste risks (bloated `CLAUDE.md`, unignored build artifacts, excessive MCP tools):
```bash
devcity audit .
```

### 4. Executive Value Report (`devcity report`)
Generate a clean `DEVCITY_REPORT.md` with headline dollar savings, AI Health Score, and top 3 habit coaching tips:
```bash
devcity report --out DEVCITY_REPORT.md
```

### 5. Git Pre-Commit Guard & Budget Hook (`devcity hook`)
Install local pre-commit checks for API keys and destructive SQL migrations:
```bash
devcity hook install
```

---

## 🔒 Privacy & Safety Contract

1. **Zero Text Ingestion**: Prompts, assistant replies, source code, and diffs are discarded at parse time. Only token integers, timestamps, model IDs, and tool names are retained.
2. **Zero Absolute Paths**: Only folder basenames are stored. User home directories, usernames, and git remotes are never collected.
3. **100% Local & Offline**: Zero network calls, telemetry pings, or cloud phone-home calls.
4. **Automated Privacy Tests**: `tests/test_privacy.py` continuously asserts that sensitive tokens (`sk-...`, passwords, private keys) never leak into output JSON, SQLite tables, or markdown reports.

---

## 📄 License & Attribution

DevCity is open-source software licensed under the [MIT License](LICENSE).  
Created with ❤️ by Sanjaydeep Gowrishankar.
