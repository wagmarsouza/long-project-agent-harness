"""Pure preservation contracts and non-compensating comparisons; no effects or tools."""
from datetime import date
import hashlib
import json
import math
import re


class Invalid(ValueError):
    pass


def need(condition, detail):
    if not condition:
        raise Invalid(detail)


def text(value):
    return isinstance(value, str) and bool(value.strip()) and '\x00' not in value


def canonical(value):
    try:
        return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',', ':'))
    except (ValueError, TypeError, RecursionError):
        raise Invalid('Only finite JSON-compatible values are accepted') from None


def sha(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def checksum(value):
    return isinstance(value, str) and re.fullmatch('[a-f0-9]{64}', value) is not None


def relative(value, pattern=False):
    need(text(value) and not value.startswith('/') and ':' not in value and '\\' not in value,
         'Use portable forward-slash project-relative paths')
    need(not set(value.split('/')) & {'..', '.', '', '.harness', '.git'}, 'Unsafe path segment')
    if not pattern:
        need(not any(c in value for c in '*?[]{}'), 'Literal evidence paths cannot contain placeholders/globs')
    return value


def loads(raw):
    def pairs(rows):
        result = {}
        for k, v in rows:
            need(k not in result, 'Duplicate JSON keys are refused')
            result[k] = v
        return result
    def constant(_):
        raise Invalid('Non-finite numbers are refused')
    try:
        value = json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
        canonical(value)
        return value
    except (json.JSONDecodeError, UnicodeError, RecursionError):
        raise Invalid('Malformed preservation JSON') from None


def baseline(value, criterion_ids):
    canonical(value)
    need(isinstance(value, dict) and set(value) == {'format', 'reference', 'protected_files', 'context_files', 'obligations', 'debt'},
         'Use the exact verimission-baseline-v1 contract')
    need(value['format'] == 'verimission-baseline-v1', 'Unknown baseline format')
    ref = value['reference']
    need(isinstance(ref, dict) and set(ref) == {'kind', 'id'} and ref['kind'] in ('specification', 'commit') and text(ref['id']),
         'A declared specification or resolved commit reference is required')
    if ref['kind'] == 'commit':
        need(re.fullmatch('([a-f0-9]{40}|[a-f0-9]{64})', ref['id']) is not None, 'Resolve Git references before adoption')
    for key in ('protected_files', 'context_files'):
        need(isinstance(value[key], dict), 'File bindings must be hash maps')
        for path, digest in value[key].items():
            relative(path); need(checksum(digest), 'Expected a SHA-256 file binding')
    need(value['protected_files'], 'Pin the oracle/test/comparator resources explicitly')
    need(isinstance(value['obligations'], list) and value['obligations'], 'Declare at least one protected obligation')
    ids, cases = set(), set()
    for row in value['obligations']:
        need(isinstance(row, dict) and {'id', 'criterion', 'case', 'critical', 'sources', 'comparator'} <= set(row) <=
             {'id', 'criterion', 'case', 'critical', 'sources', 'comparator', 'contract'}, 'Unknown or missing obligation fields')
        need(text(row['id']) and row['id'] not in ids and text(row['case']), 'Unique obligation IDs and nonempty case IDs required')
        need(isinstance(row['criterion'], str) and row['criterion'] in criterion_ids, 'Obligation criterion is not declared')
        pair = (row['criterion'], row['case'])
        need(pair not in cases and type(row['critical']) is bool, 'Case binding must be unique and critical must be boolean')
        ids.add(row['id']); cases.add(pair)
        need(isinstance(row['sources'], list) and row['sources'] and len(set(row['sources'])) == len(row['sources']), 'Declare unique source dependencies')
        for path in row['sources']: relative(path)
        c = row['comparator']
        need(isinstance(c, dict) and c.get('kind') in ('status', 'exact', 'numeric', 'minimum', 'maximum'), 'Unknown comparator')
        keys = {'status': {'kind'}, 'exact': {'kind', 'expected'}, 'numeric': {'kind', 'expected', 'abs_tol', 'rel_tol'},
                'minimum': {'kind', 'expected'}, 'maximum': {'kind', 'expected'}}[c['kind']]
        need(set(c) == keys, 'Use explicit comparator fields; no implicit tolerances')
        if c['kind'] == 'numeric':
            for k in ('expected', 'abs_tol', 'rel_tol'):
                need(type(c[k]) in (int, float) and math.isfinite(c[k]), 'Numeric comparators require finite real values')
            need(c['abs_tol'] >= 0 and c['rel_tol'] >= 0, 'Tolerances cannot be negative')
        if c['kind'] in ('minimum','maximum'):
            need(type(c['expected']) in (int,float) and math.isfinite(c['expected']), 'Explicit finite metric bound required')
        if 'contract' in row:
            need(isinstance(row['contract'], dict), 'Metric/domain contract must be an object')
    need(isinstance(value['debt'], list), 'Debt must be explicit and separate from preserved passes')
    debt_ids = set()
    for row in value['debt']:
        need(isinstance(row, dict) and set(row) == {'id', 'reason', 'owner', 'expires'} and
             all(text(v) for v in row.values()) and row['id'] not in debt_ids, 'Debt requires unique ID, reason, owner and ISO expiry')
        try: date.fromisoformat(row['expires'])
        except ValueError: raise Invalid('Debt expiry must be an ISO date') from None
        debt_ids.add(row['id'])
    return value


STATES = {'pass', 'fail', 'error', 'timeout', 'skipped', 'xfail', 'xpass', 'missing', 'unsupported', 'inconclusive'}


def results(rows):
    need(isinstance(rows, list), 'Case results must be a list')
    canonical(rows)
    ids = set()
    for row in rows:
        need(isinstance(row, dict) and {'id', 'status'} <= set(row) <=
             {'id', 'status', 'raw_status', 'observed', 'contract'}, 'Unknown result fields')
        need(text(row['id']) and row['id'] not in ids and isinstance(row['status'], str) and row['status'] in STATES,
             'Unique case IDs and explicit result states required')
        ids.add(row['id'])
        if 'raw_status' in row: need(text(row['raw_status']), 'Raw status must be nonempty')
        if 'contract' in row: need(isinstance(row['contract'], dict), 'Case contract must be structured')
    return rows


def coverage(verified, total):
    return {'verified': verified, 'total': total, 'percent': 100 * verified / total if total else None}


def compare(reference, rows, criterion=None):
    # Reject malformed/nonfinite observed data as incomplete, never as a pass.
    try: results(rows)
    except Invalid as error:
        if 'finite' not in str(error): raise
        return {'passed': False, 'status': 'inconclusive', 'rows': [], 'coverage': coverage(0, len(reference['obligations'])),
                'critical': coverage(0, sum(r['critical'] for r in reference['obligations']))}
    actual = {row['id']: row for row in rows}
    output = []
    for obligation in reference['obligations']:
        if criterion is not None and obligation['criterion'] != criterion: continue
        got = actual.get(obligation['case'], {'status': 'missing'})
        status = got['status']
        if status == 'pass' and 'contract' in obligation and canonical(got.get('contract')) != canonical(obligation['contract']):
            status = 'incomparable'
        c = obligation['comparator']
        if status == 'pass' and c['kind'] == 'exact' and ('observed' not in got or canonical(got['observed']) != canonical(c['expected'])):
            status = 'fail'
        if status == 'pass' and c['kind'] == 'numeric':
            number = got.get('observed')
            if type(number) not in (int, float) or not math.isfinite(number): status = 'inconclusive'
            elif not math.isclose(number, c['expected'], rel_tol=c['rel_tol'], abs_tol=c['abs_tol']): status = 'fail'
        if status == 'pass' and c['kind'] in ('minimum','maximum'):
            number=got.get('observed')
            if type(number) not in (int,float) or not math.isfinite(number): status='inconclusive'
            elif (number<c['expected'] if c['kind']=='minimum' else number>c['expected']): status='fail'
        output.append({'id': obligation['id'], 'case': obligation['case'], 'criterion': obligation['criterion'],
                       'critical': obligation['critical'], 'status': status})
    critical = [r for r in output if r['critical']]
    passed = bool(output) and all(r['status'] == 'pass' for r in output)
    return {'passed': passed, 'status': 'preserved' if passed else 'not_preserved', 'rows': output,
            'coverage': coverage(sum(r['status'] == 'pass' for r in output), len(output)),
            'critical': coverage(sum(r['status'] == 'pass' for r in critical), len(critical)),
            'extra_cases': sorted(set(actual) - {r['case'] for r in output}), 'debt': reference['debt'],
            'semantic_truth_verified': False}


def affected(graph, changed):
    result = set(changed)
    while True:
        parents = {caller for caller, callees in graph.items() if set(callees) & result}
        if parents <= result: return result
        result |= parents
