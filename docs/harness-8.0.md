# VeriMission Control 8.0

V8.0 is designed for extensive missions with several workstreams and dependencies. It preserves V7.9 and adds a task graph, revalidatable claims, aliases and search, diagnostics, task-specific context, a traceability matrix, final mission assessment, and an optional local adapter for governed operations.

V8 is not a daemon and does not intercept every agent tool. `task-ready` reports eligibility; it does not dispatch work. `accept-mission` evaluates the declared contract; it does not guarantee universal correctness. Approval for an operation applies only to that exact operation and never authorises a mission change.

## Command groups

```text
init migrate-sqlite review start check close interrupt resume validate
claim retract claim-reverify step-back consolidate
evidence-scope evidence-scopes prepare-mission capsule capsule-status
metrics export backup preview-mission revise-mission
```

```text
task-add task-claim task-complete task-reopen tasks task-ready
alias-add search context-pack view-status diagnostic-add
trace traceability accept-mission capabilities usage-report
```

```text
operation-prepare operation-status operation-approve operation-run operation-reconcile
```

```powershell
$h = '.\harnesses\v8.0\scripts\harness.py'
$p = 'C:\project'
python -B $h --project $p init --input "$p\mission.json"
python -B $h --project $p task-add --input "$p\task.json"
python -B $h --project $p task-ready
python -B $h --project $p review --topic 'component'
python -B $h --project $p start --input "$p\plan.json"
python -B $h --project $p check --cycle 1 --criterion C1
python -B $h --project $p close --cycle 1 --outcome verified --next 'Next task'
python -B $h --project $p traceability
python -B $h --project $p accept-mission --output "$p\ACCEPTANCE.json"
python -B $h --project $p validate
```

Use `--help` after any subcommand for published parameters. Never answer an interactive confirmation on the user's behalf and never search for a `--yes` bypass.

Use [skills/skill-harness-v8-0](../skills/skill-harness-v8-0/) and invoke `skill-harness-v8-0`.
