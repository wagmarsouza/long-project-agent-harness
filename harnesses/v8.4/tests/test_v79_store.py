import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


old = load('actual_v79_store', ROOT / 'tests/fixtures/harness_v79.py')
new = load('current_v80_store', ROOT / 'scripts/harness.py')


class V79StoreTests(unittest.TestCase):
    def test_real_v79_database_migrates_without_contract_changes(self):
        with tempfile.TemporaryDirectory(prefix='v79-to-v80-') as folder:
            root = Path(folder)
            (root / 'result.txt').write_text('correct', encoding='utf-8')
            legacy = old.Harness(root)
            legacy.init({'objective': 'Legacy declared acceptance', 'mode': 'light', 'in_scope': ['result.txt'], 'out_of_scope': [],
                         'criteria': [{'id': 'C1', 'description': 'Local fixture', 'argv': [sys.executable, '-c',
                                       "from pathlib import Path; assert Path('result.txt').read_text() == 'correct'"], 'artifacts': ['result.txt']}]})
            before = legacy.db.read_bytes()
            current = new.Harness(root)
            migration = current.migrate_sqlite()
            self.assertTrue(current.validate()['passed'])
            self.assertEqual(current.traceability()['requirements_source'], 'legacy_criterion_projection')
            current.search('legacy')
            current.capsule()
            self.assertEqual(legacy.db.read_bytes(), before)
            self.assertEqual(migration['canonical_store'], '.harness/state.yaml')
            old_hash = legacy.resume()['mission_hash']
            current.alias_add({'alias': 'fixture', 'topic': 'legacy'})
            self.assertEqual(current.resume()['mission_hash'], old_hash)
            self.assertFalse(current.accept_mission()['accepted'])


if __name__ == '__main__':
    unittest.main()
