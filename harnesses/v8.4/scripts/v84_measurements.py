"""Optional neutral measurement/audit gates composed with the existing execution hook."""
import copy
from datetime import datetime, timezone
import hashlib
import importlib.util
import os
from pathlib import Path
import random
import secrets
import uuid

_s=importlib.util.spec_from_file_location('native_measurement_contract',Path(__file__).with_name('measurement_contract.py'))
c=importlib.util.module_from_spec(_s);_s.loader.exec_module(c)

def extend(Base,require,digest,now,file_digest,nonempty,Refusal):
    class Harness84(Base):
        def _measurement_registry(self,p):
            try:
                path=self.project_file(p['universe']['path']);raw=path.read_bytes()
                c.need(hashlib.sha256(raw).hexdigest()==p['universe']['sha256'],'Pinned universe changed')
                return c.universe(c.loads(raw))
            except (ValueError,OSError,KeyError,Refusal) as e:raise Refusal('MEASUREMENT_SOURCE',str(e)) from None

        def _measurement_protected(self,p):
            files={}
            for name,expected in p['protected_files'].items():
                actual=file_digest(self.project_file(name))
                require(actual==expected,'MEASUREMENT_SOURCE','Protected verifier/context changed')
                files[name]=actual
            return files

        def normalize_mission(self,mission):
            value=super().normalize_mission(mission);p=value.get('measurement_policy')
            if p is None:return value
            try:
                fields={'schema','universe','criterion','output_pattern','required_gates','protected_files',
                        'input_patterns','acceptance_minimum','audit'}
                c.need(isinstance(p,dict) and fields<=set(p)<=fields|{'environment'},'Use the measurement policy template')
                c.need(type(p['schema']) is int and p['schema']==1,'Unsupported measurement policy')
                c.reference(p['universe']);r=self._measurement_registry(p)
                ids={row['id'] for row in value['criteria']};a=p['audit']
                c.need(isinstance(a,dict) and set(a)=={'criterion','output_pattern','every_cycles','sample_size'},'Declare exact audit policy')
                c.need(p['criterion'] in ids and a['criterion'] in ids and p['criterion']!=a['criterion'],'Distinct measurement/audit acceptance criteria required')
                c.need(type(a['every_cycles']) is int and a['every_cycles']>0 and type(a['sample_size']) is int and
                       a['sample_size']>0,'Positive audit cadence/sample size required')
                for pattern in (p['output_pattern'],a['output_pattern']):
                    c.relative(pattern,pattern=True)
                    c.need(pattern.count('{run}')==1 and not any(x in pattern.replace('{run}','') for x in '{}*?[]'),
                           'Fresh output pattern needs exactly one run placeholder')
                c.need(p['output_pattern']!=a['output_pattern'],'Measurement and audit outputs must be separate')
                gates=p['required_gates']
                c.need(isinstance(gates,list) and gates and all(c.text(g) for g in gates) and len(set(gates))==len(gates),'Unique required gate names required')
                c.need(type(p['acceptance_minimum']) is int and 0<=p['acceptance_minimum']<=len(r['live']),'Acceptance minimum exceeds fixed live universe')
                c.need(isinstance(p['protected_files'],dict) and p['protected_files'],'Pin verifier/context resources')
                for name,sha in p['protected_files'].items():c.reference({'path':name,'sha256':sha})
                self._measurement_protected(p)
                c.need(isinstance(p['input_patterns'],list) and p['input_patterns'] and len(set(p['input_patterns']))==len(p['input_patterns']),'Unique input patterns required')
                for pattern in p['input_patterns']:c.relative(pattern,pattern=True)
                c.need(isinstance(p.get('environment',[]),list) and all(c.text(k) and k.replace('_','a').isalnum() for k in p.get('environment',[])),'Declare relevant environment names')
            except (ValueError,OSError,KeyError,TypeError) as e:raise Refusal('MEASUREMENT_POLICY',str(e)) from None
            return value

        def regression_init(self,state):
            super().regression_init(state)
            old=state.pop('measurement_guard',None)
            if old:state.setdefault('measurement_history',[]).append(old)
            if state['mission'].get('measurement_policy'):
                state['measurement_guard']={'mission_hash':state['mission_hash'],'anchor':len(state['cycles']),
                                            'hold':False,'plans':[]}

        def _measurement_guard(self,state):
            require(digest(state['mission'])==state['mission_hash'],'MISSION_CHANGED','Mission changed outside revision')
            guard=state.get('measurement_guard',{})
            require(guard.get('mission_hash')==state['mission_hash'],'MEASUREMENT_EPOCH','Measurement policy was not adopted in this epoch')
            return guard

        def _measurement_inputs(self,p):
            files={}
            for pattern in p['input_patterns']:
                for path in self.root.glob(pattern):
                    if path.is_dir():continue
                    require(not any(q.is_symlink() for q in (path,*path.parents) if q.is_relative_to(self.root)),
                            'MEASUREMENT_SOURCE','Symbolic input refused')
                    relative=path.relative_to(self.root).as_posix();c.relative(relative)
                    files[relative]=file_digest(self.project_file(relative))
            return files

        def _measurement_context(self,state,cid):
            self._measurement_guard(state);p=state['mission']['measurement_policy']
            registry=self._measurement_registry(p);protected=self._measurement_protected(p)
            argv=self.criterion(state,cid)['argv'];exe=self._reg_executable(argv[0]);arguments={}
            for i,arg in enumerate(argv[1:],1):
                candidate=Path(arg) if Path(arg).is_absolute() else self.root/arg
                if candidate.is_file():arguments[str(i)]={'path':str(candidate.resolve()),'sha256':file_digest(candidate)}
            context={'mission_hash':state['mission_hash'],'policy_sha256':c.sha(p),'universe_sha256':p['universe']['sha256'],
                     'protected':protected,'argv_sha256':digest(argv),'argument_files':arguments,
                     'executable_sha256':file_digest(Path(exe)),
                     'engine_files':{q.name:file_digest(q) for q in sorted(Path(__file__).parent.glob('*.py'))},
                     'environment':{k:hashlib.sha256(os.environ.get(k,'').encode()).hexdigest() for k in p.get('environment',[])}}
            return registry,context,exe

        def _measurement_bind(self,ref):
            c.reference(ref);path=self.project_file(ref['path'])
            require(file_digest(path)==ref['sha256'],'MEASUREMENT_STALE','Unit artifact changed or disappeared')
            return path

        def _measurement_read(self,state,record):
            p=state['mission']['measurement_policy'];e=record['measurement']
            registry,context,_=self._measurement_context(state,p['criterion'])
            require(record['passed'] and e['kind']=='measurement' and context==e['context'],
                    'MEASUREMENT_STALE','No current successful measurement proof')
            path=self._measurement_bind(e['report']);value=c.loads(path.read_bytes())
            parsed=c.parse_report(value,registry,p['required_gates'],e['run_id'],e['context_sha256'],p['universe']['sha256'])
            require(c.sha(parsed['eligible_ids'])==e['eligible_sha256'],'MEASUREMENT_STALE','Sealed unit set differs from its evidence')
            fresh=set()
            for uid in parsed['eligible_ids']:
                try:
                    for ref in parsed['units'][uid]['artifacts'].values():self._measurement_bind(ref)
                    fresh.add(uid)
                except (Refusal,OSError,ValueError):pass
            parsed['fresh_ids']=sorted(c.closed_subset(fresh,registry))
            parsed['registry']=registry
            return parsed

        def _measurement_candidate(self,state,cycle):
            cid=state['mission']['measurement_policy']['criterion']
            records=[r for r in cycle['checks'] if r['criterion']==cid]
            require(records and records[-1]['passed'],'MEASUREMENT_REQUIRED','Run the measurement check first')
            parsed=self._measurement_read(state,records[-1])
            require(parsed['fresh_ids']==parsed['eligible_ids'],'MEASUREMENT_STALE','Revalidate changed unit evidence before closing/auditing')
            return records[-1],parsed

        def _measurement_due(self,state,cycle_id):
            p=state['mission']['measurement_policy'];g=self._measurement_guard(state)
            closed={x['id'] for x in state['cycles'] if x['status']=='verified' and x['mission_hash']==state['mission_hash']}
            anchor=max([g['anchor']]+[x['cycle'] for x in g['plans'] if x['status']=='passed' and x['cycle'] in closed])
            return g['hold'] or cycle_id-anchor>=p['audit']['every_cycles']

        def regression_start(self,state,plan):
            if state['mission'].get('measurement_policy'):
                p=state['mission']['measurement_policy']
                needed={p['criterion']}
                if self._measurement_due(state,len(state['cycles'])+1):needed.add(p['audit']['criterion'])
                require(needed<=set(plan['criteria']),'MEASUREMENT_PLAN','Plan omits mandatory measurement/audit checks')
            return super().regression_start(state,plan)

        def regression_prepare(self,state,cycle,criterion):
            prepared=super().regression_prepare(state,cycle,criterion)
            p=state['mission'].get('measurement_policy')
            if not p or criterion['id'] not in (p['criterion'],p['audit']['criterion']):return prepared
            registry,context,exe=self._measurement_context(state,criterion['id']);run=uuid.uuid4().hex
            kind='measurement' if criterion['id']==p['criterion'] else 'audit'
            setting=p if kind=='measurement' else p['audit']
            relative=setting['output_pattern'].replace('{run}',run);path=self.project_file(relative,exists=False)
            require(not path.exists(),'MEASUREMENT_OUTPUT','Never overwrite an evidence result')
            path.parent.mkdir(parents=True,exist_ok=True)
            meta={'kind':kind,'run_id':run,'context':context,'context_sha256':c.sha(context),'path':relative,
                  'inputs':self._measurement_inputs(p),'regression_active':prepared is not None}
            env={'VERIMISSION_MEASUREMENT_KIND':kind,'VERIMISSION_MEASUREMENT_RUN_ID':run,
                 'VERIMISSION_MEASUREMENT_CONTEXT_SHA256':meta['context_sha256'],
                 'VERIMISSION_MEASUREMENT_REPORT':str(path)}
            if kind=='audit':
                _,parsed=self._measurement_candidate(state,cycle)
                candidates=[x for x in self._measurement_guard(state)['plans'] if x['cycle']==cycle['id'] and x['status']=='pending']
                require(len(candidates)==1,'MEASUREMENT_AUDIT_PLAN','Freeze one current audit selection before execution')
                plan=candidates[0];self._measurement_bind(plan['selection'])
                require(plan['fingerprint']==self._measurement_fingerprint(state,cycle,parsed),
                        'MEASUREMENT_AUDIT_STALE','Audit candidate changed after sample selection')
                meta['plan_id']=plan['id'];env['VERIMISSION_AUDIT_SELECTION']=str(self.project_file(plan['selection']['path']))
            if prepared is None:prepared={'argv':[exe,*criterion['argv'][1:]],'env':dict(os.environ)}
            prepared['measurement']=meta;prepared['env'].update(env)
            return prepared

        def regression_finish(self,state,cycle,record,prepared):
            meta=(prepared or {}).get('measurement')
            super().regression_finish(state,cycle,record,prepared if not meta or meta['regression_active'] else None)
            if not meta:return
            p=state['mission']['measurement_policy'];e={k:copy.deepcopy(meta[k]) for k in ('kind','run_id','context','context_sha256')}
            e['report']=None;e['passed']=False;record['measurement']=e
            try:
                require(self._measurement_inputs(p)==meta['inputs'],'MEASUREMENT_STALE','Declared inputs changed during check')
                registry,context,_=self._measurement_context(state,record['criterion'])
                require(context==meta['context'],'MEASUREMENT_STALE','Verifier/context changed during check')
                path=self.project_file(meta['path']);raw=path.read_bytes()
                e['report']={'path':meta['path'],'sha256':hashlib.sha256(raw).hexdigest()}
                value=c.loads(raw)
                if meta['kind']=='measurement':
                    parsed=c.parse_report(value,registry,p['required_gates'],meta['run_id'],meta['context_sha256'],p['universe']['sha256'])
                    for row in parsed['units'].values():
                        for ref in row['artifacts'].values():self._measurement_bind(ref)
                        if row['id'] in parsed['eligible_ids']:
                            ref=row['artifacts']['deliverable']
                            require(meta['inputs'].get(ref['path'])==ref['sha256'],'MEASUREMENT_INPUT','Deliverable must be in pre-execution input set')
                    e.update(verified_count=len(parsed['eligible_ids']),eligible_sha256=c.sha(parsed['eligible_ids']),
                             inputs_sha256=c.sha(meta['inputs']),passed=record['passed'])
                else:
                    _,parsed=self._measurement_candidate(state,cycle)
                    plan=next(x for x in self._measurement_guard(state)['plans'] if x['id']==meta['plan_id'])
                    result=c.parse_audit(value,plan,parsed['eligible_ids'],meta['run_id'],meta['context_sha256'])
                    for ref in result['artifacts']:self._measurement_bind(ref)
                    e.update(plan_id=plan['id'],audit=result,passed=record['passed'] and result['passed'])
            except (ValueError,OSError,Refusal,KeyError,TypeError) as error:e['error']=str(error)
            record['passed']=record['passed'] and e['passed']
            if meta['kind']=='audit':
                guard=self._measurement_guard(state)
                plan=next(x for x in guard['plans'] if x['id']==meta['plan_id'])
                plan.update(status='passed' if record['passed'] else 'failed',check_id=record['id'])
                if not record['passed']:guard['hold']=True
            self.event(state,'measurement-check',record['id'],{'kind':meta['kind'],'passed':record['passed']})

        def _measurement_fingerprint(self,state,cycle,parsed):
            record,_=self._measurement_candidate(state,cycle) if parsed is None else (next(
                r for r in reversed(cycle['checks']) if r['criterion']==state['mission']['measurement_policy']['criterion']),parsed)
            return c.sha({'context':record['measurement']['context_sha256'],'inputs':record['measurement']['inputs_sha256'],
                          'units':parsed['eligible_ids'],'artifacts':{u:parsed['units'][u]['artifacts'] for u in parsed['eligible_ids']}})

        def measurement_audit_plan(self,cycle_id,full=False):
            require(type(full) is bool,'MEASUREMENT_AUDIT_PLAN','Full selection flag must be boolean')
            with self.state(write=True) as state:
                p=state['mission'].get('measurement_policy');require(p is not None,'MEASUREMENT_POLICY','No measurement policy')
                cycle=self.cycle(state,cycle_id);require(cycle['status']=='active','CYCLE','Audit plan needs an active cycle')
                require(p['audit']['criterion'] in cycle['criteria'],'MEASUREMENT_PLAN','Select audit before execution')
                record,parsed=self._measurement_candidate(state,cycle);guard=self._measurement_guard(state)
                fingerprint=self._measurement_fingerprint(state,cycle,parsed)
                prior=[x for x in guard['plans'] if x['status']=='pending']
                if prior and not full:
                    require(prior[-1]['fingerprint']==fingerprint,'MEASUREMENT_AUDIT_STALE','Frozen selection changed; explicit full audit required')
                    prior[-1]['cycle']=cycle_id
                    return copy.deepcopy(prior[-1])
                if prior:
                    prior[-1]['status']='superseded_by_full_audit'
                seed=prior[-1]['seed'] if prior else secrets.randbits(256)
                eligible=parsed['eligible_ids'];all_units=full or guard['hold']
                selected=eligible[:] if all_units else sorted(random.Random(seed).sample(eligible,min(p['audit']['sample_size'],len(eligible))))
                plan={'id':uuid.uuid4().hex,'cycle':cycle_id,'seed':seed,'units':selected,'eligible_ids':eligible,
                      'fingerprint':fingerprint,'full':len(selected)==len(eligible),'status':'pending'}
                relative=p['audit']['output_pattern'].replace('{run}','selection-'+plan['id'])
                path=self.project_file(relative,exists=False);path.parent.mkdir(parents=True,exist_ok=True)
                with path.open('xb') as stream:stream.write(c.encoded(plan))
                plan['selection']={'path':relative,'sha256':file_digest(path)}
                guard['plans'].append(plan);self.event(state,'measurement-audit-plan',plan['id'],{'units':selected,'full':plan['full']})
                return copy.deepcopy(plan)

        def current_check(self,state,cycle,cid):
            record=super().current_check(state,cycle,cid)
            p=state['mission'].get('measurement_policy')
            if p and cid==p['criterion']:
                parsed=self._measurement_read(state,record)
                require(parsed['fresh_ids']==parsed['eligible_ids'],'MEASUREMENT_STALE','Current unit proof is stale')
            elif p and cid==p['audit']['criterion']:
                e=record.get('measurement',{});require(e.get('passed'),'MEASUREMENT_AUDIT','No passing current audit')
                self._measurement_bind(e['report']);_,context,_=self._measurement_context(state,cid)
                require(context==e['context'],'MEASUREMENT_AUDIT_STALE','Audit context changed')
                plan=next(x for x in self._measurement_guard(state)['plans'] if x['id']==e['plan_id'])
                _,parsed=self._measurement_candidate(state,cycle)
                require(plan['fingerprint']==self._measurement_fingerprint(state,cycle,parsed),'MEASUREMENT_AUDIT_STALE','Audit candidate changed')
                for ref in e['audit']['artifacts']:self._measurement_bind(ref)
            return record

        def regression_close(self,state,cycle,outcome):
            p=state['mission'].get('measurement_policy')
            if p and outcome=='verified':
                self._measurement_candidate(state,cycle)
                if self._measurement_due(state,cycle['id']):self.current_check(state,cycle,p['audit']['criterion'])
            return super().regression_close(state,cycle,outcome)

        def regression_closed(self,state,cycle):
            super().regression_closed(state,cycle)
            if state['mission'].get('measurement_policy') and cycle['status']=='verified':
                guard=self._measurement_guard(state)
                if any(x['cycle']==cycle['id'] and x['status']=='passed' and x['full'] for x in guard['plans']):guard['hold']=False

        def _measurement_view(self,state):
            p=state['mission'].get('measurement_policy')
            if not p:return {'applicable':False,'format':'verimission-measurement-view-v1','runs_commands':False}
            guard=self._measurement_guard(state);registry=self._measurement_registry(p)
            latest=None
            for cycle in reversed(state['cycles']):
                if cycle['status']=='verified' and cycle['mission_hash']==state['mission_hash']:
                    records=[r for r in cycle['checks'] if r['criterion']==p['criterion']]
                    if records:latest=(cycle,records[-1]);break
            eligible=set();declared=set();stale=set();error=None
            if latest:
                cycle,record=latest
                try:
                    parsed=self._measurement_read(state,record);declared=set(parsed['eligible_ids'])
                    eligible=set(parsed['fresh_ids']);stale=declared-eligible
                    if guard['hold']:stale|=eligible;eligible=set()
                except (Refusal,OSError,ValueError,KeyError) as e:stale=set(registry['live']);error=str(e)
            states=[]
            for uid,original in sorted(registry['units'].items()):
                status='excluded' if uid in registry['excluded'] else 'verified' if uid in eligible else 'stale' if uid in stale else 'pending'
                states.append({'id':uid,'identity':original['identity'],'deliverable':original['deliverable'],'status':status,
                               'reason':registry['excluded'].get(uid)})
            counts={label:sum(u['status']==label for u in states) for label in ('verified','pending','stale','excluded')}
            active=[x for x in state['cycles'] if x['status']=='active']
            value={'format':'verimission-measurement-view-v1','applicable':True,'units':states,'counts':counts,
                'denominator':len(registry['live']),'inventory_total':len(registry['units']),'declared_qualified':len(declared),
                'universe':p['universe'],'policy_sha256':c.sha(p),'source':{'mission_hash':state['mission_hash'],
                    'revision':state['revision'],'cycle':latest[0]['id'] if latest else None,
                    'check_id':latest[1]['id'] if latest else None},'audit_hold':guard['hold'],
                'audit_due':self._measurement_due(state,len(state['cycles'])+(0 if active else 1)),
                'active_cycle':active[-1]['id'] if active else None,'coverage_applicable':bool(registry['live']),
                'threshold_satisfied':bool(registry['live']) and len(eligible)>=p['acceptance_minimum'],
                'claim_ceiling':{'verified_count':len(eligible),'unit_ids':sorted(eligible),'denominator':len(registry['live'])},
                'runs_commands':False,'semantic_truth_authenticated':False,'error':error}
            return value

        def measurement_report(self):
            with self.state() as state:return self._measurement_view(state)

        def cycle_boundary(self,cycle_id):
            with self.state() as state:
                cycle=self.cycle(state,cycle_id)
                passed=cycle['status']=='verified' and cycle['mission_hash']==state['mission_hash']
                if passed:
                    try:
                        for cid in cycle['criteria']:self.current_check(state,cycle,cid)
                    except (Refusal,OSError,ValueError):passed=False
                return {'passed':passed,'cycle':cycle_id,'status':cycle['status'],'implicit_close':False,
                        'measurement':self._measurement_view(state)}

        def accept_mission(self,output=None):
            value=super().accept_mission()
            with self.state() as state:
                if state['mission'].get('measurement_policy'):
                    view=self._measurement_view(state);value['measurement']=view
                    if not view['threshold_satisfied'] or view['active_cycle'] is not None or view['audit_hold']:
                        value['accepted']=False;value['blockers'].append('measurement_not_qualified')
            if output:self.write_view(output,value)
            return value

        def capabilities(self):
            value=super().capabilities();value['v84']={'neutral_measurements':True,'sealed_quantities':True,
                'exact_recount_and_frozen_audits':True,'implicit_scheduling':False,'semantic_authentication':False}
            return value
    return Harness84
