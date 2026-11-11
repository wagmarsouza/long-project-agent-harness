"""Temporary general-project preservation pilots; no installation, publication or external service."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('control83_general_pilot',ROOT/'scripts/harness.py')
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


def run(kind):
    with tempfile.TemporaryDirectory(prefix='control83-'+kind+'-') as tmp:
        p=Path(tmp)
        if kind=='software':
            good='def add(a,b):\n return a+b\n'; bad='def add(a,b):\n return a-b\n'
            (p/'candidate.py').write_text(good)
            checks='import unittest\nimport candidate\nclass C(unittest.TestCase):\n def test_retained(self):\n  self.assertEqual(candidate.add(2,3),5)\n  self.assertEqual(candidate.add(7,1),8)\n'
        else:
            good=json.dumps({'sources':['S1','S2'],'unverified':[]}); bad=json.dumps({'sources':['S1'],'unverified':['S2']})
            (p/'candidate.py').write_text('# Non-code research fixture; see record.json\n')
            (p/'record.json').write_text(good)
            checks='import json,unittest\nfrom pathlib import Path\nclass C(unittest.TestCase):\n def test_retained(self):\n  r=json.loads(Path("record.json").read_text())\n  self.assertEqual(set(r["sources"]),{"S1","S2"})\n  self.assertEqual(r["unverified"],[])\n'
        (p/'checks.py').write_text(checks)
        baseline={'format':'verimission-baseline-v1','reference':{'kind':'specification','id':'synthetic-'+kind},
                  'protected_files':{'checks.py':hashlib.sha256((p/'checks.py').read_bytes()).hexdigest()},'context_files':{},
                  'obligations':[{'id':'RETAINED','criterion':'REG','case':'checks.C.test_retained','critical':True,
                                 'sources':['candidate.py'] if kind=='software' else ['record.json'], 'comparator':{'kind':'status'}}], 'debt':[]}
        (p/'baseline.json').write_text(json.dumps(baseline))
        policy={'schema':1,'baseline':{'path':'baseline.json','sha256':hashlib.sha256((p/'baseline.json').read_bytes()).hexdigest()},
                'input_patterns':['candidate.py','checks.py']+(['record.json'] if kind!='software' else []),
                'criteria':{'REG':{'output_pattern':'reports/{run}.json'}},'mode':'full','graph':{},'graph_complete':False,'environment':[]}
        mission={'objective':'Preserve a bounded '+kind+' fixture','mode':'light','in_scope':['temporary fixtures'],
                 'out_of_scope':['external services','domain tools','installation'],
                 'criteria':[{'id':'REG','description':'Retain the approved fixture obligation',
                              'argv':[sys.executable,'-B',str(ROOT/'scripts/result_runner.py'),'unittest','--start','.','--pattern','checks.py'],
                              'artifacts':['candidate.py','checks.py']+(['record.json'] if kind!='software' else [])}],
                 'budget':{'max_no_progress':10,'max_same_failures':10},'regression_policy':policy}
        h=m.Harness(p); h.init(mission)
        def cycle():
            review=h.review('retained')['review']
            cid=h.start({'topic':'retained','task':'replay','premise':'Retain accepted behavior','residual':'Read actual results',
                         'review_id':review['id'],'reviewed_claims':review['claims'],'criteria':['REG'],
                         'approach':{'method':'finite explicit replay','inputs':'local fixtures','environment':'temporary'},
                         'reverify_reason':'Revalidate current candidate'})['cycle']
            return cid,h.check(cid,'REG')
        first,record=cycle(); assert record['passed']; h.close(first,'verified','next bounded change')
        target=p/('candidate.py' if kind=='software' else 'record.json')
        target.write_text(bad)
        failed,record=cycle(); assert not record['passed']
        try: h.close(failed,'verified','must refuse')
        except m.Refusal as error: assert error.code=='REGRESSION_BLOCKED'
        else: raise AssertionError('Regression was accepted')
        h.interrupt(failed,'Repair known broken obligation')
        target.write_text(good)
        restored,record=cycle(); assert record['passed']; assert not h.close(restored,'verified','restored')['progress']
        assert h.accept_mission()['accepted']
        return {'domain':kind,'initial_pass':True,'broken_candidate_blocked':True,'repair_revalidated':True,
                'history_preserved':True,'new_discovery_claimed':False,'installed':False,'semantic_truth_verified':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--domain',choices=['software','research','all'],default='all')
    args=parser.parse_args()
    print(json.dumps([run(kind) for kind in (['software','research'] if args.domain=='all' else [args.domain])]))
