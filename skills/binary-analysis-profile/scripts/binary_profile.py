"""Read-only integrity and declared-observation checks; no target execution."""
import argparse
import hashlib
import json
from pathlib import Path, PureWindowsPath
import sys


class ProfileError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def require(condition, code, message):
    if not condition:
        raise ProfileError(code, message)


def text(value):
    return isinstance(value, str) and bool(value.strip())


def integer(value, minimum=0):
    return type(value) is int and value >= minimum


def digest(data):
    return hashlib.sha256(data).hexdigest()


def manifest_digest(value):
    return digest(json.dumps(value, sort_keys=True, separators=(',', ':'),
                             ensure_ascii=False, allow_nan=False).encode('utf-8'))


def project_file(root, value):
    require(text(value), 'PATH', 'A project-relative file path is required')
    portable = value.replace('\\', '/')
    path = Path(portable)
    win = PureWindowsPath(value)
    require(not path.is_absolute() and not win.drive and not win.root,
            'PATH', 'Absolute paths are not evidence references')
    require('..' not in path.parts and ':' not in portable,
            'PATH', 'Parent traversal and alternate streams are refused')
    base = Path(root).resolve()
    resolved = (base / path).resolve()
    require(resolved.is_relative_to(base), 'PATH', 'File resolves outside the project')
    relative = resolved.relative_to(base)
    require(not any(p.casefold() == '.harness' for p in (*path.parts, *relative.parts)),
            'PATH', 'Harness state is not analysis evidence')
    require(resolved.is_file(), 'PATH', 'Referenced file is missing')
    return resolved


def reference(root, ref):
    require(isinstance(ref, dict), 'REPORT', 'File reference must be an object')
    data = project_file(root, ref.get('path')).read_bytes()
    actual = digest(data)
    require(ref.get('sha256') == actual, 'IDENTITY', 'Referenced file hash differs')
    return actual


def target_snapshot(root, target):
    require(isinstance(target, dict) and target.get('format') == 'binary-target-v1',
            'TARGET', 'Expected binary-target-v1')
    data = project_file(root, target.get('binary')).read_bytes()
    sha = digest(data)
    require(target.get('sha256') == sha, 'IDENTITY', 'Binary hash differs')
    require(text(target.get('architecture')), 'TARGET', 'Declare architecture, including unknown if necessary')
    require(target.get('endianness') in ('little', 'big', 'mixed', 'unknown'), 'TARGET', 'Invalid endianness')
    scale = target.get('address_unit_bytes')
    require(integer(scale, 1), 'TARGET', 'Address unit must be a positive byte count')
    config = target.get('analysis_configuration')
    require(isinstance(config, dict) and text(config.get('tool')) and text(config.get('version'))
            and isinstance(config.get('settings'), dict), 'TARGET', 'Declare tool, version and settings')
    segments = target.get('segments')
    require(isinstance(segments, list) and bool(segments), 'SEGMENT', 'Declare at least one mapped segment')
    ids = set()
    for s in segments:
        require(isinstance(s, dict) and text(s.get('id')) and s['id'] not in ids
                and text(s.get('address_space')), 'SEGMENT', 'Segment IDs must be unique; space is required')
        ids.add(s['id'])
        require(integer(s.get('file_offset')) and integer(s.get('size'), 1)
                and integer(s.get('virtual_base')), 'SEGMENT', 'Invalid segment interval')
        require(s['file_offset'] + s['size'] <= len(data) and s['size'] % scale == 0,
                'SEGMENT', 'Segment exceeds file or has partial address units')
    def overlaps(a, an, b, bn):
        return a < b + bn and b < a + an
    for i, a in enumerate(segments):
        for b in segments[i + 1:]:
            if a['address_space'] != b['address_space']:
                continue
            require(not overlaps(a['file_offset'], a['size'], b['file_offset'], b['size'])
                    and not overlaps(a['virtual_base'], a['size'] // scale,
                                     b['virtual_base'], b['size'] // scale),
                    'SEGMENT', 'Overlays require explicitly different address spaces')
    result = {'passed': True, 'sha256': sha, 'size_bytes': len(data),
              'segments': len(segments), 'architecture_authenticated': False,
              'address_map_authenticated': False, 'semantic_truth_verified': False,
              'target_manifest_sha256': manifest_digest(target),
              'configuration_sha256': manifest_digest(config)}
    return result, data


def validate_target(root, target):
    return target_snapshot(root, target)[0]


def validate_unit(root, target, unit):
    checked, data = target_snapshot(root, target)
    require(isinstance(unit, dict) and unit.get('format') == 'binary-unit-v1', 'UNIT', 'Expected binary-unit-v1')
    require(unit.get('target_sha256') == checked['sha256'], 'IDENTITY', 'Unit belongs to another binary')
    require(text(unit.get('id')) and text(unit.get('isa_mode')), 'UNIT', 'Declare ID and ISA mode')
    require(unit.get('classification') in ('unknown', 'candidate_function', 'candidate_data', 'mixed_region'),
            'UNIT', 'Unit classification must remain a candidate, not a proof')
    segment = next((s for s in target['segments'] if s['id'] == unit.get('segment')), None)
    require(segment is not None, 'ADDRESS', 'Unknown mapped segment')
    offset, size, scale = unit.get('file_offset'), unit.get('size'), target['address_unit_bytes']
    require(integer(offset) and integer(size, 1), 'ADDRESS', 'Invalid unit byte interval')
    delta = offset - segment['file_offset']
    require(delta >= 0 and delta + size <= segment['size'] and delta % scale == 0 and size % scale == 0,
            'ADDRESS', 'Unit is outside segment or not aligned to address units')
    address = segment['virtual_base'] + delta // scale
    require(type(unit.get('virtual_address')) is int and unit['virtual_address'] == address,
            'ADDRESS', 'File offset and declared virtual address disagree')
    return {'passed': True, 'id': unit['id'], 'target_sha256': checked['sha256'],
            'unit_sha256': digest(data[offset:offset + size]), 'virtual_address': address,
            'identity': {'binary_sha256': checked['sha256'], 'segment': segment['id'],
                         'address_space': segment['address_space'], 'file_offset': offset,
                         'size': size, 'isa_mode': unit['isa_mode']},
            'configuration_sha256': checked['configuration_sha256'],
            'target_manifest_sha256': checked['target_manifest_sha256'],
            'unit_manifest_sha256': manifest_digest(unit),
            'function_boundary_proven': False, 'semantic_truth_verified': False}


def witness_case(root, case):
    require(isinstance(case, dict) and text(case.get('id')) and text(case.get('purpose')),
            'REPORT', 'Witness needs ID and purpose')
    expected, observed = case.get('expected'), case.get('observed')
    require(isinstance(expected, dict) and bool(expected), 'EXPECTATION', 'Explicit nonempty expectations required')
    require(isinstance(observed, dict) and type(case.get('completed')) is bool,
            'REPORT', 'Observed mapping and boolean completion required')
    inputs = case.get('inputs')
    require(isinstance(inputs, list) and bool(inputs), 'WITNESS', 'Witness inputs required')
    signature = tuple(sorted({reference(root, ref) for ref in inputs}))
    reference(root, case.get('log'))
    # JSON strict equality: booleans must not silently equal numbers, nor 1 equal 1.0.
    def equal(a, b):
        return json.dumps(a, sort_keys=True, separators=(',', ':')) == json.dumps(b, sort_keys=True, separators=(',', ':'))
    differences = [key for key, value in expected.items() if key not in observed or not equal(value, observed[key])]
    return {'id': case['id'], 'passed': case['completed'] and not differences,
            'completed': case['completed'], 'mismatched_or_missing_keys': differences}, signature


def validate_witnesses(root, target, unit, report):
    checked = validate_unit(root, target, unit)
    require(isinstance(report, dict) and report.get('format') == 'binary-witness-report-v1',
            'REPORT', 'Expected binary-witness-report-v1')
    require(report.get('target_sha256') == checked['target_sha256'] and report.get('unit_id') == unit['id']
            and report.get('unit_sha256') == checked['unit_sha256'], 'IDENTITY', 'Report target or unit differs')
    require(report.get('target_manifest_sha256') == checked['target_manifest_sha256']
            and report.get('unit_manifest_sha256') == checked['unit_manifest_sha256'],
            'IDENTITY', 'Report manifests or analysis configuration differ')
    require(report.get('method') in ('isolated_function', 'boot_trace', 'emulated_integration',
                                    'hardware_observation', 'synthetic_fixture'), 'REPORT', 'Declare observation method')
    require(all(text(report.get(key)) for key in ('environment', 'execution_reference')),
            'REPORT', 'Execution reference and environment required')
    for key in ('injections', 'limitations'):
        require(isinstance(report.get(key), list) and all(text(s) for s in report[key]),
                'REPORT', 'Explicit injections and limitations lists required; use [] only if reviewed and none')
    control, _ = witness_case(root, report.get('positive_control'))
    cases = report.get('cases')
    require(isinstance(cases, list) and len(cases) >= 2, 'WITNESS', 'At least two contrasting witnesses required')
    rows, signatures, ids = [], set(), {control['id']}
    for case in cases:
        result, signature = witness_case(root, case)
        require(result['id'] not in ids, 'WITNESS', 'Witness IDs must be unique')
        require(signature not in signatures, 'WITNESS', 'Duplicate input content is not a distinct witness')
        ids.add(result['id'])
        signatures.add(signature)
        rows.append(result)
    return {'passed': control['passed'] and all(row['passed'] for row in rows),
            'positive_control': control, 'cases': rows, 'cases_checked': len(rows),
            'scope': 'File integrity and equality of declared expectations/observations only',
            'execution_authenticated': False, 'semantic_truth_verified': False,
            'hardware_validation_established': False, 'promotion_authorized': False}


def load_json(path):
    def unique(pairs):
        obj = {}
        for key, value in pairs:
            require(key not in obj, 'JSON', 'Duplicate JSON keys refused')
            obj[key] = value
        return obj
    def nonfinite(value):
        raise ProfileError('JSON', 'Nonfinite JSON numbers refused')
    return json.loads(Path(path).read_text(encoding='utf-8-sig'), object_pairs_hook=unique, parse_constant=nonfinite)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True)
    sub = parser.add_subparsers(dest='command', required=True)
    inspect = sub.add_parser('inspect', help='Fingerprint a binary; does not detect architecture')
    inspect.add_argument('--binary', required=True)
    for command in ('target', 'unit', 'witnesses'):
        p = sub.add_parser(command)
        p.add_argument('--input', required=True, help='Manifest/report JSON (explicit path)')
        if command != 'target':
            p.add_argument('--target', required=True)
        if command == 'witnesses':
            p.add_argument('--unit', required=True)
    args = parser.parse_args()
    try:
        root = Path(args.project).resolve()
        require(root.is_dir(), 'PATH', 'Project root is missing')
        if args.command == 'inspect':
            data = project_file(root, args.binary).read_bytes()
            result = {'passed': True, 'sha256': digest(data), 'size_bytes': len(data),
                      'architecture_authenticated': False}
        else:
            payload = load_json(args.input)
            if args.command == 'target':
                result = validate_target(root, payload)
            elif args.command == 'unit':
                result = validate_unit(root, load_json(args.target), payload)
            else:
                result = validate_witnesses(root, load_json(args.target), load_json(args.unit), payload)
        print(json.dumps({'ok': True, 'result': result}, ensure_ascii=True))
        return 0 if result['passed'] else 3
    except (ProfileError, OSError, ValueError, RecursionError) as error:
        code = error.code if isinstance(error, ProfileError) else 'INPUT'
        print(json.dumps({'ok': False, 'code': code, 'error': str(error)}, ensure_ascii=True))
        return 2


if __name__ == '__main__':
    sys.exit(main())
