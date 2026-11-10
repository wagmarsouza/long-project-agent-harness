"""Disposable synthetic projects shared by explicit, finite assurance campaigns."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import uuid

SCRIPTS = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('verimission_assurance_engine', SCRIPTS / 'harness.py')
engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)

RUNNER = '''import json,os
from pathlib import Path
v=json.loads(Path('candidate.json').read_text(encoding='utf-8'))
r={'format':'verimission-results-v1','run_id':os.environ['VERIMISSION_RUN_ID'],
   'context_sha256':os.environ['VERIMISSION_CONTEXT_SHA256'],
   'complete':v.get('complete',True),'cases':v['cases']}
if v.get('old'): r['run_id']='deliberately-old-run'
with Path(os.environ['VERIMISSION_REPORT']).open('x',encoding='utf-8') as f: json.dump(r,f)
'''
EXPECTED = {'answer': 42, 'memory': [0, 0]}
CASE = 'retained-capability'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fresh_engine(root, nonce):
    """Worker access is limited to an identified, non-symlink synthetic temp workspace."""
    root = Path(root)
    if (root.is_symlink() or root.resolve() != root.absolute() or
            not root.name.startswith('verimission-assurance-') or
            not root.is_relative_to(Path(tempfile.gettempdir()).resolve())):
        raise ValueError('Only an owned synthetic temporary workspace is supported')
    marker = root / 'ASSURANCE_FIXTURE.json'
    if marker.is_symlink() or json.loads(marker.read_text(encoding='utf-8')) != {
            'format': 'verimission-assurance-fixture-v1', 'nonce': nonce}:
        raise ValueError('Synthetic workspace marker mismatch')
    return engine.Harness(root)


class Fixture:
    def __enter__(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='verimission-assurance-')
        self.root = Path(self.temporary.name).resolve()
        self.nonce = uuid.uuid4().hex
        (self.root / 'ASSURANCE_FIXTURE.json').write_text(json.dumps({
            'format': 'verimission-assurance-fixture-v1', 'nonce': self.nonce}), encoding='utf-8')
        (self.root / 'runner.py').write_text(RUNNER, encoding='utf-8')
        self.epoch = 0
        self.candidate()
        baseline = {'format': 'verimission-baseline-v1',
                    'reference': {'kind': 'specification', 'id': 'synthetic-assurance-contract-v1'},
                    'protected_files': {'runner.py': sha(self.root / 'runner.py')}, 'context_files': {},
                    'obligations': [{'id': 'PRESERVE', 'criterion': 'R', 'case': CASE, 'critical': True,
                                     'sources': ['candidate.json'],
                                     'comparator': {'kind': 'exact', 'expected': EXPECTED}}], 'debt': []}
        (self.root / 'baseline.json').write_text(json.dumps(baseline), encoding='utf-8')
        self.mission = {'objective': 'Exercise verifier controls on disposable synthetic data',
                        'mode': 'light', 'in_scope': ['synthetic fixture'], 'out_of_scope': ['real projects'],
                        'criteria': [{'id': 'R', 'description': 'Retain the synthetic observable',
                                      'argv': [sys.executable, 'runner.py'],
                                      'artifacts': ['runner.py', 'candidate.json']},
                                     {'id': 'OTHER', 'description': 'Not a protected criterion',
                                      'argv': [sys.executable, '-c', 'pass'], 'artifacts': []}],
                        'budget': {'max_cycles': 512, 'max_no_progress': 512, 'max_same_failures': 512,
                                   'consolidate_every': 512, 'max_check_seconds': 15},
                        'regression_policy': {'schema': 1,
                            'baseline': {'path': 'baseline.json', 'sha256': sha(self.root / 'baseline.json')},
                            'input_patterns': ['candidate.json', 'runner.py'],
                            'criteria': {'R': {'output_pattern': 'reports/{run}.json'}},
                            'mode': 'full', 'graph': {}, 'graph_complete': False, 'environment': []}}
        self.h = fresh_engine(self.root, self.nonce)
        self.h.init(self.mission)
        return self

    def __exit__(self, *args):
        self.temporary.cleanup()

    def candidate(self, good=True, **extra):
        self.epoch += 1
        observed = EXPECTED if good else {'answer': 42, 'memory': [0, 99]}
        value = {'epoch': self.epoch, 'cases': [{'id': CASE, 'status': 'pass', 'observed': observed}], **extra}
        (self.root / 'candidate.json').write_text(json.dumps(value), encoding='utf-8')

    def plan(self, criteria=None, reason=True):
        review = self.h.review('assurance')['review']
        plan = {'topic': 'assurance', 'task': 'synthetic-proof', 'premise': 'Preserve explicit observables',
                'residual': 'Check the current fixture', 'review_id': review['id'],
                'reviewed_claims': review['claims'], 'criteria': criteria or ['R'],
                'approach': {'method': 'finite-synthetic-replay', 'inputs': 'candidate.json',
                             'environment': 'disposable local workspace'}}
        if reason:
            plan['reverify_reason'] = 'Explicit bounded assurance revalidation; not new knowledge'
        return plan

    def start(self):
        return self.h.start(self.plan())['cycle']


def case_result(case_id, expected, observed, **details):
    return {'id': case_id, 'expected': expected, 'observed': observed,
            'passed': expected == observed, **details}
