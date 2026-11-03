import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/binary_profile.py'
spec = importlib.util.spec_from_file_location('binary_profile_test', SCRIPT)
profile = importlib.util.module_from_spec(spec)
if SCRIPT.exists():
    spec.loader.exec_module(profile)


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='binary-profile-')
        self.root = Path(self.temp.name)
        (self.root / 'image.bin').write_bytes(bytes(range(32)))
        self.sha = hashlib.sha256((self.root / 'image.bin').read_bytes()).hexdigest()
        self.target = {'format': 'binary-target-v1', 'binary': 'image.bin', 'sha256': self.sha,
                       'architecture': 'declared-fixture-isa', 'endianness': 'little', 'address_unit_bytes': 1,
                       'segments': [{'id': 'text', 'address_space': 'main', 'file_offset': 0, 'size': 32, 'virtual_base': 4096}],
                       'analysis_configuration': {'tool': 'fixture-reader', 'version': 'test-only', 'settings': {'mode': 'fixture'}}}
        self.unit = {'format': 'binary-unit-v1', 'id': 'U1', 'target_sha256': self.sha, 'segment': 'text',
                     'file_offset': 4, 'size': 4, 'virtual_address': 4100, 'isa_mode': 'declared-mode', 'classification': 'candidate_function'}

    def tearDown(self):
        self.temp.cleanup()

    def file_ref(self, name, data):
        (self.root / name).write_bytes(data)
        return {'path': name, 'sha256': hashlib.sha256(data).hexdigest()}

    def report(self):
        cases = []
        for i in range(2):
            cases.append({'id': 'W' + str(i), 'purpose': 'Declared boundary case ' + str(i),
                          'inputs': [self.file_ref('input' + str(i) + '.json', json.dumps({'n': i}).encode())],
                          'log': self.file_ref('case' + str(i) + '.log', ('synthetic fixture result ' + str(i)).encode()),
                          'completed': True, 'expected': {'result': i + 1}, 'observed': {'result': i + 1}})
        control = {'id': 'CTRL', 'purpose': 'Known fixture control, not a firmware execution',
                   'inputs': [self.file_ref('control-input.json', b'{"n":10}')],
                   'log': self.file_ref('control.log', b'synthetic positive control'), 'completed': True,
                   'expected': {'result': 11}, 'observed': {'result': 11}}
        return {'format': 'binary-witness-report-v1', 'target_sha256': self.sha, 'unit_id': 'U1',
                'unit_sha256': hashlib.sha256(bytes(range(4, 8))).hexdigest(),
                'target_manifest_sha256': profile.manifest_digest(self.target),
                'unit_manifest_sha256': profile.manifest_digest(self.unit),
                'method': 'isolated_function', 'environment': 'synthetic fixtures; no target execution',
                'injections': ['Fixture observations supplied by tests'], 'limitations': ['Not an emulator or hardware run'],
                'execution_reference': 'Synthetic unit-test record', 'positive_control': control, 'cases': cases}

    def reject(self, code, call):
        with self.assertRaises(profile.ProfileError) as caught:
            call()
        self.assertEqual(caught.exception.code, code)

    def test_target_identity_is_checked_without_changing_original(self):
        before = (self.root / 'image.bin').read_bytes()
        result = profile.validate_target(self.root, self.target)
        self.assertTrue(result['passed'])
        self.assertFalse(result['architecture_authenticated'])
        self.assertEqual(before, (self.root / 'image.bin').read_bytes())

    def test_modified_image_is_rejected(self):
        (self.root / 'image.bin').write_bytes(b'changed')
        self.reject('IDENTITY', lambda: profile.validate_target(self.root, self.target))

    def test_address_mapping_and_byte_range_are_checked(self):
        result = profile.validate_unit(self.root, self.target, self.unit)
        self.assertEqual(result['virtual_address'], 4100)
        self.assertFalse(result['function_boundary_proven'])
        bad = {**self.unit, 'virtual_address': 4}
        self.reject('ADDRESS', lambda: profile.validate_unit(self.root, self.target, bad))
        bad = {**self.unit, 'size': 40}
        self.reject('ADDRESS', lambda: profile.validate_unit(self.root, self.target, bad))

    def test_word_addressed_mapping_uses_explicit_address_units(self):
        target = {**self.target, 'address_unit_bytes': 2}
        unit = {**self.unit, 'virtual_address': 4098}
        self.assertEqual(profile.validate_unit(self.root, target, unit)['virtual_address'], 4098)

    def test_segment_overlap_requires_different_address_spaces(self):
        target = copy.deepcopy(self.target)
        target['segments'].append({**target['segments'][0], 'id': 'overlay'})
        self.reject('SEGMENT', lambda: profile.validate_target(self.root, target))
        target['segments'][1]['address_space'] = 'bank2'
        self.assertTrue(profile.validate_target(self.root, target)['passed'])

    def test_path_escape_and_store_as_evidence_are_refused(self):
        target = {**self.target, 'binary': '../outside.bin'}
        self.reject('PATH', lambda: profile.validate_target(self.root, target))
        target['binary'] = '.harness/state.sqlite'
        self.reject('PATH', lambda: profile.validate_target(self.root, target))

    def test_witness_report_matches_observations_but_never_proves_semantics(self):
        result = profile.validate_witnesses(self.root, self.target, self.unit, self.report())
        self.assertTrue(result['passed'])
        self.assertFalse(result['semantic_truth_verified'])
        self.assertFalse(result['hardware_validation_established'])
        self.assertFalse(result['promotion_authorized'])

    def test_zero_or_one_witness_cannot_pass(self):
        for count in (0, 1):
            report = self.report()
            report['cases'] = report['cases'][:count]
            self.reject('WITNESS', lambda: profile.validate_witnesses(self.root, self.target, self.unit, report))

    def test_duplicate_inputs_are_not_distinct_witnesses(self):
        report = self.report()
        report['cases'][1]['inputs'] = report['cases'][0]['inputs']
        self.reject('WITNESS', lambda: profile.validate_witnesses(self.root, self.target, self.unit, report))

    def test_missing_expected_results_cannot_vacuously_pass(self):
        report = self.report()
        report['cases'][0]['expected'] = {}
        self.reject('EXPECTATION', lambda: profile.validate_witnesses(self.root, self.target, self.unit, report))

    def test_missing_observation_does_not_equal_an_expected_null(self):
        report = self.report()
        report['cases'][0]['expected'] = {'missing': None}
        result = profile.validate_witnesses(self.root, self.target, self.unit, report)
        self.assertFalse(result['passed'])

    def test_mismatch_failed_control_and_incomplete_run_fail(self):
        for location, field, value in [('case', 'observed', {'result': 999}), ('control', 'completed', False), ('case', 'completed', False)]:
            report = self.report()
            row = report['positive_control'] if location == 'control' else report['cases'][0]
            row[field] = value
            self.assertFalse(profile.validate_witnesses(self.root, self.target, self.unit, report)['passed'])

    def test_trace_or_input_change_invalidates_the_report(self):
        report = self.report()
        (self.root / 'case0.log').write_bytes(b'changed')
        self.reject('IDENTITY', lambda: profile.validate_witnesses(self.root, self.target, self.unit, report))

    def test_report_for_another_unit_or_binary_is_refused(self):
        report = self.report()
        report['unit_id'] = 'U2'
        self.reject('IDENTITY', lambda: profile.validate_witnesses(self.root, self.target, self.unit, report))

    def test_limits_and_injections_must_be_explicit(self):
        report = self.report()
        del report['injections']
        self.reject('REPORT', lambda: profile.validate_witnesses(self.root, self.target, self.unit, report))

    def test_changed_tool_configuration_invalidates_saved_report(self):
        report = self.report()
        target = copy.deepcopy(self.target)
        target['analysis_configuration']['settings']['mode'] = 'another-mode'
        self.reject('IDENTITY', lambda: profile.validate_witnesses(self.root, target, self.unit, report))

    def test_changed_isa_mode_invalidates_saved_report(self):
        report = self.report()
        unit = {**self.unit, 'isa_mode': 'other-mode'}
        self.reject('IDENTITY', lambda: profile.validate_witnesses(self.root, self.target, unit, report))

    def test_boolean_observation_is_not_numeric_result(self):
        report = self.report()
        report['cases'][0]['observed'] = {'result': True}
        self.assertFalse(profile.validate_witnesses(self.root, self.target, self.unit, report)['passed'])

    def test_segment_and_unit_must_use_complete_address_units(self):
        target = {**self.target, 'address_unit_bytes': 2}
        unit = {**self.unit, 'file_offset': 5, 'virtual_address': 4098}
        self.reject('ADDRESS', lambda: profile.validate_unit(self.root, target, unit))

    def test_renaming_same_input_does_not_create_diversity(self):
        report = self.report()
        raw = (self.root / 'input0.json').read_bytes()
        report['cases'][1]['inputs'] = [self.file_ref('renamed.json', raw)]
        self.reject('WITNESS', lambda: profile.validate_witnesses(self.root, self.target, self.unit, report))

    def test_repeating_a_file_reference_does_not_create_diversity(self):
        report = self.report()
        report['cases'][1]['inputs'] = report['cases'][0]['inputs'] * 2
        self.reject('WITNESS', lambda: profile.validate_witnesses(self.root, self.target, self.unit, report))

    def test_duplicate_json_keys_are_not_silently_overwritten(self):
        path = self.root / 'duplicate.json'
        path.write_text('{"passed":true,"passed":false}', encoding='utf-8')
        self.reject('JSON', lambda: profile.load_json(path))

    def test_nonfinite_json_is_refused(self):
        path = self.root / 'nan.json'
        path.write_text('{"result":NaN}', encoding='utf-8')
        self.reject('JSON', lambda: profile.load_json(path))

    def test_symlink_escape_is_refused_when_supported(self):
        with tempfile.TemporaryDirectory() as outside:
            external = Path(outside) / 'outside.bin'
            external.write_bytes(b'outside')
            link = self.root / 'link.bin'
            try:
                link.symlink_to(external)
            except OSError:
                self.skipTest('Creating symlinks unavailable for this Windows account')
            self.reject('PATH', lambda: profile.project_file(self.root, 'link.bin'))

    def test_cli_check_does_not_touch_binary_or_harness_state(self):
        (self.root / '.harness').mkdir()
        (self.root / '.harness/state.sqlite').write_bytes(b'untouched sentinel, not a database')
        target_path = self.root / 'target.json'
        target_path.write_text(json.dumps(self.target), encoding='utf-8')
        before = {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        run = subprocess.run([sys.executable, '-B', str(SCRIPT), '--project', str(self.root), 'target', '--input', str(target_path)], capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()})


if __name__ == '__main__':
    unittest.main()
