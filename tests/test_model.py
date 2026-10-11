import unittest

from lip_ledger.model import expected_payout, side_score


class ModelTests(unittest.TestCase):
    def test_worked_example(self):
        others = [(0.28, 120), (0.27, 300), (0.26, 450), (0.25, 600)]
        r = side_score(others, target=1000, d=0.5, mine=(0.28, 5))
        self.assertTrue(r["counted"])
        self.assertAlmostEqual(r["ref"], 0.27)
        self.assertAlmostEqual(r["total_score"], 800.0)
        self.assertAlmostEqual(r["share"], 5 / 800)

    def test_side_not_reaching_target_is_not_counted(self):
        r = side_score([(0.50, 100)], target=1000, d=0.5, mine=(0.50, 5))
        self.assertFalse(r["counted"])
        self.assertEqual(r["share"], 0.0)

    def test_payout_formula(self):
        self.assertAlmostEqual(expected_payout(100.0, 0.01, counted_fraction=0.5, present_fraction=0.5), 100 * 0.5 * 0.01 * 0.25)

    def test_prices_above_reference_score_full_weight(self):
        r = side_score([(0.60, 300), (0.59, 300)], target=500, d=0.5, mine=(0.61, 10))
        # reference is the first level whose cumulative size >= 100, i.e. the best level (0.61, my own 10 + nothing) -> check weights
        self.assertTrue(r["counted"])
        self.assertGreater(r["share"], 0.0)


if __name__ == "__main__":
    unittest.main()
