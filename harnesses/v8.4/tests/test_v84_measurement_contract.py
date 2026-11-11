"""Quantities must be derived from stable units and exact neutral gates, never a headline."""
import importlib.util
from pathlib import Path
import unittest

def load():
    p=Path(__file__).resolve().parents[1]/'scripts/measurement_contract.py'
    s=importlib.util.spec_from_file_location('metric_contract_test',p)
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def inventory():
    return {'format':'verimission-universe-v1','units':[
        {'id':'a','identity':'physical:a','deliverable':'src/a.c','depends_on':[]},
        {'id':'b','identity':'physical:b','deliverable':'src/b.c','depends_on':['a']}], 'excluded':[]}

def report(m):
    return {'format':'verimission-measurement-v1','run_id':'run','context_sha256':'a'*64,
            'universe_sha256':'b'*64,'complete':True,'claimed_verified':2,'units':[
                {'id':u['id'],'identity':u['identity'],'gates':{'source':'pass','behavior':'pass'},
                 'artifacts':{'deliverable':{'path':u['deliverable'],'sha256':'c'*64}}}
                for u in inventory()['units']]}

class MeasurementContractTests(unittest.TestCase):
    def setUp(self):self.m=load()
    def parse(self,r,universe=None):
        return self.m.parse_report(r,self.m.universe(universe or inventory()),['source','behavior'],'run','a'*64,'b'*64)
    def test_exact_set_has_two_units(self):self.assertEqual(self.parse(report(self.m))['eligible_ids'],['a','b'])
    def test_audit_requires_exact_recount_selection_and_real_control_evidence(self):
        import copy
        selection={'id':'plan','units':['a']}
        proof={'path':'audit.json','sha256':'c'*64}
        valid={'format':'verimission-measurement-audit-v1','run_id':'run','context_sha256':'a'*64,
            'complete':True,'plan_id':'plan','recount_ids':['a','b'],
            'units':[{'id':'a','status':'pass','executed':True,'artifacts':{'execution':proof}}],
            'controls':{'healthy_passed':True,'known_bad_rejected':True,'artifacts':{'control':proof}}}
        parse=lambda v:self.m.parse_audit(v,selection,['a','b'],'run','a'*64)
        self.assertTrue(parse(valid)['passed'])
        for field,value in [('recount_ids',['a']),('units',[]),('plan_id','old')]:
            bad=copy.deepcopy(valid);bad[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):parse(bad)
        bad=copy.deepcopy(valid);bad['controls']['artifacts']={}
        with self.assertRaises(ValueError):parse(bad)
        for target,field in [('controls','known_bad_rejected'),('unit','executed')]:
            bad=copy.deepcopy(valid)
            (bad['controls'] if target=='controls' else bad['units'][0])[field]=False
            with self.subTest(field=field):self.assertFalse(parse(bad)['passed'])
    def test_claimed_headline_cannot_exceed_evidence(self):
        r=report(self.m);r['claimed_verified']=4745
        with self.assertRaises(ValueError):self.parse(r)
    def test_duplicate_units_cannot_inflate(self):
        r=report(self.m);r['units'].append(r['units'][0])
        with self.assertRaises(ValueError):self.parse(r)
    def test_aliases_of_same_identity_are_rejected(self):
        u=inventory();u['units'][1]['identity']='physical:a'
        with self.assertRaises(ValueError):self.m.universe(u)
    def test_partial_or_replayed_output_refused(self):
        for key,value in [('run_id','old'),('context_sha256','d'*64),('universe_sha256','e'*64),('complete',False)]:
            r=report(self.m);r[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):self.parse(r)
    def test_missing_unit_cannot_be_hidden(self):
        r=report(self.m);r['units'].pop();r['claimed_verified']=1
        with self.assertRaises(ValueError):self.parse(r)
    def test_missing_gate_cannot_be_compensated(self):
        r=report(self.m);del r['units'][0]['gates']['source']
        with self.assertRaises(ValueError):self.parse(r)
    def test_nonpass_and_dependents_not_counted(self):
        r=report(self.m);r['units'][0]['gates']['source']='unknown';r['claimed_verified']=0
        self.assertEqual(self.parse(r)['eligible_ids'],[])
    def test_wrong_deliverable_or_identity_refused(self):
        for field in ('identity','deliverable'):
            r=report(self.m)
            if field=='identity':r['units'][0]['identity']='physical:b'
            else:r['units'][0]['artifacts']['deliverable']['path']='src/b.c'
            with self.subTest(field=field),self.assertRaises(ValueError):self.parse(r)
    def test_exclusions_are_fixed_not_inferred_from_grade(self):
        u=inventory();u['excluded']=[{'id':'b','reason':'Explicit user-approved scope exclusion'}]
        r=report(self.m);r['units'].pop();r['claimed_verified']=1
        self.assertEqual(self.parse(r,u)['eligible_ids'],['a'])
    def test_unknown_dependency_refused(self):
        u=inventory();u['units'][0]['depends_on']=['missing']
        with self.assertRaises(ValueError):self.m.universe(u)
    def test_nonfinite_and_duplicate_json_keys_refused(self):
        for raw in (b'{"a":1,"a":2}',b'{"a":NaN}'):
            with self.subTest(raw=raw),self.assertRaises(ValueError):self.m.loads(raw)

if __name__=='__main__':unittest.main()
