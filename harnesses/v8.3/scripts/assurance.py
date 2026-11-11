"""Explicit finite verifier self-tests. No real project, approval, installation or publication."""
import argparse
import json
from pathlib import Path
import sys

import assurance_controls as controls
import assurance_faults as faults
import assurance_lifecycle as lifecycle
from assurance_fixture import SCRIPTS, sha

RUNNERS = {'controls': controls.run, 'lifecycle': lifecycle.run, 'persistence': faults.run}


def source_manifest():
    paths = sorted(SCRIPTS.glob('*.py'))
    if any(p.is_symlink() for p in paths): raise ValueError('Bundled source must be physical files')
    return {p.name: sha(p) for p in paths}


def _complete(report, seed, traces, steps):
    try:
        if report['suite'] == 'controls':
            return (report['positive_control']['id'] == 'healthy' and
                    {r['id'] for r in report['cases']} == set(controls.CONTROLS) and
                    len(report['cases']) == len(controls.CONTROLS))
        if report['suite'] == 'lifecycle':
            return (report['seed'] == seed and len(report['traces']) == traces and
                    report['executed_steps'] == traces * steps and
                    all(len(r['steps']) == steps for r in report['traces']))
        if report['suite'] == 'persistence':
            expected = {f'{o}:{s}:{m}' for o in faults.OPERATIONS for s in faults.STAGES for m in faults.MODES}
            return ({r['id'] for r in report['cases']} == expected and len(report['cases']) == len(expected)
                    and all(r['fault_reached'] for r in report['cases']))
    except (KeyError, TypeError):
        return False
    return False


def run(suite='all', seed=0, traces=2, steps=24):
    lifecycle.programs(seed, traces, steps)  # Validate bounds before starting any fixture or command.
    if suite not in ('all', *RUNNERS): raise ValueError('Unknown assurance suite')
    before = source_manifest()
    requested = list(RUNNERS) if suite == 'all' else [suite]
    reports = []
    for name in requested:
        try:
            report = RUNNERS[name](seed=seed, traces=traces, steps=steps) if name == 'lifecycle' else RUNNERS[name]()
        except Exception as error:
            report = {'suite': name, 'passed': False, 'error_type': type(error).__name__}
        reports.append(report)
    complete = len(reports) == len(requested) and bool(requested) and all(_complete(r, seed, traces, steps) for r in reports)
    unchanged = source_manifest() == before
    return {'format': 'verimission-assurance-v1', 'harness_version': '8.3', 'canonical_store': 'YAML',
            'configuration': {'suite': suite, 'seed': seed, 'traces': traces, 'steps': steps},
            'engine_sources_sha256': before, 'engine_sources_unchanged': unchanged, 'complete': complete,
            'passed': complete and unchanged and all(r.get('passed') is True for r in reports),
            'suites': reports, 'mission_acceptance': False, 'semantic_truth_verified': False,
            'global_mutation_score_claimed': False, 'exhaustive': False,
            'physical_power_loss_simulated': False, 'installed': False, 'published': False}


def receipt_destination(path):
    if path is None:return None
    try:
        target=path.resolve()
    except (OSError,RuntimeError) as error:
        raise ValueError('Receipt destination cannot be resolved safely') from error
    if (path.exists() or path.is_symlink() or not target.parent.is_dir() or
            any(x.casefold() in {'.harness','.git'} for item in (path,target) for x in item.parts)):
        raise ValueError('Receipt requires a new file outside protected state and an existing parent')
    return target


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite', choices=('all', 'controls', 'lifecycle', 'persistence'), default='all')
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--traces', type=int, default=2)
    parser.add_argument('--steps', type=int, default=24)
    parser.add_argument('--output', type=Path, help='New derived JSON receipt; never a canonical store')
    args = parser.parse_args(argv)
    try:
        lifecycle.programs(args.seed, args.traces, args.steps)
        target = receipt_destination(args.output)
        result = run(args.suite, args.seed, args.traces, args.steps)
        if target:
            with target.open('x', encoding='utf-8', newline='\n') as stream:
                stream.write(json.dumps(result, ensure_ascii=True, indent=2) + '\n')
            print(json.dumps({'passed': result['passed'], 'complete': result['complete'], 'receipt': str(target)}))
        else:
            print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0 if result['passed'] else 3
    except (OSError, ValueError) as error:
        print(json.dumps({'passed': False, 'error': type(error).__name__, 'detail': str(error)}))
        return 2


if __name__ == '__main__':
    sys.exit(main())
