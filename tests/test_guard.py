import unittest
from devcity.guard.secrets import scan_text, scan_git_diff
from devcity.guard.budget import BudgetGuard


class TestGuard(unittest.TestCase):
    def test_secret_scanner_detects_api_key(self):
        text = "ANTHROPIC_KEY=sk-ant-api03-abcdef1234567890abcdef1234567890\n"
        findings = scan_text(text, filename=".env")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].category, "secret")
        self.assertEqual(findings[0].severity, "danger")
        self.assertIn("...", findings[0].match_sample)  # Masked!

    def test_secret_scanner_detects_destructive_sql(self):
        diff = "+++ b/migrations/V2__drop.sql\n+ DROP TABLE users;\n"
        findings = scan_git_diff(diff)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].category, "destructive_change")
        self.assertIn("DROP TABLE", findings[0].message)

    def test_budget_guard(self):
        bg = BudgetGuard(daily_budget_usd=10.0)
        res = bg.check_daily_budget(today_cost_usd=12.50)
        self.assertTrue(res.is_exceeded)
        self.assertIn("Daily AI Budget Alert", res.warning_message)


if __name__ == "__main__":
    unittest.main()
