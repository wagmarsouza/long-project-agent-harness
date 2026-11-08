# VeriMission Control 8.2 — public preview 1

Repository release `v2.2.0-rc.1`; harness/skill generation **8.2**. These numbers identify the
repository publication and harness generation respectively.

## Result

Control 8.2 adds a self-contained, domain-neutral digest producer and protected periodic review
at the configured `close` boundary. Physical notes, optional inventory observations, conservation,
explicit transitions, justified retractions, possible losses and governing instructions are bound
to the review. Only declared immediate-objective/scenario bodies can be updated by this workflow.
Damaged protected text can be restored while preserving the damaged copy and structured audit.

Claims, retractions, coverage denominators, claim ceilings, anti-rework controls and explicit human
mission-revision authorization remain. DisasmLedger is an optional exporter, not a dependency.
Existing missions without the periodic policy retain the earlier behavior; do not reinitialize them.

## Contents and use

- `VeriMission-8.2-preview.zip`: harness, standalone skill, tests, templates and guides.
- `skill-harness-v8_2.zip`: standalone `skill-harness-v8-2` folder.
- `harness_v8.2.zip`: standalone harness folder.

From a source checkout at this tag:

```powershell
python -B harnesses/v8.2/scripts/harness.py --help
python -B harnesses/v8.2/scripts/harness.py --project C:\your-project resume
python -B harnesses/v8.2/scripts/harness.py --project C:\your-project validate
python -B harnesses/v8.2/examples/run_periodic_pilot.py
python -B -m unittest discover -s harnesses/v8.2/tests
```

Python 3.11+ and PyYAML 6.x are required. Follow [the guide](harness-8.2.md) to configure an opt-in
policy or initialize a genuinely new authorized mission. Never apply example criteria blindly.
To request the skill in a compatible host after a separate authorized installation, say:
`Use skill-harness-v8-2 for this project; preserve the authorized mission and inspect live evidence.`
There is no universal slash command. Publishing does not activate the skill locally.

The complete harness suite passed **163 tests**, including **35 periodic-review tests**. The
standalone periodic suite and general/periodic pilots passed. Recovery and unchanged-core controls
were exercised with synthetic projects.

## Release verification and limits

The pre-publication extracted-package run executed 339 primary tests: 338 passed and one existing
Windows symlink test was skipped in Binary Analysis Profile. Repeated standalone runs are not
counted as additional independent tests. Five targeted control-inversion experiments were caught
by their focused tests; this is not a global mutation score or an independent audit.

Only publication documentation and package metadata changed after that run. Release packaging
checks every previously tested runtime/resource file against the reviewed snapshot and verifies
ZIP paths, manifests, byte counts and SHA-256 hashes. The release receipt distinguishes the tested
commit from the publication commit; no fresh runtime test run is claimed for documentation edits.

Validation used synthetic fixtures on Windows. No Linux/macOS matrix, real firmware, ARM compiler,
Renode/Unicorn/Ghidra/angr engine or live mission/memory was exercised. Hashes and consistency checks
do not authenticate authorship, cognition or semantic truth. Extraction does not install a skill,
start a scheduler or grant new permissions. Existing releases remain available.

Earlier verification documents are historical reports about the development stage and its older
archives. Use this release's per-project `SHA256SUMS.txt`, `RELEASE_RECEIPT.json` and ZIP manifests
for the published artifacts. The previously reviewed local delivery remains preserved.
