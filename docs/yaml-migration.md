# Migrating state from SQLite to YAML

Corrected VeriMission Core 7.8, Continuity 7.9, and Control 8.x publications use `.harness/state.yaml` as the sole canonical source. The document contains complete state, audit history, format version, and a SHA-256 checksum over normalised content.

## Prerequisite

```powershell
python -m pip install "PyYAML>=6,<7"
```

Do not run `init` when `.harness/state.sqlite` already exists. Use the executor version you intend to adopt:

```powershell
python -B $h --project $p migrate-sqlite
python -B $h --project $p validate
python -B $h --project $p resume
```

## Migration guarantees

- SQLite is opened read-only and must pass `PRAGMA integrity_check`.
- State and all audit rows are imported with identifiers, revisions, and content preserved.
- YAML is written to a temporary file, synchronised, and atomically replaced.
- `state.sqlite` is not deleted, renamed, or modified.
- YAML records the source name, SHA-256, revision, and event count.
- `migrate-sqlite` never overwrites an existing YAML state.

After migration, new revisions exist only in YAML. The preserved SQLite file is historical provenance, not a current backup. Returning to an old executor would hide all work performed after migration from that executor's point of view.

## Integrity and concurrency

Every read verifies the format, schema, audit structure, and checksum. An exclusive file lock serialises readers and writers across processes. Mutations use atomic replacement; a failure before `os.replace` leaves the last committed document intact. The checksum detects accidental change, but it is not a signature, operator authentication, or proof that records are semantically true.

`.harness/state.yaml.lock` coordinates access and is not a second state source. Reports, capsules, and indexes remain derived views and cannot be imported as authority.
