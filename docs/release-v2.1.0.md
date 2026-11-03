# VeriMission Control 8.1

Nova versão do harness e da skill para missões longas com evidências persistentes.

- Grafo derivado em JSON, Mermaid e DOT, com revisão e hash.
- Relatório de PR com commits Git resolvidos, diff, escopo, checks, hashes, claims, retratações, cobertura com denominadores e revisão humana pendente.
- Imports explícitos para Codex, OpenCode, Claude e Hermes, com fonte hasheada.
- Custos reais, estimados e sem preço separados; valores desconhecidos permanecem null; cache/retry/subagentes ficam visíveis.
- Estado canônico YAML e migração SQLite recuperável, preservando o núcleo de claims, retratações, teto de alegação, autorização humana e antirretrabalho.

Verificação: 128 testes no harness e 128 na skill; validador aprovado e cinco módulos com paridade de hashes. Os testes usam fixtures locais; os adaptadores não são parsers automáticos de logs nativos.

Instalação: `npx skills add wagmarsouza/long-project-agent-harness --skill skill-harness-v8-1`

Leia `docs/harness-8.1.md`, `docs/v8.1-plan.md` e `docs/yaml-migration.md`.

Binary Analysis Profile e Renode Bench estão no projeto independente https://github.com/wagmarsouza/disasmledger.
