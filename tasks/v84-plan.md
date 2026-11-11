# Control 8.4 — evidence-qualified quantities

Authorized: implement the agreed neutral/Decompile split, retain all prior behavior, test inflation
and package local ZIPs. No installation, publishing, live mission revision or schedules.

## Contract and responsibility

One optional `measurement_policy` governs one mission quantity. It pins a universe of unique
unit IDs/physical identities/deliverable paths, exclusions, verifier/context resources and declared
input patterns. It names a measurement criterion, required neutral gate names, acceptance minimum,
fresh output pattern, and a separate audit criterion/cadence/sample size. Normal mission-revision
authorization is reused. No C, firmware grade, address map or compiler becomes a harness requirement.

The measurement command emits a complete neutral report over the fixed live universe, bound to a
fresh execution ID/context. Every qualified unit has all required gates and current physical
artifacts, including its universe-bound deliverable. Numbers are derived from unique eligible IDs;
claimed counts must agree. Outputs preserve pending/failed observations rather than pretending
unfinished work is done. The whole source set is checked before/after a check; current read views
recheck per-unit dependencies without executing anything or rewriting history.

The existing single execution hook is composed with 8.3 preservation, including governed operations.
Only successful closed cycles qualify quantities. Failed/incomplete periodic review cannot seal a
snapshot. `measurement-report` derives verified/pending/stale/excluded units from the canonical YAML
check references and physical proof, with a claim ceiling. No TSV/JSON view can promote a unit.
`cycle-boundary` makes the host's completion check explicit, without scheduler or implicit close.

Audit selection is frozen after the candidate measurement, recorded in YAML and bound to actual
unit evidence. Replanning identical inputs does not reroll a sample. The audit result must recount
the exact complete eligible set, reexecute precisely the selected units and pass healthy/known-bad
controls. Any audit failure holds the snapshot and forces full audit on recovery; history remains.
The harness validates protocol/provenance, not semantic truth or a hostile trusted verifier.

Decompile owns source qualification, compilation/output binding, execution-image/trace binding,
typed original-code/data/platform maps, dependency closure, positive/negative controls and bounded
adversarial witnesses. It emits neutral reports; integrated bars query the live harness rather than
trusting an exported JSON as current authority. Legacy grade bars remain available and explicitly
declared. Lexical `if`/`goto`/register-name rules are only triage, never completion proofs.

## Ordered slices / tests

- [x] V1: neutral contract and unit evidence tests (missing/duplicate/excluded/wrong count, stale,
  malformed or replayed reports, missing gates and deliverable bindings).
- [x] V2: native hook/start/check/close/report/acceptance integration; no policy means unchanged
  8.3 behavior; active/interrupted cycles never count; governed operation path shares the gate.
- [x] V3: frozen audit selection, exact recount, negative controls, failure hold/full recovery,
  cadence and boundary; missing reviews/outputs/timeouts cannot promote.
- [x] D1: Decompile finite verifier/evidence protocol; wrong or old loaded image, stock reentry,
  indirect unknowns, weak controls, fabricated grades and source drift refused. Valid straight-line
  source remains admissible; no universal syntax or readability oracle is claimed.
- [x] D2: adapter and live census bars; declared/verified/pending/stale remain distinct; G4-stock
  and G4-recon stay separate and old CLI/data contracts remain intact.
- [x] P1: generic and real-compiler synthetic pilots where tools exist; full harness/skill,
  Decompile and sibling regression suites; targeted guard-inversion experiments.
- [x] P2: current core/reference instructions, usage/templates, validator, manifests, ZIP CRC/SHA,
  extracted-resource parity and relocation smoke checks; report actual counts/platform limits.

Existing v8.2/v8.3 generations and actual project data are not modified. Missing compiler/emulator
capabilities stay explicit; synthetic protocol tests are not real firmware validation.

Qualification completed locally on Windows and Linux/WSL. See the dated delivery report for
actual counts, source hashes, targeted guard inversions, extracted parity and remaining trust limits.
No real firmware/macOS validation, installation, publishing or live mission revision performed.
