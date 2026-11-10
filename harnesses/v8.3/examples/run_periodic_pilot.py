"""Synthetic general-project pilot; no agent, service, repository or domain plugin."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/harness.py'
spec = importlib.util.spec_from_file_location('periodic_pilot82', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def main():
    with tempfile.TemporaryDirectory(prefix='verimission-general-pilot-') as temporary:
        root = Path(temporary)
        (root / 'notes').mkdir()
        (root / 'proof.txt').write_text('ok', encoding='utf-8')
        (root / 'governing.md').write_text('EVIDENCE_FIRST: do not weaken acceptance.\n'
            '<!-- objectives -->\nCheck a bounded fixture.\n<!-- /objectives -->\n'
            '<!-- scenario -->\nGeneral project; no domain dependency.\n<!-- /scenario -->\n', encoding='utf-8')
        h = module.Harness(root)
        h.init({'objective': 'Verify three bounded conditions, without claiming whole-project correctness', 'mode': 'light',
                'in_scope': ['local synthetic fixtures'], 'out_of_scope': ['external effects', 'installations'],
                'criteria': [{'id': 'C1', 'description': 'Exact fixture', 'argv': [sys.executable, '-c',
                             "from pathlib import Path; assert Path('proof.txt').read_text() == 'ok'"], 'artifacts': ['proof.txt']}],
                'budget': {'consolidate_every': 3},
                'periodic_review': {'notes_pattern': 'notes/cycle-{cycle}.md', 'digest_pattern': 'digest-{start}-{end}.json',
                    'governing_file': 'governing.md', 'invariant_markers': ['EVIDENCE_FIRST'],
                    'mutable_sections': {'objectives': {'begin': '<!-- objectives -->', 'end': '<!-- /objectives -->'},
                                         'scenario': {'begin': '<!-- scenario -->', 'end': '<!-- /scenario -->'}}}})
        with h.state() as state:
            original_mission = state['mission_hash']
        blocked = False
        for cid in (1, 2, 3):
            review = h.review('delivery')['review']
            started = h.start({'topic': 'delivery', 'task': 'bounded-fixture', 'premise': 'fixture matches',
                'residual': 'execute the declared check', 'review_id': review['id'], 'reviewed_claims': [], 'criteria': ['C1'],
                'reverify_reason': 'Explicit bounded regression, not a new discovery',
                'approach': {'method': 'exact check', 'inputs': 'proof.txt', 'environment': 'local'}})
            assert started['cycle'] == cid
            (root / 'notes' / f'cycle-{cid}.md').write_text(f'Cycle {cid}: the fixture check is bounded; no population-wide or full-mission correctness established.\n', encoding='utf-8')
            assert h.check(cid, 'C1')['passed']
            if cid < 3:
                h.close(cid, 'verified', 'Next bounded condition')
            else:
                try:
                    h.close(cid, 'verified', 'Next reviewed objective')
                except module.Refusal as error:
                    assert error.code == 'PERIODIC_REVIEW_REQUIRED'
                    blocked = True
        digest = h.digest(3)
        proposal = digest['review_template']
        proposal['reason'] = 'Synthetic reread fixture: retain the bounded objective and explicit limitations.'
        for row in proposal['reread']:
            # Actually read the physical file; the declaration remains synthetic,
            # not a claim that a person or model semantically understood it.
            data = (root / 'notes' / f"cycle-{row['cycle']}.md").read_bytes()
            assert hashlib.sha256(data).hexdigest() == row['sha256']
            row['finding'] = data.decode('utf-8').strip()
        result = h.close(3, 'verified', 'Continue only within approved scope', review_input=proposal)
        audit = h.validate()
        with h.state() as state:
            assert state['consolidations'][-1]['through_cycle'] == 3
            assert state['mission_hash'] == original_mission
            print(json.dumps({'blocked_without_reread': blocked, 'window': digest['window'], 'closed': result['status'],
                              'consolidated_through': 3, 'audit_passed': audit['passed'], 'domain_plugin_required': False,
                              'semantic_correctness_verified': False, 'skill_installed': False,
                              'mission_hash': state['mission_hash']}, indent=2))
        assert audit['passed']


if __name__ == '__main__':
    main()
