# Control 8.3 — verifier assurance, authorized local evolution

Scope: implement recommendations 1–3 without changing accepted missions, installing skills,
publishing, adding a scheduler or replacing `.harness/state.yaml`. SQLite and LLVM are references
for testing methods; the existing optional read-only SQLite migration remains unchanged.

## Design

- Keep normal mission gates and the YAML storage schema unchanged. Add an explicitly invoked,
  finite `harness.py assurance` campaign that operates exclusively in disposable synthetic projects.
- First prove a healthy fixture is accepted. Negative controls must be rejected for the expected
  behavioral reason: launch failures, parser/import errors and timeouts never count as detection.
- Generate bounded action programs from a recorded seed. Use a small independent lifecycle model,
  checking authority, current evidence, retained history and non-inflated revalidation progress.
  Record actual programs and step outcomes, rather than claiming exhaustive state exploration.
- Sweep named YAML write boundaries for review/check/close. Inject both caught I/O faults and real
  child-process termination. Fresh parent instances verify old-or-new complete commits, audit
  continuity, unchanged mission, retained evidence and lock recovery. Never replay unknown effects.
- Patch boundaries only in disposable campaign workers. No production fault toggle or environment
  bypass is added. A child validates its synthetic workspace marker before patching anything.
- Campaign receipts are derived JSON evidence, not a second canonical ledger or mission approval.
  Include finite configuration, engine source identity, per-case expected/actual result and limits.
- Preserve all prior core rules; add concise instructions routing to a campaign reference.
  Derive the skill from the same canonical scripts/tests/docs and verify package-byte parity.

## Ordered tasks and acceptance

1. Controls: tests first, reusable positive/negative corpus and CLI; wrong failure reason fails the
   campaign. Verification: focused unittest, deliberate bypass experiment in an isolated copy.
2. Lifecycle: deterministic programs and independent model. Verification: seeds, stale evidence,
   failed closure, recovery, unauthorized revision, rework and history/progress invariants.
3. Persistence: exception/crash sweep through real YAML boundaries for three native operations.
   Verification: actual child exit marker, process result, fresh-store integrity and native states.
4. Integration/docs: finite orchestrator, no-project native CLI, safe new output, preserved core,
   skill synchronization. Verification: argument limits, non-overwrite, no touched real project.
5. Delivery: inherited/new suites, all campaigns and old pilots on extracted ZIPs; explicit PyYAML
   skill validation, manifests, hashes, source/skill/standalone parity and final usage guide.

## Limits

No formal proof, global mutation score, universal regression freedom, physical power-loss emulation
or independent audit is claimed. OS/filesystem-specific durability remains distinct from process
termination. No Linux/macOS test claim without execution. Long explorations remain explicit and
bounded, not a default cost attached to every user request or verified cycle.

Primary methods consulted: SQLite testing (https://www.sqlite.org/testing.html), LLVM regression
testing (https://llvm.org/docs/TestingGuide.html#best-practices-for-regression-tests), Hypothesis
stateful testing (https://hypothesis.readthedocs.io/en/latest/stateful.html). No external test library
is required at runtime; the bounded model/program generator uses the standard library.
