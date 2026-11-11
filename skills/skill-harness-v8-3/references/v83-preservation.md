# Control 8.3 — native preservation of accepted obligations

This is an opt-in, general-project control. It adds neither background execution nor specialist
tools. Existing missions without `regression_policy` keep the inherited 8.2 behavior, including
native periodic review, explicit mission revision, claims/retractions and anti-rework gates.

## State and authority

`init` adopts a declared baseline as part of a genuinely new authorized mission. For an existing
mission, use the existing `preview-mission` / interactive `revise-mission` workflow after explicit
user approval. Do not reinitialize a mission. Do not answer the human confirmation on the user's
behalf, pipe it, simulate a terminal or create an approval bypass.

There is no baseline-adopt/force/snapshot-update shortcut. A baseline contains accepted obligations,
not an automatically trusted snapshot of whatever the candidate currently produces. Updating an
expected value, normalization, exclusion, test selection or tolerance can weaken the oracle; review
that effect explicitly. Use a new baseline file for a new epoch and preserve old files/history.

`.harness/state.yaml` remains the only authoritative state. It records the adopted baseline,
execution records, assessments and last validated snapshot. Result files are immutable evidence
referenced by hash, not a second state store. A last validated snapshot does not replace an oracle.
Changing an accepted requirement is distinct from legitimately retracting a false factual claim.

## Baseline format

Use `templates/preservation-baseline.example.json` (or `assets/templates/` in the skill).
`verimission-baseline-v1` has these exact fields:

- `reference`: `{kind: specification|commit, id: ...}`. Commit IDs must be resolved full hashes
  present in the local repository. A specification ID documents the declared source of expectations;
  it does not authenticate a person or certify that the old behavior was correct.
- `protected_files`: project-relative paths and SHA-256 hashes of tests, oracles, comparator
  configuration, masks, fixtures and retained counterexample corpus. At least one is required.
- `context_files`: frozen toolchain/executor/lock/configuration file hashes. A change refuses reuse
  and requires explicit context/contract review. Use side-by-side replay to study a changed tool.
- `obligations`: unique `{id, criterion, case, critical, sources, comparator}` entries. `sources`
  lists input-universe paths. The criterion must be declared in the mission and the policy.
- `debt`: separate `{id, reason, owner, expires}` records. Debt is reported, never counted as a pass.

Comparators: `{kind: status}` requires a real case pass; `{kind: exact, expected: JSON}` also
compares the observed value; `{kind: numeric, expected: NUMBER, abs_tol: NUMBER, rel_tol: NUMBER}`
uses the explicitly declared finite nonnegative tolerances. There is no default global epsilon.
`{kind: minimum, expected: NUMBER}` and `{kind: maximum, expected: NUMBER}` impose an explicit
finite floor or budget ceiling. They do not silently advance the accepted bound after a better
measurement. A different bound requires review of the accepted contract; no universal percentage
is supplied. Keep the scope, denominator and exclusions in the immutable case contract.
For bitwise floating-point, NaN, signed zero or domain-specific treatment, use an explicitly tested
domain comparator and a protected configuration; do not encode a universal floating-point policy.

An optional obligation `contract` object must equal the case's contract. Put metric universe,
exclusions, scope, reference identity, input assumptions and formula there. A denominator change
then becomes incomparable rather than an artificial improvement. Exact JSON comparison is
type/representation-sensitive; choose observable structures deliberately.

## Mission policy

`regression_policy` has exact fields:

```json
{
  "schema": 1,
  "baseline": {"path": "analysis/preservation-v1.json", "sha256": "REPLACE_WITH_REAL_HASH"},
  "input_patterns": ["src/*.py", "tests/*.py", "corpus/*.json"],
  "criteria": {"REG": {"output_pattern": "reports/preservation-{run}.json"}},
  "mode": "full",
  "graph": {},
  "graph_complete": false,
  "environment": []
}
```

Use forward-slash paths inside the authorized project. Do not match `.git`, `.harness`, generated
reports or build outputs with input patterns. Every pattern must match, and all obligation sources
and protected files must be in the resolved input universe. New/deleted files are significant.
Input symlinks are refused rather than silently broadening that universe. Include test discovery
configuration, shared helpers, generated inputs and dependencies that could affect a conclusion.
Undeclared dependencies remain outside the tool's observation; no universal preservation is claimed.

The engine additionally hashes its bundled Python helpers and the resolved acceptance executable.
It hashes only the values of explicitly named environment variables; it does not dump the complete
environment into state. Dependency packages, remote services and tool options must be bound by
the project's own context resources. Hashes do not prove an executor used the declared configuration.

## Execution and result binding

Inspect `regression-plan` after `review` and include every required criterion in the actual plan.
`start` refuses omission. `check` runs the already authorized criterion argv without a shell and
sets these variables for its result writer:

- `VERIMISSION_REPORT`: fresh output path derived from the approved pattern;
- `VERIMISSION_RUN_ID`: unique run ID;
- `VERIMISSION_CONTEXT_SHA256`: identity of the declared/current check context;
- `VERIMISSION_TIMEOUT`: check time budget (the outer cycle budget may be shorter).

The acceptance executable is resolved and hashed before execution. Inputs are fingerprinted before
and after the check; generated result files are separate outputs. Do not list the result file as
an input artifact. Existing result files are never overwritten by the bundled runner. An incomplete
file left by a crash remains evidence of that interruption; a retry uses a new run ID/path.

The optional governed `operation-run` adapter uses the same preservation preparation/finalization.
Preflight happens before single-use approval is consumed; admission still commits before launch.
An interruption after admission remains unresolved and cannot be replayed merely to discover its
outcome. A completed operation must still produce a current passing preservation proof for closure.

The result envelope is exactly:

```json
{
  "format": "verimission-results-v1",
  "run_id": "CURRENT_RUN_ID",
  "context_sha256": "CURRENT_CONTEXT_HASH",
  "complete": true,
  "cases": [{"id": "tests.C.test_old_capability", "status": "pass", "raw_status": "unittest:pass"}]
}
```

States are `pass`, `fail`, `error`, `timeout`, `skipped`, `xfail`, `xpass`, `missing`, `unsupported`,
`inconclusive`. A case may contain `observed` JSON and a structured `contract`. IDs must be unique.
Missing/partial/foreign-run reports, malformed JSON and nonfinite values do not satisfy a protected
pass. A green process cannot compensate for failed/missing cases. Repeated identical inputs after
a failed check retain instability instead of becoming green by retry-until-pass.

The bundled library-standard runner can be an acceptance command:

```text
python /absolute/skill/scripts/result_runner.py unittest --start tests --pattern test*.py
```

It records parent-test failures from failing subtests, skips and expected/unexpected successes.
A test ID follows unittest's module/class/method naming. Renaming/replacing a protected case needs
an explicit obligation/history mapping through the revised baseline, not a count-only comparison.

JUnit is optional and does not require pytest in the harness. An explicitly authorized command can use:

```text
python /absolute/skill/scripts/result_runner.py junit --source reports/raw.xml -- python -m pytest --junitxml reports/raw.xml
```

The raw JUnit path must be new, inside the project, and writable by the approved command. Give each
invocation a distinct raw path or use a project wrapper that derives one from the run ID. Raw XML
must be UTF-8, complete, nonempty, without DTD/entities, consistent counts and duplicate IDs. IDs
are `classname.name` as reported by JUnit. Recognized pytest xfail remains xfail; ambiguous states
are not upgraded to a protected pass. The wrapper's child has a finite timeout; an interrupted
runner leaves incomplete evidence and grants no authority to replay external effects.

`result_readers.metric()` supports explicit coverage counts and Stryker's declared detected/valid
mutation formula, keeping states, exclusions and scope. Timeout remains a distinct state even if
the provider counts it as detected. Compile/runtime-invalid mutants are not credited as killed.
Use neutral results with immutable metric contracts for an actual project gate; no threshold is
enabled merely by importing a metric, and these helpers do not run coverage or mutation tools.

## Gates and reporting

- `regression-plan`: read-only required criteria and eligible original-proof references; no dispatch.
- `baseline-preview --input mission.json`: read-only proposed policy, not adoption or authorization.
- `regression-report [--cycle N]`: current assessment; `passed` is the verdict, command read-success
  alone is not a preservation pass. Failed-case diagnostics and current-proof errors stay visible.
- `close --outcome verified`: native preservation gate, then all inherited gates. On preservation
  failure the cycle remains active and structured assessment/audit persist. Interrupt/block remains possible.
- `resume`, `traceability`, `accept-mission` and `validate`: expose current evidence gaps. Declared
  claim dependencies require current supporting checks. No report promotes a claim or a grade.

At an existing periodic boundary the same assessment is summarized with consolidation, without
creating a separate schedule, store or reconciler. Preserve the physical-note reread and core
tripwire. A stored declaration of reading does not authenticate cognition.

## Optional impact reuse

Start with `mode: full`. Every protected suite is rerun for each verified cycle. `mode: impact`
permits reuse only for noncritical criteria backed by a verified original cycle, unchanged
mission/policy/context/report, the same input universe and an explicitly complete graph covering
that universe. Edges point **caller/dependent -> callee/dependency**. The reverse transitive closure
of changed sources invalidates callers, including cycles. Critical criteria are always selected.
New/deleted inputs, incomplete graphs and unknown changed nodes fall back to full replay.

The reused check is a reference to the original execution, not a fabricated new execution or new
discovery. Later failures for identical declared inputs/context prevent silent reuse. This is
conservative declared dependency analysis, not automatic discovery of imports, globals, indirect
calls or hardware state. A false completeness declaration can still omit real dependencies;
keep the claim ceiling explicit and prefer full replay when that uncertainty matters.

## Recovery and limits

The canonical YAML transaction atomically commits audit and last-validated state. A result file and
YAML commit are not a single OS transaction. On interruption, inspect/resume; an orphan result does
not advance the baseline or prove closure. The engine does not automatically reset Git, delete
corpus files, repair a candidate or accept a new oracle.

This is provenance/consistency enforcement within the routed workflow, not isolation against an
operator who can rewrite the engine/store/OS or a malicious runner that fabricates results. For
that threat model use separate permissions, independent review and CI outside the writer's control.
No hardware correctness, universal equivalence, model honesty or human identity is authenticated.

Counterexamples belong in the project's versioned, protected corpus with an obligation and justified
expected behavior. Fuzz/property exploration is separately authorized and budgeted; discoveries do
not silently become new obligations or modify accepted expectations. Use synthetic/authorized data;
reports and corpus have the sensitivity of their contents, and hashing does not anonymize them.
