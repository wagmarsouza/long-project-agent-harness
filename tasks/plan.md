# Control 8.2 — self-contained boundary reviews

Owner decision, 2026-11-08: VeriMission is a general long-project harness. Its digest producer is native. DisasmLedger is optional and owns domain-specific interpretation, never a required runtime dependency. Project marker sets, wake labels, paths, denominators and firmware rules stay out of repository artifacts.

Preserve all 8.1 behavior when periodic review is not configured. Preserve the mission-revision human gate, evidence ceiling, retractions, coverage denominators, no implicit autonomy, YAML storage and recovery.

1. Add a strict mission policy for N-cycle cadence, notes, optional structured inventory observations, governing instructions and two mutable sections.
2. Produce deterministic digests by physically reading every note in the window. Reconcile configured inventories, transitions and receipts; distinguish justified retractions from unexplained regression. Arithmetic is not semantic correctness.
3. Invoke digest and review inside close. A due boundary remains active until reconciliation, tripwire and declared substantive reread pass. Stale/missing/wrong-window digests refuse with exit 2. Successful boundaries automatically consolidate.
4. Hash all governing text outside permitted objectives/scenario sections, preserving later protected instructions too. Restore a damaged prompt only from the last trusted snapshot, preserving the damaged version. No automatic mission changes.
5. Persist successes, pending work, failures, hashes, reread declarations and changes as structured events in the canonical YAML. Gate start after interrupted/unreviewed boundaries.
6. Exercise generic business/research fixtures, CLI and legacy regressions, package portable harness and skill, and write precise limitations. No installation, publication, schedule changes or live project migration.

The initial 8.1 baseline passed 128 tests. Sources will be written in the repository's English convention; the delivery explanation is in Portuguese.

Risks: file updates are not one OS transaction with YAML (recoverable hash binding required); nonempty reread declarations do not prove cognition; arbitrary operator edits/source changes can bypass a local tool; inventory receipts establish provenance/consistency, not semantic truth. Closed source notes must be immutable; corrections belong in later notes and explicit retractions.
