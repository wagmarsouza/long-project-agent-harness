"""Harness 7.8: portable local lifecycle, evidence and recovery. Python 3.11+."""
from __future__ import annotations

import argparse
from contextlib import closing, contextmanager
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

try:
    from yaml_store import StoreError, YAMLStore
except ModuleNotFoundError:
    import importlib.util
    _store_spec = importlib.util.spec_from_file_location('verimission_yaml_store_v78', Path(__file__).with_name('yaml_store.py'))
    _store_module = importlib.util.module_from_spec(_store_spec)
    _store_spec.loader.exec_module(_store_module)
    StoreError, YAMLStore = _store_module.StoreError, _store_module.YAMLStore

VERSION = '7.8'


class Refusal(Exception):
    def __init__(self, code, detail):
        self.code, self.detail = code, detail
        super().__init__(detail)


def require(condition, code, detail):
    if not condition:
        raise Refusal(code, detail)


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def file_digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


class Harness:
    def __init__(self, project):
        self.root = Path(project).resolve(strict=True)
        require(self.root.is_dir(), 'PROJECT', 'Project must be a directory')
        self.db = self.root / '.harness' / 'state.yaml'
        self.legacy_db = self.root / '.harness' / 'state.sqlite'
        require(not self.db.parent.is_symlink() and not self.db.is_symlink(), 'PATH', 'Store cannot be a symlink')
        require(self.db.parent.resolve().is_relative_to(self.root), 'PATH', 'Store cannot resolve outside the project')
        self.store = YAMLStore(self.db, now)

    def project_file(self, relative, exists=True):
        require(nonempty(relative), 'PATH', 'A project-relative path is required')
        rel = Path(relative)
        require(not rel.is_absolute() and '..' not in rel.parts, 'PATH', 'Use a path inside the project')
        path = (self.root / rel).resolve(strict=exists)
        require(path.is_relative_to(self.root), 'PATH', 'Path leaves the project')
        require(not path.is_relative_to(self.db.parent), 'PATH', 'Store files are not deliverable evidence')
        if exists:
            require(path.is_file(), 'PATH', 'Evidence must be a file')
        return path

    @contextmanager
    def state(self, write=False):
        try:
            with self.store.state(write=write) as state:
                yield state
        except StoreError as error:
            raise Refusal(error.code, error.detail) from error

    def normalize_mission(self, mission):
        require(isinstance(mission, dict), 'MISSION', 'Mission must be an object')
        require(nonempty(mission.get('objective')), 'MISSION', 'Objective required')
        require(mission.get('mode') in ('light', 'strict'), 'MISSION', 'Choose light or strict')
        for key in ('in_scope', 'out_of_scope'):
            require(isinstance(mission.get(key), list), 'MISSION', f'{key} must be a list')
        criteria = mission.get('criteria')
        require(isinstance(criteria, list) and criteria, 'MISSION', 'At least one acceptance criterion is required')
        ids = set()
        for criterion in criteria:
            require(isinstance(criterion, dict), 'MISSION', 'Criterion must be an object')
            cid = criterion.get('id')
            require(nonempty(cid) and cid not in ids, 'MISSION', 'Unique criterion IDs required')
            ids.add(cid)
            require(nonempty(criterion.get('description')), 'MISSION', 'Criterion description required')
            argv = criterion.get('argv')
            require(isinstance(argv, list) and argv and all(nonempty(v) for v in argv), 'MISSION', 'Each criterion needs an explicit argv test')
            require(isinstance(criterion.get('artifacts', []), list), 'MISSION', 'Artifacts must be a list of project-relative paths')
            for artifact in criterion.get('artifacts', []):
                self.project_file(artifact, exists=False)
        defaults = {'max_cycles': 20, 'max_cycle_seconds': 1800, 'max_check_seconds': 120,
                    'max_no_progress': 3, 'max_same_failures': 2, 'consolidate_every': 10}
        require(isinstance(mission.get('budget', {}), dict), 'BUDGET', 'Budget must be an object')
        budget = {**defaults, **mission.get('budget', {})}
        require(set(budget) <= set(defaults) | {'max_reported_usd'}, 'BUDGET', 'Unknown budget field')
        require(all(type(value) is int and value > 0 for key, value in budget.items() if key != 'max_reported_usd'), 'BUDGET', 'Budgets must be positive integers')
        if 'max_reported_usd' in budget:
            require(type(budget['max_reported_usd']) in (int, float) and math.isfinite(budget['max_reported_usd']) and budget['max_reported_usd'] > 0, 'BUDGET', 'Finite positive reported cost budget required')
        return json.loads(json.dumps({**mission, 'budget': budget}, ensure_ascii=False))

    def init(self, mission):
        require(not self.db.exists(), 'EXISTS', 'Store already exists; init never resets history')
        require(not self.legacy_db.exists(), 'MIGRATION_REQUIRED', 'Legacy state.sqlite found; run migrate-sqlite instead of init')
        mission = self.normalize_mission(mission)
        state = {'schema': 1, 'version': VERSION, 'created': now(), 'revision': 0,
                 'mission': mission, 'mission_hash': digest(mission), 'cycles': [],
                 'claims': {}, 'reviews': {}, 'stepbacks': [], 'consolidations': []}
        try:
            self.store.create(state)
        except StoreError as error:
            raise Refusal(error.code, error.detail) from error
        return {'initialized': True, 'mode': mission['mode'], 'mission_hash': state['mission_hash'], 'store': '.harness/state.yaml'}

    def migrate_sqlite(self):
        require(not self.db.exists(), 'EXISTS', 'YAML store already exists; migration never overwrites it')
        require(self.legacy_db.exists(), 'MIGRATION', 'No legacy .harness/state.sqlite was found')
        try:
            migration = self.store.migrate_sqlite(self.legacy_db)
        except StoreError as error:
            raise Refusal(error.code, error.detail) from error
        return {'migrated': True, 'canonical_store': '.harness/state.yaml',
                'legacy_store_preserved': '.harness/state.sqlite', 'migration': migration}

    def _revision_preview(self, state, proposal):
        require(isinstance(proposal, dict), 'REVISION', 'Revision proposal must be an object')
        require(set(proposal) == {'expected_mission_hash', 'expected_revision', 'reason', 'authorization', 'mission'},
                'REVISION', 'Use the exact revision template; approval flags are not accepted')
        authorization = proposal['authorization']
        require(isinstance(authorization, dict) and set(authorization) == {'source', 'reference'} and
                authorization['source'] == 'user' and nonempty(authorization['reference']),
                'USER_AUTHORIZATION', 'An explicit user request or approval reference is required; automation is forbidden')
        require(nonempty(proposal['reason']), 'REVISION', 'Explain the user-authorized change')
        require(digest(state['mission']) == state['mission_hash'], 'MISSION_CHANGED', 'Current contract has been altered outside the workflow')
        require(type(proposal['expected_revision']) is int and proposal['expected_revision'] == state['revision'] and
                proposal['expected_mission_hash'] == state['mission_hash'], 'REVISION_STALE', 'Contract/state changed; prepare and approve a fresh proposal')
        require(not any(c['status'] == 'active' for c in state['cycles']), 'OVERLAP', 'Explicitly close or interrupt the active cycle before a mission revision')
        new_mission = self.normalize_mission(proposal['mission'])
        require(digest(new_mission) != state['mission_hash'], 'NO_CHANGE', 'The normalized mission is unchanged')
        bound_request = {**proposal, 'mission': new_mission}
        request_hash = digest(bound_request)
        changed = [key for key in sorted(set(state['mission']) | set(new_mission)) if state['mission'].get(key) != new_mission.get(key)]
        return {'before': state['mission'], 'after': new_mission, 'changed_fields': changed,
                'expected_revision': state['revision'], 'before_hash': state['mission_hash'],
                'after_hash': digest(new_mission), 'reason': proposal['reason'], 'authorization': authorization,
                'request_sha256': request_hash, 'confirmation': 'REVISAR ' + request_hash[:12],
                'warning': 'Previous verified conclusions will need review; budgets and history are not reset. New argv commands must be reviewed before confirming.'}

    def preview_mission(self, proposal):
        with self.state() as state:
            return self._revision_preview(state, proposal)

    def revise_mission(self, proposal):
        preview = self.preview_mission(proposal)
        require(sys.stdin.isatty() and sys.stdout.isatty(), 'INTERACTIVE_REQUIRED',
                'Mission revision requires a real human at an interactive terminal; pipes and unattended calls are refused')
        automated = lambda value: value.strip().casefold() not in ('', '0', 'false', 'no')
        require(not any(automated(os.environ.get(key, '')) for key in ('CI', 'HARNESS_AUTOMATION')),
                'AUTOMATION_FORBIDDEN', 'Mission revision cannot run in automation')
        print(json.dumps(preview, ensure_ascii=True, indent=2))
        try:
            confirmation = input('User: review the exact proposal and type ' + preview['confirmation'] + ' to apply; anything else cancels: ')
        except (EOFError, KeyboardInterrupt):
            raise Refusal('CONFIRMATION', 'Revision cancelled; no mission change was applied')
        require(confirmation == preview['confirmation'], 'CONFIRMATION', 'Exact interactive confirmation required; revision cancelled')
        with self.state(write=True) as state:
            current = self._revision_preview(state, proposal)
            require(current['request_sha256'] == preview['request_sha256'], 'REVISION_STALE', 'Proposal changed during confirmation')
            folder = self.db.parent / 'mission-backups'
            require(not folder.is_symlink() and folder.resolve().is_relative_to(self.db.parent.resolve()), 'PATH', 'Backup folder must stay inside the store')
            folder.mkdir(exist_ok=True)
            backup = folder / (str(uuid.uuid4()) + '.yaml')
            # The YAML store lock held by state(write=True) excludes other readers
            # and writers; copy the committed pre-revision document before mutation.
            try:
                self.store.copy_current_unlocked(backup)
            except StoreError as error:
                raise Refusal(error.code, error.detail) from error
            revisions = state.setdefault('mission_revisions', [])
            revision_id = len(revisions) + 1
            entry = {'id': revision_id, 'at': now(), 'before': current['before'], 'after': current['after'],
                     'before_hash': current['before_hash'], 'after_hash': current['after_hash'],
                     'reason': current['reason'], 'authorization': current['authorization'],
                     'request_sha256': current['request_sha256'], 'confirmed_interactively': True,
                     'prior_state_revision': state['revision'], 'backup': backup.relative_to(self.root).as_posix(),
                     'backup_sha256': file_digest(backup), 'reopened_cycles': [], 'reopened_claims': []}
            for cycle in state['cycles']:
                if cycle['status'] == 'verified':
                    cycle.update(status='needs_review', invalidated_by_mission_revision=revision_id)
                    entry['reopened_cycles'].append(cycle['id'])
            for cid, claim in state['claims'].items():
                if claim['status'] == 'verified':
                    claim.update(status='needs_review', invalidated_by_mission_revision=revision_id)
                    entry['reopened_claims'].append(cid)
            revisions.append(entry)
            state['mission'], state['mission_hash'] = current['after'], current['after_hash']
            return {'mission_revised': True, 'mission_revision': revision_id, 'mission_hash': state['mission_hash'],
                    'backup': entry['backup'], 'backup_sha256': entry['backup_sha256'], 'history_preserved': True,
                    'reopened_cycles': entry['reopened_cycles'], 'reopened_claims': entry['reopened_claims'],
                    'next': 'Review the new contract and revalidate current acceptance; previous evidence is historical, not automatic proof of the new mission'}

    def review(self, topic):
        require(nonempty(topic), 'TOPIC', 'Topic required')
        with self.state(write=True) as state:
            relevant = {cid: claim for cid, claim in state['claims'].items() if claim['topic'].casefold() == topic.casefold()}
            cycles = [c for c in state['cycles'] if c['topic'].casefold() == topic.casefold()]
            rid = str(uuid.uuid4())
            # review itself advances revision; any later write invalidates the receipt.
            review = {'id': rid, 'revision': state['revision'] + 1, 'topic': topic,
                      'claims': list(relevant), 'prior_cycles': [c['id'] for c in cycles], 'at': now()}
            state['reviews'][rid] = review
            return {'review': review, 'claims': relevant, 'prior_cycles': cycles,
                    'limit': 'Exact topic match; also search aliases and source vocabulary manually'}

    @staticmethod
    def cycle(state, cycle_id):
        found = [c for c in state['cycles'] if c['id'] == cycle_id]
        require(len(found) == 1, 'CYCLE', 'Unknown cycle')
        return found[0]

    @staticmethod
    def criterion(state, criterion_id):
        found = [c for c in state['mission']['criteria'] if c['id'] == criterion_id]
        require(len(found) == 1, 'CRITERION', 'Unknown acceptance criterion')
        return found[0]

    @staticmethod
    def verified_dependencies(state, ids):
        require(isinstance(ids, list), 'DEPENDENCY', 'Dependencies must be a list')
        for cid in ids:
            require(cid in state['claims'] and state['claims'][cid]['status'] == 'verified', 'DEPENDENCY', f'Dependency is not verified: {cid}')

    def start(self, plan):
        for field in ('topic', 'task', 'premise', 'residual', 'review_id'):
            require(nonempty(plan.get(field)), 'PLAN', f'{field} is required')
        approach = plan.get('approach', {})
        require(set(approach) == {'method', 'inputs', 'environment'} and all(nonempty(v) for v in approach.values()), 'PLAN', 'Approach needs method, inputs, environment; names do not change fingerprints')
        with self.state(write=True) as state:
            budget = state['mission']['budget']
            require(digest(state['mission']) == state['mission_hash'], 'MISSION_CHANGED', 'Mission changed outside the contract')
            require(not any(c['status'] == 'active' for c in state['cycles']), 'OVERLAP', 'An active cycle already exists; resume or interrupt it explicitly')
            require(len(state['cycles']) < budget['max_cycles'], 'BUDGET', 'Cycle budget exhausted')
            reported = sum(c.get('reported_usd', 0) for c in state['cycles'])
            require('max_reported_usd' not in budget or reported < budget['max_reported_usd'], 'BUDGET', 'Reported cost budget exhausted')
            last_cw = state['consolidations'][-1]['through_cycle'] if state['consolidations'] else 0
            require(len(state['cycles']) - last_cw < budget['consolidate_every'], 'CONSOLIDATION_DUE', 'Consolidate before starting another cycle')
            review = state['reviews'].get(plan['review_id'])
            require(review and review['revision'] == state['revision'] and review['topic'] == plan['topic'], 'G1_STALE', 'Read a fresh review of the same topic')
            acknowledged = plan.get('reviewed_claims', [])
            require(isinstance(acknowledged, list) and all(nonempty(cid) for cid in acknowledged), 'PLAN', 'reviewed_claims must be a list of IDs')
            require(set(review['claims']) <= set(acknowledged), 'G1_UNREAD', 'Acknowledge all claims and retractions returned by review')
            criteria = plan.get('criteria')
            require(isinstance(criteria, list) and criteria and len(set(criteria)) == len(criteria), 'G3_CRITERIA', 'Select unique predeclared acceptance criteria')
            for cid in criteria:
                self.criterion(state, cid)
            if state['mission']['mode'] == 'strict':
                require(nonempty(plan.get('reference_review')) and nonempty(plan.get('simplest_test')), 'STRICT', 'Strict mode needs reference review and simplest discriminating test')
            self.verified_dependencies(state, plan.get('relies_on', []))
            fingerprint = digest(approach)
            failures = sum(c['approach_hash'] == fingerprint and any(not check['passed'] for check in c['checks']) for c in state['cycles'])
            require(failures < budget['max_same_failures'], 'G2_BLIND_RETRY', 'Approach failed repeatedly; change a technical dimension')
            last_step = max((s['through_cycle'] for s in state['stepbacks'] if s['task'] == plan['task'] and s['premise'] == plan['premise']), default=0)
            attempts = [c for c in state['cycles'][last_step:] if c['task'] == plan['task'] and c['premise'] == plan['premise']]
            no_progress = 0
            for prior in reversed(attempts):
                if prior.get('progress'):
                    break
                no_progress += 1
            require(no_progress < budget['max_no_progress'], 'STEP_BACK_DUE', 'Review premise, references, data model and simpler alternative before continuing')
            previously_verified = {cid for c in state['cycles'] if c['status'] == 'verified' for cid in c['criteria']}
            already_done = set(criteria) <= previously_verified
            require(not already_done or nonempty(plan.get('reverify_reason')), 'G1_REWORK', 'Selected criteria already verified; explicit revalidation reason required')
            cycle_id = len(state['cycles']) + 1
            cycle = {**plan, 'id': cycle_id, 'approach_hash': fingerprint, 'mission_hash': state['mission_hash'],
                     'status': 'active', 'started': now(), 'checks': [], 'gates': {'G1': 'PASS', 'G2': 'PASS', 'G3': 'PASS'}}
            state['cycles'].append(cycle)
            return {'cycle': cycle_id, 'gates': cycle['gates'], 'acceptance_frozen': criteria}

    def check(self, cycle_id, criterion_id):
        # Holding the YAML store lock prevents two check/close operations
        # from racing. A second writer waits or fails without executing its command.
        with self.state(write=True) as state:
            cycle = self.cycle(state, cycle_id)
            require(cycle['status'] == 'active', 'CYCLE', 'Check needs an active cycle')
            require(digest(state['mission']) == state['mission_hash'] == cycle['mission_hash'], 'MISSION_CHANGED', 'Acceptance contract changed; execution refused')
            require(criterion_id in cycle['criteria'], 'G3_CRITERIA', 'Criterion was not selected before execution')
            criterion = self.criterion(state, criterion_id)
            remaining = state['mission']['budget']['max_cycle_seconds'] - (datetime.now(timezone.utc) - datetime.fromisoformat(cycle['started'])).total_seconds()
            require(remaining > 0, 'TIMEBOX', 'Cycle timebox exceeded; interrupt and review')
            files = {name: file_digest(self.project_file(name)) for name in criterion.get('artifacts', [])}
            timeout = min(remaining, state['mission']['budget']['max_check_seconds'])
            started = time.monotonic()
            try:
                result = subprocess.run(criterion['argv'], cwd=self.root, shell=False, capture_output=True, timeout=timeout)
                exit_code = result.returncode
                output_hash = hashlib.sha256(result.stdout + b'\x00' + result.stderr).hexdigest()
                outcome = 'executed'
            except subprocess.TimeoutExpired:
                exit_code, output_hash, outcome = None, None, 'timeout'
            except OSError:
                exit_code, output_hash, outcome = None, None, 'launch_failed'
            try:
                unchanged = all(file_digest(self.project_file(name)) == value for name, value in files.items())
            except (OSError, Refusal):
                unchanged = False
            record = {'id': str(uuid.uuid4()), 'criterion': criterion_id, 'at': now(), 'argv_hash': digest(criterion['argv']),
                      'exit_code': exit_code, 'outcome': outcome, 'seconds': time.monotonic() - started,
                      'passed': exit_code == 0 and unchanged, 'artifacts': files, 'output_sha256': output_hash}
            cycle['checks'].append(record)
            return record

    def current_check(self, state, cycle, cid):
        require(digest(state['mission']) == state['mission_hash'] == cycle['mission_hash'], 'MISSION_CHANGED', 'Acceptance contract changed')
        records = [r for r in cycle['checks'] if r['criterion'] == cid]
        require(records and records[-1]['passed'], 'EVIDENCE', f'No passing executed check for {cid}')
        record = records[-1]
        require(record['argv_hash'] == digest(self.criterion(state, cid)['argv']), 'EVIDENCE', 'Acceptance command changed')
        require(all(file_digest(self.project_file(name)) == value for name, value in record['artifacts'].items()), 'STALE_ARTIFACT', 'Deliverable changed after its check; run the check again')
        return record

    def close(self, cycle_id, outcome, next_step, tokens=0, reported_usd=0, usage_source=''):
        require(type(tokens) is int and tokens >= 0 and math.isfinite(reported_usd) and reported_usd >= 0, 'USAGE', 'Usage must be finite and nonnegative')
        require(not (tokens or reported_usd) or nonempty(usage_source), 'USAGE', 'Reported usage requires a source')
        with self.state(write=True) as state:
            cycle = self.cycle(state, cycle_id)
            require(cycle['status'] == 'active', 'CYCLE', 'Cycle already closed')
            self.verified_dependencies(state, cycle.get('relies_on', []))
            require(outcome in ('verified', 'blocked'), 'OUTCOME', 'Choose verified or blocked')
            require(nonempty(next_step), 'RESTART', 'Record a next action or explicit completion')
            if outcome == 'verified':
                require((datetime.now(timezone.utc) - datetime.fromisoformat(cycle['started'])).total_seconds() <= state['mission']['budget']['max_cycle_seconds'], 'TIMEBOX', 'Cycle timebox exceeded')
                for cid in cycle['criteria']:
                    self.current_check(state, cycle, cid)
            prior_criteria = {cid for c in state['cycles'][:-1] if c['status'] == 'verified' for cid in c['criteria']}
            new_claim = any(c.get('cycle') == cycle_id and c['status'] == 'verified' for c in state['claims'].values())
            cycle.update(status=outcome, ended=now(), next_step=next_step,
                         progress=bool(outcome == 'verified' and (set(cycle['criteria']) - prior_criteria or new_claim)),
                         tokens=tokens, reported_usd=reported_usd, usage_source=usage_source)
            return {'cycle': cycle_id, 'status': outcome, 'progress': cycle['progress'], 'restart_saved': True}

    def interrupt(self, cycle_id, reason):
        require(nonempty(reason), 'REASON', 'Reason required')
        with self.state(write=True) as state:
            cycle = self.cycle(state, cycle_id)
            require(cycle['status'] == 'active', 'CYCLE', 'Cycle is not active')
            cycle.update(status='blocked', ended=now(), next_step=reason, progress=False)
        return {'interrupted': cycle_id, 'history_preserved': True}

    def resume(self):
        with self.state() as state:
            return {'version': VERSION, 'revision': state['revision'], 'mission': state['mission'],
                    'mission_hash': state['mission_hash'], 'active_cycles': [c for c in state['cycles'] if c['status'] == 'active'],
                    'recent_cycles': state['cycles'][-5:], 'claims': state['claims'],
                    'mission_revisions': state.get('mission_revisions', []),
                    'last_consolidation': state['consolidations'][-1:]}

    def claim(self, entry):
        for field in ('id', 'topic', 'statement'):
            require(nonempty(entry.get(field)), 'CLAIM', f'{field} required')
        require(entry.get('kind') in ('fact', 'hypothesis'), 'CLAIM', 'Choose fact or hypothesis')
        with self.state(write=True) as state:
            cid = entry['id']
            require(cid not in state['claims'], 'CLAIM_EXISTS', 'Existing claims are never silently overwritten')
            normalized = ' '.join(entry['statement'].casefold().split())
            require(not any(' '.join(c['statement'].casefold().split()) == normalized and c['topic'] == entry['topic'] for c in state['claims'].values()), 'DUPLICATE_CLAIM', 'Statement already recorded; use its existing ID')
            cycle = self.cycle(state, entry.get('cycle'))
            require(cycle['status'] == 'active', 'CYCLE', 'Record findings in an active cycle')
            dependencies = entry.get('depends_on', [])
            require(cid not in dependencies, 'DEPENDENCY', 'A claim cannot depend on itself')
            self.verified_dependencies(state, dependencies)
            status, check_id = 'candidate', None
            if entry['kind'] == 'fact':
                record = self.current_check(state, cycle, entry.get('criterion'))
                require(record['artifacts'], 'CLAIM', 'A verified fact needs a hashed evidence artifact')
                status, check_id = 'verified', record['id']
            value = {**entry, 'status': status, 'depends_on': dependencies, 'created': now(), 'check_id': check_id}
            state['claims'][cid] = value
            return {'id': cid, 'status': status, 'limitation': 'The gate checks provenance, not the semantic truth of the statement'}

    def retract(self, correction):
        for field in ('id', 'what_falls', 'reason', 'correction_evidence'):
            require(nonempty(correction.get(field)), 'RETRACTION', f'{field} required')
        evidence = self.project_file(correction['correction_evidence'])
        with self.state(write=True) as state:
            cid = correction['id']
            require(cid in state['claims'], 'CLAIM', 'Claim not found')
            root = state['claims'][cid]
            require(correction['what_falls'] == root['statement'], 'RETRACTION', 'Identify the exact statement being corrected')
            require(root['status'] != 'retracted', 'RETRACTION', 'Already retracted; history preserved')
            affected = {cid}
            while True:
                expanded = affected | {key for key, value in state['claims'].items() if set(value['depends_on']) & affected}
                if expanded == affected:
                    break
                affected = expanded
            proof = {'at': now(), 'reason': correction['reason'], 'what_falls': correction['what_falls'],
                     'evidence': correction['correction_evidence'], 'sha256': file_digest(evidence)}
            root.update(status='retracted', retraction=proof)
            for key in affected - {cid}:
                if state['claims'][key]['status'] != 'retracted':
                    state['claims'][key].update(status='needs_review', invalidated_by=cid)
            reopened = []
            affected_cycles = {state['claims'][key]['cycle'] for key in affected}
            for cycle in state['cycles']:
                if cycle['status'] == 'verified' and (set(cycle.get('relies_on', [])) & affected or cycle['id'] in affected_cycles):
                    cycle.update(status='needs_review', invalidated_by=cid)
                    reopened.append(cycle['id'])
            return {'retracted': cid, 'dependent_claims_needing_review': sorted(affected - {cid}), 'reopened_cycles': reopened, 'history_deleted': False}

    def step_back(self, review):
        for field in ('task', 'premise', 'reference_review', 'data_model_review', 'simpler_alternative', 'next_test'):
            require(nonempty(review.get(field)), 'STEP_BACK', f'{field} required')
        with self.state(write=True) as state:
            require(not any(c['status'] == 'active' for c in state['cycles']), 'OVERLAP', 'Close or interrupt the active cycle first')
            state['stepbacks'].append({**review, 'at': now(), 'through_cycle': len(state['cycles'])})
        return {'step_back_saved': True, 'limit': 'A recorded review does not prove its reasoning is correct'}

    def validate(self):
        issues = []
        with self.state() as state:
            if digest(state['mission']) != state['mission_hash']:
                issues.append({'kind': 'mission_changed'})
            revisions = state.get('mission_revisions', [])
            for number, entry in enumerate(revisions, 1):
                if (entry['id'] != number or digest(entry['before']) != entry['before_hash'] or
                        digest(entry['after']) != entry['after_hash'] or
                        (number > 1 and revisions[number - 2]['after_hash'] != entry['before_hash']) or
                        (number == len(revisions) and entry['after_hash'] != state['mission_hash'])):
                    issues.append({'kind': 'mission_revision_history', 'mission_revision': number})
            if [c['id'] for c in state['cycles']] != list(range(1, len(state['cycles']) + 1)):
                issues.append({'kind': 'cycle_sequence'})
            if sum(c['status'] == 'active' for c in state['cycles']) > 1:
                issues.append({'kind': 'overlap'})
            for cycle in state['cycles']:
                if cycle['status'] != 'verified':
                    continue
                try:
                    self.verified_dependencies(state, cycle.get('relies_on', []))
                    for cid in cycle['criteria']:
                        self.current_check(state, cycle, cid)
                except (Refusal, OSError) as error:
                    issues.append({'kind': getattr(error, 'code', 'missing_artifact'), 'cycle': cycle['id']})
            for cid, claim in state['claims'].items():
                if any(key not in state['claims'] for key in claim['depends_on']):
                    issues.append({'kind': 'broken_dependency', 'claim': cid})
                if claim['status'] == 'verified':
                    cycle = self.cycle(state, claim['cycle'])
                    records = [r for r in cycle['checks'] if r['id'] == claim['check_id'] and r['passed']]
                    if not records:
                        issues.append({'kind': 'missing_claim_evidence', 'claim': cid})
                    else:
                        try:
                            if not all(file_digest(self.project_file(name)) == value for name, value in records[0]['artifacts'].items()):
                                issues.append({'kind': 'stale_claim_evidence', 'claim': cid})
                            self.verified_dependencies(state, claim['depends_on'])
                        except (Refusal, OSError):
                            issues.append({'kind': 'invalid_claim_dependency_or_artifact', 'claim': cid})
            revision = state['revision']
        try:
            healthy = self.store.validate()
        except StoreError:
            healthy = False
        if not healthy:
            issues.append({'kind': 'yaml_integrity'})
        return {'passed': not issues, 'issues': issues, 'revision': revision}

    def consolidate(self, note):
        for field in ('failures_and_dead_ends', 'retractions_and_repairs', 'established_facts', 'open_questions', 'patterns_and_actions'):
            require(isinstance(note.get(field), list), 'CONSOLIDATION', f'{field} must be a list; empty is explicit')
        audit = self.validate()
        require(audit['passed'], 'STORE_INVALID', 'Fix evidence/state inconsistencies before consolidation')
        with self.state(write=True) as state:
            require(state['revision'] == audit['revision'], 'RACE', 'State changed; validate and consolidate again')
            require(not any(c['status'] == 'active' for c in state['cycles']), 'OVERLAP', 'Finish the active cycle first')
            previous = state['consolidations'][-1]['through_cycle'] if state['consolidations'] else 0
            cycles = state['cycles'][previous:]
            require(cycles, 'CONSOLIDATION', 'No new cycles to consolidate')
            state['consolidations'].append({'at': now(), 'through_cycle': len(state['cycles']), 'cycle_ids_read': [c['id'] for c in cycles],
                                            'cycle_records_sha256': digest(cycles), 'note': note, 'audit': audit})
            return {'consolidated_cycles': [c['id'] for c in cycles], 'through_cycle': len(state['cycles']), 'source': 'canonical YAML records, not chat summaries'}

    def timing(self, command, seconds, code):
        if not self.db.exists():
            return
        try:
            event = json.dumps({'command': command, 'seconds': seconds, 'exit_code': code})
            self.store.append_audit(event)
        except StoreError as error:
            raise Refusal(error.code, error.detail) from error

    def metrics(self):
        audit = self.validate()
        try:
            timings = [json.loads(kind) for kind in self.store.audit_kinds()
                       if isinstance(kind, str) and kind.startswith('{')]
        except StoreError as error:
            raise Refusal(error.code, error.detail) from error
        with self.state() as state:
            checks = [check for cycle in state['cycles'] for check in cycle['checks']]
            validated_cycles = [c for c in state['cycles'] if c['status'] == 'verified']
            observed = {cid for cycle in validated_cycles for cid in cycle['criteria']}
            check_seconds = sum(r['seconds'] for r in checks)
            tool_seconds = sum(e['seconds'] for e in timings)
            return {'cycles': len(state['cycles']), 'verified_cycles': len(validated_cycles),
                    'criteria_verified': len(observed) if audit['passed'] else None,
                    'recorded_criteria_verified': len(observed), 'criteria_total': len(state['mission']['criteria']),
                    'evidence_current': audit['passed'], 'evidence_issues': audit['issues'],
                    'no_progress_cycles': sum(not c.get('progress', False) for c in state['cycles'] if c['status'] != 'active'),
                    'checks_passed': sum(r['passed'] for r in checks), 'checks_failed': sum(not r['passed'] for r in checks),
                    'gate_refusals_recorded_by_cli': sum(e['exit_code'] == 2 for e in timings),
                    'check_seconds': check_seconds, 'observed_cli_seconds': tool_seconds,
                    'approx_cli_overhead_seconds': max(0, tool_seconds - check_seconds) if timings else None,
                    'reported_tokens': sum(c.get('tokens', 0) for c in state['cycles']),
                    'reported_usd': sum(c.get('reported_usd', 0) for c in state['cycles']),
                    'cost_caveat': 'Usage is user/client-reported, not a measured provider bill; overhead excludes agent reasoning and manual tool use',
                    'claims_by_status': {status: sum(c['status'] == status for c in state['claims'].values()) for status in ('verified', 'candidate', 'needs_review', 'retracted')}}

    def export(self, relative):
        target = self.project_file(relative, exists=False)
        require(target.parent.is_dir(), 'PATH', 'Export parent must already exist')
        marker = '# GENERATED BY HARNESS 7.8'
        require(not target.exists() or target.read_text(encoding='utf-8').startswith(marker), 'PROTECTED_OUTPUT', 'Refusing to replace an unrelated file')
        result = {'resume': self.resume(), 'metrics': self.metrics()}
        text = marker + '\n\nRead-only derived view; YAML remains the source of truth.\n\n```json\n' + json.dumps(result, ensure_ascii=False, indent=2) + '\n```\n'
        temporary = target.with_name(target.name + '.' + uuid.uuid4().hex + '.tmp')
        temporary.write_text(text, encoding='utf-8')
        temporary.replace(target)
        return {'generated': str(target), 'sha256': file_digest(target)}

    def backup(self, relative):
        require(self.db.exists(), 'NOT_INITIALIZED', 'Run init first')
        target = self.project_file(relative, exists=False)
        require(target.parent.is_dir() and not target.exists(), 'PATH', 'Backup needs an existing parent and a new file')
        try:
            self.store.backup(target)
        except StoreError as error:
            raise Refusal(error.code, error.detail) from error
        return {'backup': str(target), 'sha256': file_digest(target), 'integrity': 'ok'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('init', 'start', 'claim', 'retract', 'step-back', 'consolidate', 'preview-mission', 'revise-mission'):
        sub.add_parser(name).add_argument('--input', required=True)
    sub.add_parser('review').add_argument('--topic', required=True)
    check = sub.add_parser('check')
    check.add_argument('--cycle', type=int, required=True)
    check.add_argument('--criterion', required=True)
    close = sub.add_parser('close')
    close.add_argument('--cycle', type=int, required=True)
    close.add_argument('--outcome', choices=['verified', 'blocked'], required=True)
    close.add_argument('--next', required=True)
    close.add_argument('--tokens', type=int, default=0)
    close.add_argument('--reported-usd', type=float, default=0)
    close.add_argument('--usage-source', default='')
    interrupt = sub.add_parser('interrupt')
    interrupt.add_argument('--cycle', type=int, required=True)
    interrupt.add_argument('--reason', required=True)
    sub.add_parser('resume')
    sub.add_parser('validate')
    sub.add_parser('metrics')
    sub.add_parser('migrate-sqlite')
    for name in ('export', 'backup'):
        sub.add_parser(name).add_argument('--output', required=True)
    args = parser.parse_args()
    started = time.monotonic()
    harness = None
    try:
        harness = Harness(args.project)
        if args.command in ('init', 'start', 'claim', 'retract', 'step-back', 'consolidate', 'preview-mission', 'revise-mission'):
            payload = json.loads(Path(args.input).read_text(encoding='utf-8-sig'))
            result = getattr(harness, args.command.replace('-', '_'))(payload)
        elif args.command == 'review':
            result = harness.review(args.topic)
        elif args.command == 'check':
            result = harness.check(args.cycle, args.criterion)
        elif args.command == 'close':
            result = harness.close(args.cycle, args.outcome, args.next, args.tokens, args.reported_usd, args.usage_source)
        elif args.command == 'interrupt':
            result = harness.interrupt(args.cycle, args.reason)
        elif args.command in ('export', 'backup'):
            result = getattr(harness, args.command)(args.output)
        elif args.command == 'migrate-sqlite':
            result = harness.migrate_sqlite()
        else:
            result = getattr(harness, args.command)()
        print(json.dumps({'ok': True, 'result': result}, ensure_ascii=True, indent=2))
        if args.command in ('check', 'validate') and not result['passed']:
            harness.timing(args.command, time.monotonic() - started, 3)
            return 3
        harness.timing(args.command, time.monotonic() - started, 0)
        return 0
    except Refusal as error:
        if harness is not None:
            try:
                harness.timing(args.command, time.monotonic() - started, 2)
            except (OSError, StoreError, ValueError, TypeError):
                pass
        print(json.dumps({'ok': False, 'code': error.code, 'detail': error.detail}, ensure_ascii=True))
        return 2
    except (OSError, ValueError, StoreError, KeyError, TypeError) as error:
        # Input/state errors do not authorize execution or a success receipt.
        print(json.dumps({'ok': False, 'code': 'INVALID_INPUT_OR_STORE', 'detail': type(error).__name__}))
        return 2


if __name__ == '__main__':
    sys.exit(main())
