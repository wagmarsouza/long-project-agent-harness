import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/analyze_trace.py"
spec = importlib.util.spec_from_file_location("trace", SCRIPT)
trace = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trace)


class TraceTests(unittest.TestCase):
    def test_blocks_and_frequency(self):
        pcs = [0x1000, 0x1002, 0x1004, 0x2000, 0x2002, 0x1000]
        result = trace.summarize(pcs, jump_threshold=8)
        self.assertEqual(result["total_entries"], 6)
        self.assertEqual(result["unique_pcs"], 5)
        self.assertEqual(result["top"][0], (0x1000, 2))
        self.assertEqual(result["total_blocks"], 3)

    def test_empty_trace_is_not_invented(self):
        self.assertEqual(trace.summarize([]), {"total_entries": 0, "unique_pcs": 0})

    def test_invalid_line_fails_cli(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "trace.log"
            path.write_text("0x1000\nnot-an-address\n", encoding="utf-8")
            run = subprocess.run([sys.executable, "-B", str(SCRIPT), str(path)],
                                 capture_output=True, text=True)
            self.assertEqual(run.returncode, 2)
            self.assertIn("line 2", run.stderr)

    def test_comments_and_prefix_are_supported(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "trace.log"
            path.write_text("# fixture\n0x1000\n1002\n", encoding="utf-8")
            self.assertEqual(trace.load_pcs(path), [0x1000, 0x1002])


if __name__ == "__main__":
    unittest.main()
