import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/harness.py'
spec = importlib.util.spec_from_file_location('harness78', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
Harness, Refusal = module.Harness, module.Refusal


class HarnessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='harness78-')
        self.root = Path(self.temp.name)
        (self.root / 'result.txt').write_text('correct', encoding='utf-8')
        self.h = Harness(self.root)
        self.mission = {
            'objective': 'Verify a local fixture without changing external systems',
            'mode': 'light', 'in_scope': ['result.txt'], 'out_of_scope': ['external services'],
            'criteria': [{'id': 'C1', 'description': 'Result is correct', 'argv': [sys.executable, '-c',
                          "from pathlib import Path; assert Path('result.txt').read_text() == 'correct'"],
                          'artifacts': ['result.txt']}],
        }
        self.h.init(self.mission)

    def tearDown(self):
        self.temp.cleanup()

    def plan(self, method='read-result', premise='result is correct', **extra):
        review = self.h.review('result')['review']
        return {'topic': 'result', 'task': 'verify', 'premise': premise,
                'residual': 'Check the actual file with the declared assertion',
                'review_id': review['id'], 'reviewed_claims': review['claims'],
                'criteria': ['C1'], 'approach': {'method': method, 'inputs': 'result.txt', 'environment': 'local fixture'}, **extra}

    def refuse(self, code, callback):
        with self.assertRaises(Refusal) as caught:
            callback()
        self.assertEqual(caught.exception.code, code)

    def finish(self):
        cid = self.h.start(self.plan())['cycle']
        self.assertTrue(self.h.check(cid, 'C1')['passed'])
        return self.h.close(cid, 'verified', 'Acceptance achieved')

    def test_executed_evidence_required_for_done(self):
        cid = self.h.start(self.plan())['cycle']
        self.refuse('EVIDENCE', lambda: self.h.close(cid, 'verified', 'complete'))
        self.assertTrue(self.h.check(cid, 'C1')['passed'])
        self.assertTrue(self.h.close(cid, 'verified', 'complete')['progress'])

    def test_changed_artifact_invalidates_done(self):
        cid = self.h.start(self.plan())['cycle']
        self.h.check(cid, 'C1')
        (self.root / 'result.txt').write_text('changed', encoding='utf-8')
        self.refuse('STALE_ARTIFACT', lambda: self.h.close(cid, 'verified', 'complete'))

    def test_blind_retry_blocked_after_two_failed_cycles(self):
        (self.root / 'result.txt').write_text('wrong', encoding='utf-8')
        for n in range(2):
            cid = self.h.start(self.plan())['cycle']
            self.assertFalse(self.h.check(cid, 'C1')['passed'])
            self.h.close(cid, 'blocked', 'Investigate incorrect fixture')
        self.refuse('G2_BLIND_RETRY', lambda: self.h.start(self.plan()))
        self.assertTrue(self.h.start(self.plan(method='new discriminating read'))['cycle'])

    def test_active_cycle_prevents_overlap(self):
        self.h.start(self.plan())
        self.refuse('OVERLAP', lambda: self.h.start(self.plan(method='second run')))

    def test_review_receipt_stales_after_state_update(self):
        old_plan = self.plan()
        self.h.review('another topic')
        self.refuse('G1_STALE', lambda: self.h.start(old_plan))

    def test_no_rework_without_explicit_revalidation_reason(self):
        self.finish()
        self.refuse('G1_REWORK', lambda: self.h.start(self.plan()))
        self.assertTrue(self.h.start(self.plan(reverify_reason='Check after fixture change'))['cycle'])

    def test_acceptance_cannot_be_added_after_start(self):
        cid = self.h.start(self.plan())['cycle']
        self.refuse('G3_CRITERIA', lambda: self.h.check(cid, 'invented'))

    def test_resume_in_fresh_process_needs_no_chat(self):
        self.finish()
        proc = subprocess.run([sys.executable, str(SCRIPT), '--project', str(self.root), 'resume'], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        result = json.loads(proc.stdout)['result']
        self.assertEqual(result['recent_cycles'][0]['status'], 'verified')
        self.assertEqual(result['recent_cycles'][0]['next_step'], 'Acceptance achieved')
        self.assertEqual(result['mission']['objective'], self.mission['objective'])

    def test_no_escape_or_store_as_evidence(self):
        self.refuse('PATH', lambda: self.h.project_file('../other'))
        self.refuse('PATH', lambda: self.h.project_file('.harness/state.yaml'))

    def test_init_never_resets_history(self):
        self.finish()
        self.refuse('EXISTS', lambda: self.h.init(self.mission))
        self.assertEqual(len(self.h.resume()['recent_cycles']), 1)

    def alternative(self, mode='light', budget=None):
        folder = self.root / ('alternate-' + str(len(list(self.root.iterdir()))))
        folder.mkdir()
        (folder / 'result.txt').write_text('correct', encoding='utf-8')
        mission = copy.deepcopy(self.mission)
        mission['mode'] = mode
        mission['budget'] = budget or {}
        harness = Harness(folder)
        harness.init(mission)
        return harness

    def test_strict_mode_requires_reference_and_simplest_test(self):
        self.h = self.alternative(mode='strict')
        self.refuse('STRICT', lambda: self.h.start(self.plan()))
        cid = self.h.start(self.plan(reference_review='Fixture definition read', simplest_test='Declared exact assertion'))['cycle']
        self.assertTrue(self.h.check(cid, 'C1')['passed'])

    def test_nonprogress_requires_real_stepback_record(self):
        for n in range(3):
            cid = self.h.start(self.plan(method=f'controlled observation {n}'))['cycle']
            self.h.close(cid, 'blocked', 'Need evidence; creating a cycle is not progress')
        self.refuse('STEP_BACK_DUE', lambda: self.h.start(self.plan(method='more observations')))
        self.h.step_back({'task': 'verify', 'premise': 'result is correct',
                          'reference_review': 'Read fixture', 'data_model_review': 'Text value only',
                          'simpler_alternative': 'Use the already-declared assertion', 'next_test': 'Run C1'})
        self.assertTrue(self.h.start(self.plan(method='declared assertion'))['cycle'])

    def test_consolidation_must_happen_when_due(self):
        self.h = self.alternative(budget={'consolidate_every': 1})
        self.finish()
        self.refuse('CONSOLIDATION_DUE', lambda: self.h.start(self.plan(reverify_reason='regression check')))
        self.h.consolidate({key: [] for key in ('failures_and_dead_ends', 'retractions_and_repairs', 'established_facts', 'open_questions', 'patterns_and_actions')})
        self.assertTrue(self.h.start(self.plan(reverify_reason='regression check'))['cycle'])

    def test_retraction_propagates_and_preserves_history(self):
        cid = self.h.start(self.plan())['cycle']
        self.h.check(cid, 'C1')
        for name, deps in [('root', []), ('child', ['root']), ('grandchild', ['child'])]:
            self.h.claim({'id': name, 'topic': 'result', 'statement': f'Fixture claim {name}', 'kind': 'fact',
                          'cycle': cid, 'criterion': 'C1', 'depends_on': deps})
        self.h.close(cid, 'verified', 'Verified fixture')
        (self.root / 'correction.txt').write_text('Explicit correction fixture', encoding='utf-8')
        result = self.h.retract({'id': 'root', 'what_falls': 'Fixture claim root', 'reason': 'Explicit correction', 'correction_evidence': 'correction.txt'})
        self.assertEqual(result['dependent_claims_needing_review'], ['child', 'grandchild'])
        state = self.h.resume()
        self.assertEqual(state['claims']['root']['statement'], 'Fixture claim root')
        self.assertEqual(state['claims']['root']['status'], 'retracted')
        self.assertEqual(state['claims']['grandchild']['status'], 'needs_review')
        self.assertEqual(state['recent_cycles'][0]['status'], 'needs_review')
        self.refuse('DEPENDENCY', lambda: self.h.start(self.plan(relies_on=['grandchild'])))

    def test_hypothesis_is_not_automatically_fact(self):
        cid = self.h.start(self.plan())['cycle']
        self.h.claim({'id': 'guess', 'topic': 'result', 'statement': 'Possibly true fixture', 'kind': 'hypothesis', 'cycle': cid})
        self.assertEqual(self.h.resume()['claims']['guess']['status'], 'candidate')
        self.refuse('DEPENDENCY', lambda: self.h.verified_dependencies(self.h.resume(), ['guess']))

    def test_duplicate_claim_does_not_create_false_progress(self):
        cid = self.h.start(self.plan())['cycle']
        self.h.claim({'id': 'guess', 'topic': 'result', 'statement': 'Possibly true fixture', 'kind': 'hypothesis', 'cycle': cid})
        self.refuse('DUPLICATE_CLAIM', lambda: self.h.claim({'id': 'guess2', 'topic': 'result', 'statement': '  possibly TRUE fixture ', 'kind': 'hypothesis', 'cycle': cid}))

    def test_cycle_and_reported_cost_budgets(self):
        self.h = self.alternative(budget={'max_cycles': 1})
        self.finish()
        self.refuse('BUDGET', lambda: self.h.start(self.plan(reverify_reason='another run')))
        self.h = self.alternative(budget={'max_reported_usd': 0.1})
        cid = self.h.start(self.plan())['cycle']
        self.h.check(cid, 'C1')
        self.h.close(cid, 'verified', 'complete', reported_usd=0.1, usage_source='synthetic client fixture')
        self.refuse('BUDGET', lambda: self.h.start(self.plan(reverify_reason='another run')))

    def test_invalid_usage_cannot_bypass_cost_budget(self):
        cid = self.h.start(self.plan())['cycle']
        self.refuse('USAGE', lambda: self.h.close(cid, 'blocked', 'pending', reported_usd=float('nan')))

    def test_integrity_check_catches_stale_evidence(self):
        self.finish()
        self.assertTrue(self.h.validate()['passed'])
        (self.root / 'result.txt').write_text('changed after completion', encoding='utf-8')
        result = self.h.validate()
        self.assertFalse(result['passed'])
        self.assertEqual(result['issues'][0]['kind'], 'STALE_ARTIFACT')
        self.assertIsNone(self.h.metrics()['criteria_verified'])
        self.assertEqual(self.h.metrics()['recorded_criteria_verified'], 1)

    def test_backup_is_consistent_and_export_cannot_overwrite_user_file(self):
        self.finish()
        result = self.h.backup('snapshot.yaml')
        self.assertEqual(result['integrity'], 'ok')
        self.assertTrue((self.root / 'snapshot.yaml').is_file())
        report = self.h.export('report.md')
        self.assertTrue((self.root / 'report.md').read_text(encoding='utf-8').startswith('# GENERATED'))
        self.h.export('report.md')
        self.refuse('PROTECTED_OUTPUT', lambda: self.h.export('result.txt'))

    def test_real_subprocess_timeout_is_failure(self):
        mission = copy.deepcopy(self.mission)
        mission['budget'] = {'max_check_seconds': 1}
        mission['criteria'][0]['argv'] = [sys.executable, '-c', 'import time; time.sleep(3)']
        folder = self.root / 'timeout-fixture'
        folder.mkdir()
        (folder / 'result.txt').write_text('correct', encoding='utf-8')
        self.h = Harness(folder)
        self.h.init(mission)
        cid = self.h.start(self.plan())['cycle']
        result = self.h.check(cid, 'C1')
        self.assertEqual(result['outcome'], 'timeout')
        self.assertFalse(result['passed'])

    def test_existing_claims_must_be_acknowledged_after_review(self):
        cid = self.h.start(self.plan())['cycle']
        self.h.claim({'id': 'guess', 'topic': 'result', 'statement': 'Possibly true fixture', 'kind': 'hypothesis', 'cycle': cid})
        self.h.interrupt(cid, 'Await clarification')
        plan = self.plan()
        plan['reviewed_claims'] = []
        self.refuse('G1_UNREAD', lambda: self.h.start(plan))

    def test_mission_cannot_change_while_cycle_is_active(self):
        cid = self.h.start(self.plan())['cycle']
        # Simulates out-of-band corruption, not a supported amendment API.
        with self.h.state(write=True) as state:
            state['mission']['criteria'][0]['argv'] = [sys.executable, '-c', 'pass']
        self.refuse('MISSION_CHANGED', lambda: self.h.check(cid, 'C1'))

    def test_timebox_blocks_late_execution(self):
        cid = self.h.start(self.plan())['cycle']
        with self.h.state(write=True) as state:
            state['cycles'][0]['started'] = '2000-01-01T00:00:00+00:00'
        self.refuse('TIMEBOX', lambda: self.h.check(cid, 'C1'))

    def test_cli_refusal_produces_measurable_gate_count(self):
        self.finish()
        plan = self.plan()
        path = self.root / 'plan.json'
        path.write_text(json.dumps(plan), encoding='utf-8')
        result = subprocess.run([sys.executable, str(SCRIPT), '--project', str(self.root), 'start', '--input', str(path)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)['code'], 'G1_REWORK')
        self.assertEqual(self.h.metrics()['gate_refusals_recorded_by_cli'], 1)

    def test_two_processes_cannot_start_overlapping_cycles(self):
        plan = self.plan()
        path = self.root / 'concurrent-plan.json'
        path.write_text(json.dumps(plan), encoding='utf-8')
        command = [sys.executable, str(SCRIPT), '--project', str(self.root), 'start', '--input', str(path)]
        processes = [subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for _ in range(2)]
        results = []
        for proc in processes:
            out, err = proc.communicate(timeout=20)
            results.append((proc.returncode, json.loads(out)))
        self.assertEqual(sorted(code for code, _ in results), [0, 2])
        refusal = next(value for code, value in results if code == 2)
        self.assertEqual(refusal['code'], 'OVERLAP')
        self.assertEqual(len(self.h.resume()['active_cycles']), 1)

    def test_raw_command_output_is_not_persisted(self):
        folder = self.root / 'output-fixture'
        folder.mkdir()
        (folder / 'result.txt').write_text('correct', encoding='utf-8')
        marker = 'FAKE_SENSITIVE_MARKER_123'
        (folder / 'emit.py').write_text(f'print({marker!r})', encoding='utf-8')
        mission = copy.deepcopy(self.mission)
        mission['criteria'][0]['argv'] = [sys.executable, 'emit.py']
        self.h = Harness(folder)
        self.h.init(mission)
        cid = self.h.start(self.plan())['cycle']
        result = self.h.check(cid, 'C1')
        self.assertTrue(result['passed'])
        self.assertNotIn(marker, json.dumps(self.h.resume()))


if __name__ == '__main__':
    unittest.main()
