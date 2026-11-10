# Acervo — base de conhecimento corporativa

Aplicação web em português, com Django e templates, Bootstrap 5 personalizado, SQLite/WAL, PDFs privados, versões, PDF.js e busca FTS5. Tema claro em branco, cinzas e preto, com Manrope local. Sem SPA, Redis, Celery ou dependência de nuvem.

## Usar nesta instalação Windows

Na pasta do projeto, abra dois terminais:

```powershell
.\scripts\Run-Acervo.ps1 -Mode web
```

```powershell
.\scripts\Run-Acervo.ps1 -Mode worker
```

Abra http://127.0.0.1:8000. O primeiro comando aplica migrações, prepara os arquivos públicos e inicia Waitress. O segundo processa os PDFs com Django-Q2. O script encontra tanto `.venv` no projeto quanto o ambiente já existente em `../../work/venv`. Não depende do atalho `python` da Microsoft Store. Use `-PythonPath 'C:\caminho\python.exe'` para outro ambiente.

As duas bibliotecas grandes do PDF.js são preparadas por `python manage.py prepare_assets`, com versão 4.10.38 e SHA-256 fixados, antes de `collectstatic`. O script Windows faz isso automaticamente. Elas ficam locais depois da instalação; não há CDN em tempo de uso. O ZIP já contém esses arquivos; o GitHub contém o preparador em vez das bibliotecas grandes. Para instalar sem internet, use o ZIP ou copie os dois arquivos verificados para `static/vendor/`.

O script lê `.env`, caso exista, sem executar seu conteúdo. Sem esse arquivo, inicia em modo local de desenvolvimento. Para compartilhar o sistema pela rede, configure o ambiente de produção descrito abaixo.

## Instalação Windows em outro computador

Instale Python 3.12 de 64 bits a partir de python.org. Use seu caminho real ou o launcher `py` para criar o ambiente:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-ocr.txt
.\scripts\Install-Tools.ps1
$env:DEBUG='1'
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py createsuperuser
.\scripts\Run-Acervo.ps1 -Mode check
```

Para reproduzir exatamente as bibliotecas verificadas neste Windows, instale `requirements-windows.lock.txt` em vez de `requirements-ocr.txt`. A fonte Python do projeto não contém contas nem senhas predefinidas.

`Install-Tools.ps1` baixa e extrai ferramentas localmente em `tools/`: Poppler, Tesseract, idioma português e 7-Zip. Não executa os instaladores globais nem requer Linux. As ferramentas são descobertas automaticamente em `tools/`; nesta estação também é reconhecida a pasta de ferramentas em `../../work/tools`. Os binários não são enviados ao GitHub nem incluídos no ZIP de código. Respeite as licenças dos respectivos distribuidores. OCRmyPDF e suas dependências Python vêm de `requirements-ocr.txt`.

## Administração e permissões

Use `/painel/` para usuários, grupos, categorias, tags, artigos, revisões, processamento e auditoria. O `/admin/` é reservado ao superadministrador como ferramenta técnica.

1. Crie os grupos/departamentos e associe os usuários.
2. Crie categorias, com até três níveis, e defina as permissões dos grupos.
3. Envie o PDF em Enviar artigo. Ele começa como rascunho.
4. Quem tem permissão para publicar pode disponibilizá-lo aos leitores.
5. Para substituir o PDF, edite o artigo. URL e regras são preservadas, e as versões anteriores permanecem no histórico.

Sem concessão, negar. Ações: visualizar, baixar, enviar, editar, publicar, arquivar e gerenciar permissões. Regras dos grupos se somam; negação prevalece no escopo aplicável. Para cada ação, regras próprias do artigo aplicáveis aos grupos da pessoa substituem a herança daquela ação. Regras vencidas não participam. O dono do artigo não recebe acesso implícito. Superadministrador tem acesso completo.

Leitores comuns só veem artigos publicados. Rascunhos e arquivados exigem uma concessão editorial de editar, publicar ou arquivar, além de visualizar. Editar, publicar, arquivar e baixar também exigem leitura: uma negação de visualizar não pode ser contornada pelo endereço de edição. Busca, contagens e listagens aplicam essas condições em SQL, antes da paginação.

Grupos gestores de categoria podem administrar regras da categoria e de seus artigos, sem receber leitura automaticamente. O painel limita cada gestor às categorias delegadas. A tela Permissões efetivas permite selecionar a pessoa pelo nome e explica, por ação, a origem da concessão, da negação ou da restrição de publicação. Contas e grupos só são alterados pelo superadministrador; funções administrativas de grupos têm lista limitada para impedir elevação de privilégios.

## PDFs e processamento

Uploads verificam tamanho, assinatura e estrutura real do PDF. O padrão é 50 MB. Arquivos criptografados ou vazios são rejeitados. Artigo, versão e entrada na fila ORM confirmam na mesma transação: falha ao agendar não deixa registro sem arquivo e preserva a versão anterior. Mudanças de metadados não sobrescrevem texto extraído ou estado de publicação atualizado por outro processo.

O worker usa Poppler e OCRmyPDF/Tesseract, inclusive em PDFs mistos com páginas escaneadas e textuais. As ferramentas executam fora das transações de banco, com limites de tempo. Texto extraído é indexado com FTS5 e normalização de acentos. Em `/painel/processamento/`, administradores/gestores com leitura e edição acompanham fila, início, conclusão e erros e podem solicitar nova tentativa. Trabalhos recentes não são duplicados; após 20 minutos uma execução sem conclusão pode ser reenviada. Uma tarefa de versão antiga não substitui o texto da versão atual.

O visualizador tem rolagem contínua, página atual, navegação por número, zoom, ajuste à largura por página, seleção de texto, localização com destaque e tela cheia. Renderiza páginas próximas e libera canvases distantes. O endpoint protegido aceita Range/If-Range, com autorização a cada requisição; não existe URL pública para o PDF. O nome do download preserva o título, substituindo caracteres inválidos.

Separar a ação Baixar controla o endpoint de download, mas visualizar entrega bytes ao navegador; o sistema não é DRM. O original permanece imutável; o OCR enriquece o índice, sem substituir o original arquivado.

## Antivírus opcional

```powershell
.\scripts\Install-Tools.ps1 -IncludeAntivirus
```

Ative `CLAMAV_ENABLED=1` somente depois de configurar e atualizar as assinaturas do ClamAV com FreshClam. Para uma pasta/banco específico, use `CLAMAV_DATABASE`. Ferramenta indisponível, banco ausente ou detecção rejeitam o upload, preservando o documento anterior. O teste automatizado usa uma assinatura local inofensiva para verificar aceitação e rejeição reais pelo motor; não simula a disponibilidade das assinaturas de produção.

## Auditoria e métricas

Visualizações, downloads, alterações e mudanças de acesso vão para arquivo JSON rotacionado, sem gravar um evento de acesso por leitura no SQLite. `/painel/auditoria/` mostra até 200 eventos recentes e permite filtrar por ação; somente o superadministrador tem acesso. Testes usam outro arquivo de log para não misturar seus eventos à auditoria real. Proteja logs e backups: podem conter termos sensíveis.

`/metricas/` reúne acessos por artigo, buscas sem resultado, feedback e revisões vencidas. Acessos são contados dentro dos logs retidos. Não há remoção física automática de versões.

## Backup diário no Windows

Execução manual com verificação:

```powershell
.\scripts\Run-Acervo.ps1 -Mode backup
```

Por padrão, salva em `../backups-acervo`, fora de DATA_DIR. Para outro destino, informe `-BackupDirectory`. O comando usa a API de backup SQLite, copia os PDFs imutáveis referenciados e confere os hashes contra as versões registradas. Não copia o arquivo do banco em uso diretamente.

Para cadastrar uma tarefa diária às 02h, execute no seu PowerShell:

```powershell
.\scripts\Install-BackupTask.ps1
```

O script não substitui tarefa existente. Usa a sessão do usuário Windows e executa assim que possível se o horário foi perdido; o computador precisa estar ligado e o usuário conectado. Para operação sem login, configure uma conta de serviço no Agendador com as credenciais e permissões da organização.

Opcionalmente, `Install-StartupTasks.ps1` cadastra inicialização de web e worker ao entrar no Windows. Nesta instalação, o usuário já cadastrou a tarefa Acervo-Backup e confirmou uma execução com LastTaskResult=0 em 10/11/2026. O aplicativo de assistência continua sem acesso ao serviço CIM; o cadastro foi feito pelo usuário no seu PowerShell. Para o bloqueio padrão de scripts, use powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File ".\scripts\Install-BackupTask.ps1"; a política vale só para o processo, e a tarefa gerada utiliza a mesma configuração.

## Restauração

Pare web e worker. Execute `python manage.py verify_backup PASTA_DO_BACKUP`. Preserve o DATA_DIR atual. Em outro diretório vazio, restaure `knowledge.sqlite3` e `pdfs/`; não reutilize arquivos antigos `-wal` ou `-shm`. Aponte DATA_DIR para essa restauração e confira login, busca e abertura do PDF antes de substituir o ambiente real. Guarde separadamente `.env`, certificados, código e logs. Defina retenção e uma cópia em outro disco conforme sua operação.

## Compartilhar pela rede com HTTPS

Para uso somente neste computador, o endereço local HTTP é suficiente para testar. Para acesso de outras pessoas, configure um domínio/certificado e um proxy HTTPS. No Windows, há exemplo de Caddy em `deploy/Caddyfile.windows`; mantenha Waitress em 127.0.0.1. Caddy é opcional e não faz parte do servidor local padrão. Documentação oficial: https://caddyserver.com/docs/running

Em `.env`, configure `DEBUG=0`, `SECRET_KEY` aleatória longa, `ALLOWED_HOSTS` com o domínio, DATA_DIR privado e `SERVE_STATIC=1`. O proxy deve sobrescrever X-Forwarded-Proto. Waitress confia nesse cabeçalho somente vindo de 127.0.0.1. Cookies seguros, CSRF, redirecionamento HTTPS e HSTS são habilitados em produção. Nunca exponha DATA_DIR, SQLite, logs, backups nem PDFs por uma pasta pública.

HTTPS foi testado localmente com certificado temporário confiado somente pelo cliente de teste, sem alterar os certificados do Windows. Não foi instalado um certificado de produção: ainda não foi informado um domínio de publicação.

Cinco tentativas de login incorretas bloqueiam a conta por 15 minutos. Troca de senha autenticada está disponível; recuperação por e-mail não é configurada sem serviço de correio.

## Configuração

Consulte `.env.example`. Variáveis adicionais: `OCR_LANGUAGES`, `PDFTOTEXT_COMMAND`, `OCRMYPDF_COMMAND`, `TESSERACT_COMMAND`, `CLAMSCAN_COMMAND`, `CLAMAV_DATABASE`, `SERVE_STATIC`. `.env` é lido pelo script Windows; comandos Python diretos usam as variáveis já exportadas no processo.

## Testes reproduzíveis

```powershell
$env:DEBUG='1'
.\.venv\Scripts\python.exe manage.py test knowledge --noinput
$env:ACERVO_INTEGRATION='1'
.\.venv\Scripts\python.exe manage.py test knowledge --noinput
.\.venv\Scripts\python.exe scripts\Validate-Runtime.py
```

A primeira execução dispensa ferramentas externas; os testes de integração são pulados explicitamente. A segunda usa Poppler, OCRmyPDF, Tesseract e ClamAV reais. A terceira cria um banco isolado temporário, processa a fila em outro processo e restaura um backup, verificando login, busca e PDF. Não utiliza o banco da instalação. Nesta estação, substitua `.venv/Scripts/python.exe` por `../../work/venv/Scripts/python.exe`, se necessário.

O banco dos testes é um arquivo SQLite separado com WAL real. Não execute duas suítes simultaneamente no mesmo DATA_DIR. Veja `VALIDACAO.md` para resultados e limites.

## Linux opcional

O usuário desta instalação utiliza Windows. Os arquivos systemd/Nginx em `deploy/` permanecem como alternativa para Linux e não foram instalados nesta estação. Em Linux, use Gunicorn, Poppler, OCRmyPDF/Tesseract e, opcionalmente, ClamAV do sistema; exporte as variáveis, execute migrate/collectstatic/createsuperuser e ajuste os arquivos ao domínio e aos caminhos do servidor. A execução é web + worker; não há broker externo.

## Código, dependências e evolução

O repositório original continha somente README. O histórico inicial foi preservado; a implementação inclui migrações, testes, scripts Windows, exemplos Linux e documentação. Arquivos privados, ambientes Python, ferramentas binárias e backups são ignorados pelo Git.

FTS5 fica isolado em `knowledge/search.py` e sua migração; uma futura mudança para PostgreSQL precisa substituir esse módulo e a configuração SQLite. O restante utiliza ORM. Consulte `CLAUDE.md`, `DESIGN_SYSTEM.md` e `THIRD_PARTY.md`.


## Alertas, confirmações e exclusões

O tema monocromático agora inclui mensagens identificadas de sucesso, informação, atenção e erro, com fechamento por teclado. Formulários inválidos preservam os campos e mostram o que precisa ser corrigido. Alterações não salvas geram aviso ao navegar ou fechar a página.

Publicar, arquivar, substituir PDF, desativar usuário e salvar mudanças de permissões pedem confirmação no navegador. A janela identifica o registro; remoções de regras identificam o grupo e a ação afetados. Cancelar ou Escape não envia o formulário. A navegação por teclado fica restrita à janela enquanto ela está aberta. Sem JavaScript, as autorizações e validações do servidor continuam obrigatórias.

As exclusões ficam em uma página de revisão com nome e consequências, confirmação explícita e token assinado válido por dez minutos, vinculado ao registro e ao administrador. O servidor confere novamente permissão, estado e dependências no POST. GET nunca exclui. Registros alterados desde a revisão exigem nova confirmação.

- Artigos: exclusão exclusiva do administrador principal, após arquivamento e fora do processamento. Remove registros, regras, avaliações e versões do artigo. Arquivos privados permanecem retidos conforme a política de backup, sem acesso pela biblioteca; não é uma rotina de eliminação física de dados.
- Categorias: não podem ter artigos, subcategorias, regras ou delegações de gestão vinculadas.
- Grupos: não podem ter integrantes, regras, delegações ou funções administrativas vinculadas. Apenas o administrador principal pode excluí-los.
- Tags: não podem estar em uso. Categoria e tag exigem a permissão administrativa específica de exclusão.
- Pessoas: continuam sendo desativadas; não há exclusão física de contas pelo painel, preservando autoria e histórico.

Falhas de processamento aparecem no painel apenas para quem pode visualizar e editar os artigos afetados, com acesso à tela de nova tentativa.
