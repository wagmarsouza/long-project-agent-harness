import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/regression_contract.py'
spec = importlib.util.spec_from_file_location('regression_contract_test', SCRIPT)
contract = importlib.util.module_from_spec(spec)
spec.loader.exec_module(contract)


def baseline():
    return {'format': 'verimission-baseline-v1',
            'reference': {'kind': 'specification', 'id': 'approved-fixture-v1'},
            'protected_files': {'tests.py': 'a' * 64}, 'context_files': {},
            'obligations': [{'id': 'CAP-A', 'criterion': 'R', 'case': 'case-a', 'critical': True,
                             'sources': ['src.py'], 'comparator': {'kind': 'status'}}], 'debt': []}


class ContractTests(unittest.TestCase):
    def test_valid_baseline(self):
        self.assertEqual(contract.baseline(baseline(), {'R'})['reference']['id'], 'approved-fixture-v1')

    def test_unknown_fields_refused(self):
        b = baseline(); b['force'] = True
        with self.assertRaises(contract.Invalid): contract.baseline(b, {'R'})

    def test_missing_protection_refused(self):
        b = baseline(); b['protected_files'] = {}
        with self.assertRaises(contract.Invalid): contract.baseline(b, {'R'})

    def test_duplicate_obligation_and_duplicate_case_refused(self):
        for changed_id in (False, True):
            b = baseline(); b['obligations'].append(copy.deepcopy(b['obligations'][0]))
            if changed_id: b['obligations'][1]['id'] = 'OTHER'
            with self.assertRaises(contract.Invalid): contract.baseline(b, {'R'})

    def test_empty_obligations_and_unknown_criterion_refused(self):
        b = baseline(); b['obligations'] = []
        with self.assertRaises(contract.Invalid): contract.baseline(b, {'R'})
        with self.assertRaises(contract.Invalid): contract.baseline(baseline(), {'OTHER'})

    def test_nonfinite_and_duplicate_json_keys_refused(self):
        for raw in ('{"a":1,"a":2}', '{"value":NaN}', '{"value":Infinity}'):
            with self.assertRaises(contract.Invalid): contract.loads(raw)

    def test_numeric_comparison_requires_declared_nonnegative_tolerances(self):
        b = baseline(); c = b['obligations'][0]['comparator']
        c.update(kind='numeric', expected=2.0, abs_tol=0.01, rel_tol=0)
        contract.baseline(b, {'R'})
        c['abs_tol'] = -1
        with self.assertRaises(contract.Invalid): contract.baseline(b, {'R'})

    def test_commit_reference_must_be_resolved(self):
        b = baseline(); b['reference'] = {'kind': 'commit', 'id': 'HEAD'}
        with self.assertRaises(contract.Invalid): contract.baseline(b, {'R'})

    def test_missing_case_not_compensated_by_new_passes(self):
        out = contract.compare(baseline(), [{'id': 'other', 'status': 'pass'}])
        self.assertFalse(out['passed']); self.assertEqual(out['rows'][0]['status'], 'missing')

    def test_skip_timeout_error_xfail_unknown_do_not_preserve(self):
        for status in ('skipped', 'timeout', 'error', 'xfail', 'inconclusive', 'unsupported', 'xpass'):
            with self.subTest(status=status):
                self.assertFalse(contract.compare(baseline(), [{'id': 'case-a', 'status': status}])['passed'])

    def test_exact_expected_not_silently_rebaselined(self):
        b = baseline(); b['obligations'][0]['comparator'] = {'kind': 'exact', 'expected': {'return': 5, 'memory': 9}}
        out = contract.compare(b, [{'id': 'case-a', 'status': 'pass', 'observed': {'return': 5, 'memory': 0}}])
        self.assertFalse(out['passed'])

    def test_explicit_null_is_not_a_missing_observation(self):
        b=baseline(); b['obligations'][0]['comparator']={'kind':'exact','expected':None}
        self.assertFalse(contract.compare(b,[{'id':'case-a','status':'pass'}])['passed'])
        self.assertTrue(contract.compare(b,[{'id':'case-a','status':'pass','observed':None}])['passed'])

    def test_numeric_tolerance_and_nonfinite_result(self):
        b = baseline(); b['obligations'][0]['comparator'] = {'kind': 'numeric', 'expected': 1., 'abs_tol': 0.01, 'rel_tol': 0}
        self.assertTrue(contract.compare(b, [{'id': 'case-a', 'status': 'pass', 'observed': 1.005}])['passed'])
        for val in (float('nan'), 2, True):
            self.assertFalse(contract.compare(b, [{'id': 'case-a', 'status': 'pass', 'observed': val}])['passed'])

    def test_explicit_metric_floor_and_budget_ceiling(self):
        for kind,good,bad in [('minimum',90,79),('maximum',70,81)]:
            b=baseline(); b['obligations'][0]['comparator']={'kind':kind,'expected':80}
            contract.baseline(b,{'R'})
            self.assertTrue(contract.compare(b,[{'id':'case-a','status':'pass','observed':good}])['passed'])
            self.assertFalse(contract.compare(b,[{'id':'case-a','status':'pass','observed':bad}])['passed'])

    def test_contract_denominator_change_is_not_comparable(self):
        b = baseline(); b['obligations'][0]['contract'] = {'denominator': 100, 'excluded': []}
        out = contract.compare(b, [{'id': 'case-a', 'status': 'pass', 'contract': {'denominator': 99, 'excluded': ['hard']}}])
        self.assertFalse(out['passed']); self.assertEqual(out['rows'][0]['status'], 'incomparable')

    def test_duplicate_result_ids_refused(self):
        with self.assertRaises(contract.Invalid):
            contract.compare(baseline(), [{'id': 'case-a', 'status': 'pass'}] * 2)

    def test_critical_failure_cannot_be_hidden_in_average(self):
        out = contract.compare(baseline(), [{'id': 'case-a', 'status': 'fail'}] +
                               [{'id': str(i), 'status': 'pass'} for i in range(100)])
        self.assertFalse(out['passed']); self.assertEqual(out['critical']['verified'], 0)

    def test_transitive_reverse_graph_handles_cycle(self):
        self.assertEqual(contract.affected({'a': ['b'], 'b': ['c'], 'c': ['b']}, {'c'}), {'a', 'b', 'c'})

    def test_debt_not_promoted_to_obligation(self):
        b = baseline(); b['debt'] = [{'id': 'old-skip', 'reason': 'Unavailable platform', 'owner': 'maintainer', 'expires': '2027-01-01'}]
        out = contract.compare(b, [{'id': 'case-a', 'status': 'pass'}])
        self.assertTrue(out['passed']); self.assertEqual(out['coverage']['total'], 1)
        self.assertEqual(out['critical']['percent'], 100.0)


if __name__ == '__main__': unittest.main()
