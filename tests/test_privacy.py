"""Privacy verification test: asserts secret strings NEVER appear in output JSON or SQLite."""

import json
import pathlib
import tempfile
import unittest
import datetime as dt

from devcity.cache import MetricsCache
from devcity.collectors.claude import ClaudeCodeCollector
from devcity.collectors.antigravity import AntigravityCollector
from devcity.engine import AggregationEngine


class TestPrivacyLeakAssertions(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = pathlib.Path(self.temp_dir.name)
        self.db_path = self.temp_path / "privacy_test.db"
        self.cache = MetricsCache(db_path=self.db_path)

        self.secret_claude_token = "sk-ant-api03-TOP_SECRET_CLAUDE_TOKEN_999"
        self.secret_password = "SUPER_CONFIDENTIAL_DB_PASSWORD_XYZ"
        self.secret_code_snippet = "function steal_company_data() { return true; }"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_secrets_never_leak_into_output_or_sqlite(self):
        # 1. Create a Claude Code fixture containing sensitive prompts, code, and tokens
        claude_dir = self.temp_path / "claude_projects" / "ecommerce-secret"
        claude_dir.mkdir(parents=True, exist_ok=True)
        claude_file = claude_dir / "session1.jsonl"

        claude_payload = [
            {
                "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
                "type": "user",
                "sessionId": "sess_secret_1",
                "cwd": "/Users/someone/work/ecommerce-secret",
                "message": {
                    "role": "user",
                    "content": f"Here is my API key: {self.secret_claude_token} and code: {self.secret_code_snippet}"
                }
            },
            {
                "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
                "type": "assistant",
                "sessionId": "sess_secret_1",
                "requestId": "req_1",
                "cwd": "/Users/someone/work/ecommerce-secret",
                "message": {
                    "id": "msg_1",
                    "role": "assistant",
                    "model": "claude-sonnet-5-5",
                    "content": [
                        {"type": "text", "text": f"I received your password: {self.secret_password}"},
                        {"type": "tool_use", "id": "t1", "name": "Bash", "input": {"command": "echo secret"}}
                    ],
                    "usage": {
                        "input_tokens": 1500,
                        "output_tokens": 250,
                        "cache_creation_input_tokens": 4000,
                        "cache_read_input_tokens": 25000
                    }
                }
            }
        ]
        claude_file.write_text("\n".join(json.dumps(line) for line in claude_payload), encoding="utf-8")

        # 2. Create an Antigravity fixture containing sensitive thinking and content
        ag_dir = self.temp_path / "ag_brain" / "conv_secret" / ".system_generated" / "logs"
        ag_dir.mkdir(parents=True, exist_ok=True)
        ag_file = ag_dir / "transcript.jsonl"

        ag_payload = [
            {
                "step_index": 0,
                "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "source": "USER_EXPLICIT",
                "type": "USER_INPUT",
                "content": f"Do not leak this secret: {self.secret_password}"
            },
            {
                "step_index": 1,
                "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "source": "MODEL",
                "type": "PLANNER_RESPONSE",
                "input_tokens": 1200,
                "output_tokens": 300,
                "cache_read_tokens": 8000,
                "thinking": f"Reflecting on password {self.secret_password} and token {self.secret_claude_token}",
                "tool_calls": [{"name": "run_command", "args": {"Cwd": "/Users/someone/work/payment-service"}}]
            }
        ]
        ag_file.write_text("\n".join(json.dumps(line) for line in ag_payload), encoding="utf-8")

        # 3. Collect from both
        claude_col = ClaudeCodeCollector(root=self.temp_path / "claude_projects", cache=self.cache)
        ag_col = AntigravityCollector(root=self.temp_path / "ag_brain", cache=self.cache)

        since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=1)
        sessions = claude_col.collect(since=since) + ag_col.collect(since=since)

        # 4. Aggregate
        engine = AggregationEngine()
        result = engine.aggregate(sessions=sessions, range_days=1, anonymize=False)
        result_json = json.dumps(result)

        # 5. ASSERT NO SECRETS IN RESULT JSON
        self.assertNotIn(self.secret_claude_token, result_json, "Privacy violation: Claude secret token leaked into output JSON!")
        self.assertNotIn(self.secret_password, result_json, "Privacy violation: Password leaked into output JSON!")
        self.assertNotIn(self.secret_code_snippet, result_json, "Privacy violation: Code snippet leaked into output JSON!")

        # 6. ASSERT NO ABSOLUTE HOME DIRECTORY PATHS IN RESULT JSON
        self.assertNotIn("/Users/someone/work", result_json, "Privacy violation: Absolute path leaked into output JSON!")

        # 7. ASSERT NO SECRETS IN SQLITE CACHE DB
        with self.cache._get_conn() as conn:
            cur = conn.execute("SELECT tool_calls_json, project_name FROM sessions")
            db_dump = " ".join(f"{r[0]} {r[1]}" for r in cur.fetchall())
            self.assertNotIn(self.secret_claude_token, db_dump, "Privacy violation: Claude secret token found in SQLite database!")
            self.assertNotIn(self.secret_password, db_dump, "Privacy violation: Password found in SQLite database!")
            self.assertNotIn(self.secret_code_snippet, db_dump, "Privacy violation: Code snippet found in SQLite database!")
            self.assertNotIn("/Users/someone/work", db_dump, "Privacy violation: Absolute path found in SQLite database!")


if __name__ == "__main__":
    unittest.main()
