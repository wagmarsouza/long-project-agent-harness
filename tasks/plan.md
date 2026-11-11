# Plano de implementação — VeriMission 8.3, preservação verificável

Implementação local autorizada em 10/11/2026. Instalação e publicação continuam fora do escopo.
Guia mantido da implementação: [Control 8.3](../docs/harness-8.3.md). O estudo e as fontes de 10/11/2026 permanecem preservados na entrega local de pesquisa.
Tarefas canônicas: [todo.md](todo.md). Este plano está separado das tarefas concluídas do 8.2.

## Decisões de arquitetura

- Base imutável de comparação: Control 8.2 publicado, commit `6b18af728a7e69da134c87edfe2ad7628720bf35`.
- Trabalhar em branch/worktree 8.3 isolada; não alterar gerações anteriores ou missões reais.
- Núcleo genérico autossuficiente; não importar graus G4, ISA, censo de firmware ou um solver como requisitos universais.
- Um store YAML canônico e recursos imutáveis referenciados por hash; relatórios são projeções.
- Reutilizar execução `check`, orçamento/lock, revisão humana de missão e reconciliação do 8.2.
- Separar entradas imutáveis de resultados gerados. Check com política ausente preserva o comportamento legado.
- Não iniciar um segundo scheduler e não usar uma instrução textual como substituto de bloqueio no motor.
- Começar com suíte protegida completa; otimização por impacto/cache será uma etapa posterior verificada.
- Não definir percentuais universais. Criticidade, comparadores e limiares pertencem ao contrato autorizado.

## Fase A — contrato e comparação, antes de efeitos

### T01 — Fixar o comportamento herdado e o contrato 8.3

Arquivos prováveis: `docs/harness-8.3.md`, `harnesses/v8.3/templates/regression-policy.example.json`,
`harnesses/v8.3/tests/test_v82_compatibility.py`. Preparar uma cópia de trabalho 8.3 por fluxo explícito.

Aceite: listar funcionalidades herdadas e mapear casos; definir IDs de obrigação, resultado e baseline;
declarar os limites de confiança e a compatibilidade sem política; não atribuir novos testes ao 8.2.

Verificação: executar a suíte 8.2 original e guardar relatório como baseline de desenvolvimento;
conferir que a comparação é com o commit resolvido e que fontes 8.2 permanecem intactas.
Dependências: nenhuma. Escopo: médio, até três arquivos de especificação/teste inicialmente.

### T02 — Ler política e identidades de referência de forma estrita

Arquivos prováveis: `harnesses/v8.3/scripts/v83_regression.py`,
`harnesses/v8.3/tests/test_regression_contract.py`, template de T01.

Aceite: validar schema/versionamento, IDs únicos, caminhos e enums; recusar baseline ausente,
referência Git não resolvida ou contrato inconsistente; resolver raiz do projeto sem escapar dela.
Não considerar criação de arquivo ou auto-bootstrap como baseline aprovada.

Verificação: testes de campos desconhecidos, IDs duplicados, caminhos/symlinks, NaN/Infinity,
referência móvel, árvore suja sem manifesto e baseline corrompida. Nenhum runner é executado.
Dependências: T01. Escopo: médio.

### T03 — Comparador determinístico por obrigação/caso

Arquivos prováveis: `v83_regression.py`, `tests/test_regression_compare.py` e fixture sintética.

Aceite: perder caso protegido reprova mesmo com contagem total constante; novos sucessos não
compensam falhas; missing/skipped/timeout/unknown são distintos de pass. Mudança de contexto
produz incomparabilidade, não diagnóstico inventado de erro funcional.

Verificação: comparação antes/depois com IDs estáveis, caso renomeado sem mapeamento, crítico
falhando com média melhor, zero casos obrigatórios e universo desconhecido. Relatórios indicam
N/A/indeterminado quando aplicável, em vez de porcentagem artificial.
Dependências: T02. Escopo: pequeno a médio.

### Checkpoint A

Contrato e comparação são revisáveis sem executar ferramentas externas ou modificar missões.
Nenhum campo/CLI proposto deve ser anunciado como disponível antes de implementado e testado.

## Fase B — resultados e integração no ciclo

### T04 — Resultado neutro e runner unittest de biblioteca padrão

Arquivos prováveis: `scripts/result_readers.py`, `tests/test_regression_results.py`, fixture de resultado.

Aceite: normalizar por caso preservando estado original, IDs, execução e completude; diferenciar
relatório ausente/antigo/parcial; runner/adaptador não executar comandos extraídos do relatório.
Formato neutro deve servir também para verificações que não sejam testes de software.

Verificação: suíte com pass/fail/error/skip, processo interrompido, IDs duplicados, relatório forjado
por cópia antiga, corpus parcial e saída fora da raiz. Documentar que recibo não autentica runner hostil.
Dependências: T03. Escopo: médio.

### T05 — Integrar `check` sem quebrar artefatos legados

Arquivos prováveis: `scripts/harness.py`, `scripts/v83_regression.py`, `tests/test_regression_check.py`.

Aceite: entradas são hashadas antes/depois; relatórios novos são saídas vinculadas ao check;
comandos seguem argv autorizado, sem shell; artefato/fonte alterado depois invalida prova.
Política ausente mantém o formato e as decisões de verificações legadas.

Verificação: read/write races, mudança de helper/runner/comparador, falha de subprocesso, timeout,
relatório parcial e lock concorrente. Execução não deve limpar dados reais nem instalar dependências.
Dependências: T04. Escopo: médio. Evitar crescer o arquivo principal concentrando lógica nova no módulo próprio.

### T06 — Integrar start/close e avaliação de conclusão

Arquivos prováveis: `scripts/harness.py`, `scripts/v80_core.py`, `tests/test_regression_gates.py`.

Aceite: plano não omite obrigações protegidas; fechamento verified e accept-mission recusam
regressão, evidência incompleta ou incomparável; interrupção continua permitida e preserva histórico.
Checks faltantes são relatados, não lançados implicitamente pelo fechamento.

Verificação: omissão deliberada de critério, remoção de teste, skip novo, perda de uma capacidade
crítica e reentrada após interrupção. Um ciclo bloqueado não ganha progresso por gerar relatório.
Dependências: T05. Escopo: médio.

### T07 — Governar baseline e corrigir obrigações sem apagar história

Arquivos prováveis: `scripts/v83_regression.py`, `tests/test_regression_authority.py`,
`templates/baseline-proposal.example.json`.

Aceite: preview é somente leitura; adoção inicial/modificação de obrigação protegida se vincula
ao contrato e ao fluxo explícito de revisão humana existente; snapshot-update e tolerância
ampliada não viram autorização. A referência antiga permanece recuperável.

Verificação: proposta stale, hash divergente, tentativa não interativa, cron/CI tentando revisar
missão, auto-confirmação por agente, alteração de expected para absorver bug e substituição
legítima aprovada com novo caso discriminante. Preservar os testes do human gate atual.
Dependências: T06. Escopo: médio.

### T08 — Auditoria, relatórios e recuperação

Arquivos prováveis: `scripts/v83_regression.py`, `scripts/v82_periodic.py`, `tests/test_regression_recovery.py`.

Aceite: eventos estruturados no store existente; revisão periódica resume o mesmo assessment;
falha/interrupção não troca baseline ou snapshot válido silenciosamente. Resume mostra o que
deixou de ser atual, incluindo impacto sobre claims/tarefas, sem apagar registros.

Verificação: interrupção entre gravação de arquivo e commit YAML; concorrência, comparação stale,
restauração e retração honesta com queda de métrica. Nenhum ledger ou cron paralelo é criado.
Dependências: T07. Escopo: médio.

### Checkpoint B — núcleo mínimo de uma versão 8.3

Reproduzir o caso principal ponta a ponta: baseline aceita, mudança boa, fechamento válido;
segunda mudança quebra capacidade antiga, suíte aparentemente verde por skip, fechamento recusado;
correção real restaura capacidade e preserva o diagnóstico anterior. Executar os controles herdados.
Este é o MVP do motor; adaptar binários ou importar métricas não substitui esse checkpoint.

## Fase C — adaptadores e fortalecimento especializado

### T09 — Importação JUnit/pytest e verificações de métricas

Arquivos prováveis: `scripts/result_readers.py`, `tests/test_regression_junit.py`,
`references/v83-results.md`.

Aceite: leitores opcionais preservam semântica de skip/xfail, colisões e resultados não classificados;
XML inseguro/malformado é recusado; cobertura mantém universo/exclusões; mutação mantém fórmulas,
estados e contexto originais. O formato neutro continua disponível sem pytest ou Stryker instalados.

Verificação: suites aninhadas, parametrização/IDs, duplicidade, estados ambíguos, DTD/entidades,
arquivo truncado, redução de denominador e timeout de infraestrutura mascarado como killed.
Dependências: T08. Escopo: médio; se leitores exigirem mais de cinco arquivos, separar um adaptador por tarefa.

### T10 — Exportar testemunhos/contexto no DisasmLedger e renode-bench

Arquivos prováveis no projeto separado: `skills/renode-bench/scripts/differential.py`,
`skills/decompile/scripts/verimission_adapter.py`, novo teste de integração.

Aceite: API diferencial booleana existente continua; saída estruturada opcional identifica casos,
observáveis, reset e contexto. Adaptador não duplica o reconciliador e mantém G4-stock/G4-recon
separados; G4 histórico e atualidade da prova são eixos diferentes.

Verificação: helper/ABI mudado, limpeza de estado ausente, teste de retorno correto com escrita
de memória errada, ferramenta não suportada, graus stock-only e exportação com fonte alterada.
Dependências: T08 e formato neutro T04. Escopo: médio, com integração usando o motor original 8.3.

### T11 — Corpus persistente, propriedades e controles negativos

Arquivos prováveis: referência de corpus, fixture genérica e suíte de preservação adversarial.

Aceite: bug reproduzível corrigido recebe entrada/condição estável; fuzzing tem orçamento separado;
testes negativos demonstram que o guard recusa falsos verdes. Nenhum corpus sensível/malware de
terceiro é importado. Relações metamórficas são declaradas e justificadas por domínio.

Verificação: remover asserção, ampliar tolerância, regenerar expected, omitir corpus, mudar comparador,
ler relatório antigo e trocar caso mantendo a contagem. Mutações em cópias isoladas são revertidas;
projeto real não é alterado. Não apresentar a amostra como score global de mutação.
Dependências: T09–T10. Escopo: médio, dividindo por família se necessário.

### Checkpoint C

Piloto de software e piloto sintético binário demonstram perdas por caso, efeitos laterais,
mudança de contexto e correção explícita. A matriz distingue o que não foi executado em hardware
real ou em outro OS. Não prometer suporte de toolchain/emulador a partir de um fake invoke.

## Fase D — eficiência e entrega

### T12 — Seleção por impacto e cache conservador

Arquivos prováveis: `scripts/v83_regression.py`, `tests/test_regression_impact.py`,
`references/v83-impact.md`.

Aceite: casos críticos sempre exigidos; alteração de dependência inclui dependentes transitivos;
grafo incompleto, import dinâmico/indireção e contexto novo acionam campanha completa ou bloqueio.
Cache inclui entrada, toolchain, runner, corpus, comparador e política; nenhuma falha some por retry.

Verificação: função B alterada invalida A que a chama; recursão/SCC, global compartilhada, mudança
de layout e alvo indireto; decisões do modo incremental e completo são comparadas nos mesmos
cenários. Mudança fora dos arquivos principais também invalida quando faz parte do contexto.
Dependências: checkpoint C. Escopo: médio; otimização não deve preceder um caminho completo confiável.

### T13 — Instruções do núcleo, CLI e exemplos portáveis

Arquivos prováveis: `harnesses/v8.3/CORE.md`, `references/v83-preservation.md`,
`examples/run_regression_pilot.py`.

Aceite: 16 regras do relatório aparecem no núcleo com correspondência para verificação ou limite;
comandos propostos só são documentados como reais após implementação; dois pilotos de domínios
diferentes funcionam sem DisasmLedger. Revisão de missão permanece exclusivamente humana.

Verificação: help/CLI reais, caminhos Windows e POSIX, desconhecimentos/N/A, nenhuma execução
implícita ao ler uma skill. Bench/solver é opcional, não dependência disfarçada do harness.
Dependências: T08, T12. Escopo: médio.

### T14 — Sincronizar skill e validar pacotes

Arquivos prováveis: gerador de pacotes existente adaptado para 8.3, testes de paridade e nota de release.

Aceite: `skill-harness-v8-3` deriva da fonte canônica do harness; scripts/referências/templates não
divergem por edição manual. Manifests descrevem bytes canônicos. ZIPs extraídos passam validação
e pilotos; resultados/skip/limitações são exatos, sem contar repetições como evidência independente.

Verificação: suites herdadas e novas, cenários de mutação direcionada, paridade dos recursos,
validação SKILL.md com PyYAML explícito, hashes/caminhos dos ZIPs e ausência de dados reais.
Executar Windows/Linux em CI quando disponível; plataforma indisponível fica não testada.
Dependências: T09–T13. Escopo: médio. Só produzir pacotes; instalar/publicar exige novo pedido.

## Critérios finais de aceite

1. As obrigações do projeto continuam protegidas mesmo que um plano selecione só o teste da função nova.
2. Perder uma obrigação não é compensado por mais testes, cobertura, graus ou linhas de código.
3. Resultado vazio, parcial, antigo, skipped ou inconclusivo não vira PASS obrigatório.
4. Atualização indevida de referência/comparador é detectada e exige o fluxo de autorização pertinente.
5. Mudança de dependência/contexto invalida provas aplicáveis sem fabricar uma regressão funcional.
6. Correções honestas/retrações são possíveis, auditáveis e não são apresentadas como novo progresso funcional.
7. Política ausente mantém 8.2; adoção em missão existente é explícita e não zera orçamento/histórico.
8. Helpers binários são opcionais e não duplicam reconciliação nem misturam G4-stock com G4-recon.
9. O núcleo não concede autonomia, não autentica seu próprio operador e não promete observar ações externas.

## Adiar sem bloquear o MVP

- Integrações específicas Alive2/PATE e análise simbólica: apenas contrato neutro no 8.3 inicial;
  cada engine precisa de piloto, versão suportada, limites e revisão própria de licenças.
- ABI/benchmarks por ferramentas externas: usar resultado neutro escolhido pelo projeto, sem instalar.
- CI obrigatório/branch protection: recomendação de implantação futura, não alteração remota nesta proposta.
- Rollback automático do Git, limpeza automática de corpus e rebaseline automático: não implementar.

## Riscos e mitigação

| Risco | Mitigação |
| --- | --- |
| Excesso de execução em projetos longos | Começar com conjunto protegido explícito; medir custo; otimizar só com decisão conservadora verificada. |
| Baseline errada se tornar dogma | Distinguir preservação de correção; origem do oráculo e revisão humana com novo caso. |
| Outro arquivo virar store paralelo | Estado só no YAML; demais arquivos imutáveis/derivados por hash. |
| Runner alterado pelo mesmo ator | Expor limite; CI/revisão externa se esse modelo de ameaça for relevante. |
| Parser de ferramenta inventar precisão | Preservar raw status e unknown/inconclusive; leitores estritos e testados. |
| Runtime principal crescer demais | Isolar nova lógica; integração curta; não reescrever o 8.2 sem necessidade. |
| Ruído, ambiente ou FPU parecerem bug | Contexto/política explícitos, observações comparáveis, replay diagnóstico separado. |
| Dados sensíveis no corpus | Só fixtures sintéticas/autorizações específicas; hash não anonimiza conteúdo. |

As escolhas de comparadores, criticidade e corpus do projeto real devem ser resolvidas na adoção
da política. Não precisam ser inventadas para fechar esta proposta de arquitetura.
