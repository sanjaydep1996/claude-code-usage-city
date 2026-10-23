"""Unit tests for devcity/engine.py."""

import datetime as dt
import json
import unittest
from devcity.collectors.base import NormalizedSession
from devcity.engine import AggregationEngine, validate_schema_v2


class TestEngine(unittest.TestCase):
    def test_multi_tool_aggregation_and_validation(self):
        engine = AggregationEngine()
        now = dt.datetime.now(dt.timezone.utc)

        sessions = [
            NormalizedSession(
                source="claude-code",
                project_name="backend-api",
                session_id="s1",
                timestamp=now - dt.timedelta(hours=2),
                model="claude-sonnet-5-5",
                input_tokens=10000,
                output_tokens=2000,
                cache_write_tokens=50000,
                cache_read_tokens=400000,
                tool_calls={"Bash": 12, "Read": 8},
                event_timestamps=[now.timestamp() - 7200, now.timestamp() - 6000]
            ),
            NormalizedSession(
                source="antigravity",
                project_name="backend-api",
                session_id="s2",
                timestamp=now - dt.timedelta(hours=1),
                model="gemini-3.8-flash",
                input_tokens=15000,
                output_tokens=3000,
                cache_write_tokens=0,
                cache_read_tokens=60000,
                tool_calls={"run_command": 5},
                event_timestamps=[now.timestamp() - 3600, now.timestamp() - 3000]
            )
        ]

        payload = engine.aggregate(sessions=sessions, range_days=7, anonymize=False)

        # Validate Schema v2
        errors = validate_schema_v2(payload)
        self.assertEqual(errors, [], f"Schema validation failed: {errors}")

        # Check project merged multi-tool sources
        self.assertEqual(len(payload["projects"]), 1)
        p = payload["projects"][0]
        self.assertEqual(p["name"], "backend-api")
        self.assertEqual(p["sources"], ["antigravity", "claude-code"])
        self.assertIn("claude-code", p["bySource"])
        self.assertIn("antigravity", p["bySource"])

        # Check daily format: [date, tokens, cost]
        self.assertTrue(len(p["daily"]) > 0)
        self.assertEqual(len(p["daily"][0]), 3)

    def test_anonymization(self):
        engine = AggregationEngine()
        now = dt.datetime.now(dt.timezone.utc)
        sessions = [
            NormalizedSession(
                source="claude-code",
                project_name="confidential-client-work",
                session_id="s1",
                timestamp=now,
                model="claude-opus-5-5",
                input_tokens=5000,
                output_tokens=1000
            )
        ]

        payload = engine.aggregate(sessions=sessions, range_days=1, anonymize=True)
        p = payload["projects"][0]
        self.assertEqual(p["name"], "Project A")
        self.assertNotIn("confidential", json.dumps(payload))


if __name__ == "__main__":
    unittest.main()
