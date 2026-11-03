# V7.9 continuity features

V7.9 preserves the complete V7.8 lifecycle and adds three optional, non-authoritative mechanisms. None of them promotes a result to semantic truth, changes a mission, grants permission, or starts background work.

## Evidence scope

`evidence-scope --input FILE.json` binds a declaration to an actual recorded check. Describe what the check verifies, what it does not verify, limitations, and coverage over a defined universe. The executor verifies references and arithmetic but cannot judge whether the test is semantically sufficient. `semantic_truth_verified` remains false.

Use `evidence-scopes` to review declarations. Do not use a scope statement as a replacement for the check, artifacts, or conclusion. Preserve failed cases and unknown denominators. If the evidence changes or becomes stale, review the declaration and its dependants.

## Resumption capsules

`capsule --output FILE.json` creates a bounded view of the canonical mission, active work, recent checks, claims, retractions, limits, and next steps. `capsule-status --input FILE.json` compares its source identity with current state.

A capsule is a derived view. It may omit items with explicit counts and can become stale. It cannot be imported as canonical state, mission authority, permanent memory, or user approval. When it conflicts with YAML, `resume`, or original evidence, canonical state and the original records prevail.

## Mission preparation

`prepare-mission --input REQUEST.json --output DRAFT.json` turns a structured request into a reviewable draft with questions and proposed criteria. It does not run commands, initialise state, revise an existing mission, or approve the proposal. `ready_for_review` means only that the draft is structurally ready for human review.

Dependencies and technical approaches must not be invented merely to fill fields. After approval, transfer the accepted content into the mission template and review all argv and artifacts before `init`. Changes to an active mission still require the explicit, interactive revision workflow.

## Commands

```powershell
python -B $h --project $p evidence-scope --input "$p\evidence-scope.json"
python -B $h --project $p evidence-scopes
python -B $h --project $p capsule --output "$p\CAPSULE.json"
python -B $h --project $p capsule-status --input "$p\CAPSULE.json"
python -B $h --project $p prepare-mission --input "$p\mission-request.json" --output "$p\DRAFT.json"
```

These capabilities improve continuity and make proof boundaries explicit. They do not remove the need for review, discriminating tests, coverage denominators, claim ceilings, and current evidence.
