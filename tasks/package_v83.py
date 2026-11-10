"""Synchronize development resources and build verifiable, uninstalled 8.3 archives."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

REPO = Path(__file__).resolve().parents[1]
HARNESS = REPO / 'harnesses/v8.3'
SKILL = REPO / 'skills/skill-harness-v8-3'
TEXT = {'.py', '.md', '.txt', '.json', '.yaml', '.yml', '.toml', '.csv'}


def files(root):
    return sorted(p for p in root.rglob('*') if p.is_file() and
                  '__pycache__' not in p.parts and p.suffix not in {'.pyc', '.pyo'} and
                  not any(x.startswith('.') for x in p.relative_to(root).parts))


def canonical(path):
    raw = path.read_bytes()
    return raw.decode('utf-8').replace('\r\n', '\n').encode('utf-8') if path.suffix in TEXT else raw


def sync():
    overview = (HARNESS / 'harness_v8.3.txt').read_text(encoding='utf-8').split('\n\n---\n\n', 1)[0]
    core = (HARNESS / 'CORE.md').read_text(encoding='utf-8')
    guide = (HARNESS / 'references/v82-periodic-review.md').read_text(encoding='utf-8') + '\n\n' + (HARNESS / 'references/v83-preservation.md').read_text(encoding='utf-8')
    combined = overview.rstrip() + '\n\n---\n\n' + core.rstrip() + '\n\n---\n\n' + guide.rstrip() + '\n'
    (HARNESS / 'harness_v8.3.txt').write_text(combined, encoding='utf-8', newline='\n')
    for folder in ('scripts', 'tests', 'references', 'examples'):
        for source in files(HARNESS / folder):
            target = SKILL / folder / source.relative_to(HARNESS / folder)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(canonical(source))
    for source in files(HARNESS / 'templates'):
        target = SKILL / 'assets/templates' / source.relative_to(HARNESS / 'templates')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(canonical(source))
    (SKILL / 'references/harness_v8.3.txt').write_text(combined, encoding='utf-8', newline='\n')
    (SKILL / 'requirements.txt').write_bytes(canonical(HARNESS / 'requirements.txt'))
    skill = SKILL / 'SKILL.md'
    head = skill.read_text(encoding='utf-8').split('# VeriMission Control 8.3 — core operating rules', 1)[0]
    skill.write_text(head + core, encoding='utf-8', newline='\n')
    for root in (HARNESS, SKILL):
        for path in files(root):
            if path.name != 'MANIFEST.json':
                path.write_bytes(canonical(path))
        entries = [{'path': p.relative_to(root).as_posix(), 'bytes': len(p.read_bytes()),
                    'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
                   for p in files(root) if p.name != 'MANIFEST.json']
        document = {'version': '8.3', 'canonical_text': 'UTF-8 LF', 'files': entries,
                    'manifest_excludes_itself': True}
        (root / 'MANIFEST.json').write_text(json.dumps(document, indent=2) + '\n', encoding='utf-8', newline='\n')
    for source in files(HARNESS / 'scripts'):
        assert source.read_bytes() == (SKILL / 'scripts' / source.name).read_bytes()


def archive(source, root_name, output):
    staged = output / root_name
    shutil.copytree(source, staged, ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.pyo'))
    destination = output / (('skill-harness-v8_2' if root_name.startswith('skill-') else root_name) + '.zip')
    with zipfile.ZipFile(destination, 'w', compression=zipfile.ZIP_DEFLATED) as package:
        for path in files(staged):
            info = zipfile.ZipInfo(root_name + '/' + path.relative_to(staged).as_posix(), (2026, 11, 8, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            package.writestr(info, path.read_bytes())
    with zipfile.ZipFile(destination) as package:
        manifest = json.loads(package.read(root_name + '/MANIFEST.json'))
        expected = {root_name + '/' + row['path'] for row in manifest['files']}
        assert set(package.namelist()) == expected | {root_name + '/MANIFEST.json'}
        for row in manifest['files']:
            data = package.read(root_name + '/' + row['path'])
            assert len(data) == row['bytes'] and hashlib.sha256(data).hexdigest() == row['sha256']
    return {'file': destination.name, 'files': len(manifest['files']),
            'sha256': hashlib.sha256(destination.read_bytes()).hexdigest(), 'manifest_verified': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='New, absent development-release directory; never an agent installation path')
    args = parser.parse_args()
    sync()
    if args.output:
        output = args.output.resolve()
        if output.exists():
            raise SystemExit('Choose a new output directory; existing artifacts are not overwritten')
        output.mkdir(parents=True)
        receipts = [archive(HARNESS, 'harness_v8.3', output), archive(SKILL, 'skill-harness-v8-3', output)]
        shutil.copyfile(HARNESS / 'harness_v8.3.txt', output / 'harness_v8.3.txt')
        (output / 'archive-verification.json').write_text(json.dumps(receipts, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(receipts))
    else:
        print(json.dumps({'resources_synchronized': True, 'installed': False}))


if __name__ == '__main__':
    main()
