# VeriMission Control 8.4 — local preview

This generation preserves the previous runtime generations. Source: `harnesses/v8.4`;
corresponding skill: `skills/skill-harness-v8-4`. Packaging, reading a skill and adopting a
mission are distinct actions. Nothing here is installed or published automatically.

The [measurement guide](../harnesses/v8.4/references/v84-measurements.md) describes the new
optional contract, commands and trust boundaries. Canonical state remains YAML. Existing
8.2 periodic review and 8.3 preservation are composed through the same execution hooks.

| Concern | Owner |
| --- | --- |
| Stable universe, exact ID set, cardinality, dependencies, denominator | Harness |
| Executed check, native close, current eligibility, claim ceiling | Harness |
| Frozen audit selection, exact full recount, hold/full recovery | Harness |
| Source review/AST, compilation, actual image binding, witnesses | Decompile |
| Original-code exclusion, approved platforms, domain controls | Decompile |
| Declared/verified-now/pending/stale bars, G4-stock versus G4-recon | Decompile querying the live harness |

No C compiler, emulator or decompilation grade is a general harness requirement. For an
integrated finite pilot, use Decompile's `examples/run_measurement_pilot.py --harness PATH`.
It can optionally compile/execute a small host-C example with `--compiler /usr/bin/gcc`;
that is not firmware/hardware validation.

Negative fixtures cover inflated scalars, duplicate aliases, hidden/missing units, excluded
denominators, missing/weak gates, active/interrupted cycles, stale source/proof/tool context,
replayed runs, missing closure/review/audit, exact recount, selection changes, weak controls,
original/unknown-code execution and loaded-image mismatch. Tests also retain valid linear
source, explicit platform calls and data addresses rather than enforcing brittle keyword rules.

The delivery's qualification report records actual test counts/platforms and targeted guard
inversions. It does not claim a global mutation score, a hostile-evaluator proof or universal
semantic equivalence. Hashes detect drift; trusted reviewer/runner/input completeness remain
explicit dependencies. A host bypassing the CLI is outside the executor's enforcement.
