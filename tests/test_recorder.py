import json
import os
import tempfile
import unittest

from lip_ledger.recorder import analyze


class RecorderTests(unittest.TestCase):
    def test_analyze_counts_only_when_both_sides_reach_target(self):
        deep = [[0.50, 600], [0.49, 600]]
        thin = [[0.50, 100]]
        rows = [
            {"ts": "t0", "ticker": "X", "target": 1000, "d": 0.5, "pool": 100, "yes": deep, "no": deep},   # counted
            {"ts": "t1", "ticker": "X", "target": 1000, "d": 0.5, "pool": 100, "yes": deep, "no": thin},   # not counted
        ]
        with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
            path = f.name
        try:
            res = analyze(path, qty=10, side="yes")
        finally:
            os.unlink(path)
        self.assertEqual(res["X"]["snapshots"], 2)
        self.assertAlmostEqual(res["X"]["counted_fraction"], 0.5)
        self.assertGreater(res["X"]["mean_share"], 0.0)


if __name__ == "__main__":
    unittest.main()
