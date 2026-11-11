"""Finite synthetic long-history qualification. Never operates on a caller's project."""
import argparse
import copy
from contextlib import contextmanager
import json
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import time
import tracemalloc

import yaml
from assurance_fixture import Fixture, SCRIPTS
from assurance import receipt_destination, source_manifest


@contextmanager
def _backend(fixture, mode):
    namespace=fixture.h.store._load_unlocked.__globals__
    previous=(namespace['_SAFE_LOADER'],namespace['_SAFE_DUMPER'])
    if mode=='python':namespace['_SAFE_LOADER'],namespace['_SAFE_DUMPER']=yaml.SafeLoader,yaml.SafeDumper
    try:yield {'loader':namespace['_SAFE_LOADER'].__name__,'dumper':namespace['_SAFE_DUMPER'].__name__}
    finally:namespace['_SAFE_LOADER'],namespace['_SAFE_DUMPER']=previous


def _limits(native, sizes, samples, backend, budget):
    if (type(native) is not int or not 0<=native<=500 or type(samples) is not int or not 1<=samples<=5 or
            backend not in ('auto','python') or type(budget) is not int or not 1<=budget<=3600 or
            not isinstance(sizes,list) or len(sizes)>5 or len(set(sizes))!=len(sizes) or
            any(type(n) is not int or not 1<=n<=20000 for n in sizes) or (not native and not sizes)):
        raise ValueError('Use native cycles 0..500, unique history sizes 1..20000 (max 5), samples 1..5 and budget 1..3600')


def run(native_cycles=30,history_sizes=None,samples=3,backend='auto',budget_seconds=600,measure_memory=False):
    sizes=[100,1000,5000] if history_sizes is None else history_sizes
    _limits(native_cycles,sizes,samples,backend,budget_seconds)
    began=time.monotonic();deadline=began+budget_seconds
    def remaining():
        value=deadline-time.monotonic()
        if value<=0:raise TimeoutError('Finite benchmark budget exhausted; incomplete observations are not qualified')
        return value
    report={'format':'verimission-history-benchmark-v1','passed':False,'complete':False,
            'configuration':{'native_cycles':native_cycles,'history_sizes':sizes,'samples':samples,
                             'backend':backend,'budget_seconds':budget_seconds,'memory':measure_memory},
            'environment':{'os':platform.system(),'kernel':platform.release(),'python':platform.python_version(),'pyyaml':yaml.__version__},
            'native':{'started':0,'checks_passed':0,'verified_closures':0,'progress_cycles':0,'fresh_process_resumes':0},
            'histories':[],'mission_acceptance':False,'real_project_used':False}
    report['engine_sources_sha256']=source_manifest()
    try:
        if native_cycles:
            with Fixture() as f,_backend(f,backend) as actual:
                elapsed=[]
                for i in range(native_cycles):
                    remaining();start=time.perf_counter()
                    f.candidate();cid=f.start();report['native']['started']+=1
                    check=f.h.check(cid,'R')
                    if not check['passed']:raise AssertionError('Actual native acceptance command failed')
                    report['native']['checks_passed']+=1
                    closed=f.h.close(cid,'verified','Explicit bounded benchmark revalidation')
                    report['native']['verified_closures']+=1
                    with f.h.state() as state:
                        report['native']['progress_cycles']+=int(state['cycles'][-1]['progress'])
                    elapsed.append(time.perf_counter()-start)
                    if (i+1)%10==0 or i+1==native_cycles:
                        process=subprocess.run([sys.executable,'-B',str(SCRIPTS/'harness.py'),'--project',str(f.root),'resume'],
                            capture_output=True,text=True,timeout=min(30,remaining()))
                        if process.returncode!=0 or not json.loads(process.stdout)['ok']:
                            raise AssertionError('Fresh-process resume failed')
                        report['native']['fresh_process_resumes']+=1
                if not f.h.validate()['passed'] or report['native']['progress_cycles']!=1:
                    raise AssertionError('History validation or non-inflated progress invariant failed')
                report['native'].update(backend=actual,yaml_bytes=f.h.db.stat().st_size,
                    cycle_seconds=elapsed,cycle_median_seconds=statistics.median(elapsed),
                    cycle_max_seconds=max(elapsed),history_count=len(state['cycles']))
        for n in sizes:
            remaining()
            with Fixture() as f,_backend(f,backend) as actual:
                f.start();f.h.interrupt(1,'Synthetic seeded-history prototype; no executed verification')
                original=f.h.store._load_unlocked()
                prototype=original['state']['cycles'][0]
                document=copy.deepcopy(original)
                document['state']['cycles']=[{**copy.deepcopy(prototype),'id':i+1,
                    'next_step':'Synthetic seeded vector, not executed work'} for i in range(n)]
                document['state']['benchmark_fixture']='seeded blocked cycles, not executed proofs'
                document=f.h.store._document(document['state'],document['audit'])
                def reset():f.h.store._write_unlocked(document)
                def read():
                    with f.h.store.state() as state:
                        if len(state['cycles'])!=n or any(c['status']!='blocked' for c in state['cycles']):
                            raise AssertionError('Seeded fixture changed or gained verification')
                reset();raw_bytes=f.h.db.stat().st_size
                loads=[];writes=[]
                for sample in range(samples):
                    remaining();reset()
                    start=time.perf_counter();read();loads.append(time.perf_counter()-start)
                    start=time.perf_counter()
                    with f.h.store.state(write=True) as state:state['benchmark_sample']=sample
                    writes.append(time.perf_counter()-start)
                    if not f.h.store.validate():raise AssertionError('Native store validation failed')
                peak=None
                if measure_memory:
                    remaining();reset();tracemalloc.start()
                    try:read();_,peak=tracemalloc.get_traced_memory()
                    finally:tracemalloc.stop()
                report['histories'].append({'seeded_cycle_vectors':n,'native_verified_cycles':0,'samples':samples,
                    'backend':actual,'yaml_bytes':raw_bytes,'read_samples_seconds':loads,'write_samples_seconds':writes,
                    'read_median_seconds':statistics.median(loads),'write_median_seconds':statistics.median(writes),
                    'separate_python_allocation_peak_bytes':peak,'memory_is_process_rss':False})
        remaining()
        report.update(complete=True,passed=True)
    except Exception as error:
        report.update(error_type=type(error).__name__,error=str(error))
    report['source_unchanged']=source_manifest()==report['engine_sources_sha256']
    report['passed']=report['passed'] and report['source_unchanged']
    elapsed=time.monotonic()-began
    if elapsed>budget_seconds:
        report.update(complete=False,passed=False,error_type='TimeoutError',
                      error='Finite benchmark budget exhausted; incomplete observations are not qualified')
    report['seconds']=round(elapsed,3)
    return report


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native-cycles',type=int,default=30)
    parser.add_argument('--history-sizes',type=int,nargs='*',default=[100,1000,5000])
    parser.add_argument('--samples',type=int,default=3)
    parser.add_argument('--backend',choices=('auto','python'),default='auto')
    parser.add_argument('--budget-seconds',type=int,default=600)
    parser.add_argument('--memory',action='store_true')
    parser.add_argument('--output',type=Path)
    args=parser.parse_args(argv)
    try:
        target=receipt_destination(args.output)
        result=run(args.native_cycles,args.history_sizes,args.samples,args.backend,args.budget_seconds,args.memory)
        if target:
            with target.open('x',encoding='utf-8') as stream:json.dump(result,stream,ensure_ascii=True,indent=2)
            print(json.dumps({'passed':result['passed'],'complete':result['complete'],'receipt':str(target)}))
        else:print(json.dumps(result,ensure_ascii=True,indent=2))
        return 0 if result['passed'] else 3
    except (OSError,ValueError) as error:
        print(json.dumps({'passed':False,'error':str(error)}));return 2


if __name__=='__main__':sys.exit(main())
