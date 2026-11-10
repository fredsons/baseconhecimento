# Validação — Windows, 10/11/2026

## Executado com sucesso

- 82 testes automatizados com ferramentas externas habilitadas, sem testes pulados: permissões, publicação, ausência de vazamentos na busca/listagens, arquivos privados, intervalos HTTP, expiração, CSRF, bloqueio de login, versões, falha de fila, edições concorrentes, gestão delegada e painel.
- Poppler real: extração e busca de texto conhecido em PDF textual.
- OCRmyPDF 17.14.1 + Tesseract 5.4: OCR em PDF escaneado e em PDF misto, preservando o texto da página digital.
- ClamAV 1.4.6: PDF limpo aceito e PDF com marcador inofensivo correspondente a uma assinatura de teste rejeitado; versão anterior preservada. Isso não substitui atualização das assinaturas de produção.
- Django-Q2 ORM em outro processo Windows: envio -> fila -> extração -> FTS5 -> busca -> PDF parcial. O worker iniciou e encerrou normalmente.
- Backup e restauração isolados: integridade do banco e dos hashes, login com senha, busca e abertura do PDF restaurado. Script reproduzível em scripts/Validate-Runtime.py.
- HTTPS real local: Caddy 2.11.9 -> Waitress 3.0.2 -> Django com DEBUG=0. Login com CSRF, cookies Secure, PDF parcial e arquivos públicos. Certificado temporário confiado somente pelo cliente de teste, sem instalar autoridade certificadora no Windows.
- Backup pré-migração da instalação existente, seguido da migração 0003, preservando contas e artigos.
- Concorrência SQLite em arquivo e WAL: quatro leitores enquanto um administrador envia PDF, sem erro de banco bloqueado.
- Interface PDF.js verificada no navegador: documento protegido, camada textual e destaque de busca; documento de 12 páginas com tamanhos variados, navegação e ajuste de largura. O endpoint suporta intervalos com nova autorização em cada requisição.
- Painel de processamento, repetição protegida, auditoria exclusiva do administrador principal e explicação das permissões por ação e por pessoa.

## Pendências de ativação no computador

- Backup diário ativado pelo usuário nesta estação e execução confirmada com LastTaskResult=0. O acesso CIM continua indisponível para o aplicativo de assistência; isso não impede a tarefa cadastrada pelo usuário.
- Não há domínio/certificado de produção informado. O teste HTTPS utilizou um certificado temporário de laboratório; publicação HTTPS para outras pessoas depende dessa configuração. Uso local continua em 127.0.0.1.
- ClamAV é opcional e permanece desativado por padrão. Atualizar assinaturas reais antes de ativá-lo na instalação.

As pendências acima não são apresentadas como configurações já ativadas. Os arquivos systemd/Nginx são exemplos opcionais para Linux; o usuário informou que utiliza Windows.

- Preparação do PDF.js com hashes fixados: arquivos locais conferidos; testes rejeitam download adulterado e impedem download no modo de verificação.



- Alertas e confirmações: 17 novos testes de exclusão/CSRF/permissões/dependências/token/expiração/estado alterado, além da suíte existente. Navegador: Cancelar, Escape, retenção do formulário, restauração do estado inicial e modal responsivo. Remoção de regra testada em página fictícia sem banco ou envio, sem alterar acessos reais.
