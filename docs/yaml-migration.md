# Migração do estado SQLite para YAML

As publicações corrigidas do VeriMission Core 7.8, Continuity 7.9 e Control 8.0 usam `.harness/state.yaml` como única fonte canônica. O documento contém o estado completo, o histórico de auditoria, a versão do formato e um checksum SHA-256 do conteúdo normalizado.

## Pré-requisitos

```powershell
python -m pip install "PyYAML>=6,<7"
```

Não execute `init` se `.harness/state.sqlite` já existir. Use o executor da mesma versão que pretende adotar:

```powershell
python -B $h --project $p migrate-sqlite
python -B $h --project $p validate
python -B $h --project $p resume
```

## Garantias da migração

- o SQLite é aberto somente para leitura e precisa passar em `PRAGMA integrity_check`;
- o estado e todas as linhas de auditoria são importados preservando IDs, revisões e conteúdo;
- o YAML é gravado em arquivo temporário, sincronizado e substituído atomicamente;
- `state.sqlite` não é apagado, renomeado nem alterado;
- o YAML registra nome, hash SHA-256, revisão e quantidade de eventos da origem;
- um YAML existente nunca é sobrescrito por `migrate-sqlite`.

Depois da migração, novas revisões existem somente no YAML. Portanto, o SQLite preservado é uma origem histórica, não um backup atualizado. Voltar a um executor antigo descartaria do ponto de vista desse executor todo trabalho posterior à migração.

## Integridade e concorrência

Cada leitura verifica formato, schema, estrutura da auditoria e checksum. Um lock de arquivo exclusivo serializa leitores e escritores entre processos. As mutações usam substituição atômica; uma falha antes de `os.replace` mantém o último documento confirmado. O checksum detecta alteração acidental, mas não é assinatura, autenticação de operador ou prova da verdade semântica dos registros.

Arquivos `.harness/state.yaml.lock` coordenam o acesso e não são uma segunda fonte de estado. Relatórios, cápsulas e índices continuam derivados e não podem ser importados como autoridade.
