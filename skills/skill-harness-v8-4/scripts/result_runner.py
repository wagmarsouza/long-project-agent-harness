"""Finite, explicit unittest/JUnit runner producing a fresh bound neutral result file."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

from result_readers import junit


class Recorded(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cases = {}

    def record(self, test, status):
        self.cases[test.id()] = {'id': test.id(), 'status': status, 'raw_status': 'unittest:' + status}

    def addSuccess(self, test):
        super().addSuccess(test)
        if test.id() not in self.cases: self.record(test, 'pass')

    def addFailure(self, test, err):
        super().addFailure(test, err); self.record(test, 'fail')

    def addError(self, test, err):
        super().addError(test, err); self.record(test, 'error')

    def addSkip(self, test, reason):
        super().addSkip(test, reason); self.record(test, 'skipped')

    def addExpectedFailure(self, test, err):
        super().addExpectedFailure(test, err); self.record(test, 'xfail')

    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test); self.record(test, 'xpass')

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        if err is not None: self.record(test, 'fail')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='kind', required=True)
    u = commands.add_parser('unittest')
    u.add_argument('--start', required=True); u.add_argument('--pattern', default='test*.py')
    j = commands.add_parser('junit')
    j.add_argument('--source', required=True)
    j.add_argument('argv', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    output = Path(os.environ['VERIMISSION_REPORT'])
    # Exclusive creation first means a rerun cannot overwrite previously recorded evidence.
    with output.open('x', encoding='utf-8', newline='\n') as stream:
        envelope = {'format': 'verimission-results-v1', 'run_id': os.environ['VERIMISSION_RUN_ID'],
                    'context_sha256': os.environ['VERIMISSION_CONTEXT_SHA256'], 'complete': False, 'cases': []}
        code = 2
        try:
            if args.kind == 'unittest':
                sys.path.insert(0, str(Path(args.start).resolve()))
                suite = unittest.defaultTestLoader.discover(args.start, args.pattern)
                result = unittest.TextTestRunner(resultclass=Recorded).run(suite)
                envelope['cases'] = list(result.cases.values())
                envelope['complete'] = result.testsRun == len(result.cases) and not result.shouldStop
                code = 0 if result.wasSuccessful() and result.testsRun else 1
            else:
                source = Path(args.source).resolve()
                if not source.is_relative_to(Path.cwd().resolve()) or source.exists():
                    raise ValueError('JUnit raw source must be a NEW file inside the project')
                argv = args.argv[1:] if args.argv[:1] == ['--'] else args.argv
                if not argv: raise ValueError('Explicit test argv required')
                code = subprocess.run(argv, shell=False, timeout=max(0.1, float(os.environ.get('VERIMISSION_TIMEOUT', '60')) - 1)).returncode
                envelope['cases'] = junit(source.read_bytes())
                envelope['complete'] = True
        finally:
            json.dump(envelope, stream, sort_keys=True, allow_nan=False)
            stream.write('\n')
    return code


if __name__ == '__main__':
    try: sys.exit(main())
    except (KeyError, ValueError, OSError, subprocess.TimeoutExpired) as error:
        print(type(error).__name__ + ': result execution incomplete', file=sys.stderr)
        sys.exit(2)
