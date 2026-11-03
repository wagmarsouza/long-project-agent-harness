import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/harness.py"
spec = importlib.util.spec_from_file_location("harness81_insight_tests", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class InsightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="harness81-")
        self.root = Path(self.temp.name)
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.email", "fixture@example.invalid"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.name", "Fixture"], cwd=self.root, check=True)
        (self.root / "result.txt").write_text("correct", encoding="utf-8")
        subprocess.run(["git", "add", "result.txt"], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-qm", "base"], cwd=self.root, check=True)
        self.base = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=self.root, text=True).strip()
        (self.root / "notes.txt").write_text("bounded change", encoding="utf-8")
        subprocess.run(["git", "add", "notes.txt"], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-qm", "head"], cwd=self.root, check=True)
        self.head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=self.root, text=True).strip()
        self.h = module.Harness(self.root)
        self.h.init({"objective": "Verify a bounded local result", "mode": "light", "in_scope": ["result.txt"], "out_of_scope": [],
                     "criteria": [{"id": "C1", "description": "Exact fixture", "argv": [sys.executable, "-c", "from pathlib import Path; assert Path('result.txt').read_text() == 'correct'"], "artifacts": ["result.txt"]}],
                     "requirements": [{"id": "R1", "description": "Bounded requirement", "criteria": ["C1"]}]})

    def tearDown(self):
        self.temp.cleanup()

    def state(self):
        with self.h.state() as state:
            return copy.deepcopy(state)

    def refuse(self, code, call):
        with self.assertRaises(module.Refusal) as caught:
            call()
        self.assertEqual(caught.exception.code, code)

    def run_record(self, identifier, agent="codex", cost="unpriced", amount=None, retry_of=None, subagents=None):
        folder = self.root / "evidence"
        folder.mkdir(exist_ok=True)
        source = folder / (identifier + ".jsonl")
        source.write_text(json.dumps({"event": identifier}) + "\n", encoding="utf-8")
        return {"format": "verimission-explicit-run-v1", "id": identifier, "agent": agent,
                "source": {"path": source.relative_to(self.root).as_posix(), "format": agent + "-export-declared", "record_locator": identifier},
                "status": "completed", "started_at": "2026-01-01T00:00:00+00:00", "ended_at": "2026-01-01T00:01:00+00:00",
                "attempt": 2 if retry_of else 1, "retry_of": retry_of,
                "usage": [{"provider": "fixture", "model": "fixture-model", "input_tokens": 10, "output_tokens": 5,
                           "cache_read_tokens": 3, "cache_write_tokens": 1,
                           "cost": {"status": cost, "amount_usd": amount, "method": "fixture receipt" if cost != "unpriced" else "price unavailable",
                                    "pricing_ref": "receipt-1" if cost != "unpriced" else ""}}],
                "subagents": subagents or [], "notes": "Fixture import"}

    def test_graph_formats_are_stable_read_only_projections(self):
        before = self.state()
        payload = self.h.graph("json", "graph.json")
        self.assertEqual(payload["format"], "verimission-graph-v1")
        self.assertTrue(any(row["id"] == "criterion:C1" for row in payload["nodes"]))
        self.h.graph("mermaid", "graph.mmd")
        self.h.graph("dot", "graph.dot")
        self.assertIn("flowchart LR", (self.root / "graph.mmd").read_text(encoding="utf-8"))
        self.assertIn("digraph verimission", (self.root / "graph.dot").read_text(encoding="utf-8"))
        self.assertEqual(before, self.state())

    def test_explicit_adapters_hash_sources_and_never_promote_claims(self):
        for agent in module._v81.AGENTS:
            template = self.h.adapter_template(agent)
            self.assertEqual(template["agent"], agent)
            self.assertEqual(template["usage"][0]["cost"]["status"], "unpriced")
            self.assertIsNone(template["usage"][0]["cost"]["amount_usd"])
            self.assertIsNone(template["usage"][0]["input_tokens"])
        imported = self.h.run_import(self.run_record("RUN-1"), "codex")
        self.assertFalse(imported["adapter"]["native_format_parsed"])
        self.assertFalse(imported["claims_promoted"])
        self.assertFalse(imported["authorization_granted"])
        self.assertEqual(len(imported["source"]["sha256"]), 64)

    def test_costs_separate_actual_estimated_and_unpriced(self):
        self.h.run_import(self.run_record("SUB", "hermes", "actual", 0.25), "hermes")
        self.h.run_import(self.run_record("RETRY", "claude", "estimated", 0.50, subagents=["SUB"]), "claude")
        self.h.run_import(self.run_record("UNKNOWN", "opencode", "unpriced", None, retry_of="RETRY"), "opencode")
        summary = self.h.cost_summary()
        self.assertEqual(summary["totals"]["actual_usd"], 0.25)
        self.assertEqual(summary["totals"]["estimated_usd"], 0.50)
        self.assertEqual(summary["totals"]["unpriced_rows"], 1)
        self.assertFalse(summary["complete_cost_total_available"])
        self.assertEqual(summary["retry_runs"], 1)
        self.assertEqual(summary["subagent_links"], 1)
        self.assertTrue(summary["possible_parent_child_double_counting"])

    def test_empty_cost_summary_does_not_claim_complete_accounting(self):
        summary = self.h.cost_summary()
        self.assertEqual(summary["runs"], 0)
        self.assertFalse(summary["complete_cost_total_available"])

    def test_unpriced_cost_cannot_be_disguised_as_zero(self):
        entry = self.run_record("RUN-1")
        entry["usage"][0]["cost"]["amount_usd"] = 0
        self.refuse("RUN_COST", lambda: self.h.run_import(entry, "codex"))

    def test_retry_and_subagent_references_must_preexist(self):
        self.refuse("RUN_RETRY", lambda: self.h.run_import(self.run_record("RUN-1", retry_of="MISSING"), "codex"))
        self.refuse("RUN_SUBAGENT", lambda: self.h.run_import(self.run_record("RUN-2", subagents=["MISSING"]), "codex"))

    def test_pr_report_resolves_commits_and_exposes_denominators_and_limits(self):
        report = self.h.pr_report(self.base, self.head, "PR_REPORT.md", "markdown")
        self.assertEqual(report["git"]["base_commit"], self.base)
        self.assertEqual(report["git"]["head_commit"], self.head)
        self.assertEqual(report["coverage"]["requirements"], {"verified": 0, "total": 1})
        self.assertIsNone(report["coverage"]["changed_files"]["verified"])
        self.assertTrue(report["human_review"]["required"])
        body = (self.root / "PR_REPORT.md").read_text(encoding="utf-8")
        self.assertIn("Human review", body)
        self.assertIn("indeterminate", body)

    def test_import_does_not_change_mission_or_claims(self):
        before = self.state()
        self.h.run_import(self.run_record("RUN-1"), "codex")
        after = self.state()
        self.assertEqual(before["mission"], after["mission"])
        self.assertEqual(before["claims"], after["claims"])
        self.assertTrue(self.h.validate()["passed"])


if __name__ == "__main__":
    unittest.main()
