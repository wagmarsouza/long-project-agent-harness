# VeriMission Control 8.4 — Preview 1

Control 8.4 retains the entire 8.3 core and adds optional evidence-qualified unit counts for
general long projects. Canonical mission state remains YAML. No compiler, emulator, provider,
decompilation grade or domain tool becomes a core harness requirement.

## Downloads

- [Harness 8.4](https://github.com/wagmarsouza/long-project-agent-harness/releases/download/v2.4.0-rc.1/harness_v8.4.zip)
- [Skill 8.4](https://github.com/wagmarsouza/long-project-agent-harness/releases/download/v2.4.0-rc.1/skill-harness-v8_4.zip)
- [Complete sources](https://github.com/wagmarsouza/long-project-agent-harness/releases/download/v2.4.0-rc.1/VeriMission-8.4-preview.zip)

Use RELEASE_RECEIPT.json and SHA256SUMS.txt for the publication commit, tested resource snapshot,
actual qualification evidence and archive identities. Earlier release reports are historical.

## What changed

- `measurement_policy` pins the physical universe, deliverables, dependency closure, exclusions,
  required gates, executable verifier, audit cadence and relevant context. A headline cannot
  replace the exact eligible ID set; missing, duplicate, stale or replayed evidence cannot qualify.
- Only verified `close` seals quantities, after required checks and native periodic review.
  `measurement-report` rereads physical proof and exposes verified/pending/stale/excluded units
  plus a current claim ceiling. An active/interrupted cycle cannot promote a quantity.
- Adversarial audit plans freeze selected IDs, require a full eligible-set recount, fresh selected
  executions and healthy/known-bad controls. Failure holds eligibility and requires full recovery.
- Restoring/revalidating the same physical identity is not a newly discovered unit. Existing
  preservation, claims, retractions, coverage, anti-rework gates and explicit mission revision remain.

## Use without installation

Python 3.11+ and PyYAML6.x are required. Extract a complete package into a tools directory,
separate from the project. Merely extracting/publishing does not install or activate a skill.

```powershell
$h = 'C:/tools/harness_v8.4/scripts/harness.py'
$p = 'C:/your-project'
python -B $h --project $p resume
python -B $h --project $p validate
python -B $h --project $p measurement-report
python -B $h --project $p cycle-boundary --cycle 1
```

For a skill package use its scripts/harness.py and ask your agent to read SKILL.md explicitly.
Identifier: `skill-harness-v8-4`. There is no host-independent slash command. Installation and
activation remain separate user decisions. We did not install anything to publish this version.

Normal flow: review → start → check → close → validate. Adopt the policy in a new authorized
mission or through explicit human mission revision. Never reinitialize an existing mission or
edit state.yaml. Read [the complete guide](../harnesses/v8.4/references/v84-measurements.md)
for templates, M/A criteria, frozen selection and `measurement-audit-plan --cycle N [--full]`.
The host must actually enforce close/cycle-boundary; actions bypassing the CLI are not intercepted.

Optional domain counterpart: [Decompile2.0](https://github.com/wagmarsouza/disasmledger/releases/tag/decompile-v2.0.0).
The specialist supplies source/build/execution gates and bars; the harness governs mission evidence.

## Executed qualification and limits

The qualified runtime snapshot is `18e6ae584dd17080744705d1a6d7b561b7ce3e62`. Windows/Python3.12
and Ubuntu/WSL/Python3.14 each passed 292 tests (harness and identical skill resources respectively).
Targeted guard inversions detected scalar inflation and premature promotion. Four inversions
across both projects were detected; this is not a global mutation score or independent human audit.
The integrated pilot passed with synthetic tools on Windows and real GCC/process execution on Linux.
It is not firmware/ARM/hardware validation. Initial Linux infrastructure timeouts were preserved;
moving test resources wholly to Linux and repeating without weakening limits/gates passed.

Publication edits affect metadata, docs and CI routing. Runtime resources are compared with the
qualified snapshot. Hosted checks are reported separately by actual run URL/result; a declared
matrix is not evidence of execution. The CI coordinator retains its old default and accepts
`python -B tasks/ci_v83.py --generation 8.4 --output NEW_DIRECTORY` for the new generation.

Hashes establish physical binding/freshness, not honest semantic review. Trusted runner/reviewer,
complete inputs and finite witnesses remain explicit dependencies. Sampling is not universal proof.
The existing reuse-license policy remains unchanged: no general reuse license has been selected.
Older releases remain available; publishing performs no live mission migration or host installation.
