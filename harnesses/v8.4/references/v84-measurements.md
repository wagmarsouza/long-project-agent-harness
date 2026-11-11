# Control 8.4 — quantidades comprovadas, sem especializar o harness

Esta evolução é opcional e local. Preserva o contrato de missão, revisão explícita de missão,
claims/retratações, projeções, digest e revisão periódica do 8.2, preservação e campanhas do 8.3.
Sem `measurement_policy`, os fluxos anteriores continuam disponíveis. O store continua YAML:
`.harness/state.yaml`. JSONs são provas imutáveis/projeções; não são um segundo ledger editável.

## Responsabilidade

O harness governa identidade, conjunto exato, denominador, checks executados, fechamento,
invalidação, auditoria e teto de alegação para qualquer projeto longo. Não conhece C nem G4.
O decompile fornece os cinco gates de reconstrução, compila e verifica recibos de execução.
As barras do decompile consultam o harness vivo. Não é necessária uma terceira skill.

## Adoção explícita

Python 3.11+ e PyYAML 6.x. A pasta do projeto é distinta da pasta distribuída do harness.
Leia a missão atual com `resume` e `validate`; não rode `init` em uma missão existente.
Para adotar/alterar a política numa missão existente use a revisão de missão com autorização
humana explícita, descrita no guia anterior; não edite state.yaml nem reinitialize a missão.
O template `templates/measurement-policy.example.json` é apenas o objeto a incorporar na missão,
com hashes/caminhos reais, critérios M/A, budgets e escopo revisados. Não é uma missão pronta.

O universo `verimission-universe-v1` contém `units` com `id`, identidade física estável `identity`,
`deliverable` relativo e `depends_on`; `excluded` contém IDs e razões explicitamente aprovadas.
Não aumente o percentual classificando silenciosamente dificuldades como excluídas.
`protected_files` fixa verificadores/contexto. `input_patterns` deve cobrir fontes, corpus,
headers, linker scripts e demais entradas relevantes; omissões não são descobertas universalmente.
`environment` fixa os valores relevantes via hash. `pinned_roles` ancora, no primeiro fechamento,
papéis de prova cuja troca exige revisão de missão (por exemplo corpus/controle/verificador).

## Comandos (ajuste executável, raiz, arquivos e ID de ciclo)

```powershell
$h = 'C:/Pacotes/harness_v8.4/scripts/harness.py'
$p = 'C:/Trabalho/Projeto'
python -B $h --project $p resume
python -B $h --project $p validate
python -B $h --project $p review --help
python -B $h --project $p start --help
python -B $h --project $p check --cycle 1 --criterion M
python -B $h --project $p measurement-audit-plan --cycle 1
python -B $h --project $p check --cycle 1 --criterion A
python -B $h --project $p close --help
python -B $h --project $p measurement-report
python -B $h --project $p cycle-boundary --cycle 1
```

Use review/start com plano válido e M selecionado. Na cadência de auditoria selecione M e A
no plano antes de iniciar; a omissão é recusada. Execute M, congele a seleção, execute A e
feche com outcome verified apenas depois de todos os checks/revisões exigidos. Para recuperação
ou auditoria integral use `measurement-audit-plan --cycle N --full`. Sem candidato válido não
se planeja a amostra. Sem política, `measurement-report` informa não aplicável; não inventa prova.
Um host/cron que ignora close continua fora da proteção de fechamento: integre cycle-boundary
como condição de sucesso do próprio host. Nenhum serviço ou agendamento é instalado.

## Contrato do produtor

M e A são argv aprovados executados sem shell pelo check normal, inclusive pela via de operações
governadas. O motor injeta VERIMISSION_MEASUREMENT_KIND, _RUN_ID, _CONTEXT_SHA256, _REPORT e
_PREVIOUS (todos com prefixo VERIMISSION_MEASUREMENT); A recebe VERIMISSION_AUDIT_SELECTION.
O produtor cria a saída nova exclusivamente, nunca sobrescreve prova anterior. Nomes completos
estão nos scripts e nos exemplos. Respeite orçamento e timeout; complete=false não é sucesso.

O formato M é `verimission-measurement-v1`: format/run_id/context_sha256/universe_sha256,
complete=true, claimed_verified e units. Cada linha possui exatamente id/identity/gates/artifacts.
Gates exigidos são pass/fail/unknown e não se compensam. Artifacts associa papel a {path,sha256};
uma unidade qualificada precisa do deliverable exato do universo. Todas as unidades vivas
aparecem uma vez, incluindo as pendentes. claimed_verified deve coincidir com a cardinalidade
do conjunto qualificado fechado por dependências. O motor relê arquivos e não aceita o escalar.

O formato A é `verimission-measurement-audit-v1`: format/run_id/context_sha256/complete/plan_id,
recount_ids, units e controls. recount_ids é o conjunto integral elegível. units é precisamente
a seleção congelada, cada uma com id/status/executed/artifacts. controls exige healthy_passed,
known_bad_rejected e artifacts físicos. Recontagem integral e reexecução amostral são distintas.
Falha impõe hold e próxima seleção integral. Falha de A ou ausência de prova não vira zero aprovado.

## Leitura e limitações

measurement-report retorna units/status, counts, denominator, source, audit_hold e claim_ceiling.
`runs_commands:false` significa que a leitura relê/hashifica provas sem executar verificadores
ou gravar o store. A contagem atual pode cair sem apagar o histórico. O fechamento posterior
registra nova qualificação e reutiliza a invalidação de claims existente. Não promova por TSV.
A fonte de uma unidade e seu conjunto de dependências devem ser declarados corretamente.

O motor valida protocolo, identidade e validade física, não a honestidade de um produtor hostil.
Controle do mesmo usuário sobre código e arquivos não é uma fronteira criptográfica. Um argv
que somente imprime JSON mentiroso pode mentir; adote verificadores revisados e execução
independente. Recibos/AST/corpus finito não provam equivalência universal. Reexecução de
amostra não dá confiança estatística universal. A alegação final permanece limitada à prova.

## Verificação

```powershell
python -B -m unittest discover -s C:/Pacotes/harness_v8.4/tests -v
python -B C:/Pacotes/decompile/examples/run_measurement_pilot.py --harness $h
```

O segundo comando é um piloto sintético descartável. Com `--compiler /usr/bin/gcc` em Linux,
ele compila/executa processos C reais; ainda não valida firmware, ARM ou hardware.
Nenhuma instalação, publicação, modificação de missão real ou migração automática é efetuada.
