"""Sweep real YAML persistence boundaries in disposable child processes only."""
import argparse
from contextlib import ExitStack
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

from assurance_fixture import Fixture, fresh_engine, sha, engine

STAGES = ('before-open', 'partial-write', 'before-flush', 'before-fsync', 'before-replace', 'after-replace')
OPERATIONS = ('review', 'check', 'close')
MODES = ('exception', 'crash')
CRASH_EXIT = 79


class InjectedFault(OSError):
    pass


class _WriteProxy:
    def __init__(self, stream, fault):
        self.stream, self.fault = stream, fault

    def __enter__(self):
        self.stream.__enter__()
        self.fault.descriptor = self.stream.fileno()
        return self

    def __exit__(self, *args):
        self.fault.descriptor = None
        return self.stream.__exit__(*args)

    def write(self, text):
        if self.fault.stage == 'partial-write' and not self.fault.reached:
            self.stream.write(text[:max(1, len(text) // 2)])
            self.fault.hit('partial-write')
        return self.stream.write(text)

    def flush(self):
        self.fault.hit('before-flush')
        return self.stream.flush()

    def fileno(self):
        return self.stream.fileno()


class _Fault:
    """Test-only interception, scoped to this worker's specific canonical YAML target."""
    def __init__(self, target, operation, stage, mode):
        self.target, self.operation, self.stage, self.mode = target, operation, stage, mode
        self.reached = False
        self.descriptor = None

    def hit(self, stage):
        if self.stage != stage or self.reached: return
        self.reached = True
        print(json.dumps({'fault_reached': stage, 'operation': self.operation, 'mode': self.mode}), flush=True)
        if self.mode == 'crash': os._exit(CRASH_EXIT)
        raise InjectedFault('Synthetic persistence interruption at ' + stage)

    def __enter__(self):
        original_open, original_sync, original_replace = Path.open, os.fsync, os.replace
        def temporary_open(path, *args, **kwargs):
            if path.parent == self.target.parent and path.name.startswith(self.target.name + '.') and path.suffix == '.tmp':
                self.hit('before-open')
                return _WriteProxy(original_open(path, *args, **kwargs), self)
            return original_open(path, *args, **kwargs)
        def file_sync(fd):
            if fd == self.descriptor: self.hit('before-fsync')
            return original_sync(fd)
        def replace(src, dst):
            if Path(dst) == self.target:
                self.hit('before-replace')
                result = original_replace(src, dst)
                self.hit('after-replace')
                return result
            return original_replace(src, dst)
        self.stack = ExitStack()
        self.stack.enter_context(patch.object(Path, 'open', temporary_open))
        self.stack.enter_context(patch.object(os, 'fsync', file_sync))
        self.stack.enter_context(patch.object(os, 'replace', replace))
        return self

    def __exit__(self, *args):
        return self.stack.__exit__(*args)


def worker(root, nonce, operation, stage, mode):
    _configuration(operation, stage, mode)
    h = fresh_engine(root, nonce)
    try:
        with _Fault(h.db, operation, stage, mode):
            if operation == 'review': h.review('persistence-probe')
            elif operation == 'check': h.check(1, 'R')
            else: h.close(1, 'verified', 'Synthetic persistence close')
    except InjectedFault:
        return 0
    raise RuntimeError('The selected boundary was not reached')


def _configuration(operation, stage, mode):
    if operation not in OPERATIONS or stage not in STAGES or mode not in MODES:
        raise ValueError('Select a bundled operation, persistence boundary and exception/crash mode')


def _preserved(before, after, allowed):
    if ({k:v for k,v in before.items() if k not in allowed} !=
            {k:v for k,v in after.items() if k not in allowed}):
        raise AssertionError('Previously committed history changed outside the allowed operation delta')


def _committed_history(operation, old, state):
    allowed = {'revision','reviews'} if operation == 'review' else {'revision','cycles','events'}
    if operation == 'close': allowed.add('regression_guard')
    _preserved(old,state,allowed)
    if operation == 'review':
        reviews = state['reviews']
        if len(reviews) != len(old['reviews'])+1 or any(reviews.get(k) != value for k,value in old['reviews'].items()):
            raise AssertionError('Review history was lost or changed')
        return
    if state['cycles'][:-1] != old['cycles'][:-1]:
        raise AssertionError('Earlier cycle history changed')
    before, after = old['cycles'][-1], state['cycles'][-1]
    delta = {'checks'} if operation == 'check' else {
        'status','ended','next_step','progress','tokens','reported_usd','usage_source','regression_assessment'}
    _preserved(before,after,delta)
    if operation == 'check' and (after['checks'][:-1] != before['checks'] or len(after['checks']) != len(before['checks'])+1):
        raise AssertionError('Prior checks changed or more than one execution was recorded')
    previous = old.get('events',[]); current = state.get('events',[])
    kind = 'regression-check' if operation == 'check' else 'regression-assessed'
    if len(current) != len(previous)+1 or current[:-1] != previous or current[-1]['kind'] != kind:
        raise AssertionError('Prior event history changed or the expected operation event is missing')
    if operation == 'close':
        _preserved(old['regression_guard'],state['regression_guard'],{'last_validated'})
        if state['regression_guard']['last_validated']['assessment_sha256'] != engine.digest(after['regression_assessment']):
            raise AssertionError('Validated snapshot does not bind the committed assessment')


def _recovery(fixture, operation, stage, old_bytes, before):
    h = fresh_engine(fixture.root, fixture.nonce)
    h.store.validate()
    document = h.store._load_unlocked()
    state, old = document['state'], before['state']
    committed = stage == 'after-replace'
    if not committed:
        if h.db.read_bytes() != old_bytes: raise AssertionError('Uncommitted state replaced the old YAML')
    else:
        if state['revision'] != old['revision'] + 1 or len(document['audit']) != len(before['audit']) + 1:
            raise AssertionError('Committed state/audit revision is incomplete')
        if document['audit'][:-1] != before['audit']:
            raise AssertionError('Prior audit history was changed')
        if state['mission'] != old['mission'] or state['mission_hash'] != old['mission_hash']:
            raise AssertionError('Persistence recovery changed the mission')
        if state['claims'] != old['claims'] or len(state['cycles']) != len(old['cycles']):
            raise AssertionError('Recovery fabricated claims or cycles')
        _committed_history(operation,old,state)
        if operation == 'review':
            if len(state['reviews']) != len(old['reviews']) + 1:
                raise AssertionError('Review commit missing')
        elif operation == 'check':
            current = state['cycles'][-1]
            if current['status'] != 'active' or len(current['checks']) != 1 or not current['checks'][0]['passed']:
                raise AssertionError('Check commit missing or incorrectly closed')
            if state['regression_guard']['last_validated'] is not None:
                raise AssertionError('A check silently became a verified close')
        else:
            current = state['cycles'][-1]
            if current['status'] != 'verified' or state['regression_guard']['last_validated']['cycle'] != 1:
                raise AssertionError('Verified close and validated snapshot were not committed together')
        if not h.validate()['passed']:
            raise AssertionError('Recovered commit fails native consistency validation')
        if operation in ('check','close') and not h.regression_report(1)['passed']:
            raise AssertionError('Recovered execution has no current preservation proof')
    snapshots = {p.name: sha(p) for p in fixture.root.glob('reports/*.json')}
    if operation == 'check' and len(snapshots) != 1:
        raise AssertionError('Executed check result was silently lost or repeated')
    before_resume = h.db.read_bytes()
    h.resume()  # Fresh process lock must have been released; this never resumes external work.
    if h.db.read_bytes() != before_resume or snapshots != {p.name: sha(p) for p in fixture.root.glob('reports/*.json')}:
        raise AssertionError('Read-only recovery replayed or altered evidence')
    return 'new' if committed else 'old'


def run_case(operation, stage, mode):
    _configuration(operation, stage, mode)
    row = {'id': f'{operation}:{stage}:{mode}', 'operation': operation, 'stage': stage, 'mode': mode,
           'fault_reached': False, 'passed': False, 'commit': 'unverified'}
    try:
        with Fixture() as fixture:
            if operation in ('check', 'close'):
                fixture.start()
                if operation == 'close':
                    if not fixture.h.check(1, 'R')['passed']: raise AssertionError('Healthy setup check failed')
            before = fixture.h.store._load_unlocked()
            old_bytes = fixture.h.db.read_bytes()
            process = subprocess.run([sys.executable, '-B', str(Path(__file__).resolve()), '--worker',
                str(fixture.root), fixture.nonce, operation, stage, mode], capture_output=True, text=True,
                encoding='utf-8', timeout=60, env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONUTF8': '1'})
            markers = [json.loads(line) for line in process.stdout.splitlines() if line.startswith('{')]
            row['fault_reached'] = markers == [{'fault_reached': stage, 'operation': operation, 'mode': mode}]
            row['worker_exit'] = process.returncode
            expected_exit = CRASH_EXIT if mode == 'crash' else 0
            if not row['fault_reached'] or process.returncode != expected_exit:
                row['error'] = 'Expected fault marker and worker outcome not observed'
                return row
            row['commit'] = _recovery(fixture, operation, stage, old_bytes, before)
            row['orphan_result_retained'] = operation == 'check' and row['commit'] == 'old'
            row['passed'] = True
    except Exception as error:
        row.update(error_type=type(error).__name__, error=str(error))
    return row


def run():
    rows = [run_case(operation, stage, mode) for operation in OPERATIONS for stage in STAGES for mode in MODES]
    return {'suite': 'persistence', 'cases': rows, 'passed': all(r['passed'] for r in rows),
            'planned_cases': len(OPERATIONS) * len(STAGES) * len(MODES),
            'physical_power_loss_simulated': False,
            'directory_fsync_tested': False,
            'canonical_store': '.harness/state.yaml',
            'limit': 'Process termination and injected I/O faults, not physical disk/controller power loss'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Internal worker for owned synthetic assurance fixtures only')
    parser.add_argument('--worker', nargs=5, required=True, metavar=('ROOT', 'NONCE', 'OPERATION', 'STAGE', 'MODE'))
    args = parser.parse_args()
    sys.exit(worker(*args.worker))
