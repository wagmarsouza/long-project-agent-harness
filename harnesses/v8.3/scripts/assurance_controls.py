"""Known-bad controls must fail for their intended reason, after a healthy control passes."""
import json
import yaml

from assurance_fixture import CASE, Fixture, case_result, engine

CONTROLS = {
    'missing-case': 'missing', 'skipped-case': 'skipped', 'wrong-answer': 'fail',
    'wrong-memory': 'fail', 'stale-run': 'foreign_run', 'incomplete-result': 'incomplete',
    'changed-oracle': 'REGRESSION_SOURCE', 'omitted-criterion': 'REGRESSION_PLAN',
    'corrupt-store': 'STORE_INTEGRITY',
}


def _observe(fixture, control):
    h = fixture.h
    if control == 'corrupt-store':
        document = yaml.safe_load(h.db.read_text(encoding='utf-8'))
        document['state']['mission']['objective'] = 'Deliberately corrupt synthetic YAML'
        h.db.write_text(yaml.safe_dump(document), encoding='utf-8')
        try:
            h.resume()
        except engine.Refusal as error:
            return error.code
        return 'accepted'
    if control == 'omitted-criterion':
        try:
            h.start(fixture.plan(['OTHER']))
        except engine.Refusal as error:
            return error.code
        return 'accepted'
    if control == 'changed-oracle':
        with (fixture.root / 'runner.py').open('a', encoding='utf-8') as stream:
            stream.write('\n# deliberately changed protected oracle\n')
        try:
            fixture.start()
        except engine.Refusal as error:
            return error.code
        return 'accepted'
    value = json.loads((fixture.root / 'candidate.json').read_text(encoding='utf-8'))
    if control == 'missing-case': value['cases'] = []
    elif control == 'skipped-case': value['cases'][0]['status'] = 'skipped'
    elif control == 'wrong-answer': value['cases'][0]['observed']['answer'] = -1
    elif control == 'wrong-memory': value['cases'][0]['observed']['memory'] = [0, 99]
    elif control == 'stale-run': value['old'] = True
    elif control == 'incomplete-result': value['complete'] = False
    else: raise ValueError('Unknown bundled control')
    (fixture.root / 'candidate.json').write_text(json.dumps(value), encoding='utf-8')
    cid = fixture.start()
    check = h.check(cid, 'R')
    if check['outcome'] != 'executed' or check['exit_code'] != 0:
        return 'execution_error'
    assessment = check['regression']['assessment']
    if check['passed']:
        return 'accepted'
    try:
        h.close(cid, 'verified', 'Synthetic control must refuse closure')
    except engine.Refusal as error:
        if error.code != 'REGRESSION_BLOCKED': return error.code
    else: return 'closure_accepted'
    if control == 'stale-run':
        return 'foreign_run' if assessment.get('reason') == 'Report belongs to another execution/context' else 'wrong_diagnostic'
    if control == 'incomplete-result':
        return 'incomplete' if assessment.get('reason') == 'A complete current execution is required' else 'wrong_diagnostic'
    rows = [r for r in assessment.get('rows', []) if r['case'] == CASE]
    return rows[0]['status'] if len(rows) == 1 else 'wrong_diagnostic'


def run():
    with Fixture() as fixture:
        cid = fixture.start()
        check = fixture.h.check(cid, 'R')
        closed = fixture.h.close(cid, 'verified', 'Healthy synthetic control finished')
        positive = case_result('healthy', 'accepted', 'accepted' if
            check['passed'] and closed['status'] == 'verified' and fixture.h.validate()['passed'] else 'rejected')
    rows = []
    for control, expected in CONTROLS.items():
        try:
            with Fixture() as fixture:
                observed = _observe(fixture, control)
            rows.append(case_result(control, expected, observed))
        except Exception as error:
            rows.append(case_result(control, expected, 'infrastructure_error', error_type=type(error).__name__))
    return {'suite': 'controls', 'positive_control': positive, 'cases': rows,
            'passed': positive['passed'] and all(r['passed'] for r in rows),
            'global_mutation_score_claimed': False}
