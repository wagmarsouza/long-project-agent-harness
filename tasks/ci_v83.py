"""Portable local/CI qualification with durable, source-bound per-step receipts. No deployment."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
import uuid

import yaml

ROOT=Path(__file__).resolve().parents[1]
GENERATION='8.3'
H=ROOT/'harnesses/v8.3'
S=ROOT/'skills/skill-harness-v8-3'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def atomic(path,value):
    temporary=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    temporary.write_text(json.dumps(value,ensure_ascii=True,indent=2)+'\n',encoding='utf-8')
    temporary.replace(path)


def output_identity(outputs):
    result={}
    for name in outputs:
        path=Path(name)
        if path.is_symlink() or not path.exists():raise ValueError('Required output missing or symbolic: '+str(path))
        paths=sorted(path.rglob('*')) if path.is_dir() else [path]
        entries={}
        for p in paths:
            if p.is_symlink() or not p.resolve().is_relative_to(path.resolve() if path.is_dir() else path.parent.resolve()):
                raise ValueError('Unsafe derived output: '+str(p))
            if p.is_file():entries[p.relative_to(path).as_posix() if path.is_dir() else p.name]=sha(p)
        if not entries:raise ValueError('Required output is empty: '+str(path))
        result[str(path)] = entries
    return result


def execute(name,argv,root,out,source,timeout,resume=False,cases=None,extra_env=None,outputs=None):
    outputs=outputs or []
    binding={'argv':argv,'source':source,'python':platform.python_version(),'executable':sys.executable,
             'os':platform.system(),'release':platform.release(),'machine':platform.machine(),'pyyaml':yaml.__version__,
             'libyaml':getattr(yaml,'__with_libyaml__',False),'timeout':timeout,'cwd':str(root),
             'cases':cases,'extra_env':extra_env or {},'outputs':outputs}
    key=hashlib.sha256(json.dumps(binding,sort_keys=True).encode()).hexdigest()
    receipt=out/(name+'.result.json');admission=out/(name+'.admitted.json');log=out/(name+'.log')
    if receipt.exists():
        row=json.loads(receipt.read_text(encoding='utf-8'))
        if not resume or row['binding_sha256']!=key or not log.is_file() or sha(log)!=row['log_sha256']:
            raise ValueError('Prior receipt is stale, altered or not explicitly resumed: '+name)
        if cases and (not Path(cases['path']).is_file() or sha(cases['path'])!=row.get('cases_sha256')):
            raise ValueError('Prior case evidence changed: '+name)
        if outputs and row.get('outputs')!=output_identity(outputs):
            raise ValueError('Prior output evidence changed: '+name)
        return row
    if admission.exists():raise ValueError('Interrupted/unknown step: inspect its evidence before an explicit new attempt: '+name)
    atomic(admission,{'phase':'admitted','binding_sha256':key,'command':argv})
    start=time.monotonic()
    with log.open('x',encoding='utf-8') as stream:
        try:
            result=subprocess.run(argv,cwd=root,stdout=stream,stderr=subprocess.STDOUT,timeout=timeout,
                env={**os.environ,'PYTHONUTF8':'1','PYTHONDONTWRITEBYTECODE':'1',**(extra_env or {})})
            code=result.returncode
        except subprocess.TimeoutExpired:code=None
    row={'name':name,'passed':code==0,'exit_code':code,'seconds':round(time.monotonic()-start,3),
         'binding_sha256':key,'log_sha256':sha(log),'source_sha256':source}
    if cases:
        try:
            spec=importlib.util.spec_from_file_location('ci_neutral_reader',H/'scripts/result_readers.py')
            reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)
            values=reader.neutral(Path(cases['path']).read_bytes(),cases['run_id'],cases['context_sha256'])
            row.update(tests_run=len(values),tests_passed=sum(x['status']=='pass' for x in values),
                       skipped=sum(x['status']=='skipped' for x in values),cases_sha256=sha(cases['path']))
            row['passed']=row['passed'] and len(values)>=cases.get('minimum',1) and all(x['status']=='pass' for x in values)
        except (OSError,ValueError) as error:
            row.update(passed=False,case_error=str(error))
    if outputs:
        try:row['outputs']=output_identity(outputs)
        except (OSError,ValueError) as error:row.update(passed=False,output_error=str(error))
    atomic(receipt,row)
    print(json.dumps({**{k:v for k,v in row.items() if k!='outputs'},
                      'output_files':sum(len(entries) for entries in row.get('outputs',{}).values())}),flush=True)
    return row


def resources():
    identities={}
    for folder in (H,S):
        manifest=json.loads((folder/'MANIFEST.json').read_text(encoding='utf-8'))
        actual={p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file() and
                '__pycache__' not in p.parts and p.name!='MANIFEST.json'}
        expected={r['path'] for r in manifest['files']}
        if actual!=expected:raise ValueError('Manifest file set differs: '+str(folder))
        for row in manifest['files']:
            p=folder/row['path']
            if p.is_symlink() or not p.resolve().is_relative_to(folder.resolve()):raise ValueError('Unsafe source resource')
            if p.stat().st_size!=row['bytes'] or sha(p)!=row['sha256']:raise ValueError('Manifest resource differs: '+row['path'])
            identities[p.relative_to(ROOT).as_posix()]=row['sha256']
        identities[(folder/'MANIFEST.json').relative_to(ROOT).as_posix()]=sha(folder/'MANIFEST.json')
    for directory in ('scripts','tests','references','examples'):
        h={p.relative_to(H/directory).as_posix():sha(p) for p in (H/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts}
        s={p.relative_to(S/directory).as_posix():sha(p) for p in (S/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts}
        # The skill additionally carries its consolidated text reference.
        if directory=='references':s.pop('harness_v'+GENERATION+'.txt',None)
        if h!=s:raise ValueError('Harness/skill resources diverge: '+directory)
    for p in (H/'templates').rglob('*'):
        if p.is_file() and p.read_bytes()!=(S/'assets/templates'/p.relative_to(H/'templates')).read_bytes():
            raise ValueError('Template parity failed')
    text=(S/'SKILL.md').read_text(encoding='utf-8')
    meta=yaml.safe_load(text.split('---',2)[1])
    if meta.get('name')!='skill-harness-v'+GENERATION.replace('.','-') or not isinstance(meta.get('description'),str) or not meta['description'].strip():
        raise ValueError('Skill metadata invalid')
    if (H/'CORE.md').read_text(encoding='utf-8') not in text:raise ValueError('Complete core missing from skill')
    pipeline=[ROOT/'tasks/ci_v83.py',ROOT/('tasks/package_v'+GENERATION.replace('.','')+'.py'),ROOT/'requirements-ci.txt',ROOT/'.github/workflows/ci.yml']
    pipeline+=sorted((ROOT/'tasks/tests').rglob('*.py'))
    if not pipeline[4:]:raise ValueError('CI self-tests missing')
    for path in pipeline:
        if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(ROOT.resolve()):
            raise ValueError('Required pipeline source missing or unsafe: '+str(path))
        identities[path.relative_to(ROOT).as_posix()]=sha(path)
    return hashlib.sha256(json.dumps(identities,sort_keys=True).encode()).hexdigest()


def main(argv=None):
    global H,S,GENERATION
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--resume',action='store_true')
    parser.add_argument('--timeout',type=int,default=1800)
    parser.add_argument('--generation',choices=['8.3','8.4'],default='8.3',help='Explicit generation; legacy default remains 8.3')
    args=parser.parse_args(argv)
    try:
        GENERATION=args.generation
        H=ROOT/('harnesses/v'+GENERATION)
        S=ROOT/('skills/skill-harness-v'+GENERATION.replace('.','-'))
        if not 30<=args.timeout<=3600:raise ValueError('Timeout must be 30..3600 seconds per step')
        out=args.output.resolve()
        if any(out.is_relative_to(p.resolve()) for p in (H,S,ROOT/'.git')):raise ValueError('Choose a separate derived-output directory')
        source=resources()
        out.mkdir(parents=True,exist_ok=args.resume)
        atomic(out/'environment.json',{'os':platform.system(),'release':platform.release(),'python':platform.python_version(),
            'pyyaml':yaml.__version__,'source_sha256':source,'publication':False})
        rows=[]
        for name,start,runner,minimum in [
            ('unit-harness',(H/'tests').relative_to(ROOT).as_posix(),H/'scripts/result_runner.py',292 if GENERATION=='8.4' else 259),
            ('unit-skill',(S/'tests').relative_to(ROOT).as_posix(),S/'scripts/result_runner.py',292 if GENERATION=='8.4' else 259),
            ('unit-ci','tasks/tests',H/'scripts/result_runner.py',10)]:
            case={'path':str(out/(name+'.cases.json')),'run_id':name+'-'+source[:20],
                  'context_sha256':source,'minimum':minimum}
            env={'VERIMISSION_REPORT':case['path'],'VERIMISSION_RUN_ID':case['run_id'],'VERIMISSION_CONTEXT_SHA256':source}
            rows.append(execute(name,[sys.executable,'-B',str(runner),'unittest','--start',start],ROOT,out,source,
                                args.timeout,args.resume,case,env))
        commands=[('assurance',[sys.executable,'-B',str(H/'scripts/harness.py'),'assurance','--suite','all','--seed','7',
                               '--output',str(out/'assurance.json')]),
                  ('generic-pilot',[sys.executable,'-B',str(H/'examples/run_regression_pilot.py')]),
                  ('periodic-pilot',[sys.executable,'-B',str(H/'examples/run_periodic_pilot.py')]),
                  ('package',[sys.executable,'-B',str(ROOT/('tasks/package_v'+GENERATION.replace('.','')+'.py')),'--output',str(out/'packages')])]
        for name,command in commands:
            outputs={'assurance':[str(out/'assurance.json')],'package':[str(out/'packages')]}.get(name)
            rows.append(execute(name,command,ROOT,out,source,args.timeout,args.resume,outputs=outputs))
        final_source=resources()
        unchanged=final_source==source
        report={'format':'verimission-ci-v1','passed':unchanged and all(r['passed'] for r in rows),
                'source_unchanged':unchanged,'jobs':rows,'source_sha256':source,
                'final_source_sha256':final_source,'installed':False,'published':False}
        atomic(out/'qualification.json',report)
        return 0 if report['passed'] else 3
    except (OSError,ValueError,KeyError) as error:
        print(json.dumps({'passed':False,'error':str(error)}));return 2


if __name__=='__main__':sys.exit(main())
