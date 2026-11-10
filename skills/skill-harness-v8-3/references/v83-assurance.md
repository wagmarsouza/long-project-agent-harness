# Finite verifier assurance — Control 8.3

The canonical store is still **`.harness/state.yaml`**. SQLite is a source of testing methods,
not a new database dependency or storage migration. The pre-existing explicit, read-only import
of legacy SQLite files remains unchanged. These campaigns never open a real project's store.

## Explicit commands

From the complete package:

```powershell
python -B harnesses/v8.3/scripts/harness.py assurance --suite all --seed 7 --traces 2 --steps 24 --output assurance-new.json
```

From the standalone harness or skill:

```powershell
python -B scripts/harness.py assurance --suite controls
python -B scripts/harness.py assurance --suite lifecycle --seed 7 --traces 2 --steps 24
python -B scripts/harness.py assurance --suite persistence
```

`assurance` deliberately has no `--project`: every operation uses an identified disposable
synthetic workspace. It neither initializes the current directory nor adopts a mission/baseline.
Direct invocation of `scripts/assurance.py` supports the same options. No network or specialist
tool is required; Python 3.11+ and the existing PyYAML dependency suffice.

Defaults are `--suite all --seed 0 --traces 2 --steps 24`. Valid seeds are integers 0..2^32−1;
traces 1..4 and steps 16..64. Budgets are checked before fixtures start. Each persistence child
has a 60-second limit, and each fixture acceptance command has a 15-second limit. The campaign
is finite; there is no background loop, retry-until-green or automatic launch at cycle closure.

Without `--output`, stdout contains the full JSON receipt. With it, stdout is a small summary
and the new file contains the full receipt. The parent directory must exist. Existing files,
symlinks and paths inside `.harness`/`.git` (case-insensitive names) are refused. Receipts are derived evidence, never a
canonical state or mission approval. Exit 0 means this finite campaign passed; 3 means campaign
failure/incompleteness; 2 means invalid configuration or output/I/O failure. Retain diagnostics.

The output destination is resolved before execution and the resolved path is opened exclusively.
An alias/junction into protected state does not bypass the directory-name guard.

## 1. Sensitivity controls

The healthy synthetic input must pass the native check, close and validation first. Nine bundled
negative controls then exercise missing/skipped cases, wrong return, wrong memory observation,
foreign run, incomplete envelope, changed protected oracle, omitted criterion and corrupt YAML.
Each must produce its specified case-level verdict or refusal code. A timeout, launch/import error,
unrelated exception, wrong diagnostic or accidentally accepted close fails the campaign.

The fixture emits controlled synthetic observations to test the verifier; it does not execute real
firmware. Corrupting the YAML is intentional only inside this campaign's owned disposable fixture.
The nine controls are not a global mutation score. Unit tests additionally weaken a control result
and confirm that the campaign itself turns red.

## 2. Independent lifecycle model

Each program begins with 16 discriminating actions, including closure before a check, valid closure,
unjustified rework, failing candidate, interruption, repair/revalidation, reload and unauthorized
mission revision. A versioned SHA-256-based seed generator appends additional actions. The receipt
records seed, configuration, full generated programs, executed steps and expected/actual outcomes.
Repeat the same configuration to replay the same action programs with the same generator version.
UUIDs, timestamps and raw YAML bytes are not claimed to be identical between independent runs.

The model tracks active phase, input generation and current successful witness independently of
engine predicates. Invariants check mission authority, current evidence, cycle/revision history,
budget retention, read-only recovery and non-inflated revalidation progress. Model/case failures
stop that trace, remain visible and cannot count as complete exploration. There is no automatic
human confirmation; the unauthorized-revision probe explicitly uses an automation source.

This is bounded model-based testing with a deterministic generator, not Hypothesis integration,
formal verification, exhaustive schedule coverage or a universal guarantee of correctness.

## 3. YAML persistence fault sweep

The sweep covers three native operations (`review`, `check`, `close`) × six write boundaries
(`before-open`, `partial-write`, `before-flush`, `before-fsync`, `before-replace`, `after-replace`)
× two modes: caught I/O exception and abrupt termination of the worker using `os._exit`.
That is 36 scenarios, including 18 actual worker-process terminations.

The worker verifies its synthetic temp-directory marker before intercepting any boundary. The
test patches are scoped to that worker's canonical YAML target; the production store has no
fault-injection environment switch or approval bypass. A marker plus the exact child exit outcome
must demonstrate that the intended boundary was reached. An unrelated crash is not credited.

A fresh parent-side engine validates integrity, lock recovery and complete old/new commit semantics:
before replace, the previous YAML bytes must survive; after replace, state and audit must agree.
The full pre-existing state/check/event history is compared with the explicitly permitted operation
delta; native consistency and current-proof validation are additionally required after check/close.
The native check scenario verifies that an orphan result remains separate from canonical proof.
The close scenario verifies the joint verified-close/last-validated snapshot commit. Read-only
recovery neither repeats an operation nor overwrites a result. Receipt counters distinguish these
scenarios from unittest counts; repeated campaigns are not independent new discoveries.

Process termination is not physical power-loss simulation. The sweep does not validate disk caches,
controller behavior, every filesystem, directory-fsync fault behavior or every concurrent schedule.
Windows execution does not establish Linux/macOS coverage. Temporary fixture cleanup does not
authorize cleanup or history deletion in a real project.

## When to run

Use these campaigns when changing/releasing the verifier or explicitly investigating its controls.
For a project task, choose the actual domain tests and current preservation policy. A successful
self-test never replaces project evidence, grants new authority, satisfies arbitrary acceptance
criteria or starts work in another project. Preserve the existing claim ceilings and retractions.

## Method references

- [SQLite anomaly/regression testing](https://www.sqlite.org/testing.html): discriminating bug cases
  and systematic failure-boundary tests. No SQLite code or database was incorporated.
- [LLVM regression-test guidance](https://llvm.org/docs/TestingGuide.html#best-practices-for-regression-tests):
  small, explicit, reproducible tests with scope and preconditions.
- [Hypothesis stateful testing](https://hypothesis.readthedocs.io/en/latest/stateful.html): sequences
  and invariants motivate the bounded independent model; the package adds no Hypothesis dependency.
