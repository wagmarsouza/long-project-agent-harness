# Contributing

Contributions must preserve the goal of verifiable long-running projects and the project's authorisation boundaries.

1. Open an issue describing the observable problem and affected version.
2. Make small changes and keep compatibility between versions explicit.
3. Do not weaken checks, hashes, human confirmation, or history merely to make a test pass.
4. Add tests that fail when the real problem is present.
5. Run the suite for the changed version and document limitations.
6. Do not include private data, firmware, or customer logs.

Use descriptive commits such as `feat:`, `fix:`, `docs:`, and `test:`. An incompatible observable change should create a new version rather than silently rewriting a published one.
