# Control 8.3 — qualification for a stable release

Authorized scope: real Linux/macOS qualification where an execution environment is available,
larger YAML histories and sustained synthetic use, reproducible CI, independent review, and an
owner-selected reuse license. No skill installation or publication is authorized.

## Current environment and authority

- Windows 11 / Python 3.12.10 / PyYAML 6.0.3 validated in the prior r4 candidate.
- Ubuntu WSL2 is available with Python 3.14.4 and PyYAML 6.0.3. Linux tests will run in its own
  temporary filesystem, not on the Windows mount. WSL results are identified as WSL, not native macOS.
- No connected macOS environment has been found; GitHub CLI has no authenticated account.
  Prepare the workflow locally, then request only the indispensable access for remote execution.
- License choice and macOS availability were asked asynchronously. No license is inferred from silence.
- A separate reviewer has been assigned a read-only review of the actual source, with isolated
  reproductions and no installation/publication. Findings must be reproduced and fixed, then re-reviewed.

## Ordered implementation

1. Preserve the r4 runtime baseline and run the current full harness suite in Ubuntu.
2. Add a finite, portable CI entry point with durable per-check results, source/resource parity,
   full suites/campaigns and packaging checks. Prepare a Windows/Linux/macOS matrix locally.
3. Measure native multi-session replay at bounded cycle counts and separately seeded larger
   histories. Record actual executions vs seeded test vectors, elapsed time, file size and memory
   metric definition. Never claim seeded cycles were executed. Profile before optimizing.
4. If a bottleneck is demonstrated, make the smallest safe optimization, keep old/new measurements
   under the same conditions, preserve integrity/locking/safe YAML and run regression tests.
5. Resolve actionable independent-review findings with focused red/green tests and fresh review.
6. Apply the explicitly selected license and update public-facing documentation consistently.
7. Run final OS-qualified checks, regenerate synchronized skill and ZIPs, and report qualification
   and pending environments honestly. Do not label unexecuted CI cells as passed or stable.

## Evidence requirements

Record source hashes/commit, runtime/OS, finite command budgets, per-job completion, failures and
unavailable targets. A stopped coordinator resumes only unfinished work from durable receipts.
The YAML store remains canonical. No alternate DB, auto baseline approval or implicit authority
is introduced. Cross-platform design is distinct from actual execution on each platform.
