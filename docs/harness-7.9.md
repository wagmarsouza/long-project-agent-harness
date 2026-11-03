# Harness 7.9

O V7.9 mantém o núcleo V7.8 e acrescenta três mecanismos para trabalhos que duram muitas sessões:

- `evidence-scope`: vincula um check real ao que ele verifica, não verifica, limitações e cobertura;
- `capsule` e `capsule-status`: criam uma visão resumida de retomada e conferem se ela ainda corresponde ao estado canônico;
- `prepare-mission`: organiza uma proposta de missão sem inicializar, aprovar ou executar comandos.

Esses recursos não promovem resultados a fatos. A cápsula é uma visão derivada; SQLite permanece a fonte canônica. `prepare-mission` produz rascunho, não autorização. `semantic_truth_verified` permanece falso para declarações de escopo.

## Escolha esta versão quando

- o projeto tem muitas retomadas e compactações de contexto;
- a diferença entre “teste passou” e “o que o teste prova” precisa ficar explícita;
- você quer preparar missões de forma estruturada sem adotar o grafo operacional do V8.0.

## Comandos adicionais

Além dos comandos V7.8:

```text
evidence-scope evidence-scopes prepare-mission capsule capsule-status
```

Fluxo básico igual ao V7.8:

```powershell
$h = '.\harnesses\v7.9\scripts\harness.py'
$p = 'C:\projeto'
python -B $h --project $p resume
python -B $h --project $p validate
python -B $h --project $p review --topic 'componente'
python -B $h --project $p start --input "$p\plan.json"
python -B $h --project $p check --cycle 1 --criterion C1
python -B $h --project $p close --cycle 1 --outcome verified --next 'Próximo teste'
```

Escopo da evidência e retomada:

```powershell
python -B $h --project $p evidence-scope --input "$p\evidence-scope.json"
python -B $h --project $p evidence-scopes
python -B $h --project $p capsule --output "$p\CAPSULE.json"
python -B $h --project $p capsule-status --input "$p\CAPSULE.json"
```

Preparação de uma nova missão:

```powershell
python -B $h --project $p prepare-mission --input "$p\mission-request.json" --output "$p\DRAFT.json"
```

Revise o rascunho e copie a proposta aprovada para o modelo de missão antes de `init`. O comando não autoriza ações nem modifica uma missão vigente.

## Skill correspondente

Use [skills/skill-harness-v7-9](../skills/skill-harness-v7-9/) e invoque `skill-harness-v7-9`.
