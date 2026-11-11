import copy
import importlib.util
import json
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/harness.py'
spec = importlib.util.spec_from_file_location('harness80_core_tests', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='harness80-')
        self.root = Path(self.temp.name)
        (self.root / 'result.txt').write_text('correct', encoding='utf-8')
        self.h = module.Harness(self.root)
        self.mission = {'objective': 'Verify the bounded local result', 'mode': 'light', 'in_scope': ['result.txt'], 'out_of_scope': [],
                        'criteria': [{'id': 'C1', 'description': 'Exact fixture text', 'argv': [sys.executable, '-c',
                                      "from pathlib import Path; assert Path('result.txt').read_text() == 'correct'"], 'artifacts': ['result.txt']}],
                        'requirements': [{'id': 'R1', 'description': 'Bounded local text requirement', 'criteria': ['C1']}]}
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

    def add(self, identifier='T1', deps=None, claims=None):
        return self.h.task_add({'id': identifier, 'title': 'Verify fixture ' + identifier, 'criteria': ['C1'],
                                'depends_on': deps or [], 'relies_on': claims or [], 'priority': 1})

    def plan(self, task='legacy-task'):
        review = self.h.review('fixture')['review']
        return {'topic': 'fixture', 'task': task, 'premise': 'Exact text', 'residual': 'Execute the fixture assertion',
                'review_id': review['id'], 'reviewed_claims': review['claims'], 'criteria': ['C1'],
                'reverify_reason': 'Verify current task',
                'approach': {'method': 'exact text', 'inputs': 'result.txt', 'environment': 'local'}}

    def finish(self, task='legacy-task'):
        cid = self.h.start(self.plan(task))['cycle']
        self.h.check(cid, 'C1')
        self.h.close(cid, 'verified', 'Bounded acceptance achieved')
        return cid

    def test_task_graph_readiness_and_completion_need_real_proof(self):
        self.add()
        self.add('T2', ['T1'])
        self.assertEqual([t['id'] for t in self.h.task_ready()['ready']], ['T1'])
        self.refuse('TASK_BLOCKED', lambda: self.h.task_claim({'id': 'T2', 'owner': 'worker'}))
        self.h.task_claim({'id': 'T1', 'owner': 'worker'})
        self.refuse('TASK_EVIDENCE', lambda: self.h.task_complete({'id': 'T1'}))
        self.finish('T1')
        self.h.task_complete({'id': 'T1'})
        self.assertEqual([t['id'] for t in self.h.task_ready()['ready']], ['T2'])

    def test_task_cycle_needs_claim_and_does_not_relax_overlap(self):
        self.add()
        self.refuse('TASK_OWNER', lambda: self.h.start(self.plan('T1')))
        self.h.task_claim({'id': 'T1', 'owner': 'worker'})
        self.h.start(self.plan('T1'))
        self.refuse('OVERLAP', lambda: self.h.start(self.plan('T1')))

    def test_task_graph_rejects_self_dependencies_unknown_ids_and_duplicate_tasks(self):
        self.refuse('TASK_DEPENDENCY', lambda: self.add('T1', ['T1']))
        self.refuse('TASK_DEPENDENCY', lambda: self.add('T1', ['missing']))
        self.add()
        self.refuse('TASK_EXISTS', lambda: self.add())

    def test_task_claims_are_serialized(self):
        self.add()
        self.add('T2')
        self.h.task_claim({'id': 'T1', 'owner': 'worker'})
        self.refuse('TASK_OWNER', lambda: self.h.task_claim({'id': 'T2', 'owner': 'other worker'}))

    def test_stale_dependency_cannot_unlock_next_task(self):
        self.add()
        self.h.task_claim({'id': 'T1', 'owner': 'worker'})
        self.finish('T1')
        self.h.task_complete({'id': 'T1'})
        self.add('T2', ['T1'])
        (self.root / 'result.txt').write_text('stale', encoding='utf-8')
        self.assertFalse(self.h.task_ready()['ready'])
        self.refuse('TASK_BLOCKED', lambda: self.h.task_claim({'id': 'T2', 'owner': 'worker'}))

    def test_reopen_preserves_previous_task_history(self):
        self.add()
        self.h.task_claim({'id': 'T1', 'owner': 'worker'})
        self.finish('T1')
        self.h.task_complete({'id': 'T1'})
        cycles = self.state()['cycles']
        self.h.task_reopen({'id': 'T1', 'reason': 'User requested a regression check'})
        current = self.state()['cycles']
        self.assertEqual(len(current), len(cycles))
        self.assertEqual(current[0]['checks'], cycles[0]['checks'])
        self.assertEqual(current[0]['status'], 'needs_review')
        self.assertEqual(current[0]['status_history'][-1]['from'], 'verified')
        self.assertTrue(self.state()['tasks']['T1']['history'])

    def test_search_recovers_registered_aliases_and_real_record_status(self):
        cid = self.h.start(self.plan())['cycle']
        self.h.claim({'id': 'guess', 'topic': 'authentication', 'statement': 'OAuth credential issue is a hypothesis', 'kind': 'hypothesis', 'cycle': cid})
        self.h.alias_add({'alias': 'login', 'topic': 'authentication'})
        before = self.h.db.read_bytes()
        results = self.h.search('login')
        self.assertIn('guess', [row['id'] for row in results['results']])
        found = next(row for row in results['results'] if row['id'] == 'guess')
        self.assertEqual(found['status'], 'candidate')
        self.assertTrue(found['verify_before_reuse'])
        self.assertEqual(before, self.h.db.read_bytes())

    def test_search_handles_fts_syntax_as_data(self):
        result = self.h.search('" OR * ( )')
        self.assertIn(result['backend'], ('sqlite_fts5_derived_memory', 'substring_fallback'))

    def test_search_does_not_keep_a_stale_index(self):
        self.assertFalse(any(row['id'] == 'T1' for row in self.h.search('T1')['results']))
        self.add()
        self.assertTrue(any(row['id'] == 'T1' for row in self.h.search('T1')['results']))

    def test_traceability_and_final_assessment_distinguish_proof_from_links(self):
        matrix = self.h.traceability()
        self.assertEqual(matrix['requirements'][0]['status'], 'unverified')
        self.assertFalse(self.h.accept_mission()['accepted'])
        self.finish()
        self.assertEqual(self.h.traceability()['requirements'][0]['status'], 'verified_in_declared_scope')
        result = self.h.accept_mission()
        self.assertTrue(result['accepted'])
        self.assertFalse(result['universal_correctness_asserted'])

    def test_unmapped_requirement_blocks_completion_even_when_tests_pass(self):
        with self.h.state(write=True) as state:
            state['mission']['requirements'].append({'id': 'R2', 'description': 'Additional requirement', 'criteria': []})
            state['mission_hash'] = module.digest(state['mission'])
        self.finish()
        result = self.h.accept_mission()
        self.assertFalse(result['accepted'])
        self.assertIn('unverified_requirements', result['blockers'])

    def test_pending_registered_task_blocks_final_acceptance(self):
        self.add()
        self.finish()
        self.assertFalse(self.h.accept_mission()['accepted'])

    def test_mission_diff_identifies_criterion_removal_without_applying_it(self):
        before = self.state()
        mission = copy.deepcopy(before['mission'])
        mission['criteria'][0]['description'] = 'Changed criterion wording'
        proposal = {'expected_mission_hash': before['mission_hash'], 'expected_revision': before['revision'],
                    'reason': 'Explicit user request', 'authorization': {'source': 'user', 'reference': 'User approved proposal'}, 'mission': mission}
        preview = self.h.preview_mission(proposal)
        self.assertEqual(preview['structured_diff']['criteria']['modified'], ['C1'])
        self.assertEqual(before, self.state())

    def test_task_context_is_derived_and_includes_contract_and_blockers(self):
        self.add()
        before = self.h.db.read_bytes()
        context = self.h.context_pack('T1', output='CONTEXT.json')
        self.assertFalse(context['authoritative'])
        self.assertEqual(context['task']['id'], 'T1')
        self.assertIn('approval_boundaries', context)
        self.assertTrue(self.h.view_status('CONTEXT.json')['fresh'])
        self.assertEqual(before, self.h.db.read_bytes())
        self.h.alias_add({'alias': 'fixture', 'topic': 'result'})
        self.assertFalse(self.h.view_status('CONTEXT.json')['fresh'])

    def test_diagnostic_records_hypotheses_without_claiming_a_root_cause(self):
        (self.root / 'failure.txt').write_text('Reproducible failure observation', encoding='utf-8')
        result = self.h.diagnostic_add({'id': 'D1', 'symptom': 'Observed failure', 'evidence': 'failure.txt',
                                       'hypotheses': ['Potential cause'], 'criterion': 'C1', 'next_test': 'Execute C1 under the relevant condition'})
        self.assertFalse(result['root_cause_proven'])
        self.assertEqual(self.state()['claims'], {})

    def test_requirements_cannot_reference_unknown_criteria(self):
        mission = copy.deepcopy(self.mission)
        mission['requirements'][0]['criteria'] = ['missing']
        self.refuse('REQUIREMENT', lambda: self.h.normalize_mission(mission))

    def test_prepare_mission_accepts_requirement_proposals_without_applying_them(self):
        before = self.h.db.read_bytes()
        result = self.h.prepare_mission(self.mission)
        self.assertEqual(result['mission']['requirements'], self.mission['requirements'])
        self.assertFalse(result['can_apply'])
        self.assertEqual(before, self.h.db.read_bytes())

    def test_readonly_cli_commands_preserve_the_database_and_fail_closed_on_acceptance(self):
        self.add()
        before = self.h.db.read_bytes()
        for args, code in [(('tasks',), 0), (('task-ready',), 0), (('search', '--query', 'fixture'), 0),
                           (('traceability',), 0), (('accept-mission',), 3), (('trace',), 0), (('capabilities',), 0),
                           (('context-pack', '--task', 'T1', '--output', 'CONTEXT.json'), 0),
                           (('view-status', '--input', 'CONTEXT.json'), 0)]:
            result = subprocess.run([sys.executable, '-B', str(SCRIPT), '--project', str(self.root), *args], capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        self.assertEqual(before, self.h.db.read_bytes())

    def test_context_cannot_silently_drop_required_constraints_to_fit(self):
        self.add()
        with self.h.state(write=True) as state:
            state['mission']['out_of_scope'] = ['Critical protected boundary ' + 'x' * 8000]
            state['mission_hash'] = module.digest(state['mission'])
            state['tasks']['T1']['mission_hash'] = state['mission_hash']
        self.refuse('CONTEXT_SIZE', lambda: self.h.context_pack('T1', max_chars=4000))

    def test_final_assessment_fails_if_artifact_changes_after_a_passing_test(self):
        self.finish()
        (self.root / 'result.txt').write_text('changed after acceptance', encoding='utf-8')
        self.assertFalse(self.h.accept_mission()['accepted'])

    def test_search_returns_retracted_facts_without_restoring_them(self):
        cid = self.h.start(self.plan())['cycle']
        self.h.check(cid, 'C1')
        self.h.claim({'id': 'old-proof', 'topic': 'fixture', 'statement': 'Historical fixture statement', 'kind': 'fact', 'cycle': cid, 'criterion': 'C1'})
        self.h.close(cid, 'verified', 'Declared proof')
        (self.root / 'correction.txt').write_text('Explicit corrected interpretation', encoding='utf-8')
        self.h.retract({'id': 'old-proof', 'what_falls': 'Historical fixture statement', 'reason': 'User correction', 'correction_evidence': 'correction.txt'})
        row = next(row for row in self.h.search('Historical fixture statement')['results'] if row['id'] == 'old-proof')
        self.assertEqual(row['status'], 'retracted')
        self.assertTrue(row['verify_before_reuse'])

    def test_long_project_can_reverify_evolved_artifacts_without_erasing_old_proof(self):
        folder = self.root / 'evolving'
        folder.mkdir()
        (folder / 'result.txt').write_text('correct', encoding='utf-8')
        mission = copy.deepcopy(self.mission)
        mission['criteria'][0]['argv'][-1] = "from pathlib import Path; assert Path('result.txt').read_text().strip() == 'correct'"
        self.h = module.Harness(folder)
        self.h.init(mission)
        self.add()
        self.h.task_claim({'id': 'T1', 'owner': 'worker'})
        self.finish('T1')
        self.h.task_complete({'id': 'T1'})
        old_check = self.state()['cycles'][0]['checks'][0]
        (folder / 'result.txt').write_text('correct\n', encoding='utf-8')
        self.assertFalse(self.h.accept_mission()['accepted'])
        self.h.task_reopen({'id': 'T1', 'reason': 'Revalidate after an artifact changed; do not erase the earlier evidence'})
        self.h.task_claim({'id': 'T1', 'owner': 'worker'})
        self.finish('T1')
        self.h.task_complete({'id': 'T1'})
        self.assertEqual(self.state()['cycles'][0]['checks'][0], old_check)
        self.assertTrue(self.h.accept_mission()['accepted'])

    def test_reopening_task_invalidates_transitive_claim_cycles_without_deleting_them(self):
        self.add()
        self.h.task_claim({'id': 'T1', 'owner': 'worker'})
        root_cycle = self.h.start(self.plan('T1'))['cycle']
        self.h.check(root_cycle, 'C1')
        self.h.claim({'id': 'root', 'topic': 'fixture', 'statement': 'Root bounded observation', 'kind': 'fact', 'cycle': root_cycle, 'criterion': 'C1'})
        self.h.close(root_cycle, 'verified', 'Root checked')
        self.h.task_complete({'id': 'T1'})
        child_cycle = self.h.start(self.plan('legacy-child'))['cycle']
        self.h.check(child_cycle, 'C1')
        self.h.claim({'id': 'child', 'topic': 'fixture', 'statement': 'Dependent bounded observation', 'kind': 'fact',
                      'cycle': child_cycle, 'criterion': 'C1', 'depends_on': ['root']})
        self.h.close(child_cycle, 'verified', 'Dependent checked')
        original_checks = [cycle['checks'] for cycle in self.state()['cycles']]
        self.h.task_reopen({'id': 'T1', 'reason': 'Explicit review of the root proof'})
        state = self.state()
        self.assertEqual([cycle['checks'] for cycle in state['cycles']], original_checks)
        self.assertTrue(all(cycle['status'] == 'needs_review' for cycle in state['cycles']))
        self.assertEqual(state['claims']['child']['status'], 'needs_review')

    def test_search_recovers_old_stepback_decisions_without_promoting_them(self):
        self.h.step_back({'task': 'investigate', 'premise': 'Authentication mismatch', 'reference_review': 'Read the declared contract',
                          'data_model_review': 'Compared the relevant field', 'simpler_alternative': 'Reproduce before changing code',
                          'next_test': 'Investigate E_AUTH_491 as a hypothesis'})
        result = self.h.search('E_AUTH_491')
        row = next(row for row in result['results'] if row['kind'] == 'step_back')
        self.assertEqual(row['status'], 'recorded_not_verified')
        self.assertTrue(row['verify_before_reuse'])

    def test_claim_reverification_needs_new_executed_proof_and_preserves_identity(self):
        self.add()
        self.h.task_claim({'id': 'T1', 'owner': 'worker'})
        cid = self.h.start(self.plan('T1'))['cycle']
        self.h.check(cid, 'C1')
        statement = 'The bounded fixture check passed'
        self.h.claim({'id': 'F1', 'topic': 'fixture', 'statement': statement, 'kind': 'fact', 'cycle': cid, 'criterion': 'C1'})
        self.h.close(cid, 'verified', 'Root checked')
        self.h.task_complete({'id': 'T1'})
        self.add('T2', ['T1'], ['F1'])
        self.h.task_reopen({'id': 'T1', 'reason': 'Explicitly review previous proof'})
        self.h.task_claim({'id': 'T1', 'owner': 'worker'})
        next_cycle = self.h.start(self.plan('T1'))['cycle']
        entry = {'id': 'F1', 'statement': statement, 'cycle': next_cycle, 'criterion': 'C1', 'reason': 'Exact statement reviewed against new executed evidence'}
        self.refuse('EVIDENCE', lambda: self.h.claim_reverify(entry))
        self.h.check(next_cycle, 'C1')
        result = self.h.claim_reverify(entry)
        self.assertFalse(result['new_knowledge'])
        self.assertEqual(len(self.state()['claims']), 1)
        self.assertEqual(self.state()['claims']['F1']['verification_history'][0]['previous_cycle'], cid)
        self.h.close(next_cycle, 'verified', 'Renewed bounded proof')
        self.h.task_complete({'id': 'T1'})
        self.assertEqual(self.h.task_ready()['ready'][0]['id'], 'T2')

    def test_reverification_never_resurrects_a_retracted_statement(self):
        cid = self.h.start(self.plan())['cycle']
        self.h.check(cid, 'C1')
        self.h.claim({'id': 'F1', 'topic': 'fixture', 'statement': 'Old interpretation', 'kind': 'fact', 'cycle': cid, 'criterion': 'C1'})
        self.h.close(cid, 'verified', 'Old proof')
        (self.root / 'correction.txt').write_text('Explicit correction', encoding='utf-8')
        self.h.retract({'id': 'F1', 'what_falls': 'Old interpretation', 'reason': 'User correction', 'correction_evidence': 'correction.txt'})
        next_cycle = self.h.start(self.plan('recheck'))['cycle']
        self.h.check(next_cycle, 'C1')
        self.refuse('CLAIM_REVERIFY', lambda: self.h.claim_reverify({'id': 'F1', 'statement': 'Old interpretation', 'cycle': next_cycle, 'criterion': 'C1', 'reason': 'Cannot override the correction automatically'}))


if __name__ == '__main__':
    unittest.main()
