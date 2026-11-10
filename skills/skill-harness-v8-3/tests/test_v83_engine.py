import copy
import hashlib
import importlib.util
import json
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/harness.py'
spec = importlib.util.spec_from_file_location('control83_engine_tests', SCRIPT)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

RUNNER = '''import json,os,sys
from pathlib import Path
value=json.loads(Path('candidate-'+sys.argv[1]+'.json').read_text())
out={'format':'verimission-results-v1','run_id':os.environ['VERIMISSION_RUN_ID'],
'context_sha256':os.environ['VERIMISSION_CONTEXT_SHA256'],'complete':value.get('complete',True),'cases':value['cases']}
if value.get('old'): out['run_id']='old'
with Path(os.environ['VERIMISSION_REPORT']).open('x') as f: json.dump(out,f)
'''


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='control83-')
        self.root = Path(self.tmp.name)
        (self.root/'runner.py').write_text(RUNNER)
        self.data('R', [{'id':'A','status':'pass'}])
        self.baseline = {'format':'verimission-baseline-v1','reference':{'kind':'specification','id':'accepted-fixture'},
                         'protected_files':{'runner.py':hashlib.sha256((self.root/'runner.py').read_bytes()).hexdigest()},
                         'context_files':{},'obligations':[{'id':'CAP-A','criterion':'R','case':'A','critical':True,
                         'sources':['candidate-R.json'],'comparator':{'kind':'status'}}], 'debt':[]}
        self.policy = {'schema':1,'baseline':{'path':'baseline.json','sha256':''},
                       'input_patterns':['candidate-*.json','runner.py'],'criteria':{'R':{'output_pattern':'reports/{run}.json'}},
                       'mode':'full','graph':{},'graph_complete':False,'environment':[]}
        self.mission = {'objective':'Preserve declared capabilities','mode':'light','in_scope':['fixtures'],
                        'out_of_scope':['external systems'],'criteria':[self.criterion('R')],
                        'budget':{'max_cycles':20,'max_no_progress':10,'max_same_failures':10,'consolidate_every':20},
                        'regression_policy':self.policy}
        self.h = m.Harness(self.root)

    def tearDown(self): self.tmp.cleanup()

    def data(self, cid, cases, **kwargs):
        (self.root/('candidate-'+cid+'.json')).write_text(json.dumps({'cases':cases,**kwargs}))

    def criterion(self, cid):
        return {'id':cid,'description':'Retain declared cases','argv':[sys.executable,'runner.py',cid],
                'artifacts':['runner.py','candidate-'+cid+'.json']}

    def init(self):
        p=self.root/'baseline.json'; p.write_text(json.dumps(self.baseline))
        self.policy['baseline']['sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
        return self.h.init(self.mission)

    def plan(self, criteria=None):
        review=self.h.review('preservation')['review']
        return {'topic':'preservation','task':'proof','premise':'Retain capabilities','residual':'Run retained cases',
                'review_id':review['id'],'reviewed_claims':review['claims'], 'criteria':criteria or list(self.policy['criteria']),
                'approach':{'method':'finite-replay','inputs':'candidate snapshots','environment':'synthetic local'},
                'reverify_reason':'Revalidate after current candidate change'}

    def cycle(self):
        cid=self.h.start(self.plan())['cycle']
        for c in self.policy['criteria']: self.h.check(cid,c)
        return cid

    def refuse(self, code, call):
        with self.assertRaises(m.Refusal) as err: call()
        self.assertEqual(err.exception.code,code)

    def test_baseline_preview_is_read_only_and_not_adoption(self):
        self.init(); before=self.h.db.read_bytes()
        out=self.h.baseline_preview(self.mission)
        self.assertFalse(out['adopted']); self.assertEqual(before,self.h.db.read_bytes())

    def test_native_preservation_end_to_end(self):
        self.init(); cid=self.cycle()
        self.assertTrue(self.h.regression_report(cid)['passed'])
        self.assertEqual(self.h.close(cid,'verified','continue')['status'],'verified')
        self.assertTrue(self.h.accept_mission()['accepted'])

    def test_plan_cannot_omit_preservation_criterion(self):
        self.mission['criteria'].append({'id':'NEW','description':'New behavior','argv':[sys.executable,'-c','pass'],'artifacts':[]})
        self.init(); self.refuse('REGRESSION_PLAN',lambda:self.h.start(self.plan(['NEW'])))

    def test_green_process_with_missing_old_case_blocks_close(self):
        self.init(); self.data('R',[{'id':'replacement','status':'pass'}]); cid=self.cycle()
        self.refuse('REGRESSION_BLOCKED',lambda:self.h.close(cid,'verified','not done'))
        with self.h.state() as state:
            self.assertEqual(state['cycles'][-1]['status'],'active')
            self.assertFalse(state['cycles'][-1]['regression_assessment']['passed'])
        self.h.interrupt(cid,'repair old capability')

    def test_skipped_previous_pass_does_not_preserve(self):
        self.init(); self.data('R',[{'id':'A','status':'skipped'}]); cid=self.cycle()
        self.assertFalse(self.h.regression_report(cid)['passed'])

    def test_stale_source_invalidates_previous_acceptance(self):
        self.init(); cid=self.cycle(); self.h.close(cid,'verified','done')
        self.data('R',[{'id':'A','status':'fail'}])
        self.assertFalse(self.h.accept_mission()['accepted'])
        self.assertFalse(self.h.resume()['regression']['passed'])

    def test_oracle_change_refused_without_new_authorized_contract(self):
        self.init(); (self.root/'runner.py').write_text(RUNNER+'\n# weakened')
        self.refuse('REGRESSION_SOURCE',lambda:self.h.start(self.plan()))

    def test_baseline_hash_drift_refused(self):
        self.init(); (self.root/'baseline.json').write_text('{}')
        self.refuse('REGRESSION_SOURCE',lambda:self.h.start(self.plan()))

    def test_generated_report_is_immutable_and_stales_if_tampered(self):
        self.init(); cid=self.cycle()
        with self.h.state() as state: rel=state['cycles'][-1]['checks'][-1]['regression']['report']['path']
        (self.root/rel).write_text('{}')
        self.assertFalse(self.h.regression_report(cid)['passed'])

    def test_timeout_and_launch_failure_are_recorded(self):
        self.mission['criteria'][0]['argv']=[sys.executable,'-c','import time;time.sleep(3)']
        self.mission['budget']['max_check_seconds']=1
        self.init(); cid=self.cycle()
        with self.h.state() as state: self.assertEqual(state['cycles'][-1]['checks'][-1]['outcome'],'timeout')
        self.assertFalse(self.h.regression_report(cid)['passed'])

    def test_incomplete_result_and_replayed_run_refused(self):
        self.init()
        for kwargs in ({'complete':False},{'old':True}):
            self.data('R',[{'id':'A','status':'pass'}],**kwargs)
            cid=self.cycle(); self.assertFalse(self.h.regression_report(cid)['passed'])
            self.h.interrupt(cid,'incomplete evidence retained')

    def test_failed_then_pass_same_input_is_not_silently_flaky_green(self):
        self.init(); cid=self.h.start(self.plan())['cycle']
        self.h.check(cid,'R')
        with self.h.state(write=True) as state:
            state['cycles'][-1]['checks'][-1]['passed']=False
            state['cycles'][-1]['checks'][-1]['regression']['assessment']['passed']=False
        self.h.check(cid,'R')
        self.assertFalse(self.h.regression_report(cid)['passed'])

    def test_failure_history_and_honest_correction_preserved(self):
        self.init(); self.data('R',[{'id':'A','status':'fail'}]); cid=self.cycle()
        self.h.interrupt(cid,'fix implementation')
        self.data('R',[{'id':'A','status':'pass'}]); cid2=self.cycle(); self.h.close(cid2,'verified','restored')
        with self.h.state() as state:
            self.assertEqual(state['cycles'][0]['status'],'blocked')
            self.assertEqual(state['regression_guard']['last_validated']['cycle'],cid2)

    def test_missing_report_does_not_overwrite_old_evidence(self):
        self.mission['criteria'][0]['argv']=[sys.executable,'-c','pass']
        self.init(); cid=self.cycle(); self.assertFalse(self.h.regression_report(cid)['passed'])

    def test_context_file_change_blocks_until_review(self):
        (self.root/'lock.txt').write_text('tool-v1')
        self.baseline['context_files']={'lock.txt':hashlib.sha256((self.root/'lock.txt').read_bytes()).hexdigest()}
        self.init(); (self.root/'lock.txt').write_text('tool-v2')
        self.refuse('REGRESSION_SOURCE',lambda:self.h.start(self.plan()))

    def test_policy_is_not_revisable_by_noninteractive_agent(self):
        self.init()
        with self.h.state() as state:
            proposal={'expected_mission_hash':state['mission_hash'],'expected_revision':state['revision'],
                      'reason':'New oracle','authorization':{'source':'user','reference':'explicit-review'},'mission':copy.deepcopy(self.mission)}
        proposal['mission']['objective']='Revised capability'
        # Existing inherited authorization tests verify exact interactive confirmation in detail.
        with self.assertRaises(m.Refusal): self.h.revise_mission(proposal)

    def test_impact_cache_reuses_only_unaffected_noncritical_criterion(self):
        self.data('S',[{'id':'B','status':'pass'}]); self.mission['criteria'].append(self.criterion('S'))
        self.policy['criteria']['S']={'output_pattern':'reports/{run}.json'}
        self.policy.update(mode='impact',graph_complete=True,graph={'candidate-R.json':[], 'candidate-S.json':[], 'runner.py':[]})
        self.baseline['obligations'].append({'id':'CAP-B','criterion':'S','case':'B','critical':False,
                                            'sources':['candidate-S.json'],'comparator':{'kind':'status'}})
        self.init(); cid=self.cycle(); self.h.close(cid,'verified','continue')
        self.data('R',[{'id':'A','status':'pass','observed':5}])
        plan=self.h.regression_plan(); self.assertEqual(plan['required_criteria'],['R'])
        cid2=self.h.start(self.plan(['R']))['cycle']; self.h.check(cid2,'R')
        self.assertTrue(self.h.regression_report(cid2)['passed'])
        self.h.close(cid2,'verified','retained')

    def test_cli_new_read_commands_and_legacy_no_policy(self):
        self.init()
        for command in ('regression-plan','regression-report'):
            proc=subprocess.run([sys.executable,'-B',str(SCRIPT),'--project',str(self.root),command],capture_output=True,text=True)
            self.assertEqual(proc.returncode,0,proc.stdout+proc.stderr)
            self.assertTrue(json.loads(proc.stdout)['ok'])

    def test_report_retains_failed_case_diagnostics(self):
        self.init(); self.data('R',[{'id':'A','status':'fail'}]); cid=self.cycle()
        report=self.h.regression_report(cid)
        self.assertEqual(report['rows'][0]['status'],'fail')

    def test_comparison_before_close_is_not_authority_to_skip_gate(self):
        self.init(); cid=self.cycle(); self.assertTrue(self.h.regression_report(cid)['passed'])
        self.data('R',[{'id':'A','status':'fail'}])
        self.refuse('REGRESSION_BLOCKED',lambda:self.h.close(cid,'verified','must refuse stale assessment'))

    def test_baseline_output_alias_rejected_before_execution(self):
        self.policy['criteria']['R']['output_pattern']='candidate-{run}.json'
        self.init(); cid=self.cycle()
        self.assertFalse(self.h.regression_report(cid)['passed'])

    def test_noncritical_zero_denominator_is_na(self):
        self.baseline['obligations'][0]['critical']=False
        self.init(); cid=self.cycle()
        self.assertIsNone(self.h.regression_report(cid)['critical']['percent'])

    def test_new_input_changes_invalidate_full_mode(self):
        self.init(); cid=self.cycle()
        self.data('new',[{'id':'extra','status':'pass'}])
        self.assertFalse(self.h.regression_report(cid)['passed'])

    def test_source_changed_during_check_is_not_verified(self):
        script=RUNNER+"\nPath('candidate-R.json').write_text('{}')\n"
        (self.root/'runner.py').write_text(script)
        self.baseline['protected_files']['runner.py']=hashlib.sha256((self.root/'runner.py').read_bytes()).hexdigest()
        self.init(); cid=self.cycle()
        self.assertFalse(self.h.regression_report(cid)['passed'])

    def test_no_report_execution_on_start_or_close(self):
        self.init(); cid=self.h.start(self.plan())['cycle']
        self.assertFalse((self.root/'reports').exists())
        self.refuse('REGRESSION_BLOCKED',lambda:self.h.close(cid,'verified','no implicit runner'))
        self.assertFalse((self.root/'reports').exists())

    def test_atomic_store_failure_preserves_active_cycle_and_evidence(self):
        self.init(); cid=self.cycle(); before=self.h.db.read_bytes()
        with patch.object(self.h.store,'_write_unlocked',side_effect=OSError('simulated interruption')):
            with self.assertRaises(OSError): self.h.close(cid,'verified','commit not completed')
        self.assertEqual(before,self.h.db.read_bytes())
        self.assertEqual(self.h.close(cid,'verified','recover commit')['status'],'verified')

    def test_launch_failure_cannot_create_passing_receipt(self):
        self.mission['criteria'][0]['argv']=[sys.executable,'does-not-exist.py']
        self.init(); cid=self.cycle()
        self.assertFalse(self.h.regression_report(cid)['passed'])

    def test_policy_unknown_fields_and_path_escape_refused(self):
        for value in ({**self.policy,'force':True}, {**self.policy,'input_patterns':['../*.json']}):
            self.mission['regression_policy']=value
            (self.root/'baseline.json').write_text(json.dumps(self.baseline))
            value['baseline']['sha256']=hashlib.sha256((self.root/'baseline.json').read_bytes()).hexdigest()
            self.refuse('REGRESSION_POLICY',lambda:self.h.init(self.mission))

    def test_witness_mismatch_cannot_justify_rebaseline_implicitly(self):
        self.baseline['obligations'][0]['comparator']={'kind':'exact','expected':{'result':5,'memory':9}}
        self.init(); self.data('R',[{'id':'A','status':'pass','observed':{'result':5,'memory':0}}]); cid=self.cycle()
        self.refuse('REGRESSION_BLOCKED',lambda:self.h.close(cid,'verified','incorrect memory'))
        with self.h.state() as state:
            self.assertEqual(state['regression_guard']['baseline']['obligations'][0]['comparator']['expected']['memory'],9)

    def test_explicit_human_revision_preserves_previous_baseline_history(self):
        class Terminal(io.StringIO):
            def isatty(self): return True
        self.init()
        with self.h.state() as state:
            proposal={'expected_mission_hash':state['mission_hash'],'expected_revision':state['revision'],
                      'reason':'Explicitly approved capability change','authorization':{'source':'user','reference':'Synthetic explicit approval'},
                      'mission':copy.deepcopy(self.mission)}
        proposal['mission']['objective']='Reviewed new scope'
        token=self.h.preview_mission(proposal)['confirmation']
        with patch.object(m.sys,'stdin',Terminal()), patch.object(m.sys,'stdout',Terminal()), \
             patch.object(m,'input',return_value=token,create=True), patch.dict(os.environ,{'CI':'','HARNESS_AUTOMATION':''}):
            self.h.revise_mission(proposal)
        with self.h.state() as state:
            self.assertEqual(len(state['regression_history']),1)
            self.assertEqual(state['regression_guard']['mission_hash'],state['mission_hash'])
            self.assertIsNone(state['regression_guard']['last_validated'])

    def test_protected_counterexample_file_cannot_disappear(self):
        (self.root/'corpus.json').write_text('[1,2,3]')
        self.policy['input_patterns'].append('corpus.json')
        self.baseline['protected_files']['corpus.json']=hashlib.sha256((self.root/'corpus.json').read_bytes()).hexdigest()
        self.init(); (self.root/'corpus.json').unlink()
        self.refuse('REGRESSION_SOURCE',lambda:self.h.start(self.plan()))

    def test_shared_dependency_forces_noncritical_caller_replay(self):
        self.data('S',[{'id':'B','status':'pass'}]); self.mission['criteria'].append(self.criterion('S'))
        self.policy['criteria']['S']={'output_pattern':'reports/{run}.json'}
        self.policy.update(mode='impact',graph_complete=True,graph={'candidate-R.json':[], 'candidate-S.json':['candidate-R.json'], 'runner.py':[]})
        self.baseline['obligations'].append({'id':'CAP-B','criterion':'S','case':'B','critical':False,
                                            'sources':['candidate-S.json'],'comparator':{'kind':'status'}})
        self.init(); cid=self.cycle(); self.h.close(cid,'verified','continue')
        self.data('R',[{'id':'A','status':'pass','observed':5}])
        self.assertEqual(self.h.regression_plan()['required_criteria'],['R','S'])

    def test_incomplete_graph_falls_back_to_full_replay(self):
        self.baseline['obligations'][0]['critical']=False
        self.policy.update(mode='impact',graph_complete=False)
        self.init(); cid=self.cycle(); self.h.close(cid,'verified','continue')
        self.assertEqual(self.h.regression_plan()['required_criteria'],['R'])

    def test_undeclared_environment_change_does_not_authenticate_context(self):
        self.policy['environment']=['V83_TEST_CONTEXT']
        with patch.dict(os.environ,{'V83_TEST_CONTEXT':'one'}):
            self.init(); cid=self.cycle(); self.h.close(cid,'verified','continue')
        with patch.dict(os.environ,{'V83_TEST_CONTEXT':'two'}):
            self.assertFalse(self.h.regression_report(cid)['passed'])

    def test_claim_dependency_uses_current_preservation_proof(self):
        self.init(); cid=self.cycle()
        self.h.claim({'id':'FACT-A','topic':'preservation','statement':'Fixture passed in its declared scope',
                      'kind':'fact','cycle':cid,'criterion':'R','depends_on':[]})
        self.h.close(cid,'verified','continue'); self.data('R',[{'id':'A','status':'fail'}])
        plan=self.plan(); plan['relies_on']=['FACT-A']
        with self.assertRaises(m.Refusal): self.h.start(plan)

    def test_policy_and_periodic_review_use_same_cycle_boundary(self):
        prompt='CORE: preserve evidence.\n<!-- objectives -->\nNext task\n<!-- /objectives -->\n<!-- scenario -->\nLocal\n<!-- /scenario -->\n'
        (self.root/'governing.md').write_text(prompt)
        self.mission['budget']['consolidate_every']=2
        self.mission['periodic_review']={'every':2,'notes_pattern':'note-{cycle}.md','digest_pattern':'digest-{start}-{end}.json',
            'governing_file':'governing.md','invariant_markers':['CORE'],'stale_markers':[],
            'mutable_sections':{'objectives':{'begin':'<!-- objectives -->','end':'<!-- /objectives -->'},
                                'scenario':{'begin':'<!-- scenario -->','end':'<!-- /scenario -->'}}}
        self.init()
        cid=self.cycle(); (self.root/'note-1.md').write_text('Verified bounded synthetic fixture.'); self.h.close(cid,'verified','continue')
        self.data('R',[{'id':'A','status':'pass','observed':{'implementation_changed':True}}])
        cid=self.cycle(); (self.root/'note-2.md').write_text('Replayed the same bounded fixture; no new discovery.')
        digest=self.h.digest(cid)
        proposal={'window':digest['window'],'digest_sha256':digest['digest_sha256'],
                  'prompt_sha256':hashlib.sha256((self.root/'governing.md').read_bytes()).hexdigest(),
                  'reread':[{'cycle':r['cycle'],'sha256':r['sha256'],'finding':'Read the synthetic note: verification remains scoped.'} for r in digest['notes']],
                  'updates':{},'reason':'The two fixture notes preserve the same scope.','loss_acknowledgements':[]}
        self.assertEqual(self.h.close(cid,'verified','continue',review_input=proposal)['status'],'verified')
        with self.h.state() as state:
            self.assertEqual(state['consolidations'][-1]['through_cycle'],cid)
            self.assertIn('regression',state['consolidations'][-1])
            self.assertEqual(state['consolidations'][-1]['cycle_records_sha256'],m.digest(state['cycles']))

    def test_fresh_candidate_can_revalidate_without_erasing_old_cycle(self):
        self.init(); cid=self.cycle(); self.h.close(cid,'verified','continue')
        self.data('R',[{'id':'A','status':'pass','observed':{'new_implementation':True}}])
        cid2=self.cycle(); result=self.h.close(cid2,'verified','preserved')
        self.assertTrue(self.h.accept_mission()['accepted'])
        self.assertFalse(result['progress'])
        with self.h.state() as state:
            self.assertEqual(state['cycles'][0]['status'],'needs_review')
            self.assertEqual(state['cycles'][0]['status_history'][-1]['from'],'verified')

    def test_invalidated_fact_needs_explicit_reverification(self):
        self.init(); cid=self.cycle()
        self.h.claim({'id':'FACT-A','topic':'preservation','statement':'The bounded fixture passes',
                      'kind':'fact','cycle':cid,'criterion':'R','depends_on':[]})
        self.h.close(cid,'verified','continue')
        self.data('R',[{'id':'A','status':'pass','observed':7}]); cid2=self.cycle()
        with self.h.state() as state: self.assertEqual(state['claims']['FACT-A']['status'],'needs_review')
        receipt=self.h.claim_reverify({'id':'FACT-A','statement':'The bounded fixture passes','cycle':cid2,'criterion':'R','reason':'Fresh replay after candidate change'})
        self.assertFalse(receipt['new_knowledge'])

    def test_assessment_refuses_source_drift_between_criteria(self):
        self.data('S',[{'id':'B','status':'pass'}]); self.mission['criteria'].append(self.criterion('S'))
        self.policy['criteria']['S']={'output_pattern':'reports/{run}.json'}
        self.policy.update(mode='impact',graph_complete=True,graph={'candidate-R.json':[], 'candidate-S.json':[], 'runner.py':[]})
        self.baseline['obligations'].append({'id':'CAP-B','criterion':'S','case':'B','critical':False,
                                            'sources':['candidate-S.json'],'comparator':{'kind':'status'}})
        self.init(); cid=self.cycle()
        original=self.h._reg_current
        def drift(state,cycle,criterion):
            result=original(state,cycle,criterion)
            if criterion=='R': self.data('R',[{'id':'A','status':'pass','observed':'changed after assessment'}])
            return result
        with patch.object(self.h,'_reg_current',side_effect=drift):
            self.assertFalse(self.h.regression_report(cid)['passed'])


if __name__ == '__main__': unittest.main()
