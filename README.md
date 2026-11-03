<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/branding/verimission-logo-dark.png">
  <source media="(prefers-color-scheme: light)" srcset="assets/branding/verimission-logo-light.png">
  <img alt="VeriMission" src="assets/branding/verimission-logo-light.png" width="760">
</picture>

# VeriMission

**Controle baseado em evidências para projetos longos com agentes de IA.**

[Identidade visual e versões do logo](docs/branding.md)

[Guia de migração SQLite → YAML](docs/yaml-migration.md)

[![skills.sh](https://skills.sh/b/wagmarsouza/long-project-agent-harness)](https://skills.sh/wagmarsouza/long-project-agent-harness)

VeriMission é uma família de harnesses locais e skills para agentes que trabalham em projetos longos, com missão explícita, evidências verificáveis, retomada entre sessões e controles contra inflação de progresso. As skills especializadas de análise binária e bancadas Renode estão agora no projeto independente [DisasmLedger](https://github.com/wagmarsouza/disasmledger).

O projeto não fornece um agente autônomo nem amplia permissões. O harness coordena trabalho executado por um agente ou operador, registra ciclos em YAML e verifica critérios por comandos declarados. A qualidade semântica dos testes e das conclusões continua exigindo julgamento.

## Componentes

| Componente | Finalidade | Quando escolher |
| --- | --- | --- |
| [VeriMission Core 7.8](docs/harness-7.8.md) | Núcleo estável de missão, revisão, ciclos, checks, claims, retratações e recuperação | Projetos longos que precisam de disciplina e rastreabilidade com menor superfície operacional |
| [VeriMission Continuity 7.9](docs/harness-7.9.md) | Acrescenta escopo de evidência, cápsulas de retomada e preparação de missão | Projetos longos com muitas sessões e necessidade de declarar exatamente o que cada teste cobre |
| [VeriMission Control 8.0](docs/harness-8.0.md) | Acrescenta grafo de tarefas, busca, rastreabilidade, contexto, aceitação final e operações governadas | Projetos maiores, com dependências, múltiplas frentes e critérios formais de conclusão |
| [VeriMission Control 8.1](docs/harness-8.1.md) | Acrescenta projeções JSON/Mermaid/DOT, relatório de PR e importação explícita de uso/custos | Missões que precisam de revisão visual, relatórios reproduzíveis e uso de vários agentes |

As versões são preservadas lado a lado. V7.9 estende V7.8; V8.0 amplia a coordenação sem transformar resultados em verdade automática. Para trabalhos de desassemblagem ou firmware, instale separadamente [binary-analysis-profile e renode-bench](https://github.com/wagmarsouza/disasmledger#instala%C3%A7%C3%A3o).

## Requisitos

- Python 3.11 ou superior.
- PyYAML 6.x (`python -m pip install -r requirements.txt`). O importador legado usa o `sqlite3` da biblioteca padrão apenas durante `migrate-sqlite`.
- Um cliente de agentes que reconheça pastas com `SKILL.md`, para usar as skills.

## Início rápido com o VeriMission Control 8.1

Clone o repositório e defina caminhos reais:

```powershell
git clone https://github.com/wagmarsouza/long-project-agent-harness.git
$repo = Resolve-Path '.\long-project-agent-harness'
$project = Resolve-Path 'C:\caminho\do\projeto'
$harness = Join-Path $repo 'harnesses\v8.1\scripts\harness.py'
```

Copie e preencha os modelos; não use os marcadores como dados reais:

```powershell
Copy-Item "$repo\harnesses\v8.1\templates\mission.example.json" "$project\mission.json"
Copy-Item "$repo\harnesses\v8.1\templates\plan.example.json" "$project\plan.json"
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

`init` cria `.harness/state.yaml` no projeto. Não edite esse arquivo diretamente: o checksum detecta alteração externa. Em uma missão existente em YAML, comece com `resume` e `validate`; não execute `init` novamente.

### Migração de projetos anteriores

Se o projeto ainda contém `.harness/state.sqlite`, não execute `init`. Atualize o código do harness e rode uma única vez:

```powershell
python -B $harness --project $project migrate-sqlite
python -B $harness --project $project validate
```

O comando valida o banco legado, cria atomicamente `.harness/state.yaml`, importa o estado e toda a auditoria, grava hash e proveniência da migração e mantém `state.sqlite` byte a byte como cópia legada. A partir daí, somente o YAML é canônico. Se a migração falhar, nenhum YAML parcial substitui o estado anterior.

## Instalação das skills

### Instalação pelo catálogo aberto

As quatro skills do VeriMission podem ser instaladas pelo cliente `skills`:

| Nome público | ID técnico | Página no catálogo | Instalação individual |
| --- | --- | --- | --- |
| VeriMission Core 7.8 | `skill-harness-v7-8` | [skills.sh](https://skills.sh/wagmarsouza/long-project-agent-harness/skill-harness-v7-8) | `npx skills add wagmarsouza/long-project-agent-harness --skill skill-harness-v7-8` |
| VeriMission Continuity 7.9 | `skill-harness-v7-9` | [skills.sh](https://skills.sh/wagmarsouza/long-project-agent-harness/skill-harness-v7-9) | `npx skills add wagmarsouza/long-project-agent-harness --skill skill-harness-v7-9` |
| VeriMission Control 8.0 | `skill-harness-v8-0` | [skills.sh](https://skills.sh/wagmarsouza/long-project-agent-harness/skill-harness-v8-0) | `npx skills add wagmarsouza/long-project-agent-harness --skill skill-harness-v8-0` |
| VeriMission Control 8.1 | `skill-harness-v8-1` | [skills.sh](https://skills.sh/wagmarsouza/long-project-agent-harness/skill-harness-v8-1) | `npx skills add wagmarsouza/long-project-agent-harness --skill skill-harness-v8-1` |

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
Copy-Item '.\skills\skill-harness-v8-1' "$env:USERPROFILE\.config\opencode\skills\skill-harness-v8-1" -Recurse

# Diretório convencional de skills de agentes
Copy-Item '.\skills\skill-harness-v8-1' "$env:USERPROFILE\.agents\skills\skill-harness-v8-1" -Recurse
```

Reinicie ou recarregue o cliente após a cópia, conforme ele exigir. Instalar a pasta permite descoberta; não torna a skill globalmente ativa em toda mensagem.

Invocação em linguagem natural:

```text
Use a skill skill-harness-v8-1 neste projeto. Retome a missão existente e preserve o contrato e as evidências.
```

Para desassemblagem e Renode, consulte [DisasmLedger](https://github.com/wagmarsouza/disasmledger). Os IDs técnicos das duas skills foram preservados no novo repositório.

Comandos `/...` dependem do cliente e não são criados por este repositório. Mencionar o nome da skill ou seu `SKILL.md` é o método portátil.

## Estrutura

```text
harnesses/                  executores portáteis, referências, modelos e testes
  v7.8/
  v7.9/
  v8.0/
  v8.1/
skills/                     pacotes de instruções para agentes
  skill-harness-v7-8/
  skill-harness-v7-9/
  skill-harness-v8-0/
  skill-harness-v8-1/
docs/                       descrição e comandos de cada componente
assets/branding/            logos VeriMission para temas claro e escuro
```

## Verificação

Execute os testes da versão usada:

```powershell
uv run --with pyyaml python -m unittest discover -s '.\harnesses\v7.8\tests' -v
uv run --with pyyaml python -m unittest discover -s '.\harnesses\v7.9\tests' -v
uv run --with pyyaml python -m unittest discover -s '.\harnesses\v8.0\tests' -v
uv run --with pyyaml python -m unittest discover -s '.\harnesses\v8.1\tests' -v
```

Os testes de análise binária e Renode estão no [DisasmLedger](https://github.com/wagmarsouza/disasmledger).

## Segurança e publicação de evidências

Não grave segredos em missões, logs ou relatórios. Não publique firmware, chaves, traces proprietários ou endereços específicos de um produto sem autorização. Consulte [SECURITY.md](SECURITY.md).

## Licença

Ainda não foi adicionada uma licença de reutilização. O código está publicamente visível, mas a ausência de uma licença não concede automaticamente permissão para copiar, modificar ou redistribuir. O proprietário deve escolher e adicionar uma licença antes de incentivar redistribuição ampla.
