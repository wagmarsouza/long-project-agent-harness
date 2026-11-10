# VeriMission Control 8.3 — Preview 1

Control 8.3 adds opt-in native antiregression gates to the full 8.2 core: pinned baselines and
oracles, complete case-level results, current-context proof, conservative impact reuse and
non-compensating comparisons. Missing, skipped, timed-out or changed cases cannot be hidden by
additional passes. Claim ceilings, retractions, coverage denominators, explicit mission revisions,
anti-rework controls, canonical YAML recovery and protected periodic review remain in place.

[Release and downloads](https://github.com/wagmarsouza/long-project-agent-harness/releases/tag/v2.3.0-rc.1)

## Packages

- [Standalone harness](https://github.com/wagmarsouza/long-project-agent-harness/releases/download/v2.3.0-rc.1/harness_v8.3.zip)
- [Standalone skill](https://github.com/wagmarsouza/long-project-agent-harness/releases/download/v2.3.0-rc.1/skill-harness-v8_3.zip)
- [Complete package](https://github.com/wagmarsouza/long-project-agent-harness/releases/download/v2.3.0-rc.1/VeriMission-8.3-preview.zip)

Each package contains USO.md, references, tests and a SHA-256 manifest. Release assets include
SHA256SUMS.txt and RELEASE_RECEIPT.json. Keep the complete selected folder, including its scripts.
Python 3.11+ and PyYAML 6.x are required; qualification pins PyYAML 6.0.3. No binary-analysis engine,
emulator, solver or provider account is required for the general harness.

## Quick start

Extract the standalone harness into its own directory, open a terminal there and run:

```powershell
python -m pip install -r requirements.txt
python -B scripts/harness.py --help
python -B scripts/harness.py --project C:\your-project resume
python -B scripts/harness.py --project C:\your-project validate
python -B scripts/harness.py --project C:\your-project regression-plan
python -B scripts/harness.py --project C:\your-project regression-report
```

In the complete package, replace `scripts/harness.py` with `harnesses/v8.3/scripts/harness.py`.
Project commands assume an existing authorized mission. Do not reinitialize it. For a genuinely
new mission, adapt the mission/baseline/policy templates with real paths, hashes, case IDs and
acceptance commands, then use `init --input YOUR_MISSION.json`. Templates live in `templates/`
in the harness, `assets/templates/` in the skill, or `harnesses/v8.3/templates/` in the full package.
Read [the preservation guide](../harnesses/v8.3/references/v83-preservation.md) first.

The normal sequence remains review → start → check → close → validate. Existing missions without
the opt-in policy retain the old behavior; adopting/changing policy uses the explicit human
mission-revision workflow. `baseline-preview` only inspects a proposal. Never approve a weaker
baseline automatically to obtain green results.

To install later in a supported host, when explicitly desired:

```shell
npx skills add wagmarsouza/long-project-agent-harness --skill skill-harness-v8-3
```

Then request: `Use skill-harness-v8-3 for this project; preserve the authorized mission, resume
the current state and inspect antiregression obligations.` There is no universal slash command.
Publishing or extracting this package does not install or activate it in any host.

## Verification

The reviewed runtime commit is `243839237c4f9f446443c39479212f990d0072ba`. Both Windows 11 /
Python 3.12.10 and Ubuntu/WSL2 / Python 3.14.4 passed 259 harness tests, the same 259 tests from
the standalone skill, ten coordinator tests, full assurance, generic/periodic pilots and packaging
gates. No VeriMission tests were skipped. These repeated suites are not counted as unique tests.

A bounded run completed 100 actual start/check/close cycles with ten fresh-process resumes and
exactly one progress cycle. Seeded 1,000/5,000-vector histories separately measured YAML I/O;
they are not executed project work. Safe LibYAML acceleration retains the safe Python fallback,
schema, checksums, locks, atomic writes and proof/history guards. Six review findings were fixed
and independently re-reviewed by another agent; a fixture-import issue and cross-platform
manifest ordering issue found by actual CI were also fixed. This is not a human security audit.

Before publication, archives are checked against that reviewed runtime/resource snapshot.
Publication documentation and package metadata may change; the release receipt names both the
tested and publication commits. ZIP paths, manifests, file sizes and SHA-256 are verified, and
Relocated entry points are exercised. No full runtime rerun is claimed for documentation edits.

To reproduce checks in the complete package:

```shell
python -B tasks/ci_v83.py --output NEW_QUALIFICATION_DIRECTORY
python -B harnesses/v8.3/scripts/harness.py assurance --suite all --seed 7 --output NEW_ASSURANCE.json
```

Both commands use temporary synthetic projects and finite budgets. Assurance has nine negative
controls plus a healthy control, bounded lifecycle sequences and 36 persistence scenarios,
including 18 abrupt child-process terminations. Tests do not validate physical power loss,
all concurrent schedules, arbitrary domain truth or actions performed outside the executor.

The owner authorized publication based on Windows and Linux qualification without making macOS
a release prerequisite. Hosted CI results are separate evidence; the workflow declares three
platforms and two Python versions but its presence alone is not a pass. This remains a preview,
and no unexecuted platform or real production mission is claimed as validated.

The previous reuse policy is unchanged: no general reuse license selected. Public visibility
alone does not grant general modification/redistribution rights. Earlier releases and their
artifacts remain available; installation and live-mission migration require separate authorization.
