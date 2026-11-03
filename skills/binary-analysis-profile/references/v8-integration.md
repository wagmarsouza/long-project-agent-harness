# Integração com o V8 existente

Este pacote não inclui outra cópia do Harness. Usar o executor V8.0 adotado pelo projeto, com seus módulos originais. Não inicializar uma segunda base, instalar outra versão, editar `.harness/state.sqlite` ou mudar regras globais para adotar o perfil.

## Missão existente

1. Abrir a skill V8.0 e executar `resume` e `validate` com `--project` correto.
2. Buscar resultados e revisar o tópico antes de iniciar uma investigação. Preservar o fluxo `review → start → check → close`, critérios e recibos atuais.
3. Usar o auxiliar somente nos critérios já compatíveis. Para acrescentar/remover/modificar um critério da missão vigente, preparar a proposta apenas após pedido/autorização explícita e seguir o processo humano `preview-mission` / `revise-mission`. Não aplicar migração automática.
4. Separar o critério de integridade do alvo de critérios semânticos reais. O primeiro pode usar `target`/`unit`; os demais exigem uma ferramenta/teste que discriminem a afirmação. `witnesses` confere um relatório, não gera nem autentica a execução.

## Exemplo de critério em uma nova missão

Substituir caminhos/descrição antes do `init`. O exemplo é de integridade documental, não de comportamento do firmware:

```json
{
  "id": "BIN-ID",
  "description": "Conferir a identidade e a consistência do mapa declarado; sem autenticar arquitetura ou semântica",
  "argv": ["PYTHON_REAL", "-B", "tools/binary_profile.py", "--project", "RAIZ_REAL", "target", "--input", "analysis/target.json"],
  "artifacts": ["evidence/image.bin", "analysis/target.json", "tools/binary_profile.py"]
}
```

Para o exemplo funcionar, copiar o auxiliar para `tools/binary_profile.py` no projeto. A cópia local permite que o V8 proteja também a versão do verificador. Não declarar uma cópia local como evidência e executar silenciosamente outra versão da skill. Revisar o código antes de executar; caminho real do Python também deve ser verificado. O piloto incluído demonstra esse arranjo com bytes sintéticos.

O V8 executa argv com cwd na raiz do projeto. Declarar os caminhos completos relevantes em `artifacts`, incluindo inputs/logs e verificadores externos que forem copiados para o projeto. Não usar globs presumindo que o executor os expandirá. Para `unit`, incluir alvo e manifesto da unidade. Para `witnesses`, incluir também relatório e todos os arquivos referenciados por casos/controle. O hash do relatório sozinho não protege mudanças posteriores em seus arquivos externos.

Gerar e congelar os arquivos antes de `check`. Seu código de retorno precisa refletir o resultado; não encapsular a falha em um comando que sempre retorna zero. Conferir `result.passed` no retorno do coordenador. Se um resultado não puder ser reproduzido em leitura, separar aquisição autorizada e conferência do registro, declarando o limite da prova. Não inventar reexecução.

## Registrar o alcance e a retomada

Usar `evidence-scope` com o check real para declarar o que verifica e não verifica, limites e cobertura do universo pertinente. Consultar o esquema da distribuição V8 em uso; não criar um formato paralelo nem trocar essas declarações por provas. Os três denominadores do núcleo continuam válidos quando aplicáveis.

Vincular tarefas e claims com dependências reais; aliases ajudam recuperação, mas não provam equivalência entre duas regiões. Usar `context-pack`/`view-status` ou `capsule`/`capsule-status` para retomada e consultar o SQLite quando houver divergência. Cápsulas não são importáveis como autorização ou fato. Não copiar tudo para memória global nem manter uma lista concorrente de fatos em status JSON.

Depois de invalidar configuração/evidência, revisar os dependentes afetados pelo fluxo do V8. Retratação e revalidação preservam história e não contam como descoberta nova. Ao encerrar, `traceability`, `accept-mission` e `validate` avaliam o contrato adotado; aceitação de um critério de integridade não representa recuperação completa da semântica do alvo.
