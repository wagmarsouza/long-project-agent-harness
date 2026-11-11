# Control 8.1 projections and run records

## Graph

`graph --format json|mermaid|dot [--output FILE]` produces a read-only projection of declared mission, requirement, criterion, task, cycle, and claim relationships. JSON contains the complete source witness; rendered formats include revision and payload hash. Stored status is not proof of current semantic correctness. The drawing neither adds dependencies nor proves relationship completeness.

HTML is omitted: interoperable text formats support inspection and external rendering without another application or state store.

## PR report

`report-pr --base REF --head REF --format json|markdown [--output FILE]` resolves refs to commits and reads Git diff without a shell. It includes current scope, state audit, traceability, checks, artifact hashes, claims, retractions, and explicit coverage denominators. File coverage stays indeterminate without a declared file-to-criterion mapping.

Human review must assess test discrimination, authorized scope, exclusions, and claim ceilings. The command does not create, approve, or merge a PR. Hashes establish content identity rather than semantic sufficiency or human identity. Rendered output preserves existing files.

## Explicit run import

`adapter-template --agent codex|opencode|claude|hermes` returns the neutral input shape. Fill the run-import template and use `run-import --agent AGENT --input FILE.json`.

Required fields: format, id, agent, source, status, started_at, ended_at, attempt, retry_of, usage, subagents, notes. Format must be `verimission-explicit-run-v1`. Source requires a project-relative file, declared export format, and record locator. The executor hashes that file. It records `native_format_parsed: false`; source content is not automatically interpreted or authenticated.

States: completed, failed, interrupted, unknown. Timestamps include a timezone. Completed/failed require an end timestamp. IDs are immutable. Referenced retries and subagents must already exist. Import child runs before their parent. An unknown result does not authorize replay or repeat execution.

Each usage row identifies provider and model, observed input/output/cache-read/cache-write counters (null when unknown), and cost with status, amount_usd, method, pricing_ref.

| Cost state | Amount | Evidence |
| --- | --- | --- |
| actual | Finite nonnegative USD | Provider receipt or equivalent reference |
| estimated | Finite nonnegative USD | Reproducible method and pricing reference |
| unpriced | null | Explain why pricing is unavailable |

Zero means an observed zero. Missing data remains null. Do not disguise a guess as a measured value.

## Cost summary

`cost-summary` separates actual and estimated totals, counts unpriced rows and unreported token fields, and exposes retries, cache usage, and subagent links. Totals cover imported records only. Parent/child billing may overlap; inspect billing boundaries before treating their sum as a bill.

Imports do not dispatch agents, change models, approve actions, alter missions, promote claims, or replay unknown operations. These controls apply in both light and strict modes.
