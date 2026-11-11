"""Independent-review regressions: resolved output, retained history and governed preservation."""
import copy
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from test_v83_assurance import load


class Terminal(io.StringIO):
    def isatty(self): return True


class ReviewRegressionTests(unittest.TestCase):
    def test_receipt_alias_into_protected_directory_is_refused(self):
        module = load('assurance')
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for reserved in ('.harness', '.git'):
                target = root / reserved; target.mkdir()
                alias = root / ('alias-' + reserved[1:])
                if os.name == 'nt':
                    process = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command',
                        'New-Item -ItemType Junction -Path $env:VM_TEST_ALIAS -Target $env:VM_TEST_TARGET | Out-Null'],
                        env={**os.environ, 'VM_TEST_ALIAS':str(alias),'VM_TEST_TARGET':str(target)}, capture_output=True)
                    self.assertEqual(process.returncode, 0, process.stderr)
                else:
                    alias.symlink_to(target, target_is_directory=True)
                with patch.object(module, 'run', return_value={'passed':True,'complete':True}):
                    self.assertEqual(module.main(['--suite','controls','--output',str(alias/'receipt.json')]),2)
                self.assertFalse((target/'receipt.json').exists())

    def test_recovery_rejects_deleted_or_modified_prior_checks(self):
        faults = load('assurance_faults')
        fixture_module = load('assurance_fixture')
        for defect in ('deleted-checks', 'modified-check', 'lost-events'):
            with self.subTest(defect=defect), fixture_module.Fixture() as fixture:
                fixture.start(); fixture.h.check(1,'R')
                before = copy.deepcopy(fixture.h.store._load_unlocked())
                before_bytes = fixture.h.db.read_bytes()
                fixture.h.close(1,'verified','Synthetic persistence close')
                doc = fixture.h.store._load_unlocked()
                if defect == 'deleted-checks': doc['state']['cycles'][0]['checks'] = []
                elif defect == 'modified-check': doc['state']['cycles'][0]['checks'][0]['output_sha256'] = '0'*64
                else: doc['state']['events'] = doc['state']['events'][-1:]
                fixture.h.store._write_unlocked(fixture.h.store._document(doc['state'],doc['audit']))
                with self.assertRaises(AssertionError):
                    faults._recovery(fixture,'close','after-replace',before_bytes,before)


class GovernedPreservationTests(unittest.TestCase):
    def setUp(self):
        self.module = load('assurance_fixture')
        self.fixture = self.module.Fixture().__enter__()
        self.h = self.fixture.h
        self.fixture.start()

    def tearDown(self): self.fixture.__exit__(None,None,None)

    def prepare(self):
        return self.h.operation_prepare({'id':'OP','cycle':1,'criterion':'R','effect':'local','risk':'read',
                                         'reason':'Synthetic governed regression check','request_ref':'Isolated test only'})

    def approve(self):
        m = self.module.engine
        token = self.h.operation_status('OP')['confirmation']
        with patch.object(m.sys,'stdin',Terminal()),patch.object(m.sys,'stdout',Terminal()), \
             patch.object(m,'input',return_value=token,create=True), \
             patch.dict(m.os.environ,{'CI':'','HARNESS_AUTOMATION':''}):
            self.h.operation_approve('OP')

    def test_approved_operation_produces_current_preservation_evidence(self):
        self.prepare();self.approve()
        check = self.h.operation_run('OP')['check']
        self.assertTrue(check['passed'],check)
        self.assertTrue(check['regression']['assessment']['passed'])
        self.assertTrue(self.h.operation_status('OP')['approval_consumed'])
        self.assertEqual(self.h.close(1,'verified','Synthetic governed close')['status'],'verified')

    def test_preservation_preflight_failure_does_not_consume_approval(self):
        self.prepare();self.approve()
        with (self.fixture.root/'baseline.json').open('a') as stream: stream.write(' ')
        with self.assertRaises(self.module.engine.Refusal) as caught:
            self.h.operation_run('OP')
        self.assertEqual(caught.exception.code,'REGRESSION_SOURCE')
        self.assertFalse(self.h.operation_status('OP')['approval_consumed'])

    def test_failed_observable_cannot_close_after_approved_operation(self):
        self.fixture.candidate(good=False)
        self.prepare();self.approve()
        check = self.h.operation_run('OP')['check']
        self.assertFalse(check['passed'])
        self.assertEqual(check['exit_code'],0)
        self.assertFalse(check['regression']['assessment']['passed'])
        with self.assertRaises(self.module.engine.Refusal) as caught:
            self.h.close(1,'verified','Must refuse bad observable')
        self.assertEqual(caught.exception.code,'REGRESSION_BLOCKED')

    def test_interrupted_governed_preservation_keeps_admission_and_cannot_replay(self):
        self.prepare();self.approve()
        with patch.object(self.module.engine.subprocess,'run',side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt): self.h.operation_run('OP')
        status = self.h.operation_status('OP')
        self.assertTrue(status['approval_consumed'])
        self.assertTrue(status['reconciliation_required'])
        with self.assertRaises(self.module.engine.Refusal) as caught:
            self.h.operation_run('OP')
        self.assertEqual(caught.exception.code,'OPERATION_STATE')


if __name__ == '__main__': unittest.main()
