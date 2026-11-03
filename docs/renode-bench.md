# VeriMission Renode Lab

Esta skill cria uma bancada Renode genérica para firmware autorizado. Ela orienta configuração headless, registro do alvo, execução inicialmente sem hooks, preservação de logs/traces e interpretação de um PC trace. A versão pública não contém firmware, endereços, nomes de produto ou caminhos de projetos privados.

Renode é uma dependência separada. Verifique o caminho e a versão instalada. Exemplo:

```powershell
$renode = 'C:\Program Files\Renode\bin\Renode.exe'
$bench = 'C:\projeto\bench\boot-trace.resc'
& $renode --disable-gui --console $bench
```

Copie `skills/renode-bench/assets/templates/boot-trace.resc`, substitua todos os marcadores e revise arquitetura, plataforma, endereço de carga, PC e SP. O modelo é deliberadamente incompleto e não deve ser executado sem essa revisão.

Analise um trace de um PC hexadecimal por linha:

```powershell
$a = '.\skills\renode-bench\scripts\analyze_trace.py'
python -B $a 'C:\projeto\bench\trace-pc.log'
python -B $a 'C:\projeto\bench\trace-pc.log' --top 30 --blocks 60 --jump-threshold 8
```

Frequência de PCs e blocos são heurísticas de navegação. Correlacione com análise estática do mesmo hash/mapa e limite a conclusão ao modelo, injeções e casos observados. Hooks ou bypasses autorizados precisam aparecer no relatório; não os trate como boot natural nem atravesse fronteiras de segurança fora do escopo.

Invocação:

```text
Use renode-bench para preparar e executar uma bancada headless deste firmware autorizado. Comece sem hooks, preserve o binário e documente configuração, logs, injeções, cobertura e limites.
```
