# Harness 7.8

O V7.8 é o núcleo portátil para projetos que atravessam muitas conversas ou sessões. Ele congela uma missão com objetivo, escopo, exclusões, critérios executáveis e orçamento; registra ciclos de investigação; executa checks; guarda hashes de artefatos; permite claims e retratações; impede fechamento verificado sem evidência atual; e oferece retomada, exportação e backup.

Seus controles centrais são: recuperar antes de repetir, revisar evidências anteriores, planejar a hipótese e o teste, executar dentro do escopo, verificar por critérios e fechar com um próximo passo. Teto de alegação, denominadores de cobertura e auditoria de honestidade limitam o que pode ser concluído. O executor ajuda com proveniência, mas não detecta automaticamente mentiras nem avalia a suficiência semântica de um teste.

## Escolha esta versão quando

- o projeto é longo, mas o grafo de tarefas ainda pode ser gerenciado fora do executor;
- você quer um núcleo menor e estável;
- precisa de revisão explícita da missão, retratações e antirretrabalho;
- não precisa das cápsulas/escopo do V7.9 ou da coordenação avançada do V8.0.

## Comandos

```text
init start claim retract step-back consolidate
preview-mission revise-mission review check close interrupt
resume validate metrics export backup
```

Fluxo mínimo:

```powershell
$h = '.\harnesses\v7.8\scripts\harness.py'
$p = 'C:\projeto'
python -B $h --project $p init --input "$p\mission.json"
python -B $h --project $p review --topic 'componente'
python -B $h --project $p start --input "$p\plan.json"
python -B $h --project $p check --cycle 1 --criterion C1
python -B $h --project $p close --cycle 1 --outcome verified --next 'Próximo passo'
python -B $h --project $p validate
```

Retomada e diagnóstico:

```powershell
python -B $h --project $p resume
python -B $h --project $p validate
python -B $h --project $p metrics
python -B $h --project $p export --output "$p\REPORT.md"
python -B $h --project $p backup --output "$p\backups\state.sqlite"
```

Correções e conhecimento:

```powershell
python -B $h --project $p claim --input "$p\claim.json"
python -B $h --project $p retract --input "$p\retraction.json"
python -B $h --project $p step-back --input "$p\step-back.json"
python -B $h --project $p consolidate --input "$p\consolidation.json"
```

A revisão de missão é excepcional. Primeiro use `preview-mission`; `revise-mission` exige pedido/autorização explícita do usuário e confirmação interativa pessoal. Não automatize essa confirmação.

## Skill correspondente

Use [skills/skill-harness-v7-8](../skills/skill-harness-v7-8/) para dar ao agente as regras e o executor juntos. A skill pode ser chamada como `skill-harness-v7-8`.
