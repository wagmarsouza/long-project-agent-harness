# Native periodic review — Control 8.2

VeriMission is a general long-project harness. Digest production, reconciliation and protected review are built into the executor and require no domain repository, agent SDK, cron or service. Specialist tools may export observations, but are optional. Nothing is installed, scheduled or activated by these commands.

## Adopt deliberately

Python 3.11+ and PyYAML 6.x remain the requirements. An 8.1 YAML mission without `periodic_review` retains its previous behavior; do not reinitialize it. To enable the feature, the user uses the existing explicit `preview-mission` / interactive `revise-mission` workflow. Automation cannot perform that revision.

Choose `anchor` deliberately when adopting into an existing mission, normally the last closed cycle. Boundaries are `anchor + N`, `anchor + 2N`, etc. A boundary ending at cycle C covers exactly `[C-N+1, C]`. Cadence is in harness cycles, never wall-clock time or a domain-specific numbering convention. `every` must match the mission's `budget.consolidate_every` so there is one cadence, not two schedules.

The governing file must already have two uniquely delimited mutable sections: `objectives` and `scenario`. Its initial protected content must be reviewed before adoption. The rest of the document, including later safeguards present at adoption, is fingerprinted and frozen. Marker presence alone is not enough: weakening a sentence while retaining its marker also fails.

## Contract fields

Add the policy from `templates/periodic-policy.example.json` under `periodic_review` in the mission. All filenames, markers, categories, denominators and section delimiters are project configuration. Notes must have a distinct physical file per cycle. Relative patterns allow integer `{cycle}`, `{start}` and `{end}` placeholders, including padding such as `{cycle:04d}`; paths cannot leave the project.

Optional inventory reconciliation requires `inventory`, `observation_pattern` and `baseline` together. No inventory is required for a research, writing, software or other general project. In that case the digest explicitly states that inventory arithmetic is not applicable; it does not invent coverage or a denominator.

For inventories, `categories` is an ordered list of declared maturity states and `total` is the fixed universe size. `monotonic` can be a list of single-category counters or a mapping of counter names to category groups, such as `{"completed": ["implemented", "verified"]}`. The engine records real negative deltas; it does not redefine a metric to make it increase.

## Physical inputs and honest reconciliation

Each note is physically read as bytes, hashed and included verbatim in the digest artifact. The producer never substitutes a chat summary for that file. Notes/observations are pinned at cycle closure; the initial inventory baseline is pinned at adoption. Closed sources cannot be silently rewritten. Put corrections in later notes and explicit retraction records.

An observation JSON contains `cycle`, `live` and `closed` mappings from stable item IDs to categories, plus `transitions`. Optional `facts_recorded` and `facts_used` are labels for surfacing possible lost context, not assertions that a fact is true.

The native producer checks:

- Conservation against the configured denominator and stable ID universe.
- No unknown/unmarked categories and no unmarked upward transitions.
- Equality of live and closed states by item identity, not only equal totals.
- Declared counter changes and downward transitions.
- Hashed transition evidence, with optional links to existing claim provenance.
- Possible facts dropped from use across the window.

A transition receipt identifies the exact item, before/after categories, `kind` (`progress` or `retraction`), reason and current hashed evidence files. A justified retraction may lower a counter and is reported as such; it is not counted as progress or silently erased. An unexplained regression blocks. File hashes and arithmetic establish declared consistency/provenance, not semantic truth. No claim is promoted automatically.

## Closing a boundary

Use the normal pattern with an absolute executor path:

```text
python /path/to/scripts/harness.py --project /project digest --through-cycle 10
python /path/to/scripts/harness.py --project /project decade-review --through-cycle 10 --input /project/review.json
python /path/to/scripts/harness.py --project /project close --cycle 10 --outcome verified --next "Next bounded target"
```

`close` itself invokes the native producer and review gate at the boundary. The explicit `digest` command is convenient for preparing the review in advance; it is not an external requirement. A first close without a review produces the digest, saves a structured pending event and exits 2, leaving the cycle active. It cannot pretend a semantic review occurred merely because a digest exists.

Read every original note or its verbatim copy in the digest artifact. Fill `templates/periodic-review.example.json` with the actual window, digest SHA, current prompt SHA, one substantive finding and matching note hash per cycle, a reason, optional objectives/scenario replacements, and explanations for every possible lost fact. Empty updates explicitly mean “reviewed and unchanged.” Do not fabricate a reread declaration.

The `digest` response includes a `review_template` with current hashes and deliberately blank findings/reason. It is a draft, not a successful reread receipt; fill it only after physically reading the notes.

You may supply the prepared review with `close --review-input /project/review.json`. Successful review and verified checks complete the boundary and automatically append consolidation in the same canonical state update. The mission, scope, criteria, claims and previous records are not rewritten. If a prompt update changes a declared check artifact, run the affected check and refresh the digest/review before verified closure.

An interrupted cycle remains stoppable. Resuming past an interrupted boundary still requires its digest/review and consolidation; interruption does not bypass the gate. Missing sources at interruption are recorded as unavailable, not invented. Recovery can require restoring the original source or an explicit user-authorized adoption/revision with a suitable anchor.

## Tripwire, stale references and restoration

The review verifies the registered digest artifact and exact window, rereads source files to verify freshness, and checks the complete protected instruction fingerprint. Missing, modified, stale or wrong-window digests refuse with exit 2. A non-boundary `decade-review` is a real no-op, including no timing write to the YAML store.

Only section bodies may change. Unknown update keys, duplicate/nested delimiters, stale proposals, core edits and stale markers remaining after review are refused. Stale references outside permitted sections cannot be automatically edited; they need an explicitly reviewed contract/instruction change, never silent expansion of the mutable region.

A review can retarget instructions only at the current cycle boundary. A historical digest may be inspected, but an old window cannot rewrite objectives after work has advanced to later cycles.

A user-authorized mission revision starts a new periodic epoch. Its proposal must explicitly set `anchor` to the current number of cycles and, if inventory is enabled, supply a baseline observation for exactly that cycle. Initialization requires anchor zero. The new cadence counts forward from this anchor, while previous cycles, digests, declarations, consumed budgets and revision history remain preserved. Earlier conclusions still need revalidation under the revised mission. A revision cannot silently rebaseline changed protected instructions; restore the existing core first. This release deliberately refuses protected-core rewrites even within a scope revision.

```text
python /path/to/scripts/harness.py --project /project restore-prompt
```

Restoration uses the last trusted snapshot and preserves the damaged bytes in the canonical YAML. A damaged core blocks new starts, checks and governed-operation bindings until restored. Read-only recovery and explicit interruption remain available. The tool does not intercept unrelated host tools.

## Audit, recovery and limits

The canonical `.harness/state.yaml` holds digest versions, pinned source hashes, review declarations, prompt repair history and structured `events`. Events distinguish produced, pending, failed, passed, restored and consolidated states. A tripwire not reached is recorded as null, not a pass. Derived digest files do not form a second authoritative ledger.

File replacement and YAML commit are not one cross-file OS transaction. An interrupted update can leave a prompt whose permitted bodies changed before the review receipt was committed. Hash binding causes a fresh review/recovery to be required; it does not authorize proceeding. Restore from the trusted snapshot or inspect the actual result before retrying. Never replay an unknown external operation to learn its outcome.

Reread findings are declarations, not authentication of cognition. A weak test may pass; a fabricated input file can still misrepresent reality. Checksums detect byte drift, not a malicious operator who controls code and state. No native agent dispatch, model selection, autonomous mission revision, global installation, live-project migration or new schedule is introduced.
