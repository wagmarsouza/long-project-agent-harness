"""Create only local 8.3 resources from 8.2; do not install or publish."""
import json
from pathlib import Path

REPO=Path(__file__).resolve().parents[1]
H=REPO/'harnesses/v8.3'
rules='''

## Native preservation — Control 8.3

1. Preserve accepted obligations across sessions and changes. A plan cannot omit criteria required by an adopted preservation policy.
2. Compare stable obligation/case identities and contracts. Equal test counts or improved aggregate percentages do not demonstrate retention.
3. Protect the verifier: expected outputs, masks, tolerances, exclusions, discovery rules, fixtures, mocks and comparators are part of the oracle.
4. Never regenerate/approve a baseline to absorb a failure. Changes to protected obligations/oracles use the existing explicitly human-authorized mission revision.
5. A broken mandatory capability cannot be compensated by new passes, more coverage, files, grades, retries or reports.
6. Missing, skipped, xfailed, timed-out, unsupported, partial or inconclusive results do not replace a required pass. Preserve all failure history and disclose instability.
7. Bind checks to actual candidate inputs, approved argv, current runner/tool context, corpus, comparator and a fresh result file. Inputs and generated outputs are distinct.
8. Invalidate affected current proofs through declared dependencies. Changed callees affect callers; unknown dependencies require broader replay or an inconclusive conclusion.
9. Preserve reproducible counterexamples as explicit protected corpus/cases. Exploration does not silently modify accepted obligations or start background fuzzing.
10. Inspect test discrimination with meaningful negative controls/mutations in isolated copies. Coverage and a zero exit code alone do not certify quality.
11. Permit honest corrections/retractions with preserved history. A lower corrected metric is not automatically functional regression; revalidation is not a new discovery.
12. Keep byte matching, structural similarity, sampled differential behavior, ABI, simulation and formal/refinement results distinct, with their real assumptions and limits.
13. A changed requirement, oracle, denominator or tolerance needs explicit review/authorization. Silence, a failed test or a generic continuation supplies none.
14. Recover without erasing: retain failed artifacts/audit, inspect unknown outcomes, and prepare authorized repair. No automatic destructive Git reset or corpus cleanup.
15. Keep the core domain-neutral. Specialist tools export neutral evidence; no grade ladder, CPU, firmware denominator or solver is a universal harness requirement.
16. Preservation grants no implicit installation, publication, schedule, execution or mission authority. Local hashes do not authenticate operators, cognition or a malicious runner.

Configure `regression_policy` only for a new authorized mission or through explicit mission revision.
Read `references/v83-preservation.md` for the precise contract, fresh results, debt, impact reuse and
trust limits. Without this policy, inherited 8.2 cycle behavior remains available. Read `regression-plan`
before selecting checks; use `regression-report` to inspect current case-level evidence. Native
`close` enforces preservation together with all earlier gates; it does not implicitly launch checks.
'''
core=(REPO/'harnesses/v8.2/CORE.md').read_text(encoding='utf-8').replace('Control 8.2 — core','Control 8.3 — core',1)
(H/'CORE.md').write_text(core.rstrip()+rules,encoding='utf-8',newline='\n')
overview=(REPO/'harnesses/v8.2/harness_v8.2.txt').read_text(encoding='utf-8').split('\n\n---\n\n',1)[0].replace('8.2','8.3')
(H/'harness_v8.3.txt').write_text(overview,encoding='utf-8',newline='\n')

baseline={'format':'verimission-baseline-v1','reference':{'kind':'specification','id':'REPLACE_WITH_APPROVED_SPECIFICATION'},
          'protected_files':{'tests/test_existing.py':'0'*64},'context_files':{},
          'obligations':[{'id':'CAP-EXISTING','criterion':'REG','case':'test_existing.C.test_retained','critical':True,
                         'sources':['src/result.py'],'comparator':{'kind':'status'}}], 'debt':[]}
policy={'schema':1,'baseline':{'path':'analysis/preservation-v1.json','sha256':'0'*64},
        'input_patterns':['src/*.py','tests/*.py'], 'criteria':{'REG':{'output_pattern':'reports/preservation-{run}.json'}},
        'mode':'full','graph':{},'graph_complete':False,'environment':[]}
for name,value in [('preservation-baseline.example.json',baseline),('regression-policy.example.json',policy)]:
    (H/'templates'/name).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
mission={'objective':'REPLACE with the authorized objective','mode':'light','in_scope':['REPLACE with approved scope'],
         'out_of_scope':['REPLACE with exclusions'], 'criteria':[{'id':'REG','description':'Retain the accepted capabilities',
         'argv':['<PYTHON_EXE>','<ABSOLUTE_RESULT_RUNNER>','unittest','--start','tests'],
         'artifacts':['src/result.py','tests/test_existing.py']}],'regression_policy':policy}
(H/'templates/mission-preservation.example.json').write_text(json.dumps(mission,indent=2)+'\n',encoding='utf-8',newline='\n')

skill=REPO/'skills/skill-harness-v8-3'; skill.mkdir(parents=True,exist_ok=True)
header='''---
name: skill-harness-v8-3
description: "VeriMission Control 8.3: govern general long-running projects with preserved capabilities, executed evidence, recovery and protected periodic review. Use to adopt the harness or resume a governed mission; specialist domain tools remain optional."
metadata:
  display-name: VeriMission Control 8.3
  version: "8.3"
---

# Using Control 8.3

Use an absolute bundled executor path and the real project root:
`python /absolute/skill/scripts/harness.py --project /authorized/project COMMAND`.
Python 3.11+ and PyYAML 6.x are the only core executor requirements. Do not require a binary-analysis
tool, grade ladder, compiler, emulator or solver for a general project.

For an existing mission inspect `resume` and `validate`; do not reinitialize it. Normal flow remains
review → start → check → close → validate. Installation/activation, publishing and schedules need
separate explicit user authorization; a skill package grants none. Simple questions do not need
manufactured cycles. Respect higher-priority host instructions and the approved mission.

Read [preservation](references/v83-preservation.md) when adopting `regression_policy`, checking
baseline freshness, interpreting missing cases or configuring optional impact reuse. Inspect
`regression-plan` and include its required criteria; `close` now enforces the policy natively.
Expected results and prior capabilities cannot be weakened to make a candidate pass. Policy
adoption/change on an existing mission uses the existing explicit human mission-revision gate.
No separate baseline-approval bypass or background rebaselining exists.

Read [periodic review](references/v82-periodic-review.md) before changing notes, cadence, inventory
or governing-file configuration. The native review/reconciliation remains self-contained and protects
governing text outside the declared immediate-objectives/scenario bodies. No second scheduler is added.
Read [8.1 projections/imports](references/v81-projections-and-runs.md) for graph/PR/cost interfaces.
Without the optional new policy, inherited 8.2 workflow remains available. Historical references
retain their original version labels; the complete current core below governs current operation.

'''
# The package synchronizer appends the complete current CORE, including all inherited safeguards.
(skill/'SKILL.md').write_text(header+(H/'CORE.md').read_text(encoding='utf-8'),encoding='utf-8',newline='\n')
builder=(REPO/'tasks/package_v82.py').read_text(encoding='utf-8').replace('8.2','8.3').replace('v8-2','v8-3').replace('v82-periodic-review.md','v82-periodic-review.md')
# Keep the inherited periodic guide and append the preservation guide to the consolidated text.
builder=builder.replace("guide = (HARNESS / 'references/v82-periodic-review.md').read_text(encoding='utf-8')",
                        "guide = (HARNESS / 'references/v82-periodic-review.md').read_text(encoding='utf-8') + '\\n\\n' + (HARNESS / 'references/v83-preservation.md').read_text(encoding='utf-8')")
(REPO/'tasks/package_v83.py').write_text(builder,encoding='utf-8',newline='\n')
print('Prepared local 8.3 core, skill entrypoint, templates and synchronizer; not installed.')
