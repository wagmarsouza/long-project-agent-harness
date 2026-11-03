"""Synthetic file/observation pilot, optionally with a separately supplied V8 CLI."""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

SKILL = Path(__file__).resolve().parents[1]
SCRIPT = SKILL / 'scripts/binary_profile.py'
spec = importlib.util.spec_from_file_location('binary_profile_pilot', SCRIPT)
profile = importlib.util.module_from_spec(spec)
spec.loader.exec_module(profile)


def save(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=True, indent=2), encoding='utf-8')


def call(script, root, *argv, expected=0):
    run = subprocess.run([sys.executable, '-B', str(script), '--project', str(root), *argv],
                         cwd=root, capture_output=True, text=True, timeout=60)
    if run.returncode != expected:
        raise RuntimeError(f'Unexpected exit {run.returncode}: {run.stdout} {run.stderr}')
    return json.loads(run.stdout)


def run(harness=None):
    with tempfile.TemporaryDirectory(prefix='binary-profile-pilot-') as folder:
        root = Path(folder).resolve()
        (root / 'tools').mkdir()
        local = root / 'tools/binary_profile.py'
        shutil.copyfile(SCRIPT, local)
        raw = bytes(range(32))
        (root / 'image.bin').write_bytes(raw)
        sha = hashlib.sha256(raw).hexdigest()
        target = {'format': 'binary-target-v1', 'binary': 'image.bin', 'sha256': sha,
                  'architecture': 'synthetic-declaration-only', 'endianness': 'little', 'address_unit_bytes': 1,
                  'segments': [{'id': 'text', 'address_space': 'main', 'file_offset': 0, 'size': 32, 'virtual_base': 4096}],
                  'analysis_configuration': {'tool': 'synthetic-fixture-producer', 'version': '1', 'settings': {}}}
        unit = {'format': 'binary-unit-v1', 'id': 'U1', 'target_sha256': sha, 'segment': 'text',
                'file_offset': 4, 'size': 4, 'virtual_address': 4100, 'isa_mode': 'fixture', 'classification': 'unknown'}
        save(root / 'target.json', target)
        save(root / 'unit.json', unit)
        checked = profile.validate_unit(root, target, unit)

        def case(name, n):
            inp, log = root / (name + '-input.json'), root / (name + '.log')
            save(inp, {'n': n})
            log.write_text('SYNTHETIC fixture only: n=' + str(n), encoding='utf-8')
            def ref(p):
                return {'path': p.name, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
            return {'id': name, 'purpose': 'Synthetic equality fixture ' + name, 'inputs': [ref(inp)], 'log': ref(log),
                    'completed': True, 'expected': {'n': n}, 'observed': {'n': n}}

        report = {key: checked[key] for key in ('target_sha256', 'unit_sha256', 'target_manifest_sha256', 'unit_manifest_sha256')}
        report.update({'format': 'binary-witness-report-v1', 'unit_id': 'U1', 'method': 'synthetic_fixture',
                       'environment': 'No target, emulator, disassembler or hardware executed',
                       'execution_reference': 'This synthetic pilot generated all fixture observations',
                       'injections': ['All observations are supplied synthetic data'],
                       'limitations': ['No binary semantics or hardware behavior established'],
                       'positive_control': case('CTRL', 10), 'cases': [case('W1', 1), case('W2', 2)]})
        save(root / 'witnesses.json', report)
        args = {
            'ID': ['target', '--input', 'target.json'],
            'UNIT': ['unit', '--target', 'target.json', '--input', 'unit.json'],
            'REPORT': ['witnesses', '--target', 'target.json', '--unit', 'unit.json', '--input', 'witnesses.json']}
        before = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file()}
        for argv in args.values():
            assert call(local, root, *argv)['result']['passed']
        assert before == {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file()}

        # Deliberate negatives in independent synthetic reports; original fixtures preserved.
        bad = copy.deepcopy(report)
        bad['cases'][0]['observed'] = {'n': 999}
        save(root / 'mismatch.json', bad)
        result = call(local, root, *args['REPORT'][:-1], 'mismatch.json', expected=3)
        assert result['result']['passed'] is False
        bad['cases'][0]['expected'] = {}
        save(root / 'no-expectation.json', bad)
        assert call(local, root, *args['REPORT'][:-1], 'no-expectation.json', expected=2)['code'] == 'EXPECTATION'

        integration = {'executed': False}
        if harness:
            harness = Path(harness).resolve(strict=True)
            external_before = {p: p.read_bytes() for p in harness.parent.glob('*.py')}
            artifacts = sorted(before)
            mission = {'objective': 'Synthetic identity/mapping/report consistency only; no binary semantics',
                       'mode': 'light', 'in_scope': ['synthetic fixtures'], 'out_of_scope': ['target execution', 'hardware', 'semantic conclusions'],
                       'criteria': [{'id': cid, 'description': 'Synthetic declared consistency: ' + cid,
                                     'argv': [sys.executable, '-B', str(local), '--project', str(root), *argv],
                                     'artifacts': artifacts} for cid, argv in args.items()]}
            save(root / 'mission.json', mission)
            call(harness, root, 'init', '--input', 'mission.json')
            review = call(harness, root, 'review', '--topic', 'synthetic-binary-unit')['result']['review']
            plan = {'topic': 'synthetic-binary-unit', 'task': 'verify-fixtures',
                    'premise': 'Declared synthetic consistency can be checked without mutating fixtures',
                    'residual': 'No semantic behavior has been tested', 'review_id': review['id'],
                    'reviewed_claims': review['claims'], 'criteria': list(args),
                    'approach': {'method': 'Read-only hash, map and JSON comparison',
                                 'inputs': 'Synthetic byte image and reports', 'environment': 'Temporary local directory'}}
            save(root / 'plan.json', plan)
            cycle = call(harness, root, 'start', '--input', 'plan.json')['result']['cycle']
            for cid in args:
                assert call(harness, root, 'check', '--cycle', str(cycle), '--criterion', cid)['result']['passed']
            call(harness, root, 'close', '--cycle', str(cycle), '--outcome', 'verified',
                 '--next', 'Synthetic pilot only; real-target mission remains untested')
            call(harness, root, 'validate')
            acceptance = call(harness, root, 'accept-mission')['result']
            for relative, data in before.items():
                assert (root / relative).read_bytes() == data
            assert external_before == {p: p.read_bytes() for p in harness.parent.glob('*.py')}
            integration = {'executed': True, 'criteria_checked': len(args), 'acceptance': acceptance}

        return {'passed': True, 'positive_cli_checks': len(args), 'negative_cli_checks': 2,
                'read_only_checks_preserved_files': True, 'v8_integration': integration,
                'scope': 'Synthetic fixtures only', 'real_target_execution': False,
                'disassembler_validation': False, 'hardware_validation': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--harness', help='Optional V8.0 harness.py path, with its sibling modules intact')
    options = parser.parse_args()
    print(json.dumps(run(options.harness), ensure_ascii=True, indent=2))
