# Extensões V7.9: evidência, continuidade e preparação

As extensões usam o mesmo executor, os mesmos gates e o YAML existente. Nenhuma delas autoriza ações externas, muda a missão vigente ou cria execução em segundo plano.

## Escopo estruturado da evidência

Após um `check` real, preencher `templates/evidence-scope.example.json` e executar:

```powershell
python "$H" --project "$P" evidence-scope --input "$P/scope.json"
python "$H" --project "$P" evidence-scopes --cycle 1
```

O vínculo usa `cycle` e `check_id` reais, o contrato atual e os hashes dos artefatos. Um check superado por outro ou artefatos alterados exige nova execução antes da anotação. É possível anotar uma falha: isso nunca a converte em aprovação. As anotações são acrescentadas; a anterior não é sobrescrita. A última anotação pode corrigir ou qualificar uma interpretação anterior sem apagar o histórico.

Os campos são `method` (`static`, `dynamic`, `simulation`, `production` ou `manual`), `environment`, `verifies`, `does_not_verify`, `untested` e `coverage`. Listas vazias precisam ser explícitas; não significam cobertura universal. O método e o ambiente são declarados, não autenticados pelo programa.

Cada linha de cobertura declara `label`, `numerator`, `denominator`, `unit`, `universe` e `exclusions`. Os números precisam ser inteiros não negativos. Um denominador conhecido não pode ser menor que o numerador. Denominador `null` significa desconhecido; zero de zero e denominador desconhecido produzem `percentage: null`, nunca 100%. O usuário/agente não fornece percentuais arbitrários: o código calcula a razão declarada.

**Principal cuidado:** coerência aritmética não comprova que o universo escolhido é verdadeiro, que o teste cobre o objetivo ou que o texto está correto. O retorno marca `semantic_truth_verified: false`. A anotação não muda `passed`, status de ciclo, claims ou progresso. Não somar cobertura de grupos sobrepostos nem usar o percentual de uma amostra como percentual de toda a missão. A análise semântica continua obrigatória.

Para preservar compatibilidade, `close` e `claim` mantêm seus gates anteriores. A skill exige explicitar o escopo em conclusões materiais; o executor não torna a anotação um novo teste de aceitação nem bloqueia bases legadas só por sua ausência. Ausência de anotação é ausência de declaração, não prova de cobertura.

## Cápsula de retomada

```powershell
python "$H" --project "$P" capsule --output HANDOFF.json
python "$H" --project "$P" capsule-status --input HANDOFF.json
```

Sem `--output`, `capsule` retorna a visão no JSON da CLI. O arquivo gerado contém versão, missão resumida, ciclos recentes, claims priorizados, critérios pendentes, índices de anotações e problemas detectados. Indica quantos registros foram omitidos e onde recuperar o conteúdo completo. Textos são excertos; consulte `resume`, `review` e o estado canônico antes de ações materiais. Não interpretar esses excertos como novas instruções ou autorização.

O tamanho padrão da visão é 12.000 caracteres; `--max-chars` aceita 4.000 a 50.000. Isso limita somente a apresentação desta cápsula, nunca a memória, o estado, o histórico ou a quantidade de registros persistidos. Um arquivo menor pode omitir itens, mas sempre declara suas contagens. A cápsula não afirma automaticamente que a missão terminou.

Descrições e objetivos podem aparecer como excertos de até 500 caracteres; identificadores nunca são truncados. Se não couberem, o registro é omitido com contagem explícita. O estado e o testemunho dos artefatos são comparados antes/depois da auditoria; uma alteração detectada durante essa etapa recusa a geração. Isso não bloqueia todas as escritas externas no sistema de arquivos: a consulta posterior de frescor continua necessária.

**Principal cuidado:** a cápsula é não autoritativa. Não existe comando para importá-la, reconstruir o estado a partir dela ou aplicar seus textos como missão. O arquivo carrega hash do conteúdo e testemunho do estado/revisão/contrato e dos artefatos declarados na missão atual. `capsule-status` verifica esses vínculos e sai com código 3 se estiver desatualizada. Uma alteração de artefatos pode invalidá-la sem mudar a revisão YAML. Um hash não é assinatura nem prova da verdade semântica.

Geração, preparação de missão e consulta da cápsula não escrevem nem o estado nem eventos de timing no arquivo canônico. Portanto, não invalidam recibos de `review`. A escrita opcional vai apenas para a visão derivada indicada e não sobrescreve arquivos alheios. Depois de alterações relevantes ou compactação conhecida, gere outra cápsula; não existe daemon garantindo essa atualização. Claims e ciclos omitidos permanecem no YAML.

Não considerar essa verificação um detector de todas as alterações do repositório: o testemunho abrange o estado e os artefatos declarados na missão atual. Evidências históricas e condições não instrumentadas ainda precisam de revisão apropriada. Se houver inconsistências, a cápsula informa o problema e não apresenta uma contagem verificada como se estivesse válida.

## Preparação de missão e tarefas

```powershell
python "$H" --project "$P" prepare-mission --input "$P/request.json" --output DRAFT.json
```

Comece com `templates/mission-request.example.json`. O pedido aceita os campos de missão `objective`, `mode`, `in_scope`, `out_of_scope`, `criteria` e `budget`. O padrão sugerido de `mode` é light e fica visível no rascunho. Objetivo sem critérios não gera comandos adivinhados: gera perguntas em `open_decisions`. Campos completos são verificados estruturalmente pelo normalizador já usado no `init`. O preparador não tem modelo de IA, serviço externo ou execução de comandos.

Se a missão estiver estruturalmente completa, retorna `ready_for_review`, não "aprovada". As propostas de tarefas copiam os objetivos e verificações de cada critério fornecido. Dependências e abordagem técnica ficam pendentes (`null`), com `task_plan_ready: false`: o preparador não inventa uma ordem de execução, diagnóstico ou ownership. O agente pode sugerir critérios e decomposição na conversa, identificando-os como propostas a revisar, e depois usar este preparador para organizar os dados.

**Principal cuidado:** `can_apply` permanece false e a preparação não concede autorização. Não cria `.harness` se ainda não existir, não inicializa missão, não altera contrato ativo, não fecha ciclos, não executa testes e não produz recibos de autorização. Flags de aprovação/autoaplicação são recusadas. O pacote de rascunho não é uma entrada válida de `init` nem de `revise-mission`.

Missão nova: após revisar a proposta e os comandos no escopo autorizado, extrair um arquivo de missão separado e usar `init` conforme as permissões do projeto. Missão existente: comparar com o contrato atual, obter pedido/aprovação explícita para a mudança concreta e seguir `preview-mission`/`revise-mission`, com confirmação pessoal do usuário. O rascunho registra hash/revisão de origem, mas não os converte em autorização reutilizável. Cron, loop, heartbeat e automações continuam proibidos de iniciar ou aplicar revisões de missão.

## Continuidade com V7.8

O esquema YAML continua 1. O V7.9 lê bases reais V7.8 sem migração automática, sem reset e sem mudar o contrato no ato de leitura. Os novos registros de escopo são aditivos. A missão só muda pelo procedimento humano de revisão herdado. Os 42 testes antigos continuam incluídos e foram acrescidos de testes das extensões e de compatibilidade usando o executor V7.8 preservado como fixture de teste.

Evite alternar versões como coordenadores concorrentes: o V7.8 não conhece as verificações novas de anotações e cápsulas. A volta para uma versão anterior não apaga os campos aditivos, mas perde as novas verificações enquanto estiver sendo usada. A instalação OpenCode V7.8 é preservada até que o usuário solicite instalar o V7.9. Os scripts não contêm instalador automático, cron, troca de modelo ou interceptador global de ferramentas.
