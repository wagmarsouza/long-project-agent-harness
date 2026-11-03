# VeriMission Control 8.1

Control 8.1 adds graph projections, reproducible PR reports, explicit run imports, and optional cost accounting. It preserves the mission contract, claims, retractions, evidence freshness, coverage denominators, claim ceilings, and anti-rework gates.

Python 3.11+ and PyYAML 6.x are required. The canonical store is `.harness/state.yaml`. Use `migrate-sqlite` once for legacy projects; it preserves the SQLite source. Existing missions must not be reinitialized.

## Commands

```text
graph --format json|mermaid|dot [--output FILE]
report-pr --base REF --head REF --format json|markdown [--output FILE]
adapter-template --agent codex|opencode|claude|hermes
run-import --agent AGENT --input FILE.json
cost-summary
```

All commands follow `python scripts/harness.py --project PROJECT COMMAND`. Output paths are project-relative. Choose a new path for Markdown, Mermaid, and DOT output.

Graphs show declared relationships. PR reports include resolved Git commits, changed files, scope, checks, hashes, claims, retractions, coverage, and pending human review. Changed-file coverage is indeterminate without explicit file-to-criterion mapping.

Adapters use explicit, hashed imports. They do not dispatch agents, select models, approve operations, revise missions, promote claims, or replay unknown outcomes. Read the [schema reference](../harnesses/v8.1/references/v81-projections-and-runs.md) and fill the run-import template with source-supported values.

Costs distinguish `actual`, `estimated`, and `unpriced`. Unknown prices and token counters use null. Parent/subagent links expose possible double counting.

Mission changes still require explicit user authorization and personal interactive confirmation. A passing test remains limited by its method, environment, sample, and scope.

Skill ID: `skill-harness-v8-1`.
