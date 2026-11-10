"""Public behavior of finite, synthetic verifier-assurance campaigns."""
import importlib.util
from pathlib import Path
import sys
import subprocess
import json
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'


def load(name):
    spec = importlib.util.spec_from_file_location(name + '_test', SCRIPTS / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    with patch.object(sys, 'path', [str(SCRIPTS), *sys.path]):
        spec.loader.exec_module(module)
    return module


def controls():
    return load('assurance_controls')


class ControlsTests(unittest.TestCase):
    def test_healthy_control_and_each_declared_fault_are_discriminated(self):
        report = controls().run()
        self.assertTrue(report['passed'], report)
        self.assertTrue(report['positive_control']['passed'])
        self.assertGreaterEqual(len(report['cases']), 7)
        self.assertEqual(len({r['id'] for r in report['cases']}), len(report['cases']))
        self.assertTrue(all(r['passed'] and r['expected'] == r['observed'] for r in report['cases']))
        self.assertFalse(report['global_mutation_score_claimed'])

    def test_an_unrelated_exception_is_not_credited_as_detection(self):
        module = controls()
        with patch.object(module, '_observe', side_effect=ImportError('unrelated fixture failure')):
            report = module.run()
        self.assertFalse(report['passed'])
        self.assertTrue(all(not r['passed'] and r['observed'] == 'infrastructure_error' for r in report['cases']))

    def test_accepting_a_defective_case_fails_the_campaign(self):
        module = controls()
        original = module._observe
        def weakened(fixture, control):
            return 'accepted' if control == 'wrong-memory' else original(fixture, control)
        with patch.object(module, '_observe', side_effect=weakened):
            report = module.run()
        self.assertFalse(report['passed'])
        failed = [r['id'] for r in report['cases'] if not r['passed']]
        self.assertEqual(failed, ['wrong-memory'])


class LifecycleTests(unittest.TestCase):
    def test_programs_are_reproducible_and_configuration_is_finite(self):
        module = load('assurance_lifecycle')
        a = module.programs(7, 2, 24)
        self.assertEqual(a, module.programs(7, 2, 24))
        self.assertNotEqual(a, module.programs(8, 2, 24))
        self.assertEqual([len(p) for p in a], [24, 24])
        for args in ((True, 1, 16), (-1, 1, 16), (0, 0, 16), (0, 5, 16), (0, 1, 15), (0, 1, 65)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                module.programs(*args)

    def test_generated_sequences_preserve_authority_proofs_history_and_progress(self):
        result = load('assurance_lifecycle').run(seed=7, traces=2, steps=24)
        self.assertTrue(result['passed'], result)
        self.assertEqual(result['planned_steps'], 48)
        self.assertEqual(result['executed_steps'], 48)
        self.assertTrue(all(r['passed'] for r in result['traces']))
        self.assertFalse(result['exhaustive'])

    def test_independent_model_rejects_a_false_verified_close(self):
        module = load('assurance_lifecycle')
        original = module._perform
        def bypass(fixture, model, action):
            if action == 'close' and model.active and model.check_epoch is None:
                return 'verified'
            return original(fixture, model, action)
        with patch.object(module, '_perform', side_effect=bypass):
            report = module.run(seed=0, traces=1, steps=16)
        self.assertFalse(report['passed'])
        step = report['traces'][0]['steps'][-1]
        self.assertEqual(step['expected'], 'REGRESSION_BLOCKED')
        self.assertEqual(step['observed'], 'verified')


class PersistenceTests(unittest.TestCase):
    def test_all_named_boundaries_recover_complete_old_or_new_yaml_commits(self):
        report = load('assurance_faults').run()
        self.assertTrue(report['passed'], report)
        self.assertEqual(len(report['cases']), 36)
        self.assertEqual(sum(r['mode'] == 'crash' for r in report['cases']), 18)
        self.assertTrue(all(r['fault_reached'] and r['passed'] for r in report['cases']))
        self.assertFalse(report['physical_power_loss_simulated'])
        self.assertEqual({r['commit'] for r in report['cases']}, {'old', 'new'})

    def test_missing_crash_marker_is_an_infrastructure_failure(self):
        module = load('assurance_faults')
        result = subprocess.CompletedProcess([], 79, stdout='', stderr='')
        with patch.object(module.subprocess, 'run', return_value=result):
            row = module.run_case('review', 'before-replace', 'crash')
        self.assertFalse(row['passed'])
        self.assertFalse(row['fault_reached'])

    def test_a_new_commit_misreported_as_precommit_is_rejected(self):
        module = load('assurance_faults')
        def falsely_report_precommit(argv, **kwargs):
            h = module.fresh_engine(argv[4], argv[5])
            h.review('wrong-stage-commit')
            marker = {'fault_reached': argv[7], 'operation': argv[6], 'mode': argv[8]}
            return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(marker) + '\n', stderr='')
        with patch.object(module.subprocess, 'run', side_effect=falsely_report_precommit):
            row = module.run_case('review', 'before-replace', 'exception')
        self.assertFalse(row['passed'])
        self.assertTrue(row['fault_reached'])
        self.assertEqual(row['error_type'], 'AssertionError')

    def test_unknown_boundary_or_mode_is_refused_before_execution(self):
        module = load('assurance_faults')
        for args in (('reset', 'before-replace', 'crash'), ('close', 'any', 'crash'), ('close', 'before-replace', 'retry')):
            with self.subTest(args=args), self.assertRaises(ValueError):
                module.run_case(*args)


class CampaignTests(unittest.TestCase):
    def test_native_cli_runs_controls_without_initializing_the_current_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = root / 'assurance.json'
            result = subprocess.run([sys.executable, '-B', str(SCRIPTS / 'harness.py'), 'assurance',
                                     '--suite', 'controls', '--output', str(output)], cwd=root,
                                    capture_output=True, text=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads(output.read_text(encoding='utf-8'))
            self.assertTrue(report['passed'])
            self.assertEqual(report['format'], 'verimission-assurance-v1')
            self.assertEqual(report['canonical_store'], 'YAML')
            self.assertFalse(report['mission_acceptance'])
            self.assertEqual({p.name for p in root.iterdir()}, {'assurance.json'})

    def test_output_is_never_overwritten_and_invalid_budgets_do_not_run(self):
        module = load('assurance')
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'existing.json'
            output.write_text('keep me', encoding='utf-8')
            with patch.object(module, 'run', side_effect=AssertionError('must not run')):
                self.assertEqual(module.main(['--suite', 'controls', '--output', str(output)]), 2)
            self.assertEqual(output.read_text(), 'keep me')
        with patch.object(module, 'RUNNERS', {}), self.assertRaises(ValueError):
            module.run(suite='all', seed=-1)

    def test_empty_success_receipt_is_not_a_complete_campaign(self):
        module = load('assurance')
        with patch.dict(module.RUNNERS, {'controls': lambda: {'suite': 'controls', 'passed': True}}):
            report = module.run(suite='controls')
        self.assertFalse(report['complete'])
        self.assertFalse(report['passed'])

    def test_failing_campaign_has_nonzero_exit_and_preserves_diagnostics(self):
        module = load('assurance')
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'failure.json'
            failed = {'passed': False, 'complete': True, 'diagnostic': 'deliberate failed control'}
            with patch.object(module, 'run', return_value=failed):
                self.assertEqual(module.main(['--suite', 'controls', '--output', str(output)]), 3)
            self.assertEqual(json.loads(output.read_text()), failed)

    def test_non_fixture_worker_path_is_rejected_without_writes(self):
        module = load('assurance_faults')
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):
                module.worker(temp, 'not-a-fixture', 'review', 'before-open', 'exception')
            self.assertEqual(list(Path(temp).iterdir()), [])

    def test_engine_identity_change_invalidates_an_otherwise_complete_receipt(self):
        module = load('assurance')
        fake = {'suite': 'controls', 'passed': True, 'positive_control': {'id': 'healthy'},
                'cases': [{'id': name} for name in module.controls.CONTROLS]}
        with patch.dict(module.RUNNERS, {'controls': lambda: fake}), patch.object(
                module, 'source_manifest', side_effect=[{'harness.py': 'old'}, {'harness.py': 'new'}]):
            report = module.run(suite='controls')
        self.assertTrue(report['complete'])
        self.assertFalse(report['engine_sources_unchanged'])
        self.assertFalse(report['passed'])


if __name__ == '__main__':
    unittest.main()
