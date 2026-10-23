"""Unit tests for devcity/pricing.py."""

import unittest
from devcity.pricing import PricingCalculator, classify_family


class TestPricing(unittest.TestCase):
    def setUp(self):
        self.pricing = PricingCalculator()

    def test_rates_and_cost_calculation(self):
        # Sonnet 5-5: input $2, output $10, cacheRead $0.20 per 1M
        ri, ro, rw, rr = self.pricing.rates("claude-sonnet-5-5")
        self.assertEqual(ri, 2.0)
        self.assertEqual(ro, 10.0)
        self.assertEqual(rr, 0.20)

        # 1M input + 100k output = 2.0 + 1.0 = $3.0
        cost = self.pricing.compute_cost("claude-sonnet-5-5", 1_000_000, 100_000)
        self.assertAlmostEqual(cost, 3.0, places=2)

    def test_cache_savings(self):
        # 1M cacheRead saves (input_rate - cache_read_rate) = (2.0 - 0.20) = $1.80
        saved = self.pricing.compute_cache_savings("claude-sonnet-5-5", 1_000_000)
        self.assertAlmostEqual(saved, 1.80, places=2)

    def test_gemini_rates(self):
        # Gemini 3.8 Flash: input $0.15, output $0.60, cacheRead $0.0375
        ri, ro, rw, rr = self.pricing.rates("gemini-3.8-flash")
        self.assertEqual(ri, 0.15)
        self.assertEqual(ro, 0.60)
        self.assertEqual(rr, 0.0375)

    def test_family_classification(self):
        self.assertEqual(classify_family("claude-opus-5-5"), "opus")
        self.assertEqual(classify_family("claude-sonnet-5-5"), "sonnet")
        self.assertEqual(classify_family("claude-haiku-5-5"), "haiku")
        self.assertEqual(classify_family("claude-fable-5-1"), "fable")
        self.assertEqual(classify_family("gemini-3.8-flash"), "gemini")
        self.assertEqual(classify_family("gemini-2.5-pro"), "gemini")
        self.assertEqual(classify_family("unknown-model-xyz"), "other")


if __name__ == "__main__":
    unittest.main()
