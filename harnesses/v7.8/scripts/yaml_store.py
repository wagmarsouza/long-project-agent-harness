"""Integrity-protected, atomic YAML state store for VeriMission."""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import time
import uuid

import yaml


FORMAT = 'verimission-yaml-store'
STORAGE_SCHEMA = 1


class StoreError(Exception):
    def __init__(self, code, detail):
        self.code, self.detail = code, detail
        super().__init__(detail)


def _canonical_digest(value):
    payload = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(payload).hexdigest()


def _file_digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


class _FileLock:
    """Portable exclusive advisory lock with a bounded wait."""

    def __init__(self, path, timeout=10):
        self.path = Path(path)
        self.timeout = timeout
        self.stream = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.stream = self.path.open('a+b')
        if self.stream.seek(0, os.SEEK_END) == 0:
            self.stream.write(b'0')
            self.stream.flush()
        deadline = time.monotonic() + self.timeout
        while True:
            try:
                self.stream.seek(0)
                if os.name == 'nt':
                    import msvcrt
                    msvcrt.locking(self.stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(self.stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                return self
            except (OSError, BlockingIOError):
                if time.monotonic() >= deadline:
                    self.stream.close()
                    self.stream = None
                    raise StoreError('LOCK_TIMEOUT', 'Timed out waiting for the canonical YAML store lock')
                time.sleep(0.05)

    def __exit__(self, _type, _value, _traceback):
        if self.stream is None:
            return
        self.stream.seek(0)
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(self.stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(self.stream.fileno(), fcntl.LOCK_UN)
        self.stream.close()
        self.stream = None


class YAMLStore:
    def __init__(self, path, now):
        self.path = Path(path)
        self.lock_path = self.path.with_name(self.path.name + '.lock')
        self.now = now

    def _payload(self, state, audit, migration=None):
        payload = {
            'format': FORMAT,
            'storage_schema': STORAGE_SCHEMA,
            'state': state,
            'audit': audit,
        }
        if migration is not None:
            payload['migration'] = migration
        return payload

    def _document(self, state, audit, migration=None):
        payload = self._payload(state, audit, migration)
        return {**payload, 'integrity': {'algorithm': 'sha256', 'payload_sha256': _canonical_digest(payload)}}

    def _validate(self, document):
        if not isinstance(document, dict):
            raise StoreError('STORE', 'YAML store must contain one mapping')
        if document.get('format') != FORMAT or document.get('storage_schema') != STORAGE_SCHEMA:
            raise StoreError('SCHEMA', 'Unsupported YAML storage schema')
        state = document.get('state')
        audit = document.get('audit')
        if not isinstance(state, dict) or state.get('schema') != 1 or not isinstance(audit, list):
            raise StoreError('STORE', 'State or audit record is missing or invalid')
        integrity = document.get('integrity')
        if not isinstance(integrity, dict) or integrity.get('algorithm') != 'sha256':
            raise StoreError('STORE_INTEGRITY', 'YAML store integrity record is missing')
        payload = self._payload(state, audit, document.get('migration'))
        if integrity.get('payload_sha256') != _canonical_digest(payload):
            raise StoreError('STORE_INTEGRITY', 'YAML store checksum does not match its contents')
        if [entry.get('id') for entry in audit] != list(range(1, len(audit) + 1)):
            raise StoreError('STORE_INTEGRITY', 'Audit IDs are not contiguous')
        for entry in audit:
            if not isinstance(entry, dict) or not isinstance(entry.get('revision'), int) or 'at' not in entry or 'kind' not in entry:
                raise StoreError('STORE_INTEGRITY', 'Audit record is malformed')
        return document

    def _load_unlocked(self):
        if not self.path.exists():
            raise StoreError('NOT_INITIALIZED', 'Run init first, or migrate-sqlite for a legacy store')
        try:
            document = yaml.safe_load(self.path.read_text(encoding='utf-8'))
        except yaml.YAMLError as error:
            raise StoreError('STORE', 'Canonical YAML could not be parsed') from error
        return self._validate(document)

    def _write_unlocked(self, document):
        self._validate(document)
        text = yaml.safe_dump(document, allow_unicode=True, sort_keys=False, default_flow_style=False)
        temporary = self.path.with_name(self.path.name + '.' + uuid.uuid4().hex + '.tmp')
        try:
            with temporary.open('x', encoding='utf-8', newline='\n') as stream:
                stream.write(text)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
            if os.name != 'nt':
                descriptor = os.open(self.path.parent, os.O_RDONLY)
                try:
                    os.fsync(descriptor)
                finally:
                    os.close(descriptor)
        finally:
            if temporary.exists():
                temporary.unlink()

    def create(self, state, migration=None, audit=None):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with _FileLock(self.lock_path):
            if self.path.exists():
                raise StoreError('EXISTS', 'YAML store already exists; init never resets history')
            document = self._document(state, list(audit or []), migration)
            self._write_unlocked(document)

    @contextmanager
    def state(self, write=False):
        with _FileLock(self.lock_path):
            document = self._load_unlocked()
            state = document['state']
            yield state
            if write:
                state['revision'] += 1
                audit = document['audit']
                audit.append({'id': len(audit) + 1, 'at': self.now(), 'revision': state['revision'], 'kind': 'state-update'})
                self._write_unlocked(self._document(state, audit, document.get('migration')))

    def append_audit(self, kind):
        with _FileLock(self.lock_path):
            document = self._load_unlocked()
            audit = document['audit']
            audit.append({'id': len(audit) + 1, 'at': self.now(),
                          'revision': document['state']['revision'], 'kind': kind})
            self._write_unlocked(self._document(document['state'], audit, document.get('migration')))

    def audit_kinds(self):
        with _FileLock(self.lock_path):
            return [entry['kind'] for entry in self._load_unlocked()['audit']]

    def validate(self):
        with _FileLock(self.lock_path):
            self._load_unlocked()
        return True

    def copy_current_unlocked(self, target):
        """Copy the committed pre-transaction snapshot while caller holds the store lock."""
        document = self._load_unlocked()
        target = Path(target)
        if target.exists():
            raise StoreError('BACKUP', 'Backup target already exists')
        text = yaml.safe_dump(document, allow_unicode=True, sort_keys=False, default_flow_style=False)
        with target.open('x', encoding='utf-8', newline='\n') as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        self._validate(yaml.safe_load(target.read_text(encoding='utf-8')))

    def backup(self, target):
        with _FileLock(self.lock_path):
            self.copy_current_unlocked(target)

    def migrate_sqlite(self, legacy_path):
        legacy_path = Path(legacy_path)
        if not legacy_path.is_file() or legacy_path.is_symlink():
            raise StoreError('MIGRATION', 'Legacy SQLite store is missing or unsafe')
        with _FileLock(self.lock_path):
            if self.path.exists():
                raise StoreError('EXISTS', 'YAML store already exists; migration never overwrites it')
            try:
                connection = sqlite3.connect(f'file:{legacy_path.as_posix()}?mode=ro', uri=True, timeout=10)
                try:
                    if connection.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                        raise StoreError('MIGRATION', 'Legacy SQLite integrity check failed')
                    row = connection.execute('SELECT body FROM state WHERE id=1').fetchone()
                    if row is None:
                        raise StoreError('MIGRATION', 'Legacy state row is missing')
                    state = json.loads(row[0])
                    rows = connection.execute('SELECT id,at,revision,kind FROM audit ORDER BY id').fetchall()
                finally:
                    connection.close()
            except (sqlite3.Error, json.JSONDecodeError) as error:
                raise StoreError('MIGRATION', 'Legacy SQLite store could not be imported') from error
            if not isinstance(state, dict) or state.get('schema') != 1:
                raise StoreError('SCHEMA', 'Unsupported legacy state schema')
            audit = [{'id': row[0], 'at': row[1], 'revision': row[2], 'kind': row[3]} for row in rows]
            migration = {
                'source': legacy_path.name,
                'source_sha256': _file_digest(legacy_path),
                'source_preserved': True,
                'migrated_at': self.now(),
                'state_revision': state.get('revision'),
                'audit_records': len(audit),
            }
            self._write_unlocked(self._document(state, audit, migration))
        return migration

    def migration_info(self):
        with _FileLock(self.lock_path):
            return self._load_unlocked().get('migration')
