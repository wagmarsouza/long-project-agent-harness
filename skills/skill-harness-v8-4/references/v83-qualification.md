# Control 8.3 — qualification, portability and reuse

## Local and hosted gates

From the repository root, with Python 3.11+ and PyYAML 6.0.3 available:

```shell
python -B tasks/ci_v83.py --output /absolute/new/qualification-directory
```

This finite coordinator checks manifests, resource parity and skill metadata, runs the complete
harness and skill suites through case-level result envelopes, tests the coordinator, runs verifier
assurance and generic/periodic pilots, then builds and verifies archives. It installs or publishes
nothing. Output is derived evidence in a new directory, never a real mission or an agent skill path.
The repository-level coordinator is distributed in the combined development package; standalone
skills still include their full runtime/tests and can run `python -B -m unittest discover -s tests`.

The workflow `.github/workflows/ci.yml` declares Ubuntu 24.04, Windows 2025 and macOS 15, each with
Python 3.11 and 3.14. Actions are pinned to upstream commits, credentials are not persisted, permissions
are read-only and evidence is uploaded even on failure. The required aggregate refuses failed,
cancelled or skipped matrix jobs. There is no deployment step. A workflow file is not proof that its
matrix ran; reports must name the actual executed platform/runtime. WSL is Linux qualification with
its own filesystem, not macOS or a GitHub-hosted run. Repository branch protection is separate host
configuration and is not established by adding this workflow.

Each command receives an admission record before launch and a durable result/log afterwards.
`--resume` reuses only matching source/runtime/command receipts with intact logs, case envelopes and
declared outputs. Source identity includes the packager and CI tests. Assurance JSON and the complete
packaging output file set/hashes are checked on reuse. Interrupted admissions without completion are
unknown and not automatically replayed. A failed receipt remains failed; an operator may explicitly
choose a fresh output directory for a new attempt, preserving the old evidence. These hashes detect
accidental or unapproved changes; they do not authenticate a hostile writer with full OS access.

## Large-history and sustained-use experiment

```shell
python -B /absolute/package/scripts/history_benchmark.py --native-cycles 100 --history-sizes 1000 5000 --samples 3 --memory --budget-seconds 600 --output /absolute/new/benchmark.json
```

This is an explicit, bounded, synthetic experiment, not a background loop. It has no `--project` and
operates only on disposable fixtures. Native cycles execute start/check/close and periodically resume
in a fresh process; revalidation must not create new progress. Seeded blocked-cycle vectors exercise
real YAML I/O/integrity but are never counted as executed work or mission acceptance. The receipt
keeps per-sample timings, actual source hashes, environment, sizes and separate counts.

`--backend python` forces SafeLoader/SafeDumper only inside the experiment, allowing a paired
comparison with `--backend auto`. Actual fresh-process resumes use the normal auto backend;
per-cycle timing excludes those resumes, while total elapsed time includes them. Optional memory
measurement uses a separate tracemalloc pass: Python allocation peak, not process RSS or total RAM.
The budget is checked between operations and before success. An in-process YAML operation is not
preempted; a deadline overrun yields incomplete/failed qualification after control returns. Fixed
count limits and subprocess timeouts also apply. Synthetic minutes of use do not establish months
of production reliability or a universal performance guarantee.

## Safe YAML acceleration

The store selects CSafeLoader/CSafeDumper when the existing PyYAML installation provides them,
otherwise SafeLoader/SafeDumper. Schema, checksums, lock protocol, atomic replacement, fsync,
audit/history and current-proof checks remain in place. Tests exercise both available safe backends,
old text round trips, tamper refusal and refusal of Python-object constructors. Serialization bytes
may differ between safe emitters; the integrity digest is over canonical document values, not emitter
formatting. No C extension is downloaded at runtime and there is no unsafe-loader fallback.

## Reuse policy retained from earlier versions

The owner requested the same policy as previous versions. Those versions selected no general reuse
license; 8.3 therefore does not introduce MIT, Apache, GPL or another license. Public visibility or a
downloadable ZIP is not a general grant of modification/redistribution rights. References to upstream
methods are attribution, not a relicensing of third-party works. A permissive/open-source license is
still a separate owner decision if broad reuse is desired. Technical qualification does not resolve it.
