# V8.1 — projeções, relatório de PR e registros de execução

O V8.1 preserva o contrato e os gates do V8.0. Os recursos desta referência não iniciam agentes, não trocam modelos, não aprovam operações, não alteram a missão e não promovem claims.

## Grafo somente leitura

```powershell
python "$H" --project "$P" graph --format json --output graph.json
python "$H" --project "$P" graph --format mermaid --output graph.mmd
python "$H" --project "$P" graph --format dot --output graph.dot
```

As três saídas são projeções determinísticas do estado canônico. JSON inclui o testemunho completo da fonte; Mermaid e DOT incluem a revisão no cabeçalho. Nós representam missão, requisitos, critérios, tarefas, ciclos e claims. Arestas representam somente vínculos registrados. O desenho não cria dependências e não demonstra que os vínculos são completos ou verdadeiros. HTML não foi incluído: os três formatos interoperáveis cobrem inspeção, documentação e renderização sem introduzir aplicação web ou estado adicional.

## Relatório orientado a PR

```powershell
python "$H" --project "$P" report-pr --base main --head HEAD --format markdown --output PR_REPORT.md
python "$H" --project "$P" report-pr --base main --head HEAD --format json --output PR_REPORT.json
```

O executor resolve os dois refs para commits e usa `git diff --name-status` sem shell. O relatório inclui:

- commits base/head e arquivos alterados;
- missão e escopo atuais;
- auditoria do estado e matriz de rastreabilidade;
- checks e hashes de artefatos registrados;
- claims e retratações;
- requisitos, critérios e tarefas com numerador/denominador;
- arquivos modificados com cobertura `indeterminate` enquanto não existir vínculo explícito arquivo → critério;
- limitações e perguntas que exigem revisão humana.

O relatório não abre, aprova nem integra um PR. Um commit presente no diff não fica automaticamente verificado. O hash do payload permite conferir a projeção JSON que originou a revisão; ele não assina a pessoa nem a suficiência dos testes.

## Importação explícita de execuções

Adaptadores disponíveis: `codex`, `opencode`, `claude` e `hermes`.

```powershell
python "$H" --project "$P" adapter-template --agent codex
python "$H" --project "$P" run-import --agent codex --input run.json
python "$H" --project "$P" cost-summary
```

O V8.1 escolhe importação explícita e verificável, não parsers frágeis de logs nativos. A entrada `verimission-explicit-run-v1` aponta para um arquivo de exportação/evidência dentro do projeto, declara seu formato real e localiza o registro. O executor calcula o SHA-256 da fonte, valida o esquema e preserva a declaração. Ele não afirma compreender o conteúdo nativo (`native_format_parsed: false`) e não autentica automaticamente o relato.

Para cada modelo, os quatro contadores de tokens são literais observados; se não forem conhecidos, use `null`. Zero significa zero realmente observado, não ausência de dado. Custos têm três estados:

- `actual`: valor de recibo/relatório do provedor, com referência;
- `estimated`: cálculo reproduzível, com método e tabela de preço referenciada;
- `unpriced`: custo desconhecido, obrigatoriamente `amount_usd: null` — nunca zero.

`cost-summary` mantém totais reais e estimados separados e conta linhas sem preço. Cache, tentativas, retries e relações com subagentes permanecem visíveis. Importe subagentes antes da execução pai; importe a tentativa original antes de um retry. O vínculo evita dupla contagem estrutural, mas o operador ainda precisa verificar se a cobrança do pai já incorpora os filhos.

Estados `interrupted` e `unknown` são registros, não autorização para replay. Use a investigação/reconciliação adequada do hospedeiro; não reenvie trabalho de resultado desconhecido. Importar um run nunca muda a missão, concede autorização ou promove uma claim.
