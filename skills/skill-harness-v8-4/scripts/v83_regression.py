"""Native opt-in preservation gates. One canonical store, no implicit dispatch or authority."""
import copy
import hashlib
import importlib.util
import os
from pathlib import Path
import re
import shutil
import subprocess
import uuid


def sibling(name):
    spec = importlib.util.spec_from_file_location('v83_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


c = sibling('regression_contract')
readers = sibling('result_readers')


def extend(Base, require, digest, now, file_digest, nonempty, Refusal):
    class Harness83(Base):
        def _reg_baseline(self, policy):
            try:
                path = self.project_file(c.relative(policy['baseline']['path']))
                raw = path.read_bytes()
                c.need(hashlib.sha256(raw).hexdigest() == policy['baseline']['sha256'], 'Baseline file changed')
                return c.loads(raw)
            except (OSError, ValueError, KeyError, TypeError, Refusal):
                raise Refusal('REGRESSION_SOURCE', 'Baseline is missing, unsafe, changed or malformed; no implicit rebaseline') from None

        def normalize_mission(self, mission):
            value = super().normalize_mission(mission)
            p = value.get('regression_policy')
            if p is None: return value
            try:
                c.need(isinstance(p, dict) and set(p) == {'schema','baseline','input_patterns','criteria','mode','graph','graph_complete','environment'},
                       'Use the exact regression policy template')
                c.need(type(p['schema']) is int and p['schema'] == 1 and p['mode'] in ('full','impact'), 'Unsupported preservation policy')
                c.need(isinstance(p['baseline'],dict) and set(p['baseline']) == {'path','sha256'} and c.checksum(p['baseline']['sha256']), 'Pin a baseline path and SHA-256')
                c.relative(p['baseline']['path'])
                c.need(isinstance(p['input_patterns'],list) and p['input_patterns'] and len(set(p['input_patterns'])) == len(p['input_patterns']), 'Declare unique input patterns')
                for pattern in p['input_patterns']: c.relative(pattern, pattern=True)
                ids = {x['id'] for x in value['criteria']}
                c.need(isinstance(p['criteria'],dict) and p['criteria'] and set(p['criteria']) <= ids, 'Preservation criteria must be declared acceptance commands')
                for setting in p['criteria'].values():
                    c.need(isinstance(setting,dict) and set(setting) == {'output_pattern'}, 'Declare only a fresh neutral output pattern')
                    pattern = setting['output_pattern']; c.relative(pattern, pattern=True)
                    c.need(pattern.count('{run}') == 1 and '{' not in pattern.replace('{run}','') and '}' not in pattern.replace('{run}','') and
                           not any(x in pattern for x in '*?[]'), 'Output pattern requires exactly one run UUID placeholder')
                    self.project_file(pattern.replace('{run}',uuid.uuid4().hex), exists=False)
                c.need(type(p['graph_complete']) is bool and isinstance(p['graph'],dict), 'Dependency completeness is an explicit declaration')
                for source, targets in p['graph'].items():
                    c.relative(source)
                    c.need(isinstance(targets,list) and len(set(targets)) == len(targets), 'Graph targets must be unique paths')
                    for target in targets: c.relative(target)
                c.need(isinstance(p['environment'],list) and len(set(p['environment'])) == len(p['environment']) and
                       all(isinstance(k,str) and re.fullmatch('[A-Za-z_][A-Za-z0-9_]*',k) for k in p['environment']), 'Declare relevant environment variable names only')
                b = c.baseline(self._reg_baseline(p), set(p['criteria']))
                c.need({r['criterion'] for r in b['obligations']} == set(p['criteria']), 'Every protected criterion needs obligations')
                if b['reference']['kind'] == 'commit':
                    git = subprocess.run(['git','cat-file','-t',b['reference']['id']],cwd=self.root,capture_output=True,text=True)
                    c.need(git.returncode == 0 and git.stdout.strip() == 'commit', 'Referenced commit is not present locally')
                self._reg_sources(p, b)
            except (ValueError, KeyError, TypeError, OSError) as error:
                raise Refusal('REGRESSION_POLICY', str(error)) from None
            return value

        def _reg_sources(self, policy, baseline):
            try:
                files = {}
                for pattern in policy['input_patterns']:
                    matched = list(self.root.glob(pattern))
                    c.need(matched, 'An input pattern has no matches')
                    for path in matched:
                        # Globs may traverse symlink directories; reject every symlink component.
                        rel = path.relative_to(self.root).as_posix()
                        c.relative(rel)
                        c.need(not any(parent.is_symlink() for parent in (path,*path.parents) if parent.is_relative_to(self.root)), 'Symlink input refused')
                        if path.is_dir(): continue
                        physical = self.project_file(rel)
                        files[rel] = file_digest(physical)
                c.need(files, 'Input universe is empty')
                for row in baseline['obligations']:
                    c.need(set(row['sources']) <= set(files), 'An obligation dependency is outside the input universe')
                for path, expected in baseline['protected_files'].items():
                    c.need(path in files and files[path] == expected, 'Oracle/test/comparator resource changed')
                context_files = {}
                for path, expected in baseline['context_files'].items():
                    actual = file_digest(self.project_file(c.relative(path)))
                    c.need(actual == expected, 'Toolchain/context resource changed; explicit review is required')
                    context_files[path] = actual
                return files, context_files
            except (ValueError, OSError, Refusal):
                raise Refusal('REGRESSION_SOURCE', 'Preservation input, protected oracle or context is missing, changed or unsafe') from None

        def _reg_context(self, state, cid):
            require(digest(state['mission']) == state['mission_hash'],'MISSION_CHANGED','Acceptance contract changed outside revision')
            p = state['mission']['regression_policy']
            b = c.baseline(self._reg_baseline(p),set(p['criteria']))
            files, context_files = self._reg_sources(p,b)
            command = self.criterion(state,cid)['argv']
            executable = self._reg_executable(command[0])
            context = {'mission_hash':state['mission_hash'], 'policy_sha256':digest(p), 'baseline_sha256':p['baseline']['sha256'],
                       'argv_sha256':digest(command), 'executable_sha256':file_digest(Path(executable)),
                       'engine_files':{path.name:file_digest(path) for path in sorted(Path(__file__).parent.glob('*.py'))},
                       'context_files':context_files, 'environment':{key: {'present':key in os.environ,
                       'sha256':hashlib.sha256(os.environ.get(key,'').encode()).hexdigest()} for key in p['environment']}}
            return b, files, context

        def _reg_executable(self, value):
            if Path(value).is_absolute(): resolved = Path(value)
            elif '/' in value or '\\' in value: resolved = self.root / value
            else:
                found = shutil.which(value)
                require(found is not None,'REGRESSION_SOURCE','Acceptance executable is unavailable')
                resolved = Path(found)
            require(resolved.is_file(),'REGRESSION_SOURCE','Acceptance executable is unavailable')
            return str(resolved.resolve())

        def regression_init(self, state):
            old = state.pop('regression_guard',None)
            if old: state.setdefault('regression_history',[]).append(old)
            p = state['mission'].get('regression_policy')
            if p:
                baseline = self._reg_baseline(p)
                state['regression_guard'] = {'mission_hash':state['mission_hash'],'baseline':copy.deepcopy(baseline),
                                             'baseline_sha256':p['baseline']['sha256'],'last_validated':None}
                self.event(state,'regression-baseline-adopted',state['mission_hash'], {'baseline_sha256':p['baseline']['sha256']})

        def on_mission_revision(self,state):
            super().on_mission_revision(state)
            self.regression_init(state)

        def baseline_preview(self, mission):
            normalized = self.normalize_mission(mission)
            require(normalized.get('regression_policy') is not None,'REGRESSION_POLICY','Proposed mission has no preservation policy')
            with self.state() as state:
                previous = state['mission'].get('regression_policy')
                return {'adopted':False,'current_mission_hash':state['mission_hash'], 'proposed_policy':normalized['regression_policy'],
                        'policy_changed':previous != normalized['regression_policy'],
                        'next':'Adoption/change requires the existing explicitly human-authorized mission revision; preview grants no approval'}

        def regression_prepare(self,state,cycle,criterion):
            p = state['mission'].get('regression_policy')
            if not p or criterion['id'] not in p['criteria']: return None
            require(state.get('regression_guard',{}).get('mission_hash') == state['mission_hash'],'REGRESSION_SOURCE','Preservation epoch not adopted')
            baseline, files, context = self._reg_context(state,criterion['id'])
            run_id = uuid.uuid4().hex
            relative = p['criteria'][criterion['id']]['output_pattern'].replace('{run}',run_id)
            path = self.project_file(relative,exists=False)
            require(not path.exists() and relative not in files and relative != p['baseline']['path'], 'REGRESSION_OUTPUT','Fresh result output must not replace an input')
            path.parent.mkdir(parents=True,exist_ok=True)
            env = {**os.environ,'VERIMISSION_RUN_ID':run_id,'VERIMISSION_CONTEXT_SHA256':c.sha(context),
                   'VERIMISSION_REPORT':str(path),'VERIMISSION_TIMEOUT':str(state['mission']['budget']['max_check_seconds'])}
            argv = list(criterion['argv']); argv[0] = self._reg_executable(argv[0])
            return {'baseline':baseline,'inputs':files,'context':context,'run_id':run_id,'path':relative,'env':env,'argv':argv}

        def regression_finish(self,state,cycle,record,prepared):
            if prepared is None: return
            evidence = {'run_id':prepared['run_id'],'inputs':prepared['inputs'],'context':prepared['context'],
                        'context_sha256':c.sha(prepared['context']),'report':None,'case_results':[]}
            try:
                _, files, context = self._reg_context(state,record['criterion'])
                c.need(files == prepared['inputs'] and context == prepared['context'],'Inputs changed during check')
                path = self.project_file(prepared['path'])
                raw = path.read_bytes()
                evidence['report'] = {'path':prepared['path'],'sha256':hashlib.sha256(raw).hexdigest()}
                rows = readers.neutral(raw,prepared['run_id'],evidence['context_sha256'])
                assessment = c.compare(prepared['baseline'],rows,record['criterion'])
                evidence['case_results'] = rows
                if not record['passed']: assessment.update(passed=False,status='execution_failed')
                # Repeating identical inputs after a failed execution does not hide instability.
                if any(r.get('regression',{}).get('inputs') == files and r.get('regression',{}).get('context') == context and
                       (not r['passed'] or not r.get('regression',{}).get('assessment',{}).get('passed'))
                       for prior in state['cycles'] if prior['mission_hash'] == state['mission_hash']
                       for r in prior['checks'] if r['id'] != record['id'] and r['criterion'] == record['criterion']):
                    assessment.update(passed=False,status='unstable_same_input')
                evidence['assessment'] = assessment
            except (ValueError, OSError, Refusal) as error:
                evidence['assessment'] = {'passed':False,'status':'incomplete','reason':str(error)}
            record['regression'] = evidence
            record['passed'] = record['passed'] and evidence['assessment']['passed']
            self.event(state,'regression-check',record['id'],{'criterion':record['criterion'], 'passed':record['passed'],
                       'status':evidence['assessment']['status']})
            self._reg_invalidate(state,cycle,record)

        def _reg_invalidate(self,state,current,record):
            affected_cycles = set()
            for prior in state['cycles']:
                if prior['status']!='verified' or prior['mission_hash']!=state['mission_hash']: continue
                invalid = []
                for cid in prior['criteria']:
                    try: self.current_check(state,prior,cid)
                    except (Refusal,OSError,ValueError): invalid.append(cid)
                if invalid:
                    prior.setdefault('status_history',[]).append({'at':now(),'from':'verified','to':'needs_review',
                        'reason':'Declared preservation proof became stale','criteria':invalid})
                    prior.update(status='needs_review',invalidated_by_regression=record['id'])
                    affected_cycles.add(prior['id'])
            affected_claims = {key for key,claim in state['claims'].items() if claim['cycle'] in affected_cycles}
            while True:
                expanded = affected_claims | {key for key,claim in state['claims'].items() if set(claim['depends_on']) & affected_claims}
                if expanded==affected_claims: break
                affected_claims=expanded
            for identifier in affected_claims:
                claim=state['claims'][identifier]
                if claim['status']=='verified':
                    claim.update(status='needs_review',invalidated_by_regression=record['id'])
            if affected_cycles or affected_claims:
                self.event(state,'regression-proof-invalidated',current['id'],
                           {'cycles':sorted(affected_cycles),'claims':sorted(affected_claims)})

        def _reg_current(self,state,cycle,cid):
            # Refer to the real original execution instead of manufacturing a new executed check.
            ref = cycle.get('regression_reuse',{}).get(cid)
            source = self.cycle(state,ref['cycle']) if ref else cycle
            visited=set()
            while cid in source.get('regression_reuse',{}):
                require(source['id'] not in visited,'REGRESSION_EVIDENCE','Cyclic proof reuse refused')
                visited.add(source['id'])
                source=self.cycle(state,source['regression_reuse'][cid]['cycle'])
            require(not source.get('invalidated_by_task_reopen'),'REGRESSION_EVIDENCE','Task-reopened proof requires explicit fresh review')
            record = super().current_check(state,source,cid)
            e = record.get('regression')
            require(e and e['assessment']['passed'],'REGRESSION_EVIDENCE','No complete preserved-case execution')
            b, files, context = self._reg_context(state,cid)
            require(context == e['context'],'REGRESSION_STALE','Execution context changed')
            p = state['mission']['regression_policy']
            changed = {path for path in set(files)|set(e['inputs']) if files.get(path) != e['inputs'].get(path)}
            if changed:
                deps = {path for row in b['obligations'] if row['criterion']==cid for path in row['sources']}
                reusable = (p['mode']=='impact' and p['graph_complete'] and set(p['graph'])==set(files) and
                            all(set(v)<=set(files) for v in p['graph'].values()) and set(files)==set(e['inputs']) and
                            changed <= set(p['graph']) and not (c.affected(p['graph'],changed)&deps))
                require(reusable,'REGRESSION_STALE','Protected source/dependency changed; repeat the check')
            require(e['report'] and file_digest(self.project_file(e['report']['path'])) == e['report']['sha256'],
                    'REGRESSION_STALE','Executed report changed or disappeared')
            require(not any(r['at']>record['at'] and not r['passed'] and r.get('regression',{}).get('inputs')==files and
                            r.get('regression',{}).get('context')==context for later in state['cycles']
                            if later['mission_hash']==state['mission_hash'] for r in later['checks'] if r['criterion']==cid),
                    'REGRESSION_INSTABILITY','A later failure exists for identical declared inputs/context')
            return record

        def current_check(self,state,cycle,cid):
            if cid in state['mission'].get('regression_policy',{}).get('criteria',{}):
                return self._reg_current(state,cycle,cid)
            return super().current_check(state,cycle,cid)

        def _reg_plan(self,state):
            p = state['mission'].get('regression_policy')
            if not p: return {'applicable':False,'required_criteria':[],'reused':{},'runs_commands':False}
            b = self._reg_baseline(p); self._reg_sources(p,b)
            needed, reused = [], {}
            for cid in sorted(p['criteria']):
                critical = any(r['critical'] for r in b['obligations'] if r['criterion']==cid)
                if p['mode']=='impact' and p['graph_complete'] and not critical:
                    for cycle in reversed(state['cycles']):
                        if cycle['status']!='verified' or cycle['mission_hash']!=state['mission_hash']: continue
                        try:
                            self._reg_current(state,cycle,cid)
                            reused[cid] = {'cycle':cycle['id']}; break
                        except (Refusal,OSError): continue
                if cid not in reused: needed.append(cid)
            return {'applicable':True,'required_criteria':needed,'reused':reused,'runs_commands':False,
                    'dependency_completeness_declared':p['graph_complete'],'semantic_truth_verified':False}

        def regression_plan(self):
            with self.state() as state: return self._reg_plan(state)

        def regression_start(self,state,plan):
            assessment = self._reg_plan(state)
            if assessment['applicable']:
                previously={cid for cycle in state['cycles'] if cycle['mission_hash']==state['mission_hash'] and
                            (cycle['status']=='verified' or cycle.get('invalidated_by_regression')) for cid in cycle['criteria']}
                require(not set(plan['criteria'])<=previously or nonempty(plan.get('reverify_reason')),'G1_REWORK',
                        'Revalidation of previously accepted obligations needs an explicit reason')
            require(set(assessment['required_criteria']) <= set(plan['criteria']),'REGRESSION_PLAN',
                    'Plan omits protected criteria; inspect regression-plan and select the required checks')
            return {cid:ref for cid,ref in assessment['reused'].items() if cid not in plan['criteria']}

        def _reg_assess(self,state,cycle):
            p = state['mission'].get('regression_policy')
            if not p: return {'applicable':False,'passed':True,'rows':[]}
            rows, errors, checks = [], [], {}
            initial = {}
            for cid in sorted(p['criteria']):
                try: initial[cid] = self._reg_context(state,cid)[1:]
                except (Refusal,OSError,ValueError): initial[cid] = None
            for cid in sorted(p['criteria']):
                try:
                    record = self._reg_current(state,cycle,cid)
                    rows.extend(record['regression']['assessment']['rows'])
                    checks[cid] = {'check':record['id'],'reused':cid in cycle.get('regression_reuse',{})}
                except (Refusal,OSError,ValueError) as error:
                    errors.append({'criterion':cid,'code':getattr(error,'code','REGRESSION_SOURCE'),'detail':str(error)})
                    # Keep the failed-case diagnosis visible; stale passes do not count as verified.
                    source = self.cycle(state,cycle.get('regression_reuse',{}).get(cid,{}).get('cycle',cycle['id']))
                    records = [r for r in source['checks'] if r['criterion']==cid]
                    if records:
                        diagnostics = copy.deepcopy(records[-1].get('regression',{}).get('assessment',{}).get('rows',[]))
                        for row in diagnostics:
                            if row['status']=='pass': row['status']='inconclusive'
                        rows.extend(diagnostics)
            for cid, before in initial.items():
                try:
                    require(before is not None and self._reg_context(state,cid)[1:] == before,
                            'REGRESSION_ASSESSMENT_DRIFT','Declared inputs/context changed during preservation assessment')
                except (Refusal,OSError,ValueError) as error:
                    errors.append({'criterion':cid,'code':getattr(error,'code','REGRESSION_SOURCE'),'detail':str(error)})
                    for row in rows:
                        if row['criterion']==cid and row['status']=='pass': row['status']='inconclusive'
            b = state.get('regression_guard',{}).get('baseline',{})
            total = len(b.get('obligations',[])); critical = [r for r in rows if r['critical']]
            return {'applicable':True,'passed':not errors and total>0 and len(rows)==total and all(r['status']=='pass' for r in rows),
                    'rows':rows,'errors':errors,'checks':checks,'coverage':c.coverage(sum(r['status']=='pass' for r in rows),total),
                    'critical':c.coverage(sum(r['status']=='pass' for r in critical),sum(r['critical'] for r in b.get('obligations',[]))),
                    'semantic_truth_verified':False,'authoritative':False}

        def regression_report(self,cycle_id=None):
            with self.state() as state:
                if not state['cycles']:
                    return {'applicable':bool(state['mission'].get('regression_policy')),'passed':False,'status':'not_run'}
                cycle = self.cycle(state,cycle_id) if cycle_id is not None else state['cycles'][-1]
                return self._reg_assess(state,cycle)

        def regression_close(self,state,cycle,outcome):
            if not state['mission'].get('regression_policy'): return {}
            assessment = self._reg_assess(state,cycle)
            cycle['regression_assessment'] = assessment
            self.event(state,'regression-assessed',cycle['id'],{'passed':assessment['passed'],'errors':assessment['errors']})
            if outcome=='verified' and not assessment['passed']:
                return {'blocked':True,'code':'REGRESSION_BLOCKED','detail':'Protected capabilities are missing, changed, failing or incomparable; inspect regression-report'}
            return {}

        def regression_closed(self,state,cycle):
            if cycle['status']=='verified' and cycle.get('regression_assessment',{}).get('passed'):
                prior_criteria={cid for prior in state['cycles'] if prior['id']<cycle['id'] and prior['mission_hash']==state['mission_hash']
                    and (prior['status']=='verified' or prior.get('invalidated_by_regression')) for cid in prior['criteria']}
                new_fact=any(claim.get('cycle')==cycle['id'] and claim['status']=='verified' and claim['created']>=cycle['started']
                             for claim in state['claims'].values())
                cycle['progress']=bool(set(cycle['criteria'])-prior_criteria or new_fact)
                state['regression_guard']['last_validated'] = {'cycle':cycle['id'],'at':now(),
                                                               'assessment_sha256':digest(cycle['regression_assessment'])}

        def finish_periodic_close(self,state,cycle,boundary):
            super().finish_periodic_close(state,cycle,boundary)
            if boundary and cycle.get('regression_assessment'):
                assessment=cycle['regression_assessment']
                state['consolidations'][-1]['regression']={'cycle':cycle['id'],'passed':assessment['passed'],
                    'assessment_sha256':digest(assessment),'coverage':assessment['coverage']}

        def resume(self):
            value = super().resume()
            with self.state() as state: enabled = bool(state['mission'].get('regression_policy'))
            if enabled: value['regression'] = self.regression_report()
            return value

        def matrix(self,state):
            value = super().matrix(state)
            if state['mission'].get('regression_policy'):
                value['regression'] = self._reg_assess(state,state['cycles'][-1]) if state['cycles'] else {'passed':False,'status':'not_run'}
            return value

        def verified_dependencies(self,state,ids):
            super().verified_dependencies(state,ids)
            if not state['mission'].get('regression_policy'): return
            seen, pending = set(), list(ids)
            while pending:
                identifier = pending.pop()
                if identifier in seen: continue
                seen.add(identifier)
                claim = state['claims'][identifier]
                super().verified_dependencies(state,[identifier])
                self.current_check(state,self.cycle(state,claim['cycle']),claim['criterion'])
                pending.extend(claim['depends_on'])

        def validate(self):
            value = super().validate()
            with self.state() as state:
                if state['mission'].get('regression_policy'):
                    try: self._reg_plan(state)
                    except (Refusal,OSError,ValueError) as error:
                        value['issues'].append({'kind':getattr(error,'code','REGRESSION_SOURCE')})
                    for cycle in state['cycles']:
                        if cycle['status']=='verified' and cycle['mission_hash']==state['mission_hash']:
                            if not self._reg_assess(state,cycle)['passed']:
                                value['issues'].append({'kind':'REGRESSION_NOT_PRESERVED','cycle':cycle['id']})
            value['passed'] = not value['issues']
            return value

        def capabilities(self):
            value = super().capabilities()
            value['v83'] = {'native_preservation_gates':True,'opt_in_policy':True,'case_level_comparison':True,
                            'structured_results':True,'impact_scope':'declared dependencies only',
                            'automatic_baseline_approval':False,'operator_authentication':False}
            return value

        def accept_mission(self,output=None):
            with self.state() as state:
                value = super().accept_mission()
                if state['mission'].get('regression_policy'):
                    value['regression'] = self._reg_assess(state,state['cycles'][-1]) if state['cycles'] else {'passed':False,'status':'not_run'}
                    if not value['regression']['passed']:
                        value['accepted'] = False; value['blockers'].append('regression_not_preserved')
            if output: self.write_view(output,value)
            return value

    return Harness83
