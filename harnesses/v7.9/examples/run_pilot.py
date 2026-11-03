"""Run the Harness 7.9 lifecycle and the three new safeguards on a local fixture."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', required=True, help='New directory; existing data is never overwritten')
args = parser.parse_args()
project = Path(args.output).resolve()
project.mkdir(parents=True, exist_ok=False)
script = Path(__file__).resolve().parents[1] / 'scripts/harness.py'
trace = []


def invoke(command, *arguments, expected=0):
    proc = subprocess.run([sys.executable, str(script), '--project', str(project), command, *arguments], capture_output=True, text=True, timeout=30)
    data = json.loads(proc.stdout)
    trace.append({'command': command, 'exit_code': proc.returncode, 'response': data})
    assert proc.returncode == expected, (command, proc.returncode, data)
    return data.get('result', data)


def payload(name, data):
    target = project / name
    target.write_text(json.dumps(data, indent=2), encoding='utf-8')
    return str(target)


def plan(method):
    review = invoke('review', '--topic', 'total')['review']
    return payload('plan.json', {'topic': 'total', 'task': 'fix-total', 'premise': 'An extra unit is added',
                   'residual': 'The declared acceptance must pass for empty, positive and mixed inputs',
                   'review_id': review['id'], 'reviewed_claims': review['claims'], 'criteria': ['C1'],
                   'reference_review': 'Read expected sum semantics and the local function',
                   'simplest_test': 'Run the three exact assertions in acceptance.py',
                   'approach': {'method': method, 'inputs': 'calculator.py and three cases', 'environment': 'isolated local Python fixture'}})


(project / 'calculator.py').write_text('def total(values):\n    return sum(values) + 1\n', encoding='utf-8')
(project / 'acceptance.py').write_text("from calculator import total\nassert total([]) == 0\nassert total([1, 2, 3]) == 6\nassert total([-3, 3]) == 0\n", encoding='utf-8')
mission = {'objective': 'Correct an extra-unit bug in a local fixture', 'mode': 'strict',
           'in_scope': ['calculator.py'], 'out_of_scope': ['external services', 'production data'],
           'criteria': [{'id': 'C1', 'description': 'Three independent input classes produce exact sums',
                         'argv': [sys.executable, 'acceptance.py'], 'artifacts': ['calculator.py', 'acceptance.py']}],
           'budget': {'max_cycles': 6, 'max_check_seconds': 10}}
invoke('init', '--input', payload('mission.json', mission))
first = invoke('start', '--input', plan('Reproduce the original bug'))['cycle']
invoke('check', '--cycle', str(first), '--criterion', 'C1', expected=3)
invoke('close', '--cycle', str(first), '--outcome', 'verified', '--next', 'Incorrectly claiming completion', expected=2)
invoke('close', '--cycle', str(first), '--outcome', 'blocked', '--next', 'Remove the demonstrated extra unit')
(project / 'calculator.py').write_text('def total(values):\n    return sum(values)\n', encoding='utf-8')
second = invoke('start', '--input', plan('Test the minimal corrected implementation'))['cycle']
invoke('check', '--cycle', str(second), '--criterion', 'C1')
invoke('claim', '--input', payload('claim.json', {'id': 'total-three-cases', 'topic': 'total',
       'statement': 'The corrected function passes the three declared input classes', 'kind': 'fact',
       'cycle': second, 'criterion': 'C1', 'depends_on': []}))
invoke('close', '--cycle', str(second), '--outcome', 'verified', '--next', 'Acceptance achieved; no further task in this fixture')
# Every invocation is a separate process and has no access to any chat transcript.
recovered = invoke('resume')
assert recovered['recent_cycles'][-1]['status'] == 'verified'
assert recovered['claims']['total-three-cases']['status'] == 'verified'
invoke('validate')
invoke('backup', '--output', 'verified-state.yaml')
invoke('export', '--output', 'REPORT.md')
check_id = recovered['recent_cycles'][-1]['checks'][-1]['id']
scope = invoke('evidence-scope', '--input', payload('scope.json', {
    'cycle': second, 'check_id': check_id, 'method': 'dynamic', 'environment': 'isolated local Python',
    'verifies': ['The three declared sum assertions pass'], 'does_not_verify': ['Production or arbitrary numeric inputs'],
    'untested': ['Floating point and extreme values'],
    'coverage': [{'label': 'declared acceptance cases', 'numerator': 3, 'denominator': 3, 'unit': 'cases',
                  'universe': 'Only the three assertions in acceptance.py', 'exclusions': ['All other inputs']}]}))
assert not scope['semantic_truth_verified']
capsule = invoke('capsule', '--output', 'CAPSULE.json')
assert not capsule['authoritative'] and not capsule['mission_complete_asserted']
assert invoke('capsule-status', '--input', 'CAPSULE.json')['fresh']
before_prepare = (project / '.harness/state.yaml').read_bytes()
draft = invoke('prepare-mission', '--input', payload('request.json', mission), '--output', 'DRAFT.json')
assert draft['status'] == 'ready_for_review' and not draft['can_apply'] and not draft['task_plan_ready']
assert before_prepare == (project / '.harness/state.yaml').read_bytes()
assert invoke('capsule-status', '--input', 'CAPSULE.json')['fresh']
original_calculator = (project / 'calculator.py').read_bytes()
(project / 'calculator.py').write_bytes(original_calculator + b'\n# temporary drift fixture\n')
assert not invoke('capsule-status', '--input', 'CAPSULE.json', expected=3)['fresh']
(project / 'calculator.py').write_bytes(original_calculator)
assert invoke('capsule-status', '--input', 'CAPSULE.json')['fresh']
invoke('validate')
metrics = invoke('metrics')
assert metrics['checks_failed'] == 1 and metrics['checks_passed'] == 1
assert metrics['gate_refusals_recorded_by_cli'] >= 1
result = {'passed': True, 'project': str(project), 'scope': 'Local deterministic fixture, not a production project or model-behavior benchmark',
          'fresh_process_recovery': True, 'incorrect_completion_rejected': True, 'real_failed_and_passed_processes': True,
          'backup_integrity_checked': True, 'metrics': metrics}
result['v79_safeguards'] = {'scope_did_not_assert_semantic_truth': True, 'capsule_is_non_authoritative': True,
                            'artifact_drift_detected': True, 'draft_did_not_mutate_database': True,
                            'draft_did_not_authorize_or_execute_tasks': True}
(project / 'pilot-trace.json').write_text(json.dumps(trace, indent=2), encoding='utf-8')
(project / 'pilot-result.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result, indent=2))
