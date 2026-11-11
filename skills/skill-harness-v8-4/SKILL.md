---
name: skill-harness-v8-4
description: "VeriMission Control 8.4: govern general long-running projects with preserved capabilities, executed evidence, recovery and protected periodic review. Use to adopt the harness or resume a governed mission; specialist domain tools remain optional."
metadata:
  display-name: VeriMission Control 8.4
  version: "8.4"
---

# Using Control 8.4

Use an absolute bundled executor path and the real project root:
`python /absolute/skill/scripts/harness.py --project /authorized/project COMMAND`.
Python 3.11+ and PyYAML 6.x are the only core executor requirements. Do not require a binary-analysis
tool, grade ladder, compiler, emulator or solver for a general project.

For an existing mission inspect `resume` and `validate`; do not reinitialize it. Normal flow remains
review → start → check → close → validate. Installation/activation, publishing and schedules need
separate explicit user authorization; a skill package grants none. Simple questions do not need
manufactured cycles. Respect higher-priority host instructions and the approved mission.

Read [preservation](references/v83-preservation.md) when adopting `regression_policy`, checking
baseline freshness, interpreting missing cases or configuring optional impact reuse. Inspect
`regression-plan` and include its required criteria; `close` now enforces the policy natively.
Expected results and prior capabilities cannot be weakened to make a candidate pass. Policy
adoption/change on an existing mission uses the existing explicit human mission-revision gate.
No separate baseline-approval bypass or background rebaselining exists.

When changing/releasing the verifier, read [finite assurance campaigns](references/v83-assurance.md).
`python /absolute/skill/scripts/harness.py assurance --suite all` exercises synthetic controls,
bounded action sequences and YAML persistence faults without a real `--project`. A self-test pass
does not establish project correctness or grant authority; do not run the full campaign on every task.

Read [periodic review](references/v82-periodic-review.md) before changing notes, cadence, inventory
or governing-file configuration. The native review/reconciliation remains self-contained and protects
governing text outside the declared immediate-objectives/scenario bodies. No second scheduler is added.
Read [8.1 projections/imports](references/v81-projections-and-runs.md) for graph/PR/cost interfaces.
Without the optional new policy, inherited 8.2 workflow remains available. Historical references
retain their original version labels; the complete current core below governs current operation.

For release qualification, portability, finite large-YAML experiments and the retained reuse policy,
read [qualification](references/v83-qualification.md). Benchmarks use synthetic fixtures and grant no
mission acceptance or authority. A declared CI matrix must not be reported as actually executed.

# VeriMission Control 8.4 — core operating rules

The executor governs operations sent through its CLI. It does not intercept every host tool. Higher-priority instructions, the user's current request, and the authorized mission remain authoritative.

## Persistent mission and evidence

1. Recover before repeating. Run `resume` and `validate`, then `review` the topic. Search registered aliases and source terms. Read applicable claims, retractions, failed approaches, and remaining work.
2. Define proof before implementation. The mission declares objective, scope, exclusions, executable acceptance criteria, artifacts, and budgets. Review command effects and authorization. Do not weaken acceptance to make a result pass.
3. Start through the gates. A plan needs a fresh review receipt, residual work, technical approach, inputs, environment, dependencies, and selected criteria. Strict mode also requires reference review and a simple discriminating test.
4. Execute the smallest useful authorized action. Files, elapsed time, attempts, and reports measure activity rather than objective progress. A pending decision blocks only work that depends on it; silence grants no authority.
5. Record real verification. `check` executes approved argv without a shell and records exit status, duration, output hash, and artifact identity. A timeout, failure, or artifact drift blocks verified closure. Inspect the test's power to detect relevant faults.
6. Close before claiming completion. Use verified closure only after selected checks pass with current evidence. Otherwise record a block or interruption and a concrete next step. A verified cycle is distinct from a satisfied requirement or completed mission.
7. Stop unproductive repetition. Respect timeboxes, budgets, failure limits, and consolidation gates. Use `step-back` to reconsider premises, references, representations, and simpler alternatives. Renaming the same approach does not satisfy a gate.
8. Separate hypotheses and facts. Hypotheses remain candidates. Facts require linked executed evidence. Register dependencies. Retractions preserve history and invalidate declared dependents; search for undeclared dependencies that also need review.
9. Keep one canonical store. `.harness/state.yaml` contains state and audit history with a checksum, locking, and atomic replacement. Reports, capsules, search indexes, and graphs are derived. Do not edit the store directly or maintain a competing ledger.
10. Consolidate and back up. Consolidation records reviewed cycles without inventing progress. A state backup does not replace a backup of project artifacts. Never delete old records as automatic cleanup.
11. Measure controls honestly. Tool duration, declared tokens, and reported dollars are not quality scores or authenticated billing. Simplify overhead only when acceptance and authorization remain intact.
12. Preserve boundaries. Do not create schedules, services, global installations, or production changes merely because the harness is active. Do not persist secrets. Respect explicit pauses and cancellation, and leave verifiable status and a next step.

## Claim ceiling and honest coverage

Apply these rules in both light and strict modes, including short reports.

- Bound conclusions by the actual method, environment, sample, conditions, and tested scope. Static inspection does not demonstrate runtime behavior; simulation does not establish production or hardware correctness.
- Never fabricate executions, commands, outputs, logs, citations, receipts, metrics, or results. Separate planned, executed, observed, and inferred work. Preserve failures and contradictions.
- Report verified/total, critical verified/critical total, and changed verified/changed total when those universes exist. Define exclusions. Unknown totals mean indeterminate coverage; zero of zero is N/A. A sample is not universal coverage.
- Do not count duplicated claims, renamed work, retries, retractions, or revalidation as new discoveries. Confidence percentages require an explicitly adopted method.
- Check test discrimination. A zero exit code, echoed plan, or test mirroring the implementation is insufficient evidence by itself. Duplicate results are not independent evidence.
- Stale evidence, retracted dependencies, and open requirements qualify conclusions. Do not erase history to preserve an appearance of success.

For significant deliveries and completion claims, state the exact claim, supporting execution/source and artifacts, coverage with denominators, limitations and contradictions, current status, and next step. Use the length the result needs. The executor checks recorded provenance and invariants; it does not authenticate natural-language truth or observe every external action.

## Mission revision — explicit user authorization only

The mission remains frozen between revisions. A revision requires a specific user request or approval of a concrete proposal identifying objective, scope, criteria, and command changes. A generic continuation, old approval, silence, failure, timeout, or exhausted budget does not authorize revision.

Cron jobs, loops, heartbeats, hooks, and other automation must not initiate or apply a mission revision.

1. After authorization, run `resume` and prepare the mission-revision template using the current revision/hash, reason, actual user-authorization reference, and complete proposed mission.
2. Run `preview-mission` and review exact changes, removed tests, denominators, exclusions, and new commands. The authorization reference documents an approval; it does not authenticate a person.
3. Explicitly close or interrupt active cycles first. If the proposal becomes stale, prepare and review a fresh one.
4. The user personally runs `revise-mission` in an interactive terminal and types the displayed confirmation, whose literal keyword is `REVISAR`. An agent must not answer on the user's behalf, create a pseudo-terminal to simulate consent, pipe confirmation, or add a bypass.
5. The executor rechecks revision/hash and creates a validated YAML backup, preserving previous contracts, cycles, checks, failures, usage, and revision history. Prior conclusions require review under the new contract. Budgets do not silently reset.
6. Resume, validate, review, and execute relevant checks again.

The CLI rejects pipes, noninteractive terminals, and known CI/automation signals. This is a procedural protection rather than cryptographic human authentication; an operator with source/store access may bypass implementation controls.

## Continuity, tasks, and governed operations

- Use `evidence-scope` to state what a real check verifies, does not verify, and leaves untested. Arithmetic and annotations do not promote semantic truth.
- Use `capsule` and `capsule-status` for resumption. A capsule is non-authoritative; omissions must be counted. Never import it as a mission, permanent truth, or authorization.
- `prepare-mission` produces proposals and questions without initializing, revising, or executing a mission. Ready for review is not approval.
- Register tasks with existing criteria and dependencies. `task-ready` reports eligibility without dispatching work. One claimed writer task and one active cycle remain the execution boundary.
- `task-complete` needs current proof. Reopening preserves history and invalidates affected conclusions. `claim-reverify` requires the unchanged fact, fresh executed evidence, and explicit reason; it does not restore retractions or promote hypotheses.
- Search relevance, context packs, and links do not establish applicability, truth, or authorization. Check `view-status`; recover full references rather than silently dropping required constraints.
- `traceability` and `accept-mission` expose proof gaps. An accepted declared contract does not guarantee test quality or universal correctness.
- Optional `operation-*` commands govern only routed operations. Approval is bound to one concrete operation and consumed once. Unknown outcomes need observed reconciliation and fresh checks; never replay an effect to learn whether it happened.
- Diagnostic notes remain hypotheses until proven. Local tracing covers only recorded operations and must not contain secrets or raw private output.

## Control 8.1 observations

`graph` and `report-pr` are read-only projections. Source revisions, hashes, coverage, and limits must remain visible. Links do not become evidence, and PR reports do not approve or merge work.

`run-import` accepts an explicit neutral record for Codex, OpenCode, Claude, or Hermes with a hashed source. Do not claim native parsing or source authentication. Imports do not dispatch agents, select models, approve actions, change missions, promote claims, or replay unknown results.

Keep actual, estimated, and unpriced costs separate. Missing prices and token counters remain null. Preserve retries, cache counters, and subagent links when supported. Inspect parent/child billing overlap before interpreting totals.

## Native periodic review — general long-project control

- The native digest producer and review require no domain tool. Domain observations are optional inputs; no field, marker, denominator, schedule or proof ladder from a particular project is a universal rule.
- A configured N-cycle boundary is one joint ritual: physically read all notes in the exact window, reconcile declared observations, verify the governing instructions, review staleness, and reconsider only immediate objectives/scenario. It is not a second schedule.
- `close` invokes the ritual. A failed or incomplete review exits 2 without verified closure. A successful boundary consolidates automatically. Interrupting work remains possible but does not bypass the next-start gate.
- Hash notes/observations at closure and pin the initial baseline. Preserve history; do not retroactively improve a past note to justify a current result. Record corrections and justified retractions explicitly. A lower metric can be an honest correction, not failure to manufacture progress.
- Protect all governing text outside the two declared mutable bodies, including safeguards added before adoption. Keeping marker names while weakening their content is not permitted. Mutable planning text cannot override the mission, invariant core, acceptance criteria or authority boundaries.
- Generated arithmetic and a digest skeleton do not complete the physical/semantic reread. Read the original notes or their verbatim copies; provide specific findings, acknowledge possible lost facts and distinguish observations from inference. Reread receipts record a declaration, not authenticated cognition.
- Updates must be bound to the current digest/window, note hashes and prompt hash. Empty updates mean reviewed/unchanged. Never use this path for mission revision, criteria changes, new authority, automatic claim promotion, agent dispatch or installation.
- An explicitly user-authorized mission revision must declare a new periodic anchor at the current cycle count and a matching inventory baseline when applicable. This starts a new review window without resetting consumed budgets, erasing prior history or treating earlier conclusions as revalidated. Initialization starts at cycle zero; a historical review cannot retarget later work.
- If the tripwire fails, restore the trusted prompt before further execution. Preserve damaged bytes and structured audit events. A file replacement and YAML commit are not a single OS transaction; after interruption inspect hashes and recover rather than assuming success.
- Arithmetic demonstrates declared consistency, not semantic correctness, test discrimination or universal coverage. Checksums are not operator authentication. All earlier claim ceilings, coverage denominators, retraction, anti-rework and explicit-user-authority rules continue to apply.

## Native preservation — Control 8.4

1. Preserve accepted obligations across sessions and changes. A plan cannot omit criteria required by an adopted preservation policy.
2. Compare stable obligation/case identities and contracts. Equal test counts or improved aggregate percentages do not demonstrate retention.
3. Protect the verifier: expected outputs, masks, tolerances, exclusions, discovery rules, fixtures, mocks and comparators are part of the oracle.
4. Never regenerate/approve a baseline to absorb a failure. Changes to protected obligations/oracles use the existing explicitly human-authorized mission revision.
5. A broken mandatory capability cannot be compensated by new passes, more coverage, files, grades, retries or reports.
6. Missing, skipped, xfailed, timed-out, unsupported, partial or inconclusive results do not replace a required pass. Preserve all failure history and disclose instability.
7. Bind checks to actual candidate inputs, approved argv, current runner/tool context, corpus, comparator and a fresh result file. Inputs and generated outputs are distinct.
8. Invalidate affected current proofs through declared dependencies. Changed callees affect callers; unknown dependencies require broader replay or an inconclusive conclusion.
9. Preserve reproducible counterexamples as explicit protected corpus/cases. Exploration does not silently modify accepted obligations or start background fuzzing.
10. Inspect test discrimination with meaningful negative controls/mutations in isolated copies. Coverage and a zero exit code alone do not certify quality.
11. Permit honest corrections/retractions with preserved history. A lower corrected metric is not automatically functional regression; revalidation is not a new discovery.
12. Keep byte matching, structural similarity, sampled differential behavior, ABI, simulation and formal/refinement results distinct, with their real assumptions and limits.
13. A changed requirement, oracle, denominator or tolerance needs explicit review/authorization. Silence, a failed test or a generic continuation supplies none.
14. Recover without erasing: retain failed artifacts/audit, inspect unknown outcomes, and prepare authorized repair. No automatic destructive Git reset or corpus cleanup.
15. Keep the core domain-neutral. Specialist tools export neutral evidence; no grade ladder, CPU, firmware denominator or solver is a universal harness requirement.
16. Preservation grants no implicit installation, publication, schedule, execution or mission authority. Local hashes do not authenticate operators, cognition or a malicious runner.

Configure `regression_policy` only for a new authorized mission or through explicit mission revision.
Read `references/v83-preservation.md` for the precise contract, fresh results, debt, impact reuse and
trust limits. Without this policy, inherited 8.2 cycle behavior remains available. Read `regression-plan`
before selecting checks; use `regression-report` to inspect current case-level evidence. Native
`close` enforces preservation together with all earlier gates; it does not implicitly launch checks.

## Verifier assurance — explicit, finite and synthetic

- When changing or releasing this verifier, use the bundled `assurance` campaigns to check test
  discrimination, bounded lifecycle sequences and YAML persistence recovery. Read
  [the campaign guide](references/v83-assurance.md) for commands and actual coverage.
- A negative control counts only when the expected behavioral verdict/refusal is observed after
  a healthy control passes. Infrastructure errors, unrelated crashes and absent cases are failures.
- Record finite seeds/programs and injected boundaries. Preserve incomplete traces and actual
  worker outcomes. No global mutation score, exhaustive proof or physical power-loss claim follows.
- Campaign receipts do not approve a mission, replace project evidence or count replay as new
  knowledge. No automatic campaign, installation, publishing, scheduler or human confirmation is added.
- YAML remains canonical. SQLite is a testing-method reference; all prior authority, anti-inflation,
  evidence/claim ceilings, honest-retraction and anti-rework rules remain in force.
