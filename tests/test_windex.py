import unittest

from lip_ledger import windex


class WindexTests(unittest.TestCase):
    def test_lattice(self):
        self.assertAlmostEqual(windex.tick_f(8), 0.225)
        self.assertAlmostEqual(windex.tick_f(5), 0.36)
        self.assertAlmostEqual(windex.cushion_ticks(64.99 + 0.36, 64.99, 5), 1.0)

    def test_settlement_value_picks_latest_not_after_close(self):
        pts = [{"t": 1000 * 60000, "v": 60.0, "status": "normal"},
               {"t": 1003 * 60000, "v": 61.0, "status": "degraded"},
               {"t": 1004 * 60000, "v": 62.0, "status": "normal"},
               {"t": 1003 * 60000 + 1, "v": None, "status": "incomplete"}]
        self.assertEqual(windex.settlement_value(pts, 1003 * 60000), 61.0)
        self.assertEqual(windex.settlement_value(pts, 1010 * 60000), 62.0)
        self.assertIsNone(windex.settlement_value(pts, 900 * 60000))

    def test_outcome_is_strictly_greater(self):
        pts = [{"t": 0, "v": 70.99, "status": "normal"}]
        self.assertEqual(windex.outcome(pts, 0, 70.99), "no")
        self.assertEqual(windex.outcome(pts, 0, 70.98), "yes")

    def test_stale_point_is_not_used(self):
        pts = [{"t": 0, "v": 70.0, "status": "normal"}]
        self.assertIsNone(windex.settlement_value(pts, 61 * 60000))


if __name__ == "__main__":
    unittest.main()
