"""Repo AI-Readiness Audit for DevCity.

Scans local project repositories for token-waste risks:
- CLAUDE.md / .cursorrules file size (system prompt bloat)
- Missing ignore files (.gitignore, .claudeignore)
- Excess MCP server tool configurations
- Unindexed large files in source tree
Deterministic, local-only, zero LLM calls.
"""

import json
import os
import pathlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


@dataclass
class AuditFinding:
    category: str  # 'instructions', 'ignore_rules', 'mcp', 'large_files'
    severity: str  # 'info', 'warning', 'danger'
    title: str
    description: str
    remediation: str
    tokens_wasted_per_prompt_est: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "severity": self.severity,
            "title": self.title,
            "description": self.description,
            "remediation": self.remediation,
            "tokens_wasted_per_prompt_est": self.tokens_wasted_per_prompt_est,
        }


@dataclass
class AuditResult:
    target_path: str
    score: int  # 0 to 100
    grade: str  # 'A', 'B', 'C', 'D', 'F'
    findings: List[AuditFinding] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_path": self.target_path,
            "score": self.score,
            "grade": self.grade,
            "findings": [f.to_dict() for f in self.findings],
            "stats": self.stats,
        }


class RepoAuditor:
    """Audits repository configuration for AI coding efficiency."""

    def __init__(self, root_dir: Optional[pathlib.Path] = None):
        self.root = pathlib.Path(root_dir or ".").resolve()

    def audit(self) -> AuditResult:
        findings: List[AuditFinding] = []
        stats: Dict[str, Any] = {}
        penalty = 0

        # 1. Check Instruction Files (CLAUDE.md, .cursorrules, GEMINI.md)
        instruction_files = ["CLAUDE.md", ".cursorrules", "GEMINI.md", "AGENT.md", ".claude/config.json"]
        found_instructions = []
        for name in instruction_files:
            p = self.root / name
            if p.exists() and p.is_file():
                size = p.stat().st_size
                lines = len(p.read_text(encoding="utf-8", errors="ignore").splitlines())
                found_instructions.append((name, size, lines))

        stats["instruction_files"] = [f[0] for f in found_instructions]
        if not found_instructions:
            findings.append(AuditFinding(
                category="instructions",
                severity="info",
                title="No CLAUDE.md or .cursorrules Found",
                description="Without project instructions, AI tools may repeat questions or misidentify architecture conventions.",
                remediation="Add a concise CLAUDE.md (< 100 lines) describing build, test, and style commands.",
                tokens_wasted_per_prompt_est=0
            ))
        else:
            for name, size, lines in found_instructions:
                if lines > 150 or size > 5000:
                    penalty += 20
                    waste = (lines * 5)  # roughly 5 tokens per line
                    findings.append(AuditFinding(
                        category="instructions",
                        severity="warning",
                        title=f"{name} is Too Long ({lines} lines, {size} bytes)",
                        description=(
                            f"{name} is loaded into the system context on every single turn! "
                            f"At {lines} lines, it injects ~{waste} tokens of overhead into every prompt."
                        ),
                        remediation=(
                            "Compact the file to under 100 lines. Focus only on commands and architectural rules; "
                            "move detailed documentation into separate docs/ files."
                        ),
                        tokens_wasted_per_prompt_est=waste
                    ))

        # 2. Check Ignore Files (.gitignore, .claudeignore)
        gitignore_path = self.root / ".gitignore"
        claudeignore_path = self.root / ".claudeignore"
        has_gitignore = gitignore_path.exists()
        has_claudeignore = claudeignore_path.exists()

        stats["has_gitignore"] = has_gitignore
        stats["has_claudeignore"] = has_claudeignore

        essential_patterns = ["node_modules", ".git", "dist", "build", "*.log", "venv"]
        missing_ignores = []

        if has_gitignore:
            content = gitignore_path.read_text(encoding="utf-8", errors="ignore")
            for pat in essential_patterns:
                if pat not in content:
                    missing_ignores.append(pat)

        if not has_gitignore:
            penalty += 25
            findings.append(AuditFinding(
                category="ignore_rules",
                severity="danger",
                title="Missing .gitignore File",
                description="AI tools scanning your workspace may ingest binary files, build artifacts, and dependency directories.",
                remediation="Create a .gitignore file ignoring build directories, node_modules, and cache files.",
                tokens_wasted_per_prompt_est=15000
            ))
        elif missing_ignores:
            penalty += 10
            findings.append(AuditFinding(
                category="ignore_rules",
                severity="warning",
                title=f"Common Build Artifacts Not in .gitignore: {', '.join(missing_ignores[:3])}",
                description="Generated build files or dependencies may accidentally be read during AI tool file search.",
                remediation=f"Add {', '.join(missing_ignores)} to .gitignore or .claudeignore.",
                tokens_wasted_per_prompt_est=5000
            ))

        # 3. Check Large Files in Repo
        large_files = []
        try:
            for p in self.root.glob("**/*"):
                if not p.is_file():
                    continue
                # Skip .git and node_modules
                parts = p.parts
                if ".git" in parts or "node_modules" in parts or ".venv" in parts or "venv" in parts or "dist" in parts:
                    continue
                try:
                    s = p.stat().st_size
                    if s > 500 * 1024:  # > 500KB
                        large_files.append((p.relative_to(self.root).as_posix(), s))
                except Exception:
                    pass
        except Exception:
            pass

        stats["large_files_count"] = len(large_files)
        if large_files:
            penalty += min(20, len(large_files) * 5)
            sample_names = [f[0] for f in large_files[:3]]
            findings.append(AuditFinding(
                category="large_files",
                severity="warning",
                title=f"Detected {len(large_files)} Large Files (>500KB)",
                description=(
                    f"Files like {', '.join(sample_names)} can quickly overwhelm AI context windows "
                    "if read by the agent."
                ),
                remediation="Ensure massive data files, database dumps, and binaries are added to .claudeignore or .gitignore.",
                tokens_wasted_per_prompt_est=10000
            ))

        # 4. Check MCP Server Configuration
        mcp_tools_count = 0
        mcp_configs = [
            self.root / ".mcp.json",
            pathlib.Path(os.path.expanduser("~/.claude/mcp.json")),
            pathlib.Path(os.path.expanduser("~/Library/Application Support/Claude/claude_desktop_config.json"))
        ]
        for cfg in mcp_configs:
            if cfg.exists():
                try:
                    data = json.loads(cfg.read_text(encoding="utf-8"))
                    servers = data.get("mcpServers", {})
                    # Approximate 4 tools per server if not specified
                    mcp_tools_count += len(servers) * 4
                except Exception:
                    pass

        stats["mcp_tools_approx"] = mcp_tools_count
        if mcp_tools_count > 25:
            penalty += 15
            findings.append(AuditFinding(
                category="mcp",
                severity="warning",
                title=f"High MCP Tool Count (~{mcp_tools_count} tools active)",
                description="Each configured MCP server adds its tool schemas into every system prompt.",
                remediation="Disable unused MCP servers in repositories that do not require external integrations.",
                tokens_wasted_per_prompt_est=mcp_tools_count * 120
            ))

        # Calculate score and grade
        score = max(0, min(100, 100 - penalty))
        if score >= 90:
            grade = "A"
        elif score >= 80:
            grade = "B"
        elif score >= 70:
            grade = "C"
        elif score >= 60:
            grade = "D"
        else:
            grade = "F"

        return AuditResult(
            target_path=str(self.root),
            score=score,
            grade=grade,
            findings=findings,
            stats=stats
        )


def run_audit(target_dir: Optional[str] = None) -> AuditResult:
    return RepoAuditor(pathlib.Path(target_dir or ".")).audit()
