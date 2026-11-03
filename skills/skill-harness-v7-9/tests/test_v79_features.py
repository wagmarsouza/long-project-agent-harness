import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/harness.py'
spec = importlib.util.spec_from_file_location('harness79_features', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class FeatureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='harness79-')
        self.root = Path(self.temp.name)
        (self.root / 'result.txt').write_text('correct', encoding='utf-8')
        self.h = module.Harness(self.root)
        self.mission = {'objective': 'Verify a local result', 'mode': 'light',
                        'in_scope': ['result.txt'], 'out_of_scope': ['external effects'],
                        'criteria': [{'id': 'C1', 'description': 'Result text is correct',
                                      'argv': [sys.executable, '-c', "from pathlib import Path; assert Path('result.txt').read_text() == 'correct'"],
                                      'artifacts': ['result.txt']}]}
        self.h.init(self.mission)

    def tearDown(self):
        self.temp.cleanup()

    def state(self):
        with self.h.state() as state:
            return copy.deepcopy(state)

    def refuse(self, code, call):
        with self.assertRaises(module.Refusal) as caught:
            call()
        self.assertEqual(caught.exception.code, code)

    def start(self):
        review = self.h.review('fixture')['review']
        return self.h.start({'topic': 'fixture', 'task': 'check-fixture', 'premise': 'exact text',
                             'residual': 'execute assertion', 'review_id': review['id'], 'reviewed_claims': [],
                             'criteria': ['C1'], 'approach': {'method': 'assert text', 'inputs': 'result.txt', 'environment': 'local'}})['cycle']

    def scope(self):
        cycle = self.start()
        check = self.h.check(cycle, 'C1')
        return {'cycle': cycle, 'check_id': check['id'], 'method': 'dynamic', 'environment': 'local fixture',
                'verifies': ['The exact current text equals correct'], 'does_not_verify': ['Production integration'],
                'untested': ['Other inputs'], 'coverage': []}

    def test_scope_requires_real_check_and_cannot_mark_done(self):
        entry = self.scope()
        before = self.state()
        result = self.h.evidence_scope(entry)
        self.assertFalse(result['semantic_truth_verified'])
        after = self.state()
        self.assertEqual(before['cycles'], after['cycles'])
        self.assertEqual(before['claims'], after['claims'])
        self.assertEqual(after['cycles'][0]['status'], 'active')
        entry['check_id'] = 'invented'
        self.refuse('EVIDENCE', lambda: self.h.evidence_scope(entry))

    def test_scope_cannot_accept_forged_pass_or_approval_fields(self):
        entry = self.scope()
        entry['passed'] = True
        self.refuse('EVIDENCE_SCOPE', lambda: self.h.evidence_scope(entry))

    def test_scope_cannot_promote_failed_check(self):
        entry = self.scope()
        (self.root / 'result.txt').write_text('wrong', encoding='utf-8')
        failed = self.h.check(entry['cycle'], 'C1')
        entry['check_id'] = failed['id']
        result = self.h.evidence_scope(entry)
        self.assertFalse(result['check_passed'])
        self.refuse('EVIDENCE', lambda: self.h.close(entry['cycle'], 'verified', 'not actually done'))

    def test_scope_checks_artifact_freshness_and_superseded_checks(self):
        entry = self.scope()
        (self.root / 'result.txt').write_text('changed', encoding='utf-8')
        self.refuse('STALE_ARTIFACT', lambda: self.h.evidence_scope(entry))
        self.h.check(entry['cycle'], 'C1')
        self.refuse('STALE_CHECK', lambda: self.h.evidence_scope(entry))

    def test_coverage_rejects_false_arithmetic_without_claiming_truth(self):
        entry = self.scope()
        row = {'label': 'declared cases', 'numerator': 2, 'denominator': 1, 'unit': 'cases',
               'universe': 'one declared local case', 'exclusions': []}
        entry['coverage'] = [row]
        self.refuse('COVERAGE', lambda: self.h.evidence_scope(entry))
        row['numerator'], row['denominator'] = 0, 0
        result = self.h.evidence_scope(entry)
        self.assertIsNone(result['declaration']['coverage'][0]['percentage'])
        row['numerator'], row['denominator'] = 2, None
        result = self.h.evidence_scope(entry)
        self.assertIsNone(result['declaration']['coverage'][0]['percentage'])
        self.assertFalse(result['semantic_truth_verified'])

    def test_scope_requires_explicit_limits_and_does_not_overwrite_history(self):
        entry = self.scope()
        del entry['untested']
        self.refuse('EVIDENCE_SCOPE', lambda: self.h.evidence_scope(entry))
        entry['untested'] = []
        self.h.evidence_scope(entry)
        first = self.state()['evidence_scopes'][0]
        entry['does_not_verify'].append('Network behavior')
        self.h.evidence_scope(entry)
        self.assertEqual(first, self.state()['evidence_scopes'][0])

    def test_capsule_is_derived_and_changes_no_database_bytes(self):
        before = self.h.db.read_bytes()
        capsule = self.h.capsule(output='CAPSULE.json')
        self.assertEqual(before, self.h.db.read_bytes())
        self.assertFalse(capsule['authoritative'])
        self.assertFalse(capsule['mission_complete_asserted'])
        self.assertTrue(self.h.capsule_status('CAPSULE.json')['fresh'])

    def test_capsule_detects_state_changes_and_artifact_drift(self):
        self.h.capsule(output='CAPSULE.json')
        (self.root / 'result.txt').write_text('changed', encoding='utf-8')
        self.assertFalse(self.h.capsule_status('CAPSULE.json')['fresh'])
        self.h.capsule(output='CAPSULE.json')
        self.h.review('new revision')
        self.assertFalse(self.h.capsule_status('CAPSULE.json')['fresh'])

    def test_capsule_tampering_is_not_loaded_as_state(self):
        self.h.capsule(output='CAPSULE.json')
        path = self.root / 'CAPSULE.json'
        content = json.loads(path.read_text(encoding='utf-8'))
        content['mission']['objective'] = 'pretend a different mission'
        path.write_text(json.dumps(content), encoding='utf-8')
        self.assertFalse(self.h.capsule_status('CAPSULE.json')['fresh'])
        self.assertEqual(self.state()['mission']['objective'], self.mission['objective'])
        self.refuse('MISSION', lambda: self.h.normalize_mission(content))

    def test_capsule_reports_omissions_instead_of_silently_losing_records(self):
        with self.h.state(write=True) as state:
            for n in range(80):
                state['claims'][str(n)] = {'id': str(n), 'topic': 'fixture', 'statement': 'candidate ' + str(n),
                                           'kind': 'hypothesis', 'status': 'candidate', 'depends_on': [], 'cycle': 1}
        capsule = self.h.capsule(max_chars=6000)
        self.assertLessEqual(len(json.dumps(capsule, ensure_ascii=False, indent=2)), 6000)
        self.assertGreater(capsule['collections']['claims']['omitted'], 0)
        self.assertEqual(len(self.state()['claims']), 80)

    def test_derived_outputs_cannot_overwrite_unrelated_files_or_store(self):
        (self.root / 'notes.json').write_text('{"mine": true}', encoding='utf-8')
        self.refuse('PROTECTED_OUTPUT', lambda: self.h.capsule(output='notes.json'))
        self.refuse('PATH', lambda: self.h.capsule(output='.harness/state.sqlite'))
        self.refuse('PATH', lambda: self.h.capsule(output='../escape.json'))

    def test_preparer_does_not_invent_tests_or_authorize_execution(self):
        before = self.h.db.read_bytes()
        draft = self.h.prepare_mission({'objective': 'Make it better'}, output='DRAFT.json')
        self.assertEqual(draft['status'], 'needs_clarification')
        self.assertTrue(draft['open_decisions'])
        self.assertFalse(draft['can_apply'])
        self.assertIsNone(draft['mission']['criteria'])
        self.assertEqual(self.h.db.read_bytes(), before)

    def test_complete_draft_still_requires_review_and_cannot_be_initialized_directly(self):
        before = self.state()
        draft = self.h.prepare_mission(self.mission)
        self.assertEqual(draft['status'], 'ready_for_review')
        self.assertFalse(draft['can_apply'])
        self.assertEqual(self.state(), before)
        new_root = self.root / 'new-project'
        new_root.mkdir()
        new = module.Harness(new_root)
        self.refuse('MISSION', lambda: new.init(draft))
        self.assertFalse(new.db.exists())

    def test_preparation_works_without_initializing_a_new_project(self):
        folder = self.root / 'uninitialized'
        folder.mkdir()
        other = module.Harness(folder)
        draft = other.prepare_mission(self.mission, output='DRAFT.json')
        self.assertEqual(draft['status'], 'ready_for_review')
        self.assertFalse(other.db.parent.exists())

    def test_preparer_never_executes_proposed_test_commands(self):
        request = copy.deepcopy(self.mission)
        request['criteria'][0]['argv'] = [sys.executable, '-c', "from pathlib import Path; Path('SHOULD_NOT_EXIST').write_text('bad')"]
        draft = self.h.prepare_mission(request)
        self.assertEqual(draft['status'], 'ready_for_review')
        self.assertFalse((self.root / 'SHOULD_NOT_EXIST').exists())

    def test_preparer_refuses_auto_apply_and_does_not_change_existing_contract(self):
        request = copy.deepcopy(self.mission)
        request['objective'] = 'new requested objective'
        draft = self.h.prepare_mission(request)
        self.assertNotEqual(draft['mission']['objective'], self.state()['mission']['objective'])
        request['auto_apply'] = True
        self.refuse('DRAFT', lambda: self.h.prepare_mission(request))

    def test_read_only_feature_cli_does_not_write_audit_or_invalidate_receipts(self):
        review = self.h.review('fixture')['review']
        before = self.h.db.read_bytes()
        path = self.root / 'request.json'
        path.write_text(json.dumps(self.mission), encoding='utf-8')
        for args in [('prepare-mission', '--input', str(path)), ('capsule', '--output', 'CAPSULE.json'),
                     ('capsule-status', '--input', 'CAPSULE.json')]:
            proc = subprocess.run([sys.executable, '-B', str(SCRIPT), '--project', str(self.root), *args], capture_output=True, text=True, timeout=10)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(before, self.h.db.read_bytes())
        self.assertEqual(review['revision'], self.state()['revision'])

    def test_preparer_protects_unrelated_output(self):
        (self.root / 'request.json').write_text(json.dumps(self.mission), encoding='utf-8')
        self.refuse('PROTECTED_OUTPUT', lambda: self.h.prepare_mission(self.mission, output='request.json'))

    def test_task_proposals_only_copy_supplied_criteria_without_inventing_dependencies(self):
        draft = self.h.prepare_mission(self.mission)
        task = draft['task_proposals'][0]
        self.assertEqual(task['verification_argv_from_request'], self.mission['criteria'][0]['argv'])
        self.assertEqual(task['criteria'], ['C1'])
        self.assertIsNone(task['dependencies'])
        self.assertIsNone(task['approach'])
        self.assertFalse(draft['task_plan_ready'])
        self.assertEqual(self.h.prepare_mission({'objective': 'unclear'})['task_proposals'], [])

    def test_scope_with_invalid_method_or_boolean_counts_is_rejected(self):
        entry = self.scope()
        entry['method'] = 'universal-proof'
        self.refuse('EVIDENCE_SCOPE', lambda: self.h.evidence_scope(entry))
        entry['method'] = 'dynamic'
        entry['coverage'] = [{'label': 'cases', 'numerator': True, 'denominator': 1, 'unit': 'cases', 'universe': 'one case', 'exclusions': []}]
        self.refuse('COVERAGE', lambda: self.h.evidence_scope(entry))

    def test_passing_check_is_not_automatically_annotated_or_declared_universal(self):
        entry = self.scope()
        self.assertNotIn('evidence_scopes', self.state())
        annotation = self.h.evidence_scope(entry)
        self.assertEqual(annotation['declaration']['does_not_verify'], ['Production integration'])
        self.assertFalse(annotation['semantic_truth_verified'])

    def test_capsule_cli_returns_failure_for_stale_capsule(self):
        self.h.capsule(output='CAPSULE.json')
        self.h.review('changed')
        proc = subprocess.run([sys.executable, '-B', str(SCRIPT), '--project', str(self.root), 'capsule-status', '--input', 'CAPSULE.json'], capture_output=True, text=True, timeout=10)
        self.assertEqual(proc.returncode, 3)
        self.assertFalse(json.loads(proc.stdout)['result']['fresh'])

    def test_capsule_from_different_project_cannot_be_treated_as_fresh(self):
        payload = self.h.capsule(output='CAPSULE.json')
        payload['source']['project_root'] = str(self.root / 'other')
        payload['payload_sha256'] = module.digest({k: v for k, v in payload.items() if k != 'payload_sha256'})
        (self.root / 'CAPSULE.json').write_text(json.dumps(payload), encoding='utf-8')
        self.assertFalse(self.h.capsule_status('CAPSULE.json')['fresh'])

    def test_generated_draft_cannot_be_used_as_a_mission_revision_or_approval(self):
        request = copy.deepcopy(self.mission)
        request['objective'] = 'Different scope'
        draft = self.h.prepare_mission(request)
        before = self.state()
        self.refuse('REVISION', lambda: self.h.preview_mission(draft))
        self.assertEqual(self.state(), before)

    def test_scope_integrity_damage_is_reported_without_promoting_claims(self):
        self.h.evidence_scope(self.scope())
        with self.h.state(write=True) as state:
            state['evidence_scopes'][0]['declaration']['verifies'] = ['tampered']
        audit = self.h.validate()
        self.assertFalse(audit['passed'])
        self.assertIn('evidence_scope_integrity', [issue['kind'] for issue in audit['issues']])


    def test_scopes_can_be_recovered_read_only_with_exact_limits(self):
        entry = self.scope()
        self.h.evidence_scope(entry)
        before = self.h.db.read_bytes()
        result = self.h.evidence_scopes(entry['cycle'])
        self.assertEqual(result['annotations'][0]['declaration']['untested'], ['Other inputs'])
        self.assertEqual(result['total'], 1)
        self.assertFalse(result['semantic_truth_verified'])
        self.assertEqual(before, self.h.db.read_bytes())

    def test_capsule_refuses_artifact_change_during_its_audit(self):
        validate = self.h.validate
        def racing_audit():
            result = validate()
            (self.root / 'result.txt').write_text('changed during audit', encoding='utf-8')
            return result
        with patch.object(self.h, 'validate', side_effect=racing_audit):
            self.refuse('CAPSULE_DRIFT', lambda: self.h.capsule(output='CAPSULE.json'))
        self.assertFalse((self.root / 'CAPSULE.json').exists())

    def test_capsule_never_silently_truncates_identifiers(self):
        exact_id = 'claim-' + 'x' * 650
        with self.h.state(write=True) as state:
            state['claims'][exact_id] = {'id': exact_id, 'topic': 'fixture', 'statement': 'Candidate for identifier preservation',
                                        'kind': 'hypothesis', 'status': 'candidate', 'depends_on': [], 'cycle': 1}
        capsule = self.h.capsule(max_chars=6000)
        items = capsule['collections']['claims']['items']
        self.assertTrue(not items or items[0]['id'] == exact_id)
        self.assertEqual(capsule['collections']['claims']['shown'] + capsule['collections']['claims']['omitted'], 1)


if __name__ == '__main__':
    unittest.main()
