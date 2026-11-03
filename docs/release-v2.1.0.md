# VeriMission Control 8.1

Control 8.1 provides evidence-based coordination for projects spanning multiple agent sessions.

- Read-only graph projections in JSON, Mermaid, and DOT.
- PR reports with resolved commits, scope, diff, checks, hashes, claims, retractions, coverage denominators, and required human review.
- Explicit run imports for Codex, OpenCode, Claude, and Hermes with hashed sources.
- Separate actual, estimated, and unpriced cost records; unavailable values remain null.
- Canonical YAML storage with recoverable SQLite migration.
- Preserved mission authorization, claim ceilings, retractions, and anti-rework controls.

Validation: 128 tests passed in the harness and 128 in the packaged skill; skill validation and script parity checks passed. Adapters do not automatically parse native logs or dispatch agents.

Install: `npx skills add wagmarsouza/long-project-agent-harness --skill skill-harness-v8-1`

Binary analysis and Renode skills are available separately at https://github.com/wagmarsouza/disasmledger.
