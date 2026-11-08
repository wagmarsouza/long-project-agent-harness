# VeriMission Control 8.2 — general-project periodic review

Public preview: [v2.2.0-rc.1](release-v2.2.0-rc.1.md). No installation or live-project migration is implied.

Control 8.2 is self-contained. Its native producer reads physical cycle notes, reconciles optional declared inventory observations and emits a digest skeleton. The executor couples that digest to a protected governing-instructions review at the same N-cycle boundary. Research, software, writing and other long-running projects do not need a decompilation repository.

All previous controls remain: explicit user-authorized mission revisions, evidence freshness, claims/retractions, coverage denominators, claim ceilings, anti-rework gates, governed operations, graph/PR projections and cost/run imports. An 8.1 mission without periodic review configured retains its original behavior.

See [the detailed workflow](../harnesses/v8.2/references/v82-periodic-review.md), [the protected core](../harnesses/v8.2/CORE.md), and [templates](../harnesses/v8.2/templates/). The new commands are:

```text
python harnesses/v8.2/scripts/harness.py --project /your/project digest --through-cycle N
python harnesses/v8.2/scripts/harness.py --project /your/project decade-review --through-cycle N --input /your/project/review.json
python harnesses/v8.2/scripts/harness.py --project /your/project restore-prompt
```

`close` invokes production/review natively. A first boundary close without a reread produces a digest, records pending work and exits 2. A subsequent `close --review-input FILE` can apply the review and consolidate atomically with canonical cycle closure. Only immediate objectives/scenario bodies may change. All other instruction bytes are fingerprinted; retaining marker names while weakening their rules still fails.

Every physical note needs a hash-bound reread finding; the producer does not invent it. A valid retraction may lower a metric. The engine records that correction rather than forcing an increasing number. Receipt declarations and consistency checks do not establish semantic truth.

Run the no-domain synthetic pilot and tests:

```text
python -B harnesses/v8.2/examples/run_periodic_pilot.py
python -B -m unittest discover -s harnesses/v8.2/tests -v
```

No native agent dispatch, model selection, autonomous mission change, global installation or schedule creation is added. Specialist tools can provide the generic observation JSON, but remain optional exporters rather than harness dependencies.
