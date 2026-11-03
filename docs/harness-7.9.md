# VeriMission Continuity 7.9

V7.9 preserves the V7.8 core and adds three mechanisms for work that spans many sessions:

- `evidence-scope` binds a real check to what it verifies, what it does not verify, its limitations, and coverage;
- `capsule` and `capsule-status` create a compact resumption view and check whether it still matches canonical state;
- `prepare-mission` structures a mission proposal without initialising, approving, or executing it.

These features do not promote results to facts. A capsule is a derived view; YAML remains canonical. `prepare-mission` produces a draft, not authorisation. `semantic_truth_verified` remains false for evidence-scope declarations.

## Additional commands

In addition to V7.8:

```text
evidence-scope evidence-scopes prepare-mission capsule capsule-status
```

```powershell
$h = '.\harnesses\v7.9\scripts\harness.py'
$p = 'C:\project'
python -B $h --project $p resume
python -B $h --project $p validate
python -B $h --project $p evidence-scope --input "$p\evidence-scope.json"
python -B $h --project $p capsule --output "$p\CAPSULE.json"
python -B $h --project $p capsule-status --input "$p\CAPSULE.json"
python -B $h --project $p prepare-mission --input "$p\mission-request.json" --output "$p\DRAFT.json"
```

Review the draft and transfer only an approved proposal into the mission template before `init`. The command does not authorise actions or change an active mission.

Use [skills/skill-harness-v7-9](../skills/skill-harness-v7-9/) and invoke `skill-harness-v7-9`.
