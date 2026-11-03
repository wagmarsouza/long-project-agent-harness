# VeriMission Control 8.1

O V8.1 mantém o núcleo anti-inflação, anti-afirmações sem prova e antirretrabalho do V8.0. Acrescenta visualizações reproduzíveis do grafo, relatório orientado a PR, contabilização opcional de uso/custo e adaptadores explícitos para Codex, OpenCode, Claude e Hermes.

Essas extensões são deliberadamente observacionais. Elas não criam agentes autônomos, não aprovam efeitos, não alteram missão, não promovem claims e não transformam resultado desconhecido em permissão para repetir trabalho.

O estado canônico é `.harness/state.yaml`, com checksum, gravação atômica e bloqueio entre escritores. Requer Python 3.11+ e PyYAML. Projetos antigos com apenas `.harness/state.sqlite` usam `migrate-sqlite` uma vez; o arquivo legado é preservado, mas deixa de ser o armazenamento vivo.

## Quando escolher

- a missão precisa de um grafo legível fora da CLI;
- uma revisão de PR precisa reunir diff, critérios, checks, hashes, claims, cobertura e limites;
- é útil distinguir custo real, estimado e ainda sem preço;
- execuções de hospedeiros diferentes precisam de uma trilha neutra, sem acoplar o projeto a um provedor.

## Comandos novos

```text
graph --format json|mermaid|dot [--output ARQUIVO]
report-pr --base REF --head REF --format json|markdown [--output ARQUIVO]
adapter-template --agent codex|opencode|claude|hermes
run-import --agent AGENTE --input ARQUIVO.json
cost-summary
```

Exemplo:

```powershell
$h = '.\harnesses\v8.1\scripts\harness.py'
$p = 'C:\projeto'
python -m pip install pyyaml
# Somente em projeto legado ainda sem state.yaml:
python -B $h --project $p migrate-sqlite
python -B $h --project $p graph --format mermaid --output "$p\MISSION_GRAPH.mmd"
python -B $h --project $p report-pr --base main --head HEAD --format markdown --output "$p\PR_REPORT.md"
python -B $h --project $p adapter-template --agent codex
python -B $h --project $p run-import --agent codex --input "$p\run.json"
python -B $h --project $p cost-summary
```

Leia [v81-projections-and-runs.md](../harnesses/v8.1/references/v81-projections-and-runs.md) antes da primeira importação. O modelo está em `harnesses/v8.1/templates/run-import.example.json`.

## Limites que não mudaram

- A missão só muda pelo fluxo explícito e interativo já documentado.
- Uma projeção não é uma segunda fonte de estado.
- Busca, grafo, relatório e imports não autenticam verdade semântica.
- Cobertura exige universo e denominador; arquivos modificados permanecem indeterminados sem mapeamento explícito.
- `actual`, `estimated` e `unpriced` não são somados como se tivessem a mesma natureza.
- O harness não fiscaliza ações feitas fora de sua CLI.

## Skill correspondente

Use `skills/skill-harness-v8-1` e invoque `skill-harness-v8-1`.
