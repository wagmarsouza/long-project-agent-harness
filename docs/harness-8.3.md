# VeriMission Control 8.3 — local development preview

Control 8.3 adds opt-in, case-level preservation of previously accepted obligations to the complete
8.2 harness. Nothing in this preview installs a skill, migrates a live mission, schedules work or
publishes a release. The 8.2 generation remains unchanged.

Preservation complements the existing anti-inflation, evidence/claim ceilings, retractions,
mission-revision human gate, anti-rework controls, YAML recovery and native periodic review.
Missing cases cannot be compensated by additional passes. A skip, timeout or incomplete report
cannot silently replace an earlier required pass. Protected tests/oracles and contexts are pinned.

Use [the complete preservation guide](../harnesses/v8.3/references/v83-preservation.md) before
configuring policy or adopting a baseline. For periodic notes/inventories and prompt recovery,
the inherited [8.2 guide](../harnesses/v8.3/references/v82-periodic-review.md) remains applicable.
Binary tools remain independent optional providers in DisasmLedger; no solver or emulator is required.

The updated local preview also includes explicit finite [verifier assurance campaigns](../harnesses/v8.3/references/v83-assurance.md):
known-bad controls with expected diagnoses, independent lifecycle programs and a 36-scenario YAML
persistence sweep (18 abrupt worker terminations). Run `harness.py assurance --suite all` without
`--project`. The canonical store remains YAML; no SQLite storage or background loop is introduced.

```powershell
$h = (Resolve-Path '.\harnesses\v8.3\scripts\harness.py').Path
python -B $h --project C:\your-project resume
python -B $h --project C:\your-project validate
python -B $h --project C:\your-project regression-plan
python -B $h --project C:\your-project regression-report
python -B $h --project C:\your-project baseline-preview --input C:\your-project\proposed-mission.json
```

These commands inspect status/proposals; they do not adopt a new mission or run acceptance commands.
`passed` in the assessment is the verdict; read-command success is not a preservation pass.
Use the existing review/start/check/close workflow. A verified close now enforces the configured
preservation obligations natively. Existing missions without this policy retain the previous workflow.

For a genuinely new authorized mission, prepare the templates with real paths, hashes, case IDs,
oracles and command effects. For an existing mission, adoption uses the already explicit human
mission-revision workflow. Do not reinitialize it or reset consumed budgets/history.

```powershell
python -B -m unittest discover -s harnesses/v8.3/tests
python -B harnesses/v8.3/examples/run_regression_pilot.py
```

The pilots use temporary synthetic software and research-record fixtures. Their assertions validate
the control mechanism, not a real application, literature review, firmware or arbitrary prose.
Hash identities/receipts do not authenticate a person, runner honesty, cognition or semantic truth.

The skill ID is `skill-harness-v8-3`; request it in natural language after a separate authorized
installation. There is no host-independent slash command. No installation is performed by packaging.
