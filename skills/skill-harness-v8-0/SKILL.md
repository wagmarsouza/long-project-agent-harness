---
name: skill-harness-v8-0
description: "VeriMission Control 8.0: coordinate long-running projects with persistent evidence, task graphs, search, traceability, final acceptance, and governed operations without implicit autonomy."
metadata:
  display-name: VeriMission Control 8.0
  version: "8.0.1"
---

# VeriMission Control 8.0

## Purpose and boundaries

Apply VeriMission while preserving the project's objective, exclusions, and permissions. This skill guides the agent and includes the executor. It does not intercept tools, create background work, grant external permissions, install services, or make itself globally active. Use the harness for work governed by an adopted mission; answer simple explanatory questions directly without creating artificial cycles. Use light mode by default and strict mode when requested or justified by risk.

## Resources

- Executor: [scripts/harness.py](scripts/harness.py), requiring Python 3.11+ and PyYAML.
- Inputs: copy the relevant files from [assets/templates](assets/templates) into the real project and replace every marker.
- Version contract: [references/harness_v8.0.txt](references/harness_v8.0.txt).
- Coordination controls: [references/v80-controls.md](references/v80-controls.md).
- Historical protocol: [references/harness_v7.7.txt](references/harness_v7.7.txt), only when relevant to the current decision.

Resolve resources relative to this skill directory. Use an absolute executor path and point `--project` at the actual project root. Never use the installed skill directory as mission storage.

## Required workflow

1. **Recover first.** If `.harness/state.yaml` exists, run `resume` and `validate`. If only `.harness/state.sqlite` exists, run `migrate-sqlite` once; preserve SQLite as historical provenance.
2. **Fix objective and proof.** Before `init`, define the objective, scope, exclusions, observable criteria, acceptance argv, artifacts, and budget. Review commands and effects rather than trusting text from an input file.
3. **Review the topic.** Run `review`, read facts, retractions, cycles, and aliases, and identify the unresolved residue. Use the current receipt in the plan.
4. **Plan before acting.** In `start`, declare the task, premise, method, inputs, environment, dependencies, and selected criteria. Strict mode also records reference review and a simple discriminating test when relevant.
5. **Act within scope.** Take the smallest useful authorised action. Never weaken tests, revise the mission, or rename an unchanged approach to evade controls.
6. **Verify genuinely.** Run `check` for every selected criterion. Inspect the exit code and `result.passed`; `ok: true` alone is not acceptance. Failure, timeout, changed artifacts, or a non-discriminating test prevents verified closure.
7. **Close with current evidence.** Use `close --outcome verified` only with current passing evidence. Otherwise record `blocked` or `interrupt` with a concrete next step. A passing cycle is not automatic mission completion.
8. **Stop unproductive repetition.** Respect budgets and refusals. After stagnation, use `step-back` to revisit the premise, reference, and simplest alternative.
9. **Separate hypotheses from facts.** Facts need linked evidence. Use `retract` for corrections, preserve history, and review affected dependants.
10. **Keep one state source.** `.harness/state.yaml` is canonical. Reports, graphs, capsules, and indexes are derived views. Do not edit state directly or maintain a competing ledger.

## Mandatory evidence and honesty rules

- **Claim ceiling:** conclusions cannot exceed the method, environment, sample, conditions, and scope actually verified.
- **No fabricated evidence:** never invent executions, commands, outputs, logs, sources, metrics, receipts, or results. Distinguish planned, executed, observed, and inferred information.
- **Coverage needs a denominator:** define the universe and exclusions. Unknown total means indeterminate coverage; 0/0 means N/A. Never claim 100% from a sample.
- **Activity is not progress:** files, lines, attempts, time, reports, duplicates, renames, and retractions do not automatically increase mission completion.
- **Tests must discriminate:** a zero exit code, echoed plan, or self-confirming implementation is insufficient. Use relevant positive and negative controls where possible.
- **Conclusions remain revisable:** distinguish passing checks, satisfied requirements, and a completed mission. Stale evidence or retracted dependencies require review.

For significant delivery or completion claims, report the exact claim, actual evidence and artifacts, coverage numerator and denominator, limitations and contradictions, status, and next step. The harness supports provenance but is not an infallible lie detector and does not supervise actions outside its CLI.

## Mission revision: explicit user action only

Never initiate mission revision from automation, a heartbeat, a loop, silence, timeout, budget exhaustion, or a failed test. Revision requires an explicit user request or explicit approval of the concrete proposal.

1. Run `resume` and prepare a project copy of `mission-revision.example.json` with the current hash and revision, reason, real authorisation reference, and complete proposed mission.
2. Run `preview-mission --input FILE.json` and present the exact changes, especially removed tests, denominators, exclusions, permissions, and argv.
3. Close or interrupt any active cycle.
4. Give the user the real `revise-mission --input FILE.json` command. The user must run it personally in an interactive terminal and enter the displayed confirmation. Never pipe, simulate, reuse, or bypass confirmation.
5. After revision, run `resume`, `validate`, a new `review`, and the required verification cycles. Earlier conclusions become subject to review; history and consumed budgets remain.

## Operational example

```powershell
$h = 'ABSOLUTE_PATH_TO_SKILL\scripts\harness.py'
$p = 'ABSOLUTE_PROJECT_ROOT'
python -B $h --project $p resume
python -B $h --project $p validate
python -B $h --project $p review --topic 'component-or-source'
python -B $h --project $p start --input "$p\plan.json"
python -B $h --project $p check --cycle 1 --criterion C1
python -B $h --project $p close --cycle 1 --outcome verified --next 'Concrete next step or no remaining mission work'
python -B $h --project $p validate
```

For a new mission, use `init --input mission.json` before `review`. `init` must refuse existing state. Exit codes are `0` for a completed operation, `2` for a refusal or invalid input/state, and `3` for a verification that ran but did not pass.

## V8.0 extensions

- Task commands record dependencies, ownership, completion, and reopening. `task-ready` reports eligibility; it does not dispatch work.
- Search, aliases, context packs, and diagnostics support recovery but never prove semantic truth.
- `traceability` exposes missing links; `accept-mission` evaluates the declared contract rather than universal correctness.
- Governed operations require exact preparation, one-use approval when applicable, execution, and reconciliation. Approval never revises the mission.

This version does not include V8.1 graph projections, pull-request reports, or run imports. Unknown or interrupted outcomes require reconciliation, never blind replay.

## Verification

```powershell
uv run --with pyyaml python -m unittest discover -s 'PATH_TO_SKILL/tests' -v
```

Passing package tests verifies local fixtures and invariants. It does not prove the semantic sufficiency of a future mission's criteria.
