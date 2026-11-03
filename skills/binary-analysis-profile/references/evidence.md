# Evidências, bancada e teto de alegação

## Força de cada resultado

| Método | Alegação possível, quando sustentada | Lacuna que permanece |
| --- | --- | --- |
| Hash e mapa declarado | Estes bytes e estes intervalos foram usados; o mapa é internamente consistente | Arquitetura/base corretas, legitimidade e comportamento |
| Inspeção estática | Estas instruções/refs sustentam esta hipótese delimitada | Decodificação, caminhos indiretos e comportamento real podem divergir |
| Função isolada | O trecho produziu o resultado observado sob estas entradas e estado | ABI, periféricos, concorrência e integração completos |
| Boot/integração emulada | Estes estados/efeitos ocorreram no modelo descrito | Fidelidade dos periféricos e comportamento no hardware |
| Observação em hardware | O dispositivo/configuração observados tiveram este comportamento nestas condições | Outros dispositivos, entradas, versões e universalidade |

Os níveis não são uma escada automática. Observação em hardware pode ser estreita; uma prova estática específica pode responder melhor a outra pergunta. Não converter quantidade de logs em probabilidade de verdade.

## Preparar um experimento pertinente

Explicitar entrada/estado inicial, entradas dependentes, reset e pré-condições, ponto de observação, oráculo esperado e justificativa independente, timeout/condição de parada e estado final. Registrar ferramenta/versão, configuração e dependências. Distinguir configuração integral do que foi omitido. Se houve stubs, traps, valores de RAM/registradores forçados, relógio artificial, chamadas interceptadas ou periféricos substituídos, listar precisamente e limitar a conclusão.

Quando a bancada for parte da alegação, usar um controle de comportamento conhecido para mostrar que ela consegue observar o fenômeno relevante e casos contrastantes escolhidos para discriminar a hipótese. Considerar fronteiras, erro e alternativa plausível, conforme o contrato. O mínimo estrutural do auxiliar é um controle e dois casos com conteúdos de entrada diferentes; não é um cálculo do tamanho suficiente da amostra. Entradas diferentes podem percorrer o mesmo caminho ou reproduzir o mesmo erro.

Não fazer o oráculo copiar a implementação ou preencher `observed` com `expected`. Observações devem vir da execução/revisão realmente realizada e apontar para logs preservados. Logs devem identificar contexto, resultado e parada suficientes para a análise. Um log vazio ou irrelevante não sustenta a conclusão, ainda que seu hash esteja correto. Controles adicionais que a missão exige continuam obrigatórios.

Depois de uma execução interrompida/desconectada, registrar o resultado como desconhecido até recuperar o trace/checkpoint. Não assumir sucesso pelo tempo transcorrido nem repetir operações com efeitos externos sem reconciliar o estado.

## Contrato do auxiliar

`target` confere bytes, hash, campos mínimos e mapa linear declarado. `unit` confere intervalo, alinhamento, conversão de endereço e hash dos bytes selecionados. Não decodificam instruções nem comprovam que o intervalo é uma função.

`witnesses` confere os hashes do binário, unidade, manifestos, entradas e logs; exige IDs únicos, expectativas não vazias, controle, ao menos dois conjuntos distintos de conteúdo de entrada e declaração de injeções/limitações. Compara cada chave esperada ao valor observado, exigindo que a chave exista. `true`, `1` e `1.0` são distintos; usar tipos e representações estáveis. Tolerâncias numéricas exigem comparação separada apropriada, não editar a observação para fazê-la coincidir.

Campos extras observados não são interpretados como falha automaticamente; definir como expectativas as condições de erro relevantes, incluindo efeitos que devem estar ausentes. Comparações não provam que o produtor do JSON relatou honestamente o que ocorreu. `execution_reference` é uma referência textual, não autenticação. O tipo `hardware_observation` não transforma o auxiliar em validador de hardware.

Os manifestos são normalizados em JSON UTF-8, chaves ordenadas, separadores compactos e sem NaN antes do hash. `unit` retorna `target_manifest_sha256` e `unit_manifest_sha256` para copiar ao relatório. Mudança de metadados também invalida esse vínculo conservador; isso exige revisão, não significa que os bytes ou o comportamento necessariamente mudaram. Duplicatas de chaves e números não finitos são recusados na CLI.

Os caminhos internos devem resolver para arquivos dentro do projeto; traversal, caminhos absolutos, escapes por symlink e `.harness` são recusados. Isso não é isolamento contra um processo adversário trocando arquivos durante a leitura. Trabalhar sobre evidências congeladas e declarar todos os arquivos relevantes ao check do V8. Arquivos são lidos integralmente na memória; para imagens muito grandes preparar/verificar uma estratégia específica antes de usar o auxiliar, sem alterar silenciosamente o alvo.

## Auditoria de honestidade da conclusão

Informar alegação exata, método/ambiente realmente usados, arquivos/checks, cobertura/denominador, casos que falharam e o que falta testar. Uma frase aceitável: “os dois casos registrados coincidem com as expectativas sob as injeções descritas; integração e hardware não testados”. Evitar “algoritmo validado” quando só o relatório foi conferido. Preservar resultados negativos e permitir retratação, sem inventar uma certeza numérica.
