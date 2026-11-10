import copy
import hashlib
import importlib.util
import json
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/harness.py'
spec = importlib.util.spec_from_file_location('control82_tests', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

PROMPT = ('KEEP_SCOPE: never weaken acceptance.\nKEEP_PROOF: evidence first.\n'
          '<!-- objectives -->\nDeliver the next reviewed item.\n<!-- /objectives -->\n'
          '<!-- scenario -->\nA generic delivery project.\n<!-- /scenario -->\n'
          'Later safeguards remain protected too.\n')


class PeriodicTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='control82-')
        self.root = Path(self.temp.name)
        for folder in ('notes', 'observations', 'reports'):
            (self.root / folder).mkdir()
        (self.root / 'proof.txt').write_text('ok', encoding='utf-8')
        (self.root / 'governing.md').write_text(PROMPT, encoding='utf-8')
        self.items = {'ITEM-A': 'planned', 'ITEM-B': 'planned'}
        self.observation(0)
        self.policy = {
            'every': 2, 'notes_pattern': 'notes/cycle-{cycle}.md',
            'observation_pattern': 'observations/cycle-{cycle}.json',
            'baseline': 'observations/cycle-0.json',
            'inventory': {'categories': ['planned', 'delivered'], 'total': 2, 'monotonic': ['delivered']},
            'digest_pattern': 'reports/digest-{start}-{end}.json',
            'governing_file': 'governing.md', 'invariant_markers': ['KEEP_SCOPE', 'KEEP_PROOF'], 'stale_markers': ['OLD_TARGET'],
            'mutable_sections': {
                'objectives': {'begin': '<!-- objectives -->', 'end': '<!-- /objectives -->'},
                'scenario': {'begin': '<!-- scenario -->', 'end': '<!-- /scenario -->'},
            },
        }
        self.mission = {'objective': 'Deliver a bounded general-purpose project', 'mode': 'light', 'in_scope': ['local fixtures'],
                        'out_of_scope': ['external actions'], 'criteria': [{'id': 'C1', 'description': 'Exact fixture',
                        'argv': [sys.executable, '-c', "from pathlib import Path; assert Path('proof.txt').read_text() == 'ok'"],
                        'artifacts': ['proof.txt']}], 'budget': {'consolidate_every': 2, 'max_cycles': 8, 'max_no_progress': 8},
                        'periodic_review': self.policy}
        self.h = module.Harness(self.root)
        self.h.init(self.mission)

    def tearDown(self):
        self.temp.cleanup()

    def state(self):
        with self.h.state() as state:
            return copy.deepcopy(state)

    def refuse(self, code, call):
        with self.assertRaises(module.Refusal) as caught:
            call()
        self.assertEqual(code, caught.exception.code)

    def observation(self, cycle, transitions=None, **extra):
        value = {'cycle': cycle, 'live': dict(self.items), 'closed': dict(self.items), 'transitions': transitions or [], **extra}
        (self.root / 'observations' / f'cycle-{cycle}.json').write_text(json.dumps(value), encoding='utf-8')

    def start(self):
        review = self.h.review('delivery')['review']
        plan = {'topic': 'delivery', 'task': 'fixture', 'premise': 'evidence is current', 'residual': 'verify local proof',
                'review_id': review['id'], 'reviewed_claims': review['claims'], 'criteria': ['C1'], 'reverify_reason': 'bounded regression',
                'approach': {'method': 'exact fixture', 'inputs': 'proof.txt', 'environment': 'local'}}
        cid = self.h.start(plan)['cycle']
        (self.root / 'notes' / f'cycle-{cid}.md').write_text(f'Cycle {cid}: checked the local delivery fixture; no universal completion claim.\n', encoding='utf-8')
        self.observation(cid)
        self.h.check(cid, 'C1')
        return cid

    def boundary(self):
        self.h.close(self.start(), 'verified', 'Continue bounded verification')
        return self.start()

    def proposal(self, digest):
        return {'window': digest['window'], 'digest_sha256': digest['digest_sha256'],
                'prompt_sha256': hashlib.sha256((self.root / 'governing.md').read_bytes()).hexdigest(),
                'reread': [{'cycle': row['cycle'], 'sha256': row['sha256'], 'finding': f"The note for cycle {row['cycle']} describes a bounded fixture, not whole-project completion."}
                           for row in digest['notes']],
                'updates': {}, 'reason': 'Objectives remain applicable after reading each physical note.', 'loss_acknowledgements': []}

    def test_close_invokes_producer_and_blocks_until_reread(self):
        cid = self.boundary()
        self.refuse('PERIODIC_REVIEW_REQUIRED', lambda: self.h.close(cid, 'verified', 'Continue'))
        state = self.state()
        self.assertEqual(state['cycles'][-1]['status'], 'active')
        self.assertTrue(state.get('digests'))
        self.assertTrue(any(e['kind'] == 'periodic-review-pending' for e in state['events']))

    def test_joint_review_close_and_automatic_consolidation(self):
        cid = self.boundary()
        digest = self.h.digest(cid)
        proposal = self.proposal(digest)
        proposal['updates'] = {'objectives': '\nRevalidate the next bounded delivery.\n', 'scenario': '\nNo broad acceptance claim yet.\n'}
        original_hash = self.state()['mission_hash']
        result = self.h.close(cid, 'verified', 'Next delivery', review_input=proposal)
        self.assertEqual(result['status'], 'verified')
        state = self.state()
        self.assertEqual(state['mission_hash'], original_hash)
        self.assertEqual(state['consolidations'][-1]['through_cycle'], cid)
        self.assertIn('KEEP_PROOF', (self.root / 'governing.md').read_text())
        self.assertTrue(self.h.validate()['passed'])
        self.assertEqual(self.start(), 3)

    def test_nonboundary_review_is_true_noop(self):
        cid = self.start()
        before = self.h.db.read_bytes()
        self.assertFalse(self.h.decade_review(cid)['applicable'])
        self.assertEqual(before, self.h.db.read_bytes())

    def test_missing_digest_blocks_review(self):
        cid = self.boundary()
        self.refuse('DIGEST_REQUIRED', lambda: self.h.decade_review(cid))

    def test_wrong_window_or_tampered_digest_blocks(self):
        cid = self.boundary()
        result = self.h.digest(cid)
        path = self.root / result['output']
        packet = json.loads(path.read_text())
        packet['window']['start'] = 99
        path.write_text(json.dumps(packet))
        self.refuse('DIGEST_DRIFT', lambda: self.h.decade_review(cid))

    def test_removed_marker_and_paraphrased_core_detected(self):
        self.boundary()
        self.h.digest(2)
        for text in [PROMPT.replace('KEEP_PROOF', 'removed'), PROMPT.replace('never weaken acceptance', 'accept weak tests'),
                     PROMPT.replace('Later safeguards remain protected too.', 'Later safeguards removed.')]:
            (self.root / 'governing.md').write_text(text)
            self.refuse('CORE_CHANGED', lambda: self.h.decade_review(2))
            self.h.restore_prompt()
            self.assertEqual(PROMPT, (self.root / 'governing.md').read_text())
        self.assertTrue(any(e['kind'] == 'prompt-restored' for e in self.state()['events']))

    def test_updates_cannot_touch_other_sections_or_the_mission(self):
        cid = self.boundary()
        value = self.h.digest(cid)
        proposal = self.proposal(value)
        proposal['updates'] = {'invariant_core': 'weaken acceptance'}
        self.refuse('REVIEW_INPUT', lambda: self.h.decade_review(cid, proposal))
        proposal = self.proposal(value)
        proposal['mission'] = {'objective': 'different'}
        self.refuse('REVIEW_INPUT', lambda: self.h.decade_review(cid, proposal))
        self.assertEqual(PROMPT, (self.root / 'governing.md').read_text())

    def test_missing_note_blocks_instead_of_using_chat_context(self):
        cid = self.boundary()
        (self.root / 'notes/cycle-1.md').unlink()
        self.refuse('DIGEST_SOURCE', lambda: self.h.digest(cid))

    def test_live_state_equals_close_state_by_identity_not_counts(self):
        cid = self.boundary()
        self.items = {'ITEM-A': 'planned', 'ITEM-B': 'delivered'}
        self.observation(cid, closed={'ITEM-A': 'delivered', 'ITEM-B': 'planned'})
        self.refuse('RECONCILIATION_FAILED', lambda: self.h.digest(cid))

    def test_conservation_and_unmarked_transitions(self):
        cid = self.boundary()
        self.items['ITEM-A'] = 'delivered'
        self.observation(cid)
        self.refuse('RECONCILIATION_FAILED', lambda: self.h.digest(cid))
        self.items.pop('ITEM-B')
        self.observation(cid)
        self.refuse('RECONCILIATION_FAILED', lambda: self.h.digest(cid))

    def test_supported_progress_has_hashed_evidence_without_claim_promotion(self):
        cid = self.boundary()
        self.items['ITEM-A'] = 'delivered'
        receipt = {'id': 'ITEM-A', 'from': 'planned', 'to': 'delivered', 'kind': 'progress', 'reason': 'Observed fixture evidence',
                   'evidence': [{'path': 'proof.txt', 'sha256': hashlib.sha256(b'ok').hexdigest()}]}
        self.observation(cid, [receipt])
        result = self.h.digest(cid)
        self.assertTrue(result['reconciliation']['passed'])
        self.assertEqual(self.state()['claims'], {})
        self.assertFalse(result['semantic_correctness_verified'])

    def test_changed_note_invalidates_review_receipt(self):
        cid = self.boundary()
        result = self.h.digest(cid)
        proposal = self.proposal(result)
        (self.root / 'notes/cycle-1.md').write_text('Changed physical note; prior reread cannot cover this.')
        self.refuse('DIGEST_STALE', lambda: self.h.decade_review(cid, proposal))

    def test_interruption_does_not_bypass_boundary_gate(self):
        cid = self.boundary()
        self.h.interrupt(cid, 'Explicitly stop work')
        self.refuse('PERIODIC_REVIEW_REQUIRED', self.start)

    def test_cli_reports_exit_two_for_missing_digest(self):
        self.boundary()
        process = subprocess.run([sys.executable, str(SCRIPT), '--project', str(self.root), 'decade-review', '--through-cycle', '2'],
                                 capture_output=True, text=True, timeout=15)
        self.assertEqual(process.returncode, 2)
        self.assertEqual(json.loads(process.stdout)['code'], 'DIGEST_REQUIRED')

    def test_justified_retraction_preserves_negative_delta_and_does_not_fake_progress(self):
        first = self.start()
        self.items['ITEM-A'] = 'delivered'
        self.observation(first, [{'id': 'ITEM-A', 'from': 'planned', 'to': 'delivered', 'kind': 'progress', 'reason': 'Bounded initial evidence',
                                'evidence': [{'path': 'proof.txt', 'sha256': hashlib.sha256(b'ok').hexdigest()}]}])
        self.h.close(first, 'verified', 'Continue')
        cid = self.start()
        self.items['ITEM-A'] = 'planned'
        receipt = {'id': 'ITEM-A', 'from': 'delivered', 'to': 'planned', 'kind': 'retraction', 'reason': 'The earlier completion was overstated',
                   'evidence': [{'path': 'proof.txt', 'sha256': hashlib.sha256(b'ok').hexdigest()}]}
        self.observation(cid, [receipt])
        report = self.h.digest(cid)
        self.assertTrue(report['reconciliation']['passed'])
        last = report['reconciliation']['cycles'][-1]
        self.assertEqual(last['metric_deltas']['delivered'], -1)
        self.assertEqual(last['justified_retractions'], ['ITEM-A'])
        self.assertEqual(self.state()['claims'], {})

    def test_unexplained_regression_blocks(self):
        first = self.start()
        self.items['ITEM-A'] = 'delivered'
        self.observation(first, [{'id': 'ITEM-A', 'from': 'planned', 'to': 'delivered', 'kind': 'progress', 'reason': 'Bounded initial evidence',
                                'evidence': [{'path': 'proof.txt', 'sha256': hashlib.sha256(b'ok').hexdigest()}]}])
        self.h.close(first, 'verified', 'Continue')
        cid = self.start()
        self.items['ITEM-A'] = 'planned'
        self.observation(cid)
        self.refuse('RECONCILIATION_FAILED', lambda: self.h.digest(cid))
        state = self.state()
        report = next(iter(state['digests'].values()))['packet']['reconciliation']
        self.assertIn('unexplained_regression', report['cycles'][-1]['issues'])

    def test_possible_loss_requires_an_explanation(self):
        first = self.start()
        self.observation(first, facts_recorded=['FACT-1'], facts_used=['FACT-1'])
        self.h.close(first, 'verified', 'Continue')
        second = self.start()
        digest = self.h.digest(second)
        self.assertEqual(digest['reconciliation']['possible_losses'], ['FACT-1'])
        proposal = self.proposal(digest)
        self.refuse('LOSS_REVIEW_REQUIRED', lambda: self.h.decade_review(second, proposal))
        proposal['loss_acknowledgements'] = [{'id': 'FACT-1', 'reason': 'The observation was superseded, not erased from history.'}]
        self.assertTrue(self.h.decade_review(second, proposal)['passed'])

    def test_reread_cannot_be_replaced_with_digest_presence(self):
        cid = self.boundary()
        digest = self.h.digest(cid)
        proposal = self.proposal(digest)
        proposal['reread'].pop()
        self.refuse('REREAD_REQUIRED', lambda: self.h.decade_review(cid, proposal))

    def test_stale_reference_must_be_removed_in_allowed_sections(self):
        cid = self.boundary()
        digest = self.h.digest(cid)
        path = self.root / 'governing.md'
        path.write_text(path.read_text().replace('Deliver the next reviewed item.', 'OLD_TARGET'))
        proposal = self.proposal(digest)
        self.refuse('STALE_REFERENCES', lambda: self.h.decade_review(cid, proposal))
        proposal['updates'] = {'objectives': '\nA current, bounded target.\n'}
        self.assertTrue(self.h.decade_review(cid, proposal)['passed'])

    def test_no_inventory_required_for_a_general_research_project(self):
        root = self.root / 'research'
        root.mkdir()
        (root / 'notes').mkdir()
        (root / 'governing.md').write_text(PROMPT)
        mission = copy.deepcopy(self.mission)
        for key in ('inventory', 'observation_pattern', 'baseline'):
            mission['periodic_review'].pop(key)
        mission['criteria'][0] = {'id': 'C1', 'description': 'A bounded research fixture', 'argv': [sys.executable, '-c', 'assert True'], 'artifacts': []}
        h = module.Harness(root)
        h.init(mission)
        for i in (1, 2):
            review = h.review('research')['review']
            cid = h.start({'topic': 'research', 'task': 'sample', 'premise': 'bounded hypothesis', 'residual': 'test it',
                           'review_id': review['id'], 'reviewed_claims': [], 'criteria': ['C1'], 'reverify_reason': 'new bounded condition',
                           'approach': {'method': 'fixture', 'inputs': 'synthetic', 'environment': 'local'}})['cycle']
            (root / 'notes' / f'cycle-{i}.md').write_text(f'Research cycle {i}: no population-wide conclusion.')
            h.check(cid, 'C1')
            if i == 1:
                h.close(cid, 'verified', 'Next bounded condition')
        report = h.digest(2)
        self.assertFalse(report['reconciliation']['applicable'])
        self.assertFalse(report['semantic_correctness_verified'])

    def test_not_run_tripwire_is_not_falsely_recorded_as_passing(self):
        cid = self.boundary()
        self.refuse('DIGEST_REQUIRED', lambda: self.h.decade_review(cid))
        event = self.state()['events'][-1]
        self.assertIsNone(event['details']['tripwire_passed'])

    def test_native_cli_nonboundary_noop_does_not_change_store(self):
        self.start()
        before = self.h.db.read_bytes()
        process = subprocess.run([sys.executable, str(SCRIPT), '--project', str(self.root), 'decade-review', '--through-cycle', '1'], capture_output=True, timeout=15)
        self.assertEqual(0, process.returncode)
        self.assertEqual(before, self.h.db.read_bytes())

    def test_baseline_and_closed_note_cannot_be_rewritten_before_first_digest(self):
        cid = self.boundary()
        baseline = self.root / 'observations/cycle-0.json'
        original = baseline.read_bytes()
        baseline.write_text(original.decode().replace('planned', 'delivered'))
        self.refuse('DIGEST_SOURCE', lambda: self.h.digest(cid))
        baseline.write_bytes(original)
        (self.root / 'notes/cycle-1.md').write_text('A retroactively improved story.')
        self.refuse('DIGEST_SOURCE', lambda: self.h.digest(cid))

    def test_removed_core_blocks_execution_until_restored(self):
        cid = self.start()
        path = self.root / 'governing.md'
        path.write_text(PROMPT.replace('KEEP_PROOF', 'removed'))
        self.refuse('CORE_CHANGED', lambda: self.h.check(cid, 'C1'))
        self.h.restore_prompt()
        self.assertTrue(self.h.check(cid, 'C1')['passed'])

    def test_close_records_tripwire_failure_without_closing_cycle(self):
        cid = self.boundary()
        path = self.root / 'governing.md'
        path.write_text(PROMPT.replace('KEEP_PROOF', 'removed'))
        self.refuse('CORE_CHANGED', lambda: self.h.close(cid, 'verified', 'Continue'))
        state = self.state()
        self.assertEqual(state['cycles'][-1]['status'], 'active')
        self.assertFalse(state['events'][-1]['details']['tripwire_passed'])

    def test_generated_review_template_is_not_a_completed_reread(self):
        cid = self.boundary()
        result = self.h.digest(cid)
        self.refuse('REVIEW_INPUT', lambda: self.h.decade_review(cid, result['review_template']))

    def test_resume_exposes_pending_boundary_without_dispatch(self):
        self.boundary()
        before = self.h.db.read_bytes()
        result = self.h.resume()['periodic_review']
        self.assertEqual(result['pending_boundaries'], [2])
        self.assertEqual(result['next_boundary'], 2)
        self.assertFalse(result['domain_plugin_required'])
        self.assertEqual(before, self.h.db.read_bytes())

    def test_counter_groups_report_numerators_and_denominators(self):
        cid = self.boundary()
        self.items['ITEM-A'] = 'delivered'
        receipt = {'id': 'ITEM-A', 'from': 'planned', 'to': 'delivered', 'kind': 'progress', 'reason': 'Observed bounded fixture',
                   'evidence': [{'path': 'proof.txt', 'sha256': hashlib.sha256(b'ok').hexdigest()}]}
        self.observation(cid, [receipt])
        result = self.h.digest(cid)
        self.assertEqual(result['reconciliation']['cycles'][-1]['coverage']['delivered'], {'numerator': 1, 'denominator': 2, 'percent': 50.0})

    def test_bad_receipt_type_is_structured_reconciliation_failure(self):
        cid = self.boundary()
        self.observation(cid, [{'id': ['not', 'an', 'id']}])
        self.refuse('RECONCILIATION_FAILED', lambda: self.h.digest(cid))

    def test_duplicate_inventory_keys_are_not_silently_collapsed(self):
        cid = self.boundary()
        (self.root / f'observations/cycle-{cid}.json').write_text('{"cycle":2,"live":{},"closed":{"ITEM-A":"planned","ITEM-A":"delivered"},"transitions":[]}')
        self.refuse('DIGEST_SOURCE', lambda: self.h.digest(cid))

    def test_process_termination_after_prompt_replace_requires_recovery(self):
        cid = self.boundary()
        result = self.h.digest(cid)
        proposal = self.proposal(result)
        proposal['updates'] = {'objectives': '\nA changed bounded objective before interrupted commit.\n'}
        input_path = self.root / 'review-crash.json'
        input_path.write_text(json.dumps(proposal), encoding='utf-8')
        before = self.h.db.read_bytes()
        script = "import sys,json,os;sys.path.insert(0,sys.argv[1]);from harness import Harness;h=Harness(sys.argv[2]);original=h._atomic\ndef replace_then_exit(path,raw):\n original(path,raw)\n if path=='governing.md': os._exit(73)\nh._atomic=replace_then_exit\nh.decade_review(2,json.load(open(sys.argv[3])))"
        child = subprocess.run([sys.executable, '-c', script, str(SCRIPT.parent), str(self.root), str(input_path)], capture_output=True, timeout=15)
        self.assertEqual(child.returncode, 73)
        self.assertEqual(before, self.h.db.read_bytes())
        self.assertIn('interrupted commit', (self.root / 'governing.md').read_text())
        self.refuse('PERIODIC_REVIEW_REQUIRED', lambda: self.h.close(cid, 'verified', 'Continue'))
        self.h.restore_prompt()
        self.assertEqual(PROMPT, (self.root / 'governing.md').read_text())

    def test_historical_review_cannot_retarget_a_later_active_cycle(self):
        cid = self.boundary()
        digest = self.h.digest(cid)
        proposal = self.proposal(digest)
        self.h.close(cid, 'verified', 'Next bounded task', review_input=proposal)
        self.start()
        proposal['updates'] = {'objectives': '\nAn obsolete target from a past window.\n'}
        self.refuse('REVIEW_WINDOW', lambda: self.h.decade_review(cid, proposal))

    def revision_proposal(self):
        state = self.state()
        mission = copy.deepcopy(state['mission'])
        mission['objective'] += ' with explicitly revised scope'
        return {'expected_mission_hash': state['mission_hash'], 'expected_revision': state['revision'],
                'reason': 'Explicit user-requested scope revision',
                'authorization': {'source': 'user', 'reference': 'Synthetic explicit user request'}, 'mission': mission}

    def test_revision_requires_explicit_new_epoch(self):
        self.h.close(self.start(), 'verified', 'Next')
        proposal = self.revision_proposal()
        self.refuse('PERIODIC_POLICY', lambda: self.h.preview_mission(proposal))

    def test_init_cannot_skip_initial_review_cycles(self):
        root = self.root / 'other'
        root.mkdir()
        (root / 'governing.md').write_text(PROMPT)
        mission = copy.deepcopy(self.mission)
        mission['periodic_review']['anchor'] = 4
        self.refuse('PERIODIC_POLICY', lambda: module.Harness(root).init(mission))

    def test_authorized_revision_starts_new_epoch_without_resetting_history(self):
        self.h.close(self.start(), 'verified', 'Next')
        proposal = self.revision_proposal()
        policy = proposal['mission']['periodic_review']
        policy['anchor'] = 1
        policy['baseline'] = 'observations/cycle-1.json'
        token = self.h.preview_mission(proposal)['confirmation']
        class Terminal(io.StringIO):
            def isatty(self):
                return True
        with patch.object(module.sys, 'stdin', Terminal()), patch.object(module.sys, 'stdout', Terminal()), \
             patch.object(module, 'input', return_value=token, create=True), \
             patch.dict(module.os.environ, {'CI': '', 'HARNESS_AUTOMATION': ''}):
            result = self.h.revise_mission(proposal)
        self.assertTrue(result['mission_revised'])
        self.assertEqual(len(self.state()['cycles']), 1)
        self.assertEqual(self.state()['cycles'][0]['status'], 'needs_review')
        self.assertEqual(self.h.resume()['periodic_review']['next_boundary'], 3)
        self.h.close(self.start(), 'verified', 'Next')
        cid = self.start()
        digest = self.h.digest(cid)
        self.assertEqual(digest['window'], {'start': 2, 'end': 3})
        self.h.close(cid, 'verified', 'Next', review_input=self.proposal(digest))
        self.assertTrue(self.h.validate()['passed'])


if __name__ == '__main__':
    unittest.main()
