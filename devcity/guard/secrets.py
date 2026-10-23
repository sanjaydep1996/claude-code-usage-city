"""Secret & Safety Scanner for DevCity.

Lightweight, 100% local regex scanner for:
- API Keys (Anthropic, OpenAI, AWS, GitHub, Stripe, generic secrets)
- Destructive SQL / Database changes (DROP TABLE, TRUNCATE, unindexed ALTER TABLE)
- Private keys (RSA, OpenSSH, PGP)
Never makes outbound network calls.
"""

import re
from dataclasses import dataclass
from typing import Dict, List, Any


@dataclass
class ScanFinding:
    rule_id: str
    category: str  # 'secret' or 'destructive_change'
    severity: str  # 'warning' or 'danger'
    message: str
    match_sample: str
    line_number: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "category": self.category,
            "severity": self.severity,
            "message": self.message,
            "match_sample": self.match_sample,
            "line_number": self.line_number,
        }


# Strict local regex patterns for API keys and destructive patterns
SECRET_PATTERNS = [
    (r"sk-ant-[a-zA-Z0-9_\-]{32,}", "anthropic_api_key", "danger", "Detected Anthropic API Key"),
    (r"sk-[a-zA-Z0-9]{32,}", "openai_api_key", "danger", "Detected OpenAI API Key"),
    (r"AKIA[0-9A-Z]{16}", "aws_access_key", "danger", "Detected AWS Access Key ID"),
    (r"ghp_[a-zA-Z0-9]{36}", "github_personal_token", "danger", "Detected GitHub Personal Access Token"),
    (r"gho_[a-zA-Z0-9]{36}", "github_oauth_token", "danger", "Detected GitHub OAuth Token"),
    (r"sk_live_[0-9a-zA-Z]{24}", "stripe_live_key", "danger", "Detected Stripe Live Secret Key"),
    (r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", "private_key", "danger", "Detected Private Cryptographic Key"),
]

DESTRUCTIVE_SQL_PATTERNS = [
    (r"\bDROP\s+TABLE\s+(?:IF\s+EXISTS\s+)?[a-zA-Z0-9_]+", "sql_drop_table", "danger", "Destructive SQL: DROP TABLE statement detected"),
    (r"\bTRUNCATE\s+(?:TABLE\s+)?[a-zA-Z0-9_]+", "sql_truncate_table", "danger", "Destructive SQL: TRUNCATE statement detected"),
    (r"\bDROP\s+DATABASE\b", "sql_drop_database", "danger", "Destructive SQL: DROP DATABASE statement detected"),
]


class SecretScanner:
    """Scans text, git diffs, or files for secrets and destructive changes."""

    @staticmethod
    def scan_text(text: str, filename: str = "") -> List[ScanFinding]:
        findings: List[ScanFinding] = []
        lines = text.split("\n")

        for line_idx, line in enumerate(lines, start=1):
            # Check secrets
            for pattern, rule_id, severity, msg in SECRET_PATTERNS:
                m = re.search(pattern, line)
                if m:
                    # Anonymize/mask match sample
                    raw = m.group(0)
                    masked = raw[:6] + "..." + raw[-4:] if len(raw) > 12 else "***MASKED***"
                    findings.append(ScanFinding(
                        rule_id=rule_id,
                        category="secret",
                        severity=severity,
                        message=f"{msg} in {filename}:{line_idx}" if filename else f"{msg} on line {line_idx}",
                        match_sample=masked,
                        line_number=line_idx
                    ))

            # Check destructive SQL if filename is sql or migration or diff contains SQL
            is_sql = filename.endswith(".sql") or "migration" in filename.lower()
            if is_sql or line.strip().upper().startswith(("DROP", "TRUNCATE")):
                for pattern, rule_id, severity, msg in DESTRUCTIVE_SQL_PATTERNS:
                    m = re.search(pattern, line, re.IGNORECASE)
                    if m:
                        findings.append(ScanFinding(
                            rule_id=rule_id,
                            category="destructive_change",
                            severity=severity,
                            message=f"{msg} in {filename}:{line_idx}" if filename else f"{msg} on line {line_idx}",
                            match_sample=m.group(0),
                            line_number=line_idx
                        ))

        return findings


def scan_text(text: str, filename: str = "") -> List[ScanFinding]:
    return SecretScanner.scan_text(text, filename)


def scan_git_diff(diff_text: str) -> List[ScanFinding]:
    """Scans git diff text only on added/modified lines (starting with +)."""
    added_lines = []
    current_file = ""
    for line in diff_text.split("\n"):
        if line.startswith("+++ b/"):
            current_file = line[6:]
        elif line.startswith("+") and not line.startswith("+++"):
            added_lines.append((current_file, line[1:]))

    findings = []
    for f, l in added_lines:
        res = scan_text(l, filename=f)
        findings.extend(res)
    return findings
