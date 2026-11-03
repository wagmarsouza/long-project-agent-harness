# Changelog

## Publication v2.1.1 — 2026-11-03

- Fixed V8.1 manifest hashes to describe canonical Git/archive bytes and pinned the package to LF line endings across operating systems. Runtime behavior is unchanged.

## VeriMission 8.1 — 2026-11-03

- Added read-only JSON, Mermaid, and DOT graph projections with source revision and hashes.
- Added reproducible PR reports with resolved Git commits, diff, checks, artifact hashes, claims, retractions, coverage denominators, and required human review.
- Added explicit, hashed run import adapters for Codex, OpenCode, Claude, and Hermes. Native log formats are declared by the importer rather than parsed or authenticated automatically.
- Added optional usage/cost summaries separating actual, estimated, and unpriced records. Missing prices and token counters remain null.
- Adopted canonical YAML storage, atomic writes, checksums, process locking, and recoverable explicit migration from SQLite; legacy sources remain preserved.
- Preserved mission revision authorization, claim ceilings, retractions, evidence freshness, and anti-rework gates.
- Binary analysis and Renode skills now live in the independent DisasmLedger repository.

Native agent dispatch, automatic model selection, and automatic claim promotion are outside this release.
