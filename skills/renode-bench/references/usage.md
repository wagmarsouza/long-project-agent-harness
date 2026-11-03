# Uso da bancada Renode

## Preparação do alvo

Antes de escrever a bancada, documente a origem e o SHA-256 do firmware. Confirme arquitetura, modo de instrução, endianness, mapa de memória, offset/endereço de carga, vetor de reset ou PC/SP iniciais e periféricos necessários. Se algum item não estiver comprovado, marque-o como hipótese e prepare um teste que possa refutá-lo.

Use uma pasta própria para a bancada, separada dos binários originais. Mantenha `.resc`, `.repl`, logs, traces e relatório juntos. Evite caminhos absolutos em artefatos destinados a outras máquinas; injete caminhos reais numa cópia local ou use variáveis suportadas pelo seu fluxo.

O arquivo `.repl` é parte da evidência. Um modelo de CPU correto com periféricos ausentes pode levar o firmware a loops, falhas seguras ou caminhos artificiais. Documente periféricos omitidos e comportamento esperado na ausência deles.

## Execução headless

No Windows:

```powershell
$renode = 'C:\Program Files\Renode\bin\Renode.exe'
& $renode --disable-gui --console 'C:\projeto\bench\boot-trace.resc'
```

Em outros sistemas, ajuste o caminho do executável. Verifique a versão com o mecanismo fornecido pela instalação antes de comparar resultados entre máquinas. Use timeout no processo externo para impedir uma bancada presa indefinidamente. Capture stdout/stderr e o código de saída; um timeout deixa o resultado da execução desconhecido até a reconciliação dos arquivos.

Metadados `:name:` e `:description:` em `.resc` devem permanecer em uma linha. Comentários extensos usam `#`. Termine scripts headless com `quit`. Revise a sintaxe contra a documentação da versão instalada; APIs de monitor e tracing podem mudar.

## Hooks e injeções

Prefira primeiro uma execução sem hooks. Um hook pode observar, parar ou modificar o estado, mas cada alteração reduz o alcance da conclusão. Registre endereço, propósito, pré-condição, mudança de registrador/memória, condição de parada e justificativa.

Não use hooks para atravessar uma fronteira de segurança que o usuário não autorizou. Quando um bypass autorizado for necessário para testar um componente posterior, coloque uma parada explícita antes de qualquer região fora do escopo e documente que o caminho foi forçado. O comportamento depois da injeção não representa o boot natural.

## Interpretação do trace

O analisador agrupa transições próximas em blocos usando uma distância configurável. Isso é uma heurística de navegação, não um decodificador de instruções ou grafo de controle. Loops frequentes podem representar espera, erro, scheduler ou simples artefato do modelo. Um salto aparente pode ser fluxo normal, exceção ou problema de alinhamento/ISA.

Correlacione endereços com uma análise estática configurada para o mesmo binário, mapa e modo. Diferencie:

- endereço observado;
- instrução decodificada;
- função ou limite candidato;
- hipótese semântica;
- comportamento confirmado por teste.

Evite contabilizar o mesmo trace reformatado como evidência independente. Para comparar configurações, preserve os dois conjuntos, hashes, parâmetros e critérios previamente definidos.

## Integração com um harness longo

Em uma missão controlada, separe aquisição e validação. A execução do Renode pode gerar arquivos; o `check` deve ler artefatos congelados e verificar hashes, formato e expectativas. Não execute uma geração mutante dentro de um check que promete leitura estável.

Registre a evidência com teto de alegação: método emulado, plataforma, injeções, amostra, pontos observados e o que não foi testado. Relate cobertura com denominador definido. Se o inventário de caminhos for desconhecido, a cobertura total é indeterminada.
