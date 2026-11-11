"""Strict read-only preservation result readers; no commands from reports are executed."""
import importlib.util
from pathlib import Path
import xml.etree.ElementTree as ET

_spec = importlib.util.spec_from_file_location('regression_contract_readers', Path(__file__).with_name('regression_contract.py'))
c = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(c)


def neutral(raw, run_id, context_sha256):
    value = c.loads(raw)
    c.need(isinstance(value, dict) and set(value) == {'format', 'run_id', 'context_sha256', 'complete', 'cases'},
           'Use the exact verimission-results-v1 envelope')
    c.need(value['format'] == 'verimission-results-v1' and value['complete'] is True,
           'A complete current execution is required')
    c.need(value['run_id'] == run_id and value['context_sha256'] == context_sha256,
           'Report belongs to another execution/context')
    return c.results(value['cases'])


def junit(raw):
    try:
        text = raw.decode('utf-8-sig')
        c.need('\x00' not in text and '<!DOCTYPE' not in text.upper() and '<!ENTITY' not in text.upper(),
               'DTD, entities and non-UTF8 XML are refused')
        root = ET.fromstring(text)
    except (UnicodeError, ET.ParseError):
        raise c.Invalid('Malformed or incomplete JUnit XML') from None
    c.need(root.tag in {'testsuite', 'testsuites'}, 'Expected a JUnit testsuite root')
    for suite in root.iter():
        if suite.tag not in {'testsuite', 'testsuites'}: continue
        if 'tests' in suite.attrib:
            try: expected = int(suite.attrib['tests'])
            except ValueError: raise c.Invalid('Invalid JUnit test count') from None
            c.need(expected == len(list(suite.iter('testcase'))), 'Incomplete/inconsistent JUnit suite')
    rows = []
    for case in root.iter('testcase'):
        name, cls = case.get('name'), case.get('classname', '')
        c.need(c.text(name), 'JUnit case needs a stable name')
        state = 'pass'
        tags = [x.tag for x in case]
        statuses = [x for x in case if x.tag in {'failure', 'error', 'skipped'}]
        c.need(len(statuses) <= 1, 'Conflicting JUnit case outcomes')
        if 'failure' in tags: state = 'fail'
        elif 'error' in tags: state = 'error'
        elif 'skipped' in tags:
            state = 'xfail' if 'xfail' in statuses[0].get('type', '').lower() else 'skipped'
        elif case.get('status','').lower() in {'notrun','disabled','skipped'} or case.get('result','').lower() in {'suppressed','skipped'}:
            state = 'skipped'
        elif any(tag in tags for tag in ('flakyFailure','flakyError','rerunFailure','rerunError')):
            state = 'inconclusive'
        elif case.get('status','run').lower() not in {'run','passed','success','completed'} or case.get('result','completed').lower() not in {'completed','passed','success'}:
            state = 'inconclusive'
        rows.append({'id': (cls + '.' if cls else '') + name, 'status': state,
                     'raw_status': 'junit:' + (statuses[0].get('type', statuses[0].tag) if statuses else state)})
    c.need(rows, 'An empty report does not demonstrate preservation')
    return c.results(rows)


def metric(value):
    """Preserve source formulas and universes; this is not a quality certification."""
    c.canonical(value)
    c.need(isinstance(value, dict) and value.get('kind') in {'coverage', 'mutation'}, 'Unknown metric kind')
    if value['kind'] == 'coverage':
        c.need(set(value) == {'kind', 'numerator', 'denominator', 'excluded', 'scope'}, 'Explicit coverage universe required')
        numerator, denominator = value['numerator'], value['denominator']
        c.need(type(numerator) is int and type(denominator) is int and 0 <= numerator <= denominator,
               'Invalid coverage counts')
    else:
        c.need(set(value) == {'kind', 'states', 'formula', 'excluded', 'scope'} and
               value['formula'] == 'stryker-detected-over-valid', 'Keep the original mutation formula explicit')
        states = value['states']
        allowed = {'Killed', 'Timeout', 'Survived', 'NoCoverage', 'CompileError', 'RuntimeError', 'Ignored', 'Pending'}
        c.need(isinstance(states, dict) and set(states) <= allowed and
               all(type(v) is int and v >= 0 for v in states.values()), 'Invalid mutation states/counts')
        numerator = states.get('Killed', 0) + states.get('Timeout', 0)
        denominator = numerator + states.get('Survived', 0) + states.get('NoCoverage', 0)
    c.need(all(isinstance(value[k], list) and all(c.text(x) for x in value[k]) for k in ('excluded', 'scope')),
           'Explicit metric scope and exclusions required')
    return {**value, 'numerator': numerator, 'denominator': denominator,
            'percent': 100 * numerator / denominator if denominator else None, 'semantic_truth_verified': False}
