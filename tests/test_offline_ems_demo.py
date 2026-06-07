import tempfile
import unittest
from pathlib import Path

from scripts.run_offline_ems_demo import run_demo


class OfflineEmsDemoTest(unittest.TestCase):
    def test_demo_writes_trace_and_summary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "demo.jsonl"

            summary = run_demo(steps=24, peak_pv_w=25000, output=output, seed=1)

            self.assertTrue(output.exists())
            self.assertEqual(24, summary["steps"])
            self.assertGreater(summary["commands"], 0)
            self.assertIn("output", summary)
            self.assertEqual(24, len(output.read_text(encoding="utf-8").splitlines()))


if __name__ == "__main__":
    unittest.main()
