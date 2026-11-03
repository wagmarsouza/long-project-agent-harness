<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/branding/verimission-logo-dark.png">
  <source media="(prefers-color-scheme: light)" srcset="assets/branding/verimission-logo-light.png">
  <img alt="VeriMission" src="assets/branding/verimission-logo-light.png" width="760">
</picture>

# VeriMission

**Controle baseado em evidências para projetos longos com agentes de IA.**

[![skills.sh](https://skills.sh/b/wagmarsouza/long-project-agent-harness)](https://skills.sh/wagmarsouza/long-project-agent-harness)

VeriMission é uma família de harnesses locais e skills para agentes que trabalham em projetos longos, com missão explícita, evidências verificáveis, retomada entre sessões e controles contra inflação de progresso. O repositório também inclui dois complementos especializados: análise binária e bancadas Renode.

O projeto não fornece um agente autônomo nem amplia permissões. O harness coordena trabalho executado por um agente ou operador, registra ciclos em SQLite e verifica critérios por comandos declarados. A qualidade semântica dos testes e das conclusões continua exigindo julgamento.

## Componentes

| Componente | Finalidade | Quando escolher |
| --- | --- | --- |
| [VeriMission Core 7.8](docs/harness-7.8.md) | Núcleo estável de missão, revisão, ciclos, checks, claims, retratações e recuperação | Projetos longos que precisam de disciplina e rastreabilidade com menor superfície operacional |
| [VeriMission Continuity 7.9](docs/harness-7.9.md) | Acrescenta escopo de evidência, cápsulas de retomada e preparação de missão | Projetos longos com muitas sessões e necessidade de declarar exatamente o que cada teste cobre |
| [VeriMission Control 8.0](docs/harness-8.0.md) | Acrescenta grafo de tarefas, busca, rastreabilidade, contexto, aceitação final e operações governadas | Projetos maiores, com dependências, múltiplas frentes e critérios formais de conclusão |
| [VeriMission Binary](docs/binary-analysis-profile.md) | Especializa o V8 em identidade de binários, mapas de endereço, unidades e testemunhos | Desassemblagem, firmware e reconstrução de comportamento em missões longas |
| [VeriMission Renode Lab](docs/renode-bench.md) | Orienta bancadas Renode reproduzíveis e análise de traces de PC | Emulação autorizada, trace de boot e comparação de comportamento em modelo |

As versões são preservadas lado a lado. V7.9 estende V7.8; V8.0 amplia a coordenação sem transformar resultados em verdade automática. O perfil de análise binária e a bancada Renode são skills separadas: uma organiza evidência de desassemblagem; a outra conduz execução emulada.

## Requisitos

- Python 3.11 ou superior.
- Biblioteca padrão do Python e SQLite incluído no Python para os harnesses.
- Um cliente de agentes que reconheça pastas com `SKILL.md`, para usar as skills.
- Renode instalado separadamente somente para a skill `renode-bench`.

## Início rápido com o VeriMission Control 8.0

Clone o repositório e defina caminhos reais:

```powershell
git clone https://github.com/wagmarsouza/long-project-agent-harness.git
$repo = Resolve-Path '.\long-project-agent-harness'
$project = Resolve-Path 'C:\caminho\do\projeto'
$harness = Join-Path $repo 'harnesses\v8.0\scripts\harness.py'
```

Copie e preencha os modelos; não use os marcadores como dados reais:

```powershell
Copy-Item "$repo\harnesses\v8.0\templates\mission.example.json" "$project\mission.json"
Copy-Item "$repo\harnesses\v8.0\templates\plan.example.json" "$project\plan.json"
```

Depois de revisar os comandos e artefatos da missão:

```powershell
python -B $harness --project $project init --input "$project\mission.json"
python -B $harness --project $project review --topic 'primeira-tarefa'
# Preencha plan.json com o review_id e os claims retornados.
python -B $harness --project $project start --input "$project\plan.json"
python -B $harness --project $project check --cycle 1 --criterion C1
python -B $harness --project $project close --cycle 1 --outcome verified --next 'Próximo passo concreto'
python -B $harness --project $project validate
```

`init` cria `.harness/state.sqlite` no projeto. Não edite esse banco diretamente. Em uma missão existente, comece com `resume` e `validate`; não execute `init` novamente.

## Instalação das skills

### Instalação pelo catálogo aberto

As cinco skills estão publicadas no [skills.sh](https://skills.sh/) e podem ser instaladas pelo cliente oficial `skills`:

| Nome público | ID técnico | Página no catálogo | Instalação individual |
| --- | --- | --- | --- |
| VeriMission Core 7.8 | `skill-harness-v7-8` | [skills.sh](https://skills.sh/wagmarsouza/long-project-agent-harness/skill-harness-v7-8) | `npx skills add wagmarsouza/long-project-agent-harness --skill skill-harness-v7-8` |
| VeriMission Continuity 7.9 | `skill-harness-v7-9` | [skills.sh](https://skills.sh/wagmarsouza/long-project-agent-harness/skill-harness-v7-9) | `npx skills add wagmarsouza/long-project-agent-harness --skill skill-harness-v7-9` |
| VeriMission Control 8.0 | `skill-harness-v8-0` | [skills.sh](https://skills.sh/wagmarsouza/long-project-agent-harness/skill-harness-v8-0) | `npx skills add wagmarsouza/long-project-agent-harness --skill skill-harness-v8-0` |
| VeriMission Binary | `binary-analysis-profile` | [skills.sh](https://skills.sh/wagmarsouza/long-project-agent-harness/binary-analysis-profile) | `npx skills add wagmarsouza/long-project-agent-harness --skill binary-analysis-profile` |
| VeriMission Renode Lab | `renode-bench` | [skills.sh](https://skills.sh/wagmarsouza/long-project-agent-harness/renode-bench) | `npx skills add wagmarsouza/long-project-agent-harness --skill renode-bench` |

Para listar o que o instalador encontra antes de copiar qualquer arquivo:

```powershell
npx skills add wagmarsouza/long-project-agent-harness --list
```

Para instalar todas as skills do repositório no agente escolhido:

```powershell
npx skills add wagmarsouza/long-project-agent-harness --all
```

O suporte e o caminho final variam conforme o agente. Revise os arquivos antes da instalação: skills executam com as permissões concedidas ao agente hospedeiro.

### Instalação manual

Copie somente as skills desejadas para a pasta de descoberta do cliente, mantendo cada diretório inteiro. Exemplos:

```powershell
# OpenCode no Windows
Copy-Item '.\skills\skill-harness-v8-0' "$env:USERPROFILE\.config\opencode\skills\skill-harness-v8-0" -Recurse
Copy-Item '.\skills\binary-analysis-profile' "$env:USERPROFILE\.config\opencode\skills\binary-analysis-profile" -Recurse
Copy-Item '.\skills\renode-bench' "$env:USERPROFILE\.config\opencode\skills\renode-bench" -Recurse

# Diretório convencional de skills de agentes
Copy-Item '.\skills\skill-harness-v8-0' "$env:USERPROFILE\.agents\skills\skill-harness-v8-0" -Recurse
```

Reinicie ou recarregue o cliente após a cópia, conforme ele exigir. Instalar a pasta permite descoberta; não torna a skill globalmente ativa em toda mensagem.

Invocação em linguagem natural:

```text
Use a skill skill-harness-v8-0 neste projeto. Retome a missão existente e preserve o contrato e as evidências.
```

Para desassemblagem:

```text
Use skill-harness-v8-0 junto com binary-analysis-profile. Confira a identidade do binário e recupere evidências anteriores antes de analisar novamente.
```

Para Renode:

```text
Use renode-bench para preparar uma execução headless, inicialmente sem hooks, e registrar hash, configuração, logs, injeções e limites da conclusão.
```

Comandos `/...` dependem do cliente e não são criados por este repositório. Mencionar o nome da skill ou seu `SKILL.md` é o método portátil.

## Estrutura

```text
harnesses/                  executores portáteis, referências, modelos e testes
  v7.8/
  v7.9/
  v8.0/
skills/                     pacotes de instruções para agentes
  skill-harness-v7-8/
  skill-harness-v7-9/
  skill-harness-v8-0/
  binary-analysis-profile/
  renode-bench/
docs/                       descrição e comandos de cada componente
assets/branding/            logos VeriMission para temas claro e escuro
```

## Verificação

Execute os testes da versão usada:

```powershell
python -B -m unittest discover -s '.\harnesses\v7.8\tests' -v
python -B -m unittest discover -s '.\harnesses\v7.9\tests' -v
python -B -m unittest discover -s '.\harnesses\v8.0\tests' -v
python -B -m unittest discover -s '.\skills\binary-analysis-profile\tests' -v
python -B -m unittest discover -s '.\skills\renode-bench\tests' -v
```

Os testes de análise binária e Renode usam fixtures sintéticas. Eles não validam firmware, hardware nem um modelo Renode real.

## Segurança e publicação de evidências

Não grave segredos em missões, logs ou relatórios. Não publique firmware, chaves, traces proprietários ou endereços específicos de um produto sem autorização. Consulte [SECURITY.md](SECURITY.md).

## Licença

Ainda não foi adicionada uma licença de reutilização. O código está publicamente visível, mas a ausência de uma licença não concede automaticamente permissão para copiar, modificar ou redistribuir. O proprietário deve escolher e adicionar uma licença antes de incentivar redistribuição ampla.
