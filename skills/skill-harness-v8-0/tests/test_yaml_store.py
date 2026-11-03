"""YAML storage, migration, integrity and crash-safety contracts."""
import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import yaml

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/harness.py'
spec = importlib.util.spec_from_file_location('yaml_harness', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class YAMLStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='harness-yaml-')
        self.root = Path(self.temp.name)
        (self.root / 'result.txt').write_text('correct', encoding='utf-8')
        self.mission = {'objective': 'Check YAML migration', 'mode': 'light',
                        'in_scope': ['result.txt'], 'out_of_scope': [],
                        'criteria': [{'id': 'C1', 'description': 'Result exists',
                                      'argv': ['python', '-c', 'pass'], 'artifacts': ['result.txt']}]}

    def tearDown(self):
        self.temp.cleanup()

    def legacy_store(self):
        folder = self.root / '.harness'
        folder.mkdir()
        path = folder / 'state.sqlite'
        state = {'schema': 1, 'version': '7.8', 'created': 'fixture', 'revision': 4,
                 'mission': self.mission, 'mission_hash': module.digest(self.mission),
                 'cycles': [], 'claims': {}, 'reviews': {}, 'stepbacks': [], 'consolidations': []}
        connection = sqlite3.connect(path)
        connection.execute('CREATE TABLE state(id INTEGER PRIMARY KEY CHECK(id=1),body TEXT NOT NULL)')
        connection.execute('CREATE TABLE audit(id INTEGER PRIMARY KEY,at TEXT,revision INTEGER,kind TEXT)')
        connection.execute('INSERT INTO state VALUES(1,?)', (json.dumps(state),))
        connection.execute('INSERT INTO audit VALUES(1,?,?,?)', ('fixture', 4, 'state-update'))
        connection.commit()
        connection.close()
        return path, state

    def test_init_creates_yaml_with_integrity_envelope(self):
        harness = module.Harness(self.root)
        harness.init(self.mission)
        document = yaml.safe_load((self.root / '.harness/state.yaml').read_text(encoding='utf-8'))
        self.assertEqual(document['format'], 'verimission-yaml-store')
        self.assertEqual(document['storage_schema'], 1)
        self.assertEqual(document['state']['mission']['objective'], 'Check YAML migration')
        self.assertTrue(harness.validate()['passed'])

    def test_legacy_requires_explicit_migration_and_is_preserved(self):
        legacy, expected = self.legacy_store()
        original = legacy.read_bytes()
        harness = module.Harness(self.root)
        with self.assertRaises(module.Refusal) as caught:
            harness.init(self.mission)
        self.assertEqual(caught.exception.code, 'MIGRATION_REQUIRED')
        result = harness.migrate_sqlite()
        self.assertTrue(result['migrated'])
        self.assertEqual(legacy.read_bytes(), original)
        with harness.state() as state:
            self.assertEqual(state, expected)
        document = yaml.safe_load(harness.db.read_text(encoding='utf-8'))
        self.assertTrue(document['migration']['source_preserved'])
        self.assertEqual(document['migration']['audit_records'], 1)

    def test_checksum_detects_manual_tampering(self):
        harness = module.Harness(self.root)
        harness.init(self.mission)
        document = yaml.safe_load(harness.db.read_text(encoding='utf-8'))
        document['state']['mission']['objective'] = 'tampered'
        harness.db.write_text(yaml.safe_dump(document, sort_keys=False), encoding='utf-8')
        with self.assertRaises(module.Refusal) as caught:
            harness.resume()
        self.assertEqual(caught.exception.code, 'STORE_INTEGRITY')

    def test_atomic_replace_failure_preserves_previous_document(self):
        harness = module.Harness(self.root)
        harness.init(self.mission)
        before = harness.db.read_bytes()
        with patch.object(module._store_module.os, 'replace', side_effect=OSError('fixture')):
            with self.assertRaises(OSError):
                harness.review('will not commit')
        self.assertEqual(harness.db.read_bytes(), before)
        self.assertEqual(harness.resume()['revision'], 0)


if __name__ == '__main__':
    unittest.main()
