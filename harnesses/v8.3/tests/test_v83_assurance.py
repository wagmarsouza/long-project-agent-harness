"""Public behavior of finite, synthetic verifier-assurance campaigns."""
import importlib.util
from pathlib import Path
import sys
import subprocess
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
            row = module.run_case('close', 'before-replace', 'crash')
        self.assertFalse(row['passed'])
        self.assertFalse(row['fault_reached'])

    def test_unknown_boundary_or_mode_is_refused_before_execution(self):
        module = load('assurance_faults')
        for args in (('reset', 'before-replace', 'crash'), ('close', 'any', 'crash'), ('close', 'before-replace', 'retry')):
            with self.subTest(args=args), self.assertRaises(ValueError):
                module.run_case(*args)


if __name__ == '__main__':
    unittest.main()
