"""Neutral quantity contracts. No execution, grade ladder or semantic authentication."""
import hashlib
import importlib.util
import json
from pathlib import Path

_spec=importlib.util.spec_from_file_location('measurement_json_contract',Path(__file__).with_name('regression_contract.py'))
_json=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(_json)
loads=_json.loads
relative=_json.relative
checksum=_json.checksum

def need(condition,message):
    if not condition:raise ValueError(message)

def encoded(value):return json.dumps(value,sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode('utf-8')
def sha(value):return hashlib.sha256(encoded(value)).hexdigest()
def text(value):return isinstance(value,str) and bool(value.strip())

def reference(value):
    need(isinstance(value,dict) and set(value)=={'path','sha256'} and checksum(value['sha256']),'Expected a path/SHA-256 reference')
    relative(value['path']);return value

def universe(value):
    need(isinstance(value,dict) and set(value)=={'format','units','excluded'} and
         value['format']=='verimission-universe-v1','Use verimission-universe-v1')
    need(isinstance(value['units'],list) and value['units'],'Declare the full nonempty scoped inventory')
    units={};identities=set()
    for u in value['units']:
        need(isinstance(u,dict) and set(u)=={'id','identity','deliverable','depends_on'},'Expected exact neutral unit identity/deliverable/dependencies')
        need(text(u['id']) and u['id'] not in units and text(u['identity']) and u['identity'] not in identities,
             'Unit IDs and physical identities must be unique; aliases do not increase cardinality')
        relative(u['deliverable'])
        deps=u['depends_on']
        need(isinstance(deps,list) and all(text(d) for d in deps) and len(set(deps))==len(deps),'Declare unique dependencies')
        units[u['id']]=u;identities.add(u['identity'])
    need(all(set(u['depends_on'])<=set(units) for u in units.values()),'Dependency is outside the scoped inventory')
    need(isinstance(value['excluded'],list),'Exclusions need explicit reasons')
    excluded={}
    for row in value['excluded']:
        need(isinstance(row,dict) and set(row)=={'id','reason'} and row['id'] in units and
             row['id'] not in excluded and text(row['reason']),'Unique known exclusions with reasons required')
        excluded[row['id']]=row['reason']
    return {'units':units,'excluded':excluded,'live':set(units)-set(excluded)}

def closed_subset(candidates,registry):
    """Cycles are allowed when every member has proof; unknown/rejected dependencies remove dependents."""
    current=set(candidates)
    while True:
        after={u for u in current if set(registry['units'][u]['depends_on'])<=current}
        if after==current:return current
        current=after

def parse_report(value,registry,gates,run_id,context,universe_sha):
    need(isinstance(value,dict) and set(value)=={'format','run_id','context_sha256','universe_sha256',
         'complete','claimed_verified','units'} and value['format']=='verimission-measurement-v1','Use the exact neutral measurement report')
    need(value['run_id']==run_id and value['context_sha256']==context and value['universe_sha256']==universe_sha,
         'Old run, wrong context or wrong inventory')
    need(value['complete'] is True and isinstance(value['units'],list),'Incomplete measurements cannot qualify quantities')
    need(isinstance(gates,list) and gates and all(text(g) for g in gates) and len(gates)==len(set(gates)),'Unique required gates required')
    units={};eligible=set()
    for row in value['units']:
        need(isinstance(row,dict) and set(row)=={'id','identity','gates','artifacts'},'Expected exact per-unit gate evidence')
        uid=row['id'];need(text(uid) and uid in registry['live'] and uid not in units,'Missing, duplicate, unknown or excluded unit')
        original=registry['units'][uid]
        need(row['identity']==original['identity'],'Unit identity differs from its pinned inventory entry')
        need(isinstance(row['gates'],dict) and set(row['gates'])==set(gates) and
             all(s in ('pass','fail','unknown') for s in row['gates'].values()),'Missing/unknown gate; passes cannot compensate for it')
        refs=row['artifacts'];need(isinstance(refs,dict) and all(text(k) for k in refs),'Artifact roles must be named')
        for ref in refs.values():reference(ref)
        passed=all(s=='pass' for s in row['gates'].values())
        if passed:
            need('deliverable' in refs and refs['deliverable']['path']==original['deliverable'],
                 'A qualified unit needs its exact inventory-bound deliverable')
            eligible.add(uid)
        elif 'deliverable' in refs:need(refs['deliverable']['path']==original['deliverable'],'Wrong deliverable')
        units[uid]=row
    need(set(units)==registry['live'],'A complete report must include every live unit exactly once')
    eligible=closed_subset(eligible,registry)
    need(type(value['claimed_verified']) is int and value['claimed_verified']==len(eligible),
         'Claimed number differs from the cardinality of qualified dependency-closed units')
    return {'units':units,'eligible_ids':sorted(eligible),'declared_qualified_ids':sorted(
        u for u,r in units.items() if all(s=='pass' for s in r['gates'].values()))}

def parse_audit(value,selection,eligible,run_id,context):
    need(isinstance(value,dict) and set(value)=={'format','run_id','context_sha256','complete','plan_id',
         'recount_ids','units','controls'} and value['format']=='verimission-measurement-audit-v1','Expected neutral audit result')
    need(value['run_id']==run_id and value['context_sha256']==context and value['plan_id']==selection['id'] and
         value['complete'] is True,'Stale or incomplete audit')
    ids=value['recount_ids']
    need(isinstance(ids,list) and all(text(i) for i in ids) and len(set(ids))==len(ids) and set(ids)==set(eligible),
         'Recount must match exact complete eligible IDs, not only a number')
    controls=value['controls']
    need(isinstance(controls,dict) and set(controls)=={'healthy_passed','known_bad_rejected','artifacts'} and
         type(controls['healthy_passed']) is bool and type(controls['known_bad_rejected']) is bool,
         'Explicit healthy and known-bad controls are mandatory')
    need(isinstance(controls['artifacts'],dict) and controls['artifacts'],'Controls need physical evidence')
    refs=list(controls['artifacts'].values())
    for ref in refs:reference(ref)
    need(isinstance(value['units'],list),'Selected units must actually be reexecuted')
    rows={}
    for row in value['units']:
        need(isinstance(row,dict) and set(row)=={'id','status','executed','artifacts'} and
             text(row['id']) and row['id'] not in rows and row['status'] in ('pass','fail','unknown') and
             type(row['executed']) is bool and isinstance(row['artifacts'],dict) and row['artifacts'],
             'Audit requires unique units, explicit execution and physical proof')
        for ref in row['artifacts'].values():reference(ref);refs.append(ref)
        rows[row['id']]=row
    need(set(rows)==set(selection['units']),'Audit selection cannot be replaced, omitted or cherry-picked')
    passed=controls['healthy_passed'] and controls['known_bad_rejected'] and all(
        row['status']=='pass' and row['executed'] for row in rows.values())
    return {'passed':passed,'failed_units':sorted(u for u,r in rows.items() if r['status']!='pass' or not r['executed']),
            'artifacts':refs,'selected':len(rows),'recounted':len(ids)}
