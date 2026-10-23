import unittest
from devcity.guide.advisor import ToolAdvisor, recommend_tool


class TestToolAdvisor(unittest.TestCase):
    def setUp(self):
        self.advisor = ToolAdvisor()

    def test_known_task_regex(self):
        rec = self.advisor.recommend("regex_grep", size="quick")
        self.assertIn("Haiku", rec.recommended_model)
        self.assertTrue("< $" in rec.cost_est_usd)

    def test_known_task_unit_test(self):
        rec = self.advisor.recommend("unit_test", size="medium")
        self.assertIn("Sonnet", rec.recommended_model)
        self.assertTrue(rec.token_budget_est)

    def test_db_migration_high_risk(self):
        rec = self.advisor.recommend("db_migration")
        self.assertIn("DROP TABLE", rec.caveats)

    def test_unknown_task_fallback(self):
        rec = self.advisor.recommend("unknown_custom_task", size="quick")
        self.assertEqual(rec.task_type, "unknown_custom_task")
        self.assertTrue(rec.recommended_tool)


if __name__ == "__main__":
    unittest.main()
