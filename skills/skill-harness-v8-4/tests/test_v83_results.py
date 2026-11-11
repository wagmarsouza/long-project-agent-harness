import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('v83_readers_test', ROOT / 'scripts/result_readers.py')
reader = importlib.util.module_from_spec(spec); spec.loader.exec_module(reader)


class ReaderTests(unittest.TestCase):
    def test_neutral_complete_binding(self):
        data = {'format': 'verimission-results-v1', 'run_id': 'new', 'context_sha256': 'a'*64,
                'complete': True, 'cases': [{'id': 'A', 'status': 'pass'}]}
        self.assertEqual(reader.neutral(json.dumps(data).encode(), 'new', 'a'*64)[0]['id'], 'A')
        for field, value in [('complete', False), ('run_id', 'old'), ('context_sha256', 'b'*64)]:
            broken = {**data, field: value}
            with self.assertRaises(ValueError): reader.neutral(json.dumps(broken).encode(), 'new', 'a'*64)

    def test_junit_preserves_different_states(self):
        xml = b'<testsuite tests="4"><testcase classname="C" name="ok"/><testcase classname="C" name="bad"><failure/></testcase><testcase classname="C" name="skip"><skipped/></testcase><testcase classname="C" name="xf"><skipped type="pytest.xfail"/></testcase></testsuite>'
        rows = reader.junit(xml)
        self.assertEqual([r['status'] for r in rows], ['pass', 'fail', 'skipped', 'xfail'])

    def test_junit_nested_counts_and_duplicate_ids(self):
        self.assertEqual(len(reader.junit(b'<testsuites tests="1"><testsuite tests="1"><testcase name="A"/></testsuite></testsuites>')), 1)
        for xml in (b'<testsuite tests="2"><testcase name="A"/></testsuite>',
                    b'<testsuite><testcase name="A"/><testcase name="A"/></testsuite>',
                    b'<testsuite tests="0"/>', b'<testsuite><testcase name="A">'):
            with self.subTest(xml=xml), self.assertRaises(ValueError): reader.junit(xml)

    def test_junit_suppressed_unknown_and_flaky_are_not_passes(self):
        for xml in (b'<testsuite><testcase name="A" status="notrun" result="suppressed"/></testsuite>',
                    b'<testsuite><testcase name="A" status="unknown"/></testsuite>',
                    b'<testsuite><testcase name="A"><flakyFailure/></testcase></testsuite>'):
            with self.subTest(xml=xml): self.assertNotEqual(reader.junit(xml)[0]['status'],'pass')

    def test_xml_dtd_and_entities_refused(self):
        for raw in (b'<!DOCTYPE testsuite [<!ENTITY x "bad">]><testsuite/>', b'\xff\xfe<\x00'):
            with self.assertRaises(ValueError): reader.junit(raw)

    def test_metrics_keep_denominators_and_state_formula(self):
        metric = {'kind': 'mutation', 'states': {'Killed': 3, 'Timeout': 2, 'Survived': 1, 'NoCoverage': 1,
                  'CompileError': 4}, 'formula': 'stryker-detected-over-valid', 'excluded': [], 'scope': ['core']}
        result = reader.metric(metric)
        self.assertEqual(result['numerator'], 5); self.assertEqual(result['denominator'], 7)
        self.assertEqual(result['states']['Timeout'], 2)
        self.assertFalse(result['semantic_truth_verified'])
        with self.assertRaises(ValueError): reader.metric({**metric, 'states': {'Killed': -1}})

    def test_coverage_does_not_hide_denominator(self):
        data = reader.metric({'kind': 'coverage', 'numerator': 5, 'denominator': 10, 'excluded': ['vendor'], 'scope': ['src']})
        self.assertEqual(data['percent'], 50)
        self.assertIsNone(reader.metric({'kind': 'coverage', 'numerator': 0, 'denominator': 0, 'excluded': [], 'scope': []})['percent'])
        with self.assertRaises(ValueError): reader.metric({'kind': 'coverage', 'numerator': 6, 'denominator': 5, 'excluded': [], 'scope': []})

    def test_actual_unittest_runner_reports_cases_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t); (p/'test_sample.py').write_text('import unittest\nclass C(unittest.TestCase):\n def test_ok(self): self.assertEqual(2+2,4)\n @unittest.skip("fixture")\n def test_skip(self): pass\n')
            env = {**os.environ, 'VERIMISSION_RUN_ID': 'test-run', 'VERIMISSION_CONTEXT_SHA256': 'a'*64,
                   'VERIMISSION_REPORT': str(p/'report.json')}
            args = [sys.executable, '-B', str(ROOT/'scripts/result_runner.py'), 'unittest', '--start', '.']
            result = subprocess.run(args, cwd=p, env=env, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            rows = reader.neutral((p/'report.json').read_bytes(), 'test-run', 'a'*64)
            self.assertEqual({r['status'] for r in rows}, {'pass', 'skipped'})
            before = (p/'report.json').read_bytes()
            self.assertNotEqual(subprocess.run(args, cwd=p, env=env, capture_output=True).returncode, 0)
            self.assertEqual(before, (p/'report.json').read_bytes())


if __name__ == '__main__': unittest.main()
