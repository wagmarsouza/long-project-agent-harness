"""Mission changes require explicit provenance and interactive human confirmation."""
import copy
from contextlib import closing
import importlib.util
import io
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/harness.py'
spec = importlib.util.spec_from_file_location('revision_harness', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class Terminal(io.StringIO):
    def isatty(self):
        return True


class MissionRevisionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='harness-revision-')
        self.root = Path(self.temp.name)
        (self.root / 'result.txt').write_text('correct', encoding='utf-8')
        self.h = module.Harness(self.root)
        self.h.init({'objective': 'Check the local fixture', 'mode': 'light',
                     'in_scope': ['result.txt'], 'out_of_scope': ['external services'],
                     'criteria': [{'id': 'C1', 'description': 'Text is correct',
                                   'argv': [sys.executable, '-c', "from pathlib import Path; assert Path('result.txt').read_text() == 'correct'"],
                                   'artifacts': ['result.txt']}]})

    def tearDown(self):
        self.temp.cleanup()

    def state(self):
        with self.h.state() as state:
            return copy.deepcopy(state)

    def proposal(self):
        current = self.state()
        mission = copy.deepcopy(current['mission'])
        mission['objective'] = 'Check the local fixture and its documented scope'
        return {'expected_mission_hash': current['mission_hash'], 'expected_revision': current['revision'],
                'reason': 'The user explicitly requested the new scope',
                'authorization': {'source': 'user', 'reference': 'Explicit user request in this test fixture'},
                'mission': mission}

    def refuse(self, code, call):
        with self.assertRaises(module.Refusal) as caught:
            call()
        self.assertEqual(caught.exception.code, code)

    def approve(self, proposal, answer=None):
        token = self.h.preview_mission(proposal)['confirmation']
        with patch.object(module.sys, 'stdin', Terminal()), patch.object(module.sys, 'stdout', Terminal()), \
             patch.object(module, 'input', return_value=token if answer is None else answer, create=True), \
             patch.dict(module.os.environ, {'CI': '', 'HARNESS_AUTOMATION': ''}):
            return self.h.revise_mission(proposal)

    def test_preview_is_read_only_and_shows_exact_changes(self):
        before = self.state()
        proposal = self.proposal()
        proposal['mission']['criteria'][0]['description'] = 'New acceptance description'
        result = self.h.preview_mission(proposal)
        self.assertEqual(result['before'], before['mission'])
        self.assertEqual(result['after']['objective'], proposal['mission']['objective'])
        self.assertIn('criteria', result['changed_fields'])
        self.assertEqual(self.state(), before)
        self.assertFalse((self.h.db.parent / 'mission-backups').exists())

    def test_automation_origin_is_rejected_even_with_user_reference(self):
        proposal = self.proposal()
        proposal['authorization']['source'] = 'automation'
        self.refuse('USER_AUTHORIZATION', lambda: self.h.preview_mission(proposal))

    def test_missing_authorization_is_not_inferred(self):
        proposal = self.proposal()
        proposal['authorization']['reference'] = ''
        self.refuse('USER_AUTHORIZATION', lambda: self.h.preview_mission(proposal))

    def test_noninteractive_execution_cannot_apply_revision(self):
        before = self.state()
        with patch.object(module.sys, 'stdin', io.StringIO()), patch.object(module.sys, 'stdout', io.StringIO()):
            self.refuse('INTERACTIVE_REQUIRED', lambda: self.h.revise_mission(self.proposal()))
        self.assertEqual(self.state(), before)

    def test_known_automation_environment_is_rejected_even_with_tty(self):
        with patch.object(module.sys, 'stdin', Terminal()), patch.object(module.sys, 'stdout', Terminal()), \
             patch.dict(module.os.environ, {'HARNESS_AUTOMATION': '1'}):
            self.refuse('AUTOMATION_FORBIDDEN', lambda: self.h.revise_mission(self.proposal()))

    def test_wrong_confirmation_changes_nothing(self):
        before = self.state()
        self.refuse('CONFIRMATION', lambda: self.approve(self.proposal(), answer='yes'))
        self.assertEqual(self.state(), before)
        self.assertFalse((self.h.db.parent / 'mission-backups').exists())

    def test_piped_confirmation_is_rejected_by_real_cli(self):
        proposal = self.proposal()
        token = self.h.preview_mission(proposal)['confirmation']
        path = self.root / 'revision.json'
        path.write_text(json.dumps(proposal), encoding='utf-8')
        proc = subprocess.run([sys.executable, str(SCRIPT), '--project', str(self.root), 'revise-mission', '--input', str(path)],
                              input=token + '\n', capture_output=True, text=True, timeout=10)
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(json.loads(proc.stdout)['code'], 'INTERACTIVE_REQUIRED')
        self.assertEqual(self.state()['mission_hash'], proposal['expected_mission_hash'])

    def test_active_cycle_must_be_closed_explicitly(self):
        review = self.h.review('fixture')['review']
        self.h.start({'topic': 'fixture', 'task': 'check', 'premise': 'correct text', 'residual': 'execute assertion',
                      'review_id': review['id'], 'reviewed_claims': [], 'criteria': ['C1'],
                      'approach': {'method': 'assert', 'inputs': 'result.txt', 'environment': 'local'}})
        self.refuse('OVERLAP', lambda: self.h.preview_mission(self.proposal()))

    def test_stale_hash_or_state_requires_new_proposal(self):
        proposal = self.proposal()
        proposal['expected_mission_hash'] = 'wrong'
        self.refuse('REVISION_STALE', lambda: self.h.preview_mission(proposal))
        proposal = self.proposal()
        self.h.review('changed while proposal waited')
        self.refuse('REVISION_STALE', lambda: self.h.preview_mission(proposal))

    def test_invalid_or_unchanged_mission_cannot_replace_contract(self):
        proposal = self.proposal()
        proposal['mission']['criteria'] = []
        self.refuse('MISSION', lambda: self.h.preview_mission(proposal))
        proposal = self.proposal()
        proposal['mission'] = self.state()['mission']
        self.refuse('NO_CHANGE', lambda: self.h.preview_mission(proposal))

    def test_success_backs_up_preserves_history_and_reopens_old_conclusions(self):
        review = self.h.review('fixture')['review']
        cycle = self.h.start({'topic': 'fixture', 'task': 'check', 'premise': 'correct text', 'residual': 'execute assertion',
                              'review_id': review['id'], 'reviewed_claims': [], 'criteria': ['C1'],
                              'approach': {'method': 'assert', 'inputs': 'result.txt', 'environment': 'local'}})['cycle']
        self.h.check(cycle, 'C1')
        self.h.claim({'id': 'old-fact', 'topic': 'fixture', 'statement': 'The old scope passed', 'kind': 'fact',
                      'cycle': cycle, 'criterion': 'C1'})
        self.h.close(cycle, 'verified', 'Scope verified')
        before = self.state()
        result = self.approve(self.proposal())
        after = self.state()
        self.assertEqual(len(after['cycles']), len(before['cycles']))
        self.assertEqual(after['cycles'][0]['checks'], before['cycles'][0]['checks'])
        self.assertEqual(after['cycles'][0]['status'], 'needs_review')
        self.assertEqual(after['claims']['old-fact']['status'], 'needs_review')
        entry = after['mission_revisions'][0]
        self.assertEqual(entry['before'], before['mission'])
        self.assertEqual(entry['after'], after['mission'])
        backup = self.root / result['backup']
        self.assertEqual(module.file_digest(backup), result['backup_sha256'])
        with closing(sqlite3.connect(backup)) as connection:
            backed_up = json.loads(connection.execute('SELECT body FROM state WHERE id=1').fetchone()[0])
        self.assertEqual(backed_up, before)
        self.assertTrue(self.h.validate()['passed'])
        self.assertEqual(self.h.metrics()['criteria_verified'], 0)

    def test_revision_history_survives_fresh_process_and_multiple_changes(self):
        self.approve(self.proposal())
        proposal = self.proposal()
        proposal['mission']['objective'] += ' and its revision history'
        self.approve(proposal)
        proc = subprocess.run([sys.executable, str(SCRIPT), '--project', str(self.root), 'resume'], capture_output=True, text=True, timeout=10)
        self.assertEqual(proc.returncode, 0)
        history = json.loads(proc.stdout)['result']['mission_revisions']
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]['after_hash'], history[1]['before_hash'])
        self.assertTrue(self.h.validate()['passed'])

    def test_changed_state_during_confirmation_is_not_applied(self):
        proposal = self.proposal()
        confirmation = self.h.preview_mission(proposal)['confirmation']
        def answer(_prompt):
            self.h.review('concurrent update')
            return confirmation
        with patch.object(module.sys, 'stdin', Terminal()), patch.object(module.sys, 'stdout', Terminal()), \
             patch.object(module, 'input', side_effect=answer, create=True), \
             patch.dict(module.os.environ, {'CI': '', 'HARNESS_AUTOMATION': ''}):
            self.refuse('REVISION_STALE', lambda: self.h.revise_mission(proposal))
        self.assertEqual(self.state()['mission_hash'], proposal['expected_mission_hash'])
        self.assertFalse((self.h.db.parent / 'mission-backups').exists())

    def test_backup_failure_rolls_back_revision(self):
        before = self.state()
        (self.h.db.parent / 'mission-backups').write_text('not a directory', encoding='utf-8')
        with self.assertRaises((OSError, module.Refusal)):
            self.approve(self.proposal())
        self.assertEqual(self.state(), before)

    def test_revision_history_tampering_is_reported(self):
        self.approve(self.proposal())
        with self.h.state(write=True) as state:
            state['mission_revisions'][0]['before']['objective'] = 'tampered history'
        self.assertFalse(self.h.validate()['passed'])
        self.assertIn('mission_revision_history', [issue['kind'] for issue in self.h.validate()['issues']])


if __name__ == '__main__':
    unittest.main()
