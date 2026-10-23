"""Unit tests for devcity/mcp_server.py (Agent 1)."""

import json
import unittest
from devcity.mcp_server import (
    get_summary,
    get_project,
    get_daily,
    top_tools,
    check_budget,
    compare_models
)


class TestMCPServer(unittest.TestCase):
    def test_get_summary(self):
        res = get_summary(days=30)
        self.assertIn(res.get("status"), ["success", "empty"])
        if res.get("status") == "success":
            self.assertIn("total_spend_usd", res)
            self.assertIn("total_tokens", res)
            self.assertIn("cache_hit_rate", res)

    def test_top_tools(self):
        res = top_tools(limit=5, days=30)
        self.assertIn(res.get("status"), ["success", "empty"])
        if res.get("status") == "success":
            self.assertIn("top_tools", res)
            self.assertTrue(len(res["top_tools"]) <= 5)

    def test_check_budget(self):
        res = check_budget(daily_limit_usd=50.0)
        self.assertIn(res.get("status"), ["OK", "WARNING", "EXCEEDED"])
        self.assertIn("today_spend_usd", res)
        self.assertIn("remaining_usd", res)
        self.assertEqual(res["daily_limit_usd"], 50.0)

    def test_compare_models(self):
        res = compare_models(days=30)
        self.assertEqual(res.get("status"), "success")
        self.assertIn("models", res)


if __name__ == "__main__":
    unittest.main()
