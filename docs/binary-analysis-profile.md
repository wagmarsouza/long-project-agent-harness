# Binary Analysis Profile

Esta skill complementa o Harness V8.0 em desassemblagem, firmware e reconstrução de comportamento. Ela fixa a identidade do binário e da configuração, distingue offset de arquivo/VA/espaço de endereço, cria unidades estáveis e confere relatórios de testemunhos sem promover observações a verdade semântica.

O auxiliar é somente leitura. Ele não desassembla, não identifica arquitetura, não executa firmware, não autentica a origem de logs e não valida hardware. Seus campos `semantic_truth_verified`, `hardware_validation_established` e `promotion_authorized` permanecem falsos mesmo quando comparações passam.

## Uso com V8.0

```text
Use skill-harness-v8-0 junto com binary-analysis-profile. Preserve a missão vigente. Identifique o binário e a configuração, procure análises anteriores e planeje o próximo teste discriminante.
```

Prepare cópias dos modelos em `skills/binary-analysis-profile/assets/templates/` e preencha dados reais. Então:

```powershell
$b = '.\skills\binary-analysis-profile\scripts\binary_profile.py'
$p = 'C:\projeto'
python -B $b --project $p inspect --binary 'evidence\image.bin'
python -B $b --project $p target --input "$p\analysis\target.json"
python -B $b --project $p unit --target "$p\analysis\target.json" --input "$p\analysis\unit.json"
python -B $b --project $p witnesses --target "$p\analysis\target.json" --unit "$p\analysis\unit.json" --input "$p\analysis\witnesses.json"
```

Códigos: `0` consistência aprovada no escopo; `2` entrada/integridade recusada; `3` comparação executada com divergência ou incompletude. Leia `result.passed`.

No V8, gere artefatos antes do `check` e declare binário, manifestos, logs, entradas e versão do verificador. Um relatório aprovado só sustenta igualdade entre expectativas/observações declaradas e integridade dos arquivos. Consulte o [SKILL.md](../skills/binary-analysis-profile/SKILL.md) e suas referências para mapa, cobertura e retomada.
