import importlib.util
import io
import json
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/harness.py'
spec = importlib.util.spec_from_file_location('harness80_operation_tests', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class Terminal(io.StringIO):
    def isatty(self):
        return True


class OperationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='harness80-ops-')
        self.root = Path(self.temp.name)
        (self.root / 'result.txt').write_text('correct', encoding='utf-8')
        self.h = module.Harness(self.root)
        self.h.init({'objective': 'Check the local fixture', 'mode': 'light', 'in_scope': ['result.txt'], 'out_of_scope': [],
                     'criteria': [{'id': 'C1', 'description': 'Read exact fixture text', 'argv': [sys.executable, '-c',
                                   "from pathlib import Path; assert Path('result.txt').read_text() == 'correct'"], 'artifacts': ['result.txt']}]})
        r = self.h.review('fixture')['review']
        self.cid = self.h.start({'topic': 'fixture', 'task': 'check', 'premise': 'exact text', 'residual': 'execute',
                                 'review_id': r['id'], 'criteria': ['C1'],
                                 'approach': {'method': 'assert fixture', 'inputs': 'result.txt', 'environment': 'local'}})['cycle']

    def tearDown(self):
        self.temp.cleanup()

    def prepare(self):
        return self.h.operation_prepare({'id': 'OP1', 'cycle': self.cid, 'criterion': 'C1', 'effect': 'local',
                                         'risk': 'read', 'reason': 'Execute the exact declared check', 'request_ref': 'Explicit test user request'})

    def refuse(self, code, call):
        with self.assertRaises(module.Refusal) as caught:
            call()
        self.assertEqual(caught.exception.code, code)

    def approve(self):
        token = self.h.operation_status('OP1')['confirmation']
        with patch.object(module.sys, 'stdin', Terminal()), patch.object(module.sys, 'stdout', Terminal()), \
             patch.object(module, 'input', return_value=token, create=True), \
             patch.dict(module.os.environ, {'CI': '', 'HARNESS_AUTOMATION': ''}):
            return self.h.operation_approve('OP1')

    def test_prepare_does_not_execute_and_unapproved_operation_is_blocked(self):
        result = self.prepare()
        self.assertEqual(result['status'], 'prepared')
        self.refuse('APPROVAL_REQUIRED', lambda: self.h.operation_run('OP1'))
        self.refuse('OPERATION_PENDING', lambda: self.h.check(self.cid, 'C1'))

    def test_human_approval_requires_real_terminal_and_does_not_accept_automation(self):
        self.prepare()
        with patch.object(module.sys, 'stdin', io.StringIO()), patch.object(module.sys, 'stdout', io.StringIO()):
            self.refuse('INTERACTIVE_REQUIRED', lambda: self.h.operation_approve('OP1'))
        with patch.object(module.sys, 'stdin', Terminal()), patch.object(module.sys, 'stdout', Terminal()), patch.dict(module.os.environ, {'HARNESS_AUTOMATION': '1'}):
            self.refuse('AUTOMATION_FORBIDDEN', lambda: self.h.operation_approve('OP1'))

    def test_approved_execution_records_check_checkpoint_and_consumes_approval(self):
        self.prepare()
        self.approve()
        result = self.h.operation_run('OP1')
        self.assertTrue(result['check']['passed'])
        status = self.h.operation_status('OP1')
        self.assertEqual(status['status'], 'completed')
        self.assertTrue(status['approval_consumed'])
        self.assertEqual(len(status['checkpoints']), 2)
        self.refuse('OPERATION_STATE', lambda: self.h.operation_run('OP1'))
        self.assertEqual(self.h.close(self.cid, 'verified', 'Bounded check passed')['status'], 'verified')

    def test_resource_change_invalidates_approval(self):
        self.prepare()
        self.approve()
        (self.root / 'result.txt').write_text('changed', encoding='utf-8')
        self.refuse('APPROVAL_STALE', lambda: self.h.operation_run('OP1'))

    def test_crash_after_admission_leaves_unknown_result_and_never_replays(self):
        self.prepare()
        self.approve()
        with patch.object(module.subprocess, 'run', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.h.operation_run('OP1')
        status = self.h.operation_status('OP1')
        self.assertTrue(status['reconciliation_required'])
        self.refuse('OPERATION_STATE', lambda: self.h.operation_run('OP1'))
        self.refuse('OPERATION_PENDING', lambda: self.h.check(self.cid, 'C1'))

    def test_reconciliation_is_not_a_fabricated_passing_check(self):
        self.prepare()
        self.approve()
        with patch.object(module.subprocess, 'run', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.h.operation_run('OP1')
        (self.root / 'reconciliation.txt').write_text('Observed current external/local outcome', encoding='utf-8')
        result = self.h.operation_reconcile({'id': 'OP1', 'outcome': 'completed', 'evidence': 'reconciliation.txt', 'reason': 'User inspected outcome'})
        self.assertFalse(result['verification_granted'])
        self.refuse('OPERATION_RECHECK', lambda: self.h.close(self.cid, 'verified', 'Not yet reverified'))
        self.assertTrue(self.h.check(self.cid, 'C1')['passed'])
        self.h.close(self.cid, 'verified', 'Fresh recheck passed')

    def test_interruption_does_not_erase_unresolved_operations(self):
        self.prepare()
        self.approve()
        with patch.object(module.subprocess, 'run', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.h.operation_run('OP1')
        self.h.interrupt(self.cid, 'Interrupted operation')
        result = self.h.accept_mission()
        self.assertFalse(result['accepted'])
        self.assertIn('unresolved_operations', result['blockers'])

    def test_adapter_cannot_execute_arbitrary_replacement_argv(self):
        entry = {'id': 'OP1', 'cycle': self.cid, 'criterion': 'C1', 'effect': 'local', 'risk': 'read',
                 'reason': 'fixture', 'request_ref': 'user request', 'argv': ['malicious replacement']}
        self.refuse('OPERATION', lambda: self.h.operation_prepare(entry))

    def test_wrong_confirmation_does_not_approve(self):
        self.prepare()
        with patch.object(module.sys, 'stdin', Terminal()), patch.object(module.sys, 'stdout', Terminal()), \
             patch.object(module, 'input', return_value='yes', create=True), \
             patch.dict(module.os.environ, {'CI': '', 'HARNESS_AUTOMATION': ''}):
            self.refuse('CONFIRMATION', lambda: self.h.operation_approve('OP1'))
        self.refuse('APPROVAL_REQUIRED', lambda: self.h.operation_run('OP1'))

    def test_trace_reports_coverage_limits_and_no_raw_outputs(self):
        self.prepare()
        self.approve()
        self.h.operation_run('OP1')
        report = self.h.trace()
        self.assertFalse(report['all_runtime_tools_observed'])
        self.assertTrue(report['events'])
        self.assertNotIn('stdout', json.dumps(report))

    def test_usage_provenance_never_promotes_estimates_to_measured_costs(self):
        self.h.usage_report({'id': 'U1', 'source': 'estimated', 'model': 'reported model', 'tokens': 100, 'usd': 0.02, 'reference': 'explicit estimate'})
        usage = self.h.trace()['usage'][0]
        self.assertEqual(usage['source'], 'estimated')
        self.refuse('USAGE', lambda: self.h.usage_report({'id': 'U2', 'source': 'estimated', 'model': 'x', 'tokens': -1, 'usd': 0.0, 'reference': 'invalid'}))

    def test_fresh_cli_process_cannot_replay_a_persisted_unknown_operation(self):
        self.prepare()
        self.approve()
        with patch.object(module.subprocess, 'run', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.h.operation_run('OP1')
        result = subprocess.run([sys.executable, '-B', str(SCRIPT), '--project', str(self.root), 'operation-run', '--id', 'OP1'], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)['code'], 'OPERATION_STATE')

    def test_piped_approval_is_refused_by_real_cli(self):
        self.prepare()
        token = self.h.operation_status('OP1')['confirmation']
        result = subprocess.run([sys.executable, '-B', str(SCRIPT), '--project', str(self.root), 'operation-approve', '--id', 'OP1'], input=token + '\n', capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)['code'], 'INTERACTIVE_REQUIRED')

    def test_pending_adapter_operation_blocks_using_an_earlier_pass_to_close(self):
        self.h.check(self.cid, 'C1')
        self.prepare()
        self.refuse('OPERATION_PENDING', lambda: self.h.close(self.cid, 'verified', 'Cannot skip the pending approval'))

    def test_single_use_operation_approval_does_not_authorize_mission_changes(self):
        self.prepare()
        approval = self.approve()
        self.assertFalse(approval['mission_revision_authorized'])

    def test_interrupted_cycle_can_reconcile_then_reverify_in_a_new_cycle(self):
        self.prepare()
        self.approve()
        with patch.object(module.subprocess, 'run', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.h.operation_run('OP1')
        self.h.interrupt(self.cid, 'Interrupted after operation admission')
        (self.root / 'reconciliation.txt').write_text('Observed the process stopped; outcome inspected', encoding='utf-8')
        self.h.operation_reconcile({'id': 'OP1', 'outcome': 'not_executed', 'evidence': 'reconciliation.txt', 'reason': 'Concrete inspected outcome'})
        self.assertFalse(self.h.accept_mission()['accepted'])
        review = self.h.review('fixture')['review']
        cid = self.h.start({'topic': 'fixture', 'task': 'reverify', 'premise': 'current state', 'residual': 'fresh proof',
                            'review_id': review['id'], 'criteria': ['C1'],
                            'approach': {'method': 'reconcile and verify', 'inputs': 'result.txt', 'environment': 'local'}})['cycle']
        self.h.check(cid, 'C1')
        self.h.close(cid, 'verified', 'Fresh proof after recovery')
        self.assertTrue(self.h.accept_mission()['accepted'])


if __name__ == '__main__':
    unittest.main()
