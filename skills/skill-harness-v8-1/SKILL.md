---
name: skill-harness-v8-1
description: "VeriMission Control 8.1: coordinate long-running projects with persistent evidence, mission controls, graph projections, PR reports, and optional agent-run and cost imports. Use when adopting the harness or resuming an existing mission."
metadata:
  display-name: VeriMission Control 8.1
  version: "8.1"
---

# Using the Control 8.1 skill

Resolve resources relative to this skill folder. Keep every module in scripts/. Use an absolute executor path and point --project to the real project root, never the skill directory. Python 3.11+ and PyYAML 6.x are required; install with requirements.txt.

For an existing YAML mission, run resume and validate before planning. For a legacy SQLite mission without YAML, use migrate-sqlite once; the source is preserved. For a new mission, fill assets/templates/mission.example.json and plan.example.json with real data and reviewed commands.

Consult [references/v81-projections-and-runs.md](references/v81-projections-and-runs.md) before graph/report/run imports. Use the run-import template in assets/templates/. Historical references in references/ retain their original language and protocols; the current core below takes precedence for adapted behavior.

The execution pattern is:
`python /absolute/path/scripts/harness.py --project /project COMMAND`.

Typical cycle: review → start → check selected criteria → close → validate. On an existing mission, recover before repeating. For simple explanatory questions, answer directly without manufacturing execution cycles. Installation does not enable always-on behavior or grant permission to change global host settings.

# VeriMission Control 8.1 — core operating rules

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
