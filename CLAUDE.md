# Guia do projeto

Stack: Django 5.2, templates, Bootstrap 5 com CSS próprio, SQLite/WAL, Django-Q2 ORM, PDF.js, Poppler/OCRmyPDF/Tesseract. Sem SPA, Tailwind, Redis ou Celery.

Instalação atual é Windows, conforme informado pelo usuário. Waitress é a alternativa ao Gunicorn neste sistema. Scripts em scripts/ cuidam da execução, ferramentas locais, diagnóstico, tarefas do Windows e validação isolada. Caddy é opcional para proxy HTTPS; exemplos Linux permanecem opcionais. Não instalar Linux ou ativar serviços globais sem necessidade.

Permissões aprovadas: grupos como papéis; ações separadas; negar por padrão; artigo substitui categoria por ação quando há regras ativas aplicáveis; negação prevalece no escopo; expiração suportada; gestores por grupos; superusuário ignora regras. Toda busca/listagem aplica autorização em SQL. Downloads e histórico precisam de autorização independente. Nunca servir DATA_DIR publicamente.

Estilo: português brasileiro e tema claro monocromático. Área de trabalho cinza #f5f5f5, superfícies brancas, botões e seleção pretos, texto #171717 e apoio #737373. Manrope variável local, títulos sem serifa, navegação compacta e estados selecionados explícitos. Sem verde, creme ou sombras decorativas. Tokens e medidas em DESIGN_SYSTEM.md. Responsivo; conta acessível pelo avatar no celular. Assets locais.

Comandos: `python manage.py migrate`, `createsuperuser`, `runserver`, `qcluster`, `test knowledge --noinput`, `check`, `collectstatic`, `backup DESTINO`, `verify_backup PASTA`, `metrics`. Definir DEBUG=1 apenas localmente. Produção exige SECRET_KEY.

Fases implementadas: estrutura/modelos/WAL; autenticação/bloqueio; autorização SQL; uploads/versões; visualizador; extração/FTS; admin/auditoria/métricas; tema/backups/deploy. Ver README para limites de validação externa. Histórico original recuperado pela API GitHub, com os hashes dos objetos verificados; implementação local sem push.

Testes usam SQLite em arquivo para concorrência real. Manter testes de segurança ao alterar regras. Transações curtas; nunca rodar OCR dentro de transação. Não apagar versões fisicamente sem considerar snapshots. Acesso ao arquivo não equivale a DRM.

Painel próprio em `/painel/`, com templates em `templates/panel/` e autorização em `knowledge/panel.py`. Entrada por staff ou gestão delegada; poderes são conferidos no servidor em cada rota. Alteração de contas/grupos é exclusiva do superusuário. Funções administrativas dos grupos limitadas a uma lista permitida e sem mudança de privilégios sensíveis. `/admin/` técnico reservado ao superusuário por middleware. Não mudar essa separação sem testes contra elevação de privilégios. Métricas próprias exibem títulos e tabelas em português.

Editor de regras: select explícito Permitir/Bloquear mapeado para booleano deny; regras existentes separadas de novas regras; vencimento com datetime-local; formulário extra vazio não pode impedir salvar nem criar regras. Não alterar herança durante mudanças de interface. Script permissions.js adiciona formulários com índices Django; o servidor continua validando todos os campos.

Publicação: leitura comum só de publicados. Rascunhos/arquivados exigem concessão editorial e visualizar. Editar, publicar, arquivar e baixar também exigem leitura. Upload usa broker ORM dentro da mesma transação do artigo/versão: nunca agendar via callback que possa apagar um arquivo após commit. Atualizações de metadados usam update_fields para não sobrescrever extração ou publicação concorrentes. Estado/erro/datas da extração estão no artigo. Repetição é protegida por leitura+edição e não duplica trabalhos recentes. Logs dos testes ficam separados.

PDFs privados suportam intervalos HTTP e If-Range, sem dispensar login/permissão. JS usa camada textual, busca destacada, geometria por página e canvases limitados às páginas próximas. Preservar isso ao editar o tema. Validação completa: ACERVO_INTEGRATION=1 python manage.py test knowledge --noinput; python scripts/Validate-Runtime.py. Ferramentas reais e HTTPS local já testados. Agendador de Tarefas não foi ativado porque o serviço CIM está bloqueado para este aplicativo; não declarar ativação sem confirmação no Windows. Domínio/certificado de produção ainda não foram informados.
