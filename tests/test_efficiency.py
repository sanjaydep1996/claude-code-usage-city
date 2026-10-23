"""Unit tests for devcity/efficiency.py."""

import unittest
from devcity.efficiency import calculate_cache_hit_rate, evaluate_cache_leak


class TestEfficiency(unittest.TestCase):
    def test_cache_hit_rate(self):
        # 10k read / (10k read + 2k input + 8k write) = 10 / 20 = 50%
        hr = calculate_cache_hit_rate(2000, 8000, 10000)
        self.assertEqual(hr, 0.50)

        # Zero tokens
        self.assertEqual(calculate_cache_hit_rate(0, 0, 0), 0.0)

    def test_cache_leak_detection(self):
        # Spend < $5 should NOT flag
        leak, _ = evaluate_cache_leak("claude-code", cost_usd=3.50, input_tokens=1000, cache_write_tokens=50000, cache_read_tokens=1000)
        self.assertFalse(leak)

        # Claude Code: Spend >= $5, cache hit rate < 75%, cache_write > cache_read (thrashing)
        # Writes 2M, Reads 200k, Input 100k -> Hit rate is 200k / 2.3M = ~8.7%
        leak, reason = evaluate_cache_leak("claude-code", cost_usd=15.00, input_tokens=100_000, cache_write_tokens=2_000_000, cache_read_tokens=200_000)
        self.assertTrue(leak)
        self.assertIn("Cache Thrashing", reason)

        # Healthy Claude Code session: 100k input, 500k write, 10M read -> Hit rate = 10 / 10.6 = ~94%
        leak_healthy, _ = evaluate_cache_leak("claude-code", cost_usd=20.00, input_tokens=100_000, cache_write_tokens=500_000, cache_read_tokens=10_000_000)
        self.assertFalse(leak_healthy)


if __name__ == "__main__":
    unittest.main()
