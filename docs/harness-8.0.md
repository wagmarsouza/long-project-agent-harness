# VeriMission Control 8.0

O V8.0 é a versão indicada para missões extensas com várias frentes e dependências. Ele preserva o V7.9 e acrescenta grafo de tarefas, claims revalidáveis, aliases e busca, diagnósticos, contexto por tarefa, matriz de rastreabilidade, avaliação final da missão e um adaptador local opcional para operações governadas.

O V8 não é um daemon nem intercepta todas as ferramentas do agente. `task-ready` consulta elegibilidade; não despacha trabalho. `accept-mission` avalia o contrato declarado; não garante correção universal. Aprovação de uma operação vale para a operação exata e não autoriza mudança da missão.

## Escolha esta versão quando

- tarefas possuem dependências e critérios diferentes;
- várias sessões precisam recuperar contexto por tópico/tarefa;
- a conclusão precisa de matriz requisito → critério → check → artefato;
- operações com efeitos precisam de preparação, aprovação e reconciliação explícitas;
- você quer uma avaliação final reproduzível da missão adotada.

## Grupos de comandos

Núcleo e evidência:

```text
init review start check close interrupt resume validate
claim retract claim-reverify step-back consolidate
evidence-scope evidence-scopes prepare-mission capsule capsule-status
metrics export backup preview-mission revise-mission
```

Tarefas e recuperação:

```text
task-add task-claim task-complete task-reopen tasks task-ready
alias-add search context-pack view-status diagnostic-add
trace traceability accept-mission capabilities usage-report
```

Operações governadas:

```text
operation-prepare operation-status operation-approve operation-run operation-reconcile
```

## Fluxo de missão

```powershell
$h = '.\harnesses\v8.0\scripts\harness.py'
$p = 'C:\projeto'
python -B $h --project $p init --input "$p\mission.json"
python -B $h --project $p task-add --input "$p\task.json"
python -B $h --project $p task-ready
python -B $h --project $p task-claim --input "$p\task-owner.json"
python -B $h --project $p review --topic 'componente'
python -B $h --project $p start --input "$p\plan.json"
python -B $h --project $p check --cycle 1 --criterion C1
python -B $h --project $p close --cycle 1 --outcome verified --next 'Próxima tarefa'
python -B $h --project $p task-complete --input "$p\task-complete.json"
```

Recuperação e aceitação:

```powershell
python -B $h --project $p search --query 'termo' --limit 20
python -B $h --project $p context-pack --task T1 --output "$p\CONTEXT.json"
python -B $h --project $p view-status --input "$p\CONTEXT.json"
python -B $h --project $p traceability
python -B $h --project $p accept-mission --output "$p\ACCEPTANCE.json"
python -B $h --project $p validate
```

Operação governada:

```powershell
python -B $h --project $p operation-prepare --input "$p\operation.json"
python -B $h --project $p operation-status --id OP1
# O usuário revisa e confirma pessoalmente quando a operação exigir aprovação.
python -B $h --project $p operation-approve --id OP1
python -B $h --project $p operation-run --id OP1
```

Use `--help` após qualquer subcomando para ver parâmetros da versão publicada. Não responda confirmações interativas em nome do usuário e não procure um bypass `--yes`.

## Skill correspondente

Use [skills/skill-harness-v8-0](../skills/skill-harness-v8-0/) e invoque `skill-harness-v8-0`.
