"""Benchmark evidence distinguishes executed cycles from seeded historical vectors."""
import unittest
from unittest.mock import patch
from test_v83_assurance import load


class HistoryBenchmarkTests(unittest.TestCase):
    def test_final_budget_overrun_never_receives_success(self):
        m=load('history_benchmark');clock=[0.0]
        original=m.Fixture
        class SlowFinalValidation(original):
            def __enter__(self):
                f=super().__enter__();validate=f.h.store.validate
                def finish():
                    result=validate();clock[0]=10.0;return result
                f.h.store.validate=finish
                return f
        with patch.object(m,'Fixture',SlowFinalValidation),patch.object(m.time,'monotonic',side_effect=lambda:clock[0]):
            r=m.run(native_cycles=0,history_sizes=[1],samples=1,budget_seconds=1)
        self.assertFalse(r['passed'],r)
        self.assertFalse(r['complete'])
        self.assertEqual(r['error_type'],'TimeoutError')
        self.assertEqual(r['seconds'],10.0)

    def test_native_replay_preserves_history_and_does_not_inflate_progress(self):
        r=load('history_benchmark').run(native_cycles=3,history_sizes=[],samples=1,backend='auto',budget_seconds=60)
        self.assertTrue(r['passed'],r)
        self.assertEqual(r['native']['verified_closures'],3)
        self.assertEqual(r['native']['progress_cycles'],1)
        self.assertGreaterEqual(r['native']['fresh_process_resumes'],1)
        self.assertFalse(r['mission_acceptance'])

    def test_seeded_vectors_are_not_reported_as_executed_work(self):
        r=load('history_benchmark').run(native_cycles=0,history_sizes=[20],samples=1,backend='python',budget_seconds=60)
        self.assertTrue(r['passed'],r)
        self.assertEqual(r['native']['verified_closures'],0)
        self.assertEqual(r['histories'][0]['seeded_cycle_vectors'],20)
        self.assertEqual(r['histories'][0]['native_verified_cycles'],0)
        self.assertEqual(r['histories'][0]['samples'],1)

    def test_unbounded_or_empty_requests_are_refused(self):
        m=load('history_benchmark')
        for kwargs in ({'native_cycles':501},{'history_sizes':[20001]},{'samples':0},
                       {'budget_seconds':0},{'native_cycles':0,'history_sizes':[]}):
            with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):m.run(**kwargs)


if __name__=='__main__':unittest.main()
