# Organização de uma missão longa de análise binária

## 1. Fixar o contrato e a identidade

Partir do objetivo autorizado: localizar um algoritmo, reconstruir um protocolo, explicar uma região, comparar versões ou validar um comportamento específico. Converter esse objetivo em critérios observáveis; “entender todo o firmware” não é um critério executável por si só. Definir exclusões, formatos de saída, ambiente disponível e o nível de evidência que o usuário realmente exige.

Manter uma cópia original e sua proveniência; SHA-256 identifica os bytes, não a legitimidade, versão comercial ou origem. Registrar quais dados foram fornecidos, extraídos, descomprimidos, descriptografados ou reconstruídos, com hashes de entrada/saída e ferramenta/configuração. Não misturar regiões de duas versões sob a mesma identidade. Não executar o alvo para descobrir sua arquitetura.

O manifesto `binary-target-v1` suporta mapeamento linear por segmentos de arquivo: offset/tamanho em bytes e VA em unidades de `address_unit_bytes`. VA = base + (offset − offset_do_segmento) / unidades. Intervalos precisam caber no arquivo. Sobreposições exigem espaços explicitamente diferentes, como bancos. Regiões sem bytes no arquivo, relocação, MMIO, RAM de runtime e transformações não lineares exigem documentação adicional e critérios adequados; não forçar um mapa fictício para o auxiliar aceitar.

Validar separadamente a hipótese do mapa usando cabeçalhos, especificação da arquitetura, vetores, referências cruzadas e observações pertinentes. A aprovação estrutural do manifesto não realiza essa validação. Registrar incertezas de ISA, endianness ou base até discriminá-las.

## 2. Inventariar sem inventar completude

Criar um inventário versionado com ID, intervalo, espaço de endereço, modo, classificação e origem da hipótese. A unidade pode ser uma função candidata, tabela, bloco misto ou região ainda desconhecida. Não cortar todos os arquivos no mesmo tamanho nem contar cada bloco como função.

Para uma hipótese de função, registrar entradas candidatas, saídas, convenção de chamada suposta, branches relevantes, chamadas/refs, possíveis dados intercalados e contradições. Um retorno aparente ou uma assinatura reconhecida não resolve todos os limites. Chamadas indiretas, tail calls, trampolins, código comprimido/gerado e bancos podem deixar lacunas explícitas.

O grafo de chamadas é um resultado técnico com arestas observadas, inferidas ou desconhecidas. O grafo de tarefas do V8 é coordenação de trabalho. Não tratar um como substituto do outro nem criar uma tarefa por instrução sem necessidade.

Definir denominadores por pergunta: regiões do inventário examinadas, requisitos de protocolo testados, caminhos críticos definidos ou casos do contrato. Exemplo: “3 de 12 unidades inventariadas tiveram hipótese X testada; inventário incompleto, cobertura do binário indeterminada”. Não dizer “25% do firmware compreendido”. Excluir regiões só com justificativa rastreável; mudança do escopo autorizado requer revisão da missão.

## 3. Recuperar e planejar a menor investigação útil

Consultar `resume`, `validate`, `search` e `review` no V8. Buscar por hash, offset/VA, ID e aliases já registrados. Ler status e limites antes de reaproveitar um resultado. Não reabrir a mesma pergunta porque o nome simbólico mudou ou porque o histórico foi compactado.

Usar um tópico estável, por exemplo `bin:<sha256>:main:text:off-4:len-4:isa-<modo>`. Registrar aliases amigáveis sem substituir a identidade. Definir a hipótese e a alternativa mais plausível, o teste mais barato que as separa e os critérios da missão que ele realmente atende. Timebox e step-back vêm do V8; não multiplicar tentativas idênticas até obter saída favorável.

## 4. Exportar, verificar e registrar

Após a análise autorizada, congelar um export por unidade/resultado relevante: bytes, assembly com endereços e modo, referências e/ou pseudocódigo quando pertinente, versão/configuração do exportador e limitações. Um hash confirma a identidade desses arquivos; a correspondência entre export e binário precisa de um teste adicional apropriado se for parte da conclusão. O auxiliar não faz essa correspondência semântica.

Gerar traces e demais artefatos antes do check. Usar nomes/versionamento que preservem a prova antiga; quando um artefato declarado precisa mudar, seguir a revisão/reabertura pertinente do V8. Não editar hashes antigos para esconder mudanças. O hash do banco de uma ferramenta costuma mudar com anotações irrelevantes; manter esse banco como contexto e exports delimitados como evidência permite invalidar com precisão, desde que as dependências reais estejam declaradas.

Rodar verificações em leitura pelo V8 e vincular `evidence-scope`. Conferir se os comandos distinguem de fato a hipótese. Registrar o comportamento delimitado como claim somente quando a evidência sustentar a frase exata; o resultado do auxiliar sozinho nunca autoriza uma conclusão semântica. `claim-reverify` mantém uma declaração já existente e sua história; não é mecanismo de promover hipóteses nem gerar nova descoberta.

## 5. Retomar e concluir

No contexto da tarefa guardar: hash/manifestos; ID, espaço, offset, VA e modo; ferramenta/configuração; hipótese atual e alternativas; evidência e limitações; dependências/retratações; perguntas abertas; próximo teste discriminante; operações pendentes de reconciliação. Cápsulas/context packs são visões derivadas; conferir frescor e recuperar originais quando necessário.

Ao trocar de versão de firmware, explicitar a nova identidade e revisar a aplicabilidade das conclusões anteriores. Mesma função presumida ou nome não permite transportar provas automaticamente. Comparação de versões exige um critério próprio.

No encerramento, separar o que está descrito estaticamente, o que foi observado na bancada e o que foi observado no ambiente final. Executar a aceitação da missão adotada, apresentar cobertura com universo/exclusões e registrar limites. Nenhum campo preenchido ou banco íntegro demonstra que toda a semântica do binário foi recuperada.
