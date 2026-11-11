"""Native metric gate, sealing, staleness and adversarial audit integration."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from test_v84_measurement_contract import inventory

SCRIPTS=Path(__file__).resolve().parents[1]/'scripts'
s=importlib.util.spec_from_file_location('quantity_harness',SCRIPTS/'harness.py')
engine=importlib.util.module_from_spec(s);s.loader.exec_module(engine)

WRITER='''import json,os
from pathlib import Path
kind=os.environ['VERIMISSION_MEASUREMENT_KIND']
p=json.loads(Path('candidate.json' if kind=='measurement' else 'audit-candidate.json').read_text())
p.update(run_id=os.environ['VERIMISSION_MEASUREMENT_RUN_ID'],context_sha256=os.environ['VERIMISSION_MEASUREMENT_CONTEXT_SHA256'])
if kind=='audit':
 plan=json.loads(Path(os.environ['VERIMISSION_AUDIT_SELECTION']).read_text())
 p.update(plan_id=plan['id'],units=[{'id':u,'status':p.pop('selected_status','pass') if len(plan['units'])==1 else p.get('selected_status','pass'),'executed':p.get('actually_executed',True),'artifacts':{'execution':{'path':'audit-proof.txt','sha256':__import__('hashlib').sha256(Path('audit-proof.txt').read_bytes()).hexdigest()}}} for u in plan['units']])
 p.pop('selected_status',None);p.pop('actually_executed',None)
if Path('replay.flag').exists():p['run_id']='old'
with Path(os.environ['VERIMISSION_MEASUREMENT_REPORT']).open('x') as f:json.dump(p,f)
'''

class Fixture:
    def __init__(self,pinned_roles=None):self.pinned_roles=pinned_roles
    def __enter__(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='measurement-test-');self.root=Path(self.tmp.name)
        (self.root/'src').mkdir()
        for name in ('a','b'):(self.root/'src'/f'{name}.c').write_text('fixture source '+name)
        (self.root/'verifier.py').write_text(WRITER)
        (self.root/'audit-proof.txt').write_text('synthetic control/execution evidence')
        self.write('universe.json',inventory())
        self.policy={'schema':1,'universe':{'path':'universe.json','sha256':self.sha('universe.json')},
            'criterion':'M','output_pattern':'measurement/{run}.json','required_gates':['source','behavior'],
            'protected_files':{'verifier.py':self.sha('verifier.py')},
            'input_patterns':['src/*.c','candidate.json'], 'acceptance_minimum':2,
            'audit':{'criterion':'A','output_pattern':'audit/{run}.json','every_cycles':5,'sample_size':1}}
        if self.pinned_roles is not None:self.policy['pinned_roles']=self.pinned_roles
        self.mission={'objective':'Synthetic generic quantity qualification','mode':'light','in_scope':['units'],
            'out_of_scope':['semantic truth'],'criteria':[{'id':cid,'description':cid,
                'argv':[sys.executable,'verifier.py'],'artifacts':['verifier.py']} for cid in ('M','A')],
            'measurement_policy':self.policy,
            'budget':{'max_cycles':30,'max_no_progress':30,'max_same_failures':30,'consolidate_every':30}}
        self.h=engine.Harness(self.root)
        self.candidate();self.audit_candidate()
        self.h.init(self.mission)
        return self
    def __exit__(self,*args):self.tmp.cleanup()
    def write(self,name,value):
        (self.root/name).parent.mkdir(parents=True,exist_ok=True)
        (self.root/name).write_text(json.dumps(value),encoding='utf-8')
    def sha(self,name):return engine.file_digest(self.root/name)
    def candidate(self):
        self.value={'format':'verimission-measurement-v1','complete':True,'claimed_verified':2,
            'universe_sha256':self.sha('universe.json'),'units':[{'id':u['id'],'identity':u['identity'],
            'gates':{'source':'pass','behavior':'pass'},'artifacts':{'deliverable':{
            'path':u['deliverable'],'sha256':self.sha(u['deliverable'])}}} for u in inventory()['units']]}
        self.write('candidate.json',self.value)
    def audit_candidate(self,**extra):
        self.audit={'format':'verimission-measurement-audit-v1','complete':True,'recount_ids':['a','b'],
            'controls':{'healthy_passed':True,'known_bad_rejected':True,'artifacts':{
                'control':{'path':'audit-proof.txt','sha256':self.sha('audit-proof.txt')}}},**extra}
        self.write('audit-candidate.json',self.audit)
    def start(self,criteria=None):
        r=self.h.review('quantity')
        return self.h.start({'topic':'quantity','task':'derive metric','premise':'evidence qualifies units',
            'residual':'verify actual evidence','review_id':r['review']['id'],'reviewed_claims':list(r['claims']),
            'criteria':criteria or ['M'],'approach':{'method':'finite verifier','inputs':'bound units','environment':'test'},
            'reverify_reason':'Explicitly revalidate current metric inputs'})['cycle']
    def close(self,cid):return self.h.close(cid,'verified','Continue only with qualified counts')

class NativeMetricTests(unittest.TestCase):
    def test_newly_qualified_units_are_progress_but_revalidation_is_not_new_work(self):
        with Fixture() as f:
            f.value['units'][1]['gates']['behavior']='unknown';f.value['claimed_verified']=1
            f.write('candidate.json',f.value)
            cid=f.start();f.h.check(cid,'M');f.close(cid)
            f.candidate();cid=f.start();f.h.check(cid,'M');f.close(cid)
            with f.h.state() as state:
                self.assertTrue(state['cycles'][-1]['progress'])
                self.assertEqual(state['cycles'][-1]['measurement_progress']['new_unit_ids'],['b'])
            cid=f.start();f.h.check(cid,'M');f.close(cid)
            with f.h.state() as state:
                self.assertFalse(state['cycles'][-1]['progress'])
                self.assertEqual(state['cycles'][-1]['measurement_progress']['new_unit_ids'],[])

    def test_pinned_oracle_role_cannot_be_changed_to_make_a_candidate_pass(self):
        with Fixture(pinned_roles=['oracle']) as f:
            (f.root/'oracle.txt').write_text('expected behavior')
            for row in f.value['units']:row['artifacts']['oracle']={'path':'oracle.txt','sha256':f.sha('oracle.txt')}
            f.write('candidate.json',f.value)
            cid=f.start();self.assertTrue(f.h.check(cid,'M')['passed']);f.close(cid)
            (f.root/'oracle.txt').write_text('weaker expected behavior')
            for row in f.value['units']:row['artifacts']['oracle']['sha256']=f.sha('oracle.txt')
            f.write('candidate.json',f.value)
            cid=f.start();self.assertFalse(f.h.check(cid,'M')['passed'])
            self.assertEqual(f.h.measurement_report()['counts']['verified'],0)

    def test_checked_active_units_do_not_count_until_close(self):
        with Fixture() as f:
            cid=f.start();self.assertTrue(f.h.check(cid,'M')['passed'])
            view=f.h.measurement_report();self.assertEqual(view['counts']['verified'],0)
            self.assertEqual(view['counts']['pending'],2)
            self.assertFalse(f.h.cycle_boundary(cid)['passed'])
            f.close(cid)
            self.assertEqual(f.h.measurement_report()['counts']['verified'],2)
            self.assertTrue(f.h.cycle_boundary(cid)['passed'])
    def test_source_drift_invalidates_unit_and_dependents_without_rewriting_history(self):
        with Fixture() as f:
            cid=f.start();f.h.check(cid,'M');f.close(cid)
            before=f.h.db.read_bytes();(f.root/'src/a.c').write_text('changed')
            view=f.h.measurement_report()
            self.assertEqual(view['counts']['verified'],0);self.assertEqual(view['counts']['stale'],2)
            self.assertEqual(f.h.db.read_bytes(),before)
            self.assertFalse(f.h.validate()['passed'])
    def test_report_edit_or_deletion_cannot_keep_a_verified_count(self):
        for remove in (False,True):
            with self.subTest(remove=remove),Fixture() as f:
                cid=f.start();r=f.h.check(cid,'M');f.close(cid)
                p=f.root/r['measurement']['report']['path']
                p.unlink() if remove else p.write_text('{}')
                self.assertEqual(f.h.measurement_report()['counts']['verified'],0)
    def test_arbitrary_headline_and_replayed_run_fail(self):
        for replay in (False,True):
            with self.subTest(replay=replay),Fixture() as f:
                if replay:(f.root/'replay.flag').write_text('replay')
                else:f.value['claimed_verified']=4745;f.write('candidate.json',f.value)
                cid=f.start();self.assertFalse(f.h.check(cid,'M')['passed'])
                with self.assertRaises(engine.Refusal):f.close(cid)
                self.assertEqual(f.h.measurement_report()['counts']['verified'],0)
    def test_omitted_required_measurement_is_refused_before_work(self):
        with Fixture() as f:
            with self.assertRaises(engine.Refusal):f.start(['A'])
    def test_close_rechecks_current_deliverables(self):
        with Fixture() as f:
            cid=f.start();f.h.check(cid,'M');(f.root/'src/b.c').write_text('modified')
            with self.assertRaises(engine.Refusal):f.close(cid)
    def test_interruption_never_promotes_candidate(self):
        with Fixture() as f:
            cid=f.start();f.h.check(cid,'M');f.h.interrupt(cid,'Explicit interruption')
            self.assertEqual(f.h.measurement_report()['counts']['verified'],0)
            self.assertFalse(f.h.cycle_boundary(cid)['passed'])
    def test_protected_verifier_change_is_refused(self):
        with Fixture() as f:
            cid=f.start();(f.root/'verifier.py').write_text("print('D=4745/4745')")
            with self.assertRaises(engine.Refusal):f.h.check(cid,'M')
    def test_frozen_audit_selection_and_exact_recount(self):
        with Fixture() as f:
            cid=f.start(['M','A']);f.h.check(cid,'M')
            a=f.h.measurement_audit_plan(cid);b=f.h.measurement_audit_plan(cid)
            self.assertEqual(a['id'],b['id']);self.assertEqual(a['units'],b['units'])
            self.assertEqual(len(a['units']),1)
            self.assertTrue(f.h.check(cid,'A')['passed']);f.close(cid)
            self.assertEqual(f.h.measurement_report()['counts']['verified'],2)
    def test_wrong_recount_or_weak_controls_hold_count(self):
        for fault in ('recount','controls','executed'):
            with self.subTest(fault=fault),Fixture() as f:
                cid=f.start(['M','A']);f.h.check(cid,'M');f.h.measurement_audit_plan(cid)
                if fault=='recount':f.audit['recount_ids']=['a']
                elif fault=='controls':f.audit['controls']['known_bad_rejected']=False
                else:f.audit['actually_executed']=False
                f.write('audit-candidate.json',f.audit)
                self.assertFalse(f.h.check(cid,'A')['passed'])
                self.assertEqual(f.h.measurement_report()['counts']['verified'],0)
                with self.assertRaises(engine.Refusal):f.close(cid)
    def test_audit_failure_forces_full_recovery_not_another_favorable_sample(self):
        with Fixture() as f:
            cid=f.start(['M','A']);f.h.check(cid,'M');f.h.measurement_audit_plan(cid)
            f.audit['controls']['known_bad_rejected']=False;f.write('audit-candidate.json',f.audit)
            f.h.check(cid,'A');f.h.interrupt(cid,'Audit failed; preserve evidence')
            f.audit_candidate();cid=f.start(['M','A']);f.h.check(cid,'M')
            plan=f.h.measurement_audit_plan(cid)
            self.assertEqual(set(plan['units']),{'a','b'})
            self.assertTrue(f.h.check(cid,'A')['passed']);f.close(cid)
            self.assertEqual(f.h.measurement_report()['counts']['verified'],2)
    def test_due_audit_cannot_be_skipped_by_new_cycle_plan(self):
        with Fixture() as f:
            for i in range(4):
                cid=f.start();f.h.check(cid,'M');f.close(cid)
            with self.assertRaises(engine.Refusal):f.start(['M'])
            cid=f.start(['M','A']);f.h.check(cid,'M')
            with self.assertRaises(engine.Refusal):f.close(cid)
    def test_metric_acceptance_needs_threshold_and_no_open_cycle(self):
        with Fixture() as f:
            cid=f.start();f.h.check(cid,'M')
            self.assertFalse(f.h.accept_mission()['accepted'])
            f.close(cid)
            # A is also a declared criterion; metric acceptance must expose its own exact threshold.
            self.assertTrue(f.h.measurement_report()['threshold_satisfied'])
    def test_missing_policy_preserves_old_behavior(self):
        with Fixture() as f:
            other=f.root/'old';other.mkdir();h=engine.Harness(other)
            m=copy.deepcopy(f.mission);m.pop('measurement_policy')
            m['criteria']=[{'id':'X','description':'old contract','argv':[sys.executable,'-c','pass'],'artifacts':[]}]
            h.init(m);self.assertFalse(h.measurement_report()['applicable'])

if __name__=='__main__':unittest.main()
