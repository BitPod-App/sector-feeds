from __future__ import annotations

import unittest

from bitpod.cost_meter import estimate_tokens_from_text, excerpt_text


class CostMeterTests(unittest.TestCase):
    def test_estimate_tokens_rounds_up(self) -> None:
        self.assertEqual(estimate_tokens_from_text(""), 0)
        self.assertEqual(estimate_tokens_from_text("abcd"), 1)
        self.assertEqual(estimate_tokens_from_text("abcde"), 2)

    def test_excerpt_text_truncates_with_marker(self) -> None:
        text = "x" * 10000
        out = excerpt_text(text, max_chars=2000)
        self.assertIn("[...TRUNCATED FOR COST CONTROL...]", out)
        self.assertTrue(len(out) < len(text))


if __name__ == "__main__":
    unittest.main()
