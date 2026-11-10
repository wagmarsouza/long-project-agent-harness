"""Bounded model-based lifecycle exploration; the oracle does not call engine predicates."""
import hashlib
import json

from assurance_fixture import Fixture, case_result, engine, fresh_engine

PREFIX = ['start', 'close', 'check', 'close', 'start-no-reason', 'edit-bad', 'start', 'check',
          'close', 'interrupt', 'edit-good', 'start', 'check', 'close', 'reload', 'unauthorized-revision']
ACTIONS = ['start', 'start-no-reason', 'check', 'close', 'interrupt', 'edit-good', 'edit-bad',
           'reload', 'inspect', 'unauthorized-revision']


def programs(seed, traces, steps):
    if (type(seed) is not int or not 0 <= seed < 2**32 or type(traces) is not int or
            not 1 <= traces <= 4 or type(steps) is not int or not 16 <= steps <= 64):
        raise ValueError('Use seed 0..2^32-1, traces 1..4 and steps 16..64')
    return [PREFIX + [ACTIONS[int.from_bytes(hashlib.sha256(
        f'control83-lifecycle-v1:{seed}:{trace}:{i}'.encode()).digest()[:4], 'big') % len(ACTIONS)]
        for i in range(len(PREFIX), steps)] for trace in range(traces)]


class Model:
    """Small independent oracle: active phase, input generation and last successful witness."""
    def __init__(self):
        self.active = False
        self.cycle = 0
        self.epoch = 1
        self.good = True
        self.check_epoch = None
        self.check_good = False
        self.verified = 0
        self.revision = 0

    def expected(self, action):
        if action in ('start', 'start-no-reason'):
            if self.active: return 'OVERLAP'
            if action == 'start-no-reason' and self.verified: return 'G1_REWORK'
            return 'started'
        if action == 'check':
            return 'CYCLE' if not self.active else ('pass' if self.good else 'fail')
        if action == 'close':
            if not self.active: return 'CYCLE'
            return 'verified' if self.check_epoch == self.epoch and self.check_good and self.good else 'REGRESSION_BLOCKED'
        if action == 'interrupt': return 'interrupted' if self.active else 'CYCLE'
        if action == 'unauthorized-revision': return 'USER_AUTHORIZATION'
        return 'done'

    def advance(self, action, observed):
        if observed == 'started':
            self.active = True; self.cycle += 1; self.check_epoch = None; self.check_good = False
        elif action == 'check' and observed in ('pass', 'fail'):
            self.check_epoch = self.epoch; self.check_good = observed == 'pass'
        elif observed in ('verified', 'interrupted'):
            self.active = False
            if observed == 'verified': self.verified += 1
        elif action in ('edit-good', 'edit-bad'):
            self.epoch += 1; self.good = action == 'edit-good'


def _perform(fixture, model, action):
    h = fixture.h
    try:
        if action in ('start', 'start-no-reason'):
            h.start(fixture.plan(reason=action == 'start'))
            return 'started'
        if action == 'check':
            return 'pass' if h.check(model.cycle or 999, 'R')['passed'] else 'fail'
        if action == 'close':
            return h.close(model.cycle or 999, 'verified', 'Bounded synthetic lifecycle check')['status']
        if action == 'interrupt':
            h.interrupt(model.cycle or 999, 'Explicit synthetic interruption')
            return 'interrupted'
        if action in ('edit-good', 'edit-bad'):
            fixture.candidate(good=action == 'edit-good')
        elif action == 'reload':
            before = h.db.read_bytes()
            fixture.h = fresh_engine(fixture.root, fixture.nonce)
            fixture.h.resume()
            if before != fixture.h.db.read_bytes(): return 'read_modified_state'
        elif action == 'inspect':
            before = h.db.read_bytes()
            h.regression_report()
            if before != h.db.read_bytes(): return 'read_modified_state'
        elif action == 'unauthorized-revision':
            with h.state() as state:
                proposal = {'expected_mission_hash': state['mission_hash'], 'expected_revision': state['revision'],
                            'reason': 'Synthetic unauthorized change',
                            'authorization': {'source': 'automation', 'reference': 'not-authorized'},
                            'mission': {**fixture.mission, 'objective': 'Unauthorized replacement'}}
            h.revise_mission(proposal)
            return 'unauthorized_revision_applied'
        return 'done'
    except engine.Refusal as error:
        return error.code


def _invariants(fixture, model, mission_hash):
    h = fixture.h
    h.store.validate()
    with h.state() as state:
        if state['mission_hash'] != mission_hash or engine.digest(state['mission']) != mission_hash:
            raise AssertionError('Mission changed without human authority')
        if state['revision'] < model.revision or len(state['cycles']) != model.cycle:
            raise AssertionError('Revision or cycle history was lost')
        if sum(c['status'] == 'active' for c in state['cycles']) != int(model.active):
            raise AssertionError('Active-cycle model mismatch')
        if state['claims'] or state.get('mission_revisions') or state.get('operations'):
            raise AssertionError('Synthetic exploration acquired undeclared authority or claims')
        if [c['id'] for c in state['cycles']] != list(range(1, model.cycle + 1)):
            raise AssertionError('Cycle history IDs changed')
        # Every later successful replay covers the same obligation and creates no new fact.
        successes = [c for c in state['cycles'] if c['status'] == 'verified' or c.get('invalidated_by_regression')]
        if len(successes) != model.verified or any(c['progress'] for c in successes[1:]):
            raise AssertionError('Revalidation inflated progress or erased verified history')
        if state['mission']['budget'] != h.normalize_mission(fixture.mission)['budget']:
            raise AssertionError('Campaign reset the mission budget')
        model.revision = state['revision']


def run(seed=0, traces=2, steps=24):
    generated = programs(seed, traces, steps)
    reports = []
    for index, program in enumerate(generated):
        rows = []
        with Fixture() as fixture:
            model = Model()
            with fixture.h.state() as state: mission_hash = state['mission_hash']
            for number, action in enumerate(program):
                expected = model.expected(action)
                try:
                    observed = _perform(fixture, model, action)
                    row = case_result(str(number + 1), expected, observed, action=action)
                    if row['passed']:
                        model.advance(action, observed)
                        _invariants(fixture, model, mission_hash)
                except Exception as error:
                    row = case_result(str(number + 1), expected, 'invariant_or_infrastructure_error',
                                      action=action, error_type=type(error).__name__, detail=str(error))
                rows.append(row)
                if not row['passed']: break
        reports.append({'id': index + 1, 'program': program, 'steps': rows,
                        'passed': len(rows) == len(program) and all(r['passed'] for r in rows)})
    return {'suite': 'lifecycle', 'seed': seed, 'program_version': 1, 'configuration': {'traces': traces, 'steps': steps},
            'planned_steps': traces * steps, 'executed_steps': sum(len(r['steps']) for r in reports),
            'traces': reports, 'passed': all(r['passed'] for r in reports), 'exhaustive': False,
            'model': 'independent active-phase / input-generation / current-witness oracle'}
