# VeriMission Core 7.8

V7.8 is the portable core for projects that span many conversations or sessions. It freezes a mission with an objective, scope, exclusions, executable criteria, and budget; records investigation cycles; runs checks; stores artifact hashes; supports claims and retractions; prevents verified closure without current evidence; and provides resumption, export, and backup.

Its central loop is: recover before repeating, review prior evidence, plan the hypothesis and test, work within scope, verify against criteria, and close with a concrete next step. Claim ceilings, coverage denominators, and honesty audits limit permitted conclusions. The executor improves provenance but cannot automatically detect dishonesty or judge the semantic sufficiency of a test.

## Choose this version when

- the project is long, but its task graph can remain outside the executor;
- you want a smaller, stable core;
- you need explicit mission revision, retractions, and anti-rework controls;
- you do not need V7.9 capsules and evidence scope or V8.0 coordination.

## Commands

```text
init migrate-sqlite start claim retract step-back consolidate
preview-mission revise-mission review check close interrupt
resume validate metrics export backup
```

```powershell
$h = '.\harnesses\v7.8\scripts\harness.py'
$p = 'C:\project'
python -B $h --project $p init --input "$p\mission.json"
python -B $h --project $p review --topic 'component'
python -B $h --project $p start --input "$p\plan.json"
python -B $h --project $p check --cycle 1 --criterion C1
python -B $h --project $p close --cycle 1 --outcome verified --next 'Concrete next step'
python -B $h --project $p validate
```

For a project created by an earlier SQLite publication, preserve `.harness/state.sqlite` and run `migrate-sqlite` once. Validate immediately afterwards. YAML becomes canonical and SQLite remains preserved only as the legacy source.

Mission revision is exceptional. Run `preview-mission` first. `revise-mission` requires an explicit user request or authorisation and personal interactive confirmation; never automate that confirmation.

Use [skills/skill-harness-v7-8](../skills/skill-harness-v7-8/) and invoke `skill-harness-v7-8`.
