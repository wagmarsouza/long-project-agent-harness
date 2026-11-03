# Migração das skills de análise binária e Renode

`binary-analysis-profile` e `renode-bench` foram movidas para [DisasmLedger](https://github.com/wagmarsouza/disasmledger). Os nomes das skills e os comandos de invocação em linguagem natural continuam os mesmos. O novo repositório publica as skills independentemente do VeriMission.

```powershell
npx skills add wagmarsouza/disasmledger --skill binary-analysis-profile
npx skills add wagmarsouza/disasmledger --skill renode-bench
```

Revise a versão instalada pelo seu agente e substitua as cópias antigas quando desejar. Releases e tags históricas do VeriMission continuam disponíveis; esta mudança afeta somente o ramo principal a partir da migração. Para integrar uma missão longa ao VeriMission, use o harness instalado e consulte a integração opcional documentada no DisasmLedger.
