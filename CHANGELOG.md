# Alterações

## 10/11/2026 — primeira implementação

- Base Django/SQLite com WAL, categorias, grupos, permissões herdadas e substituições por artigo.
- Login com bloqueio temporário, PDFs privados, validação, histórico e download protegido.
- FTS5 com acentos normalizados e autorização aplicada em SQL.
- Painel próprio em português, tema monocromático e fontes locais.
- Upload e fila ORM em uma única transação; preservação de versões após falhas de agendamento.
- Rascunhos e arquivados restritos a pessoas com leitura e função editorial; edição não contorna negação de leitura.
- Proteção contra sobrescrita de extração/publicação por edições concorrentes.
- Visualizador com camada textual, busca destacada, páginas de formatos diferentes, navegação, zoom e intervalos HTTP autorizados.
- Acompanhamento de extrações, repetição protegida, auditoria e explicação do acesso por pessoa.
- Extração real, OCR de PDFs escaneados/mistos e integração opcional com ClamAV.
- Waitress e scripts Windows, diagnóstico, backup com hashes e restauração verificada.
- 65 testes automatizados, além de worker real separado, restauração completa, HTTPS local e verificação visual desktop/celular.

Ativação do Agendador e certificado de domínio real permanecem como passos de configuração do computador/ambiente; consulte VALIDACAO.md.


