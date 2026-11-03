# Migration of binary-analysis and Renode skills

`binary-analysis-profile` and `renode-bench` moved to [DisasmLedger](https://github.com/wagmarsouza/disasmledger). Skill names and natural-language invocation remain unchanged. The new repository publishes both skills independently of VeriMission.

```powershell
npx skills add wagmarsouza/disasmledger --skill binary-analysis-profile
npx skills add wagmarsouza/disasmledger --skill renode-bench
```

Review the version installed by your agent and replace older copies when appropriate. Historical VeriMission releases and tags remain available; the move affects the main branch from the migration onwards. To integrate long-running work with VeriMission, use the installed harness and consult the optional integration guide in DisasmLedger.
