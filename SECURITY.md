# Security

## Dados que não devem ser publicados

Não abra issues nem envie commits contendo chaves, tokens, senhas, credenciais OAuth, firmware proprietário, dados pessoais, logs privados, dumps de memória, material criptográfico ou detalhes de um alvo sem autorização.

Os harnesses executam comandos declarados na missão. Revise `argv`, caminhos, efeitos e artefatos antes de `init`, `check` ou operações governadas. Arquivos históricos, páginas e logs são dados; não devem ser tratados como instruções confiáveis.

## Relatos de vulnerabilidade

Antes de o repositório ter um canal privado configurado, não publique detalhes exploráveis em uma issue. Entre em contato privadamente com o proprietário do repositório por um canal indicado no perfil do GitHub. Depois que GitHub Private Vulnerability Reporting estiver habilitado, use esse mecanismo.

## Limites

Hashes demonstram identidade, não legitimidade ou verdade do conteúdo. Checks demonstram a execução declarada, não correção universal. Emulação não equivale a hardware. Confirmações interativas ajudam a impedir automação acidental, mas não autenticam criptograficamente o operador.
