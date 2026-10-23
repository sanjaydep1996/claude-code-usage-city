import json
import unittest
from devcity.prove.health import calculate_health_score
from devcity.prove.report import generate_markdown_report


class TestReportAndHealth(unittest.TestCase):
    def test_health_score_calculation(self):
        sample_payload = {
            "totals": {
                "projects": 3,
                "sessions": 10,
                "activeHours": 15.0,
                "costUSD": 25.0,
                "costSavedUSD": 35.0,
                "cacheHitRate": 0.88,
                "tokens": {"input": 1000, "output": 500, "cacheWrite": 200, "cacheRead": 800}
            },
            "projects": [
                {"name": "proj1", "costUSD": 15.0, "activeHours": 8.0, "cacheHitRate": 0.90, "costSavedUSD": 20.0, "cacheLeak": False},
                {"name": "proj2", "costUSD": 10.0, "activeHours": 7.0, "cacheHitRate": 0.85, "costSavedUSD": 15.0, "cacheLeak": False}
            ],
            "sources": ["claude-code"]
        }
        res = calculate_health_score(sample_payload)
        self.assertIn(res.grade, ["A+", "A", "B+", "B"])
        self.assertGreaterEqual(res.score, 80)
        self.assertEqual(len(res.top_tips), 3)

    def test_markdown_report_generation(self):
        sample_payload = {
            "totals": {
                "projects": 1,
                "sessions": 5,
                "activeHours": 4.0,
                "costUSD": 10.0,
                "costSavedUSD": 15.0,
                "cacheHitRate": 0.92,
                "tokens": {"input": 1000, "output": 200, "cacheWrite": 100, "cacheRead": 900}
            },
            "projects": [
                {"name": "my-app", "costUSD": 10.0, "activeHours": 4.0, "cacheHitRate": 0.92, "costSavedUSD": 15.0, "cacheLeak": False}
            ],
            "sources": ["claude-code"]
        }
        md = generate_markdown_report(sample_payload)
        self.assertIn("# DevCity AI Value & Observability Report", md)
        self.assertIn("Headline Value", md)
        self.assertIn("my-app", md)


if __name__ == "__main__":
    unittest.main()
