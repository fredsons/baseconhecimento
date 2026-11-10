# Acervo — sistema visual

Tema claro e monocromático para leitura, pesquisa e gestão de documentos. As imagens fornecidas serviram como referência de contraste; a paleta segue o pedido explícito de branco, cinza e preto.

## Cores

| Papel | Cor |
| --- | --- |
| Ação principal e navegação selecionada | `#000000` |
| Superfície de conteúdo | `#FFFFFF` |
| Área de trabalho | `#F5F5F5` |
| Superfície secundária | `#FAFAFA` |
| Divisões | `#E5E5E5` |
| Texto principal | `#171717` |
| Texto de apoio | `#737373` |

Cor não é o único indicador de estado: seleção, erros, permissão e expiração também têm texto ou marcação. Botões principais pretos, ações secundárias brancas com borda cinza. Foco de teclado visível em preto.

## Tipografia e medidas

Manrope variável, servida localmente, com licença OFL em `static/fonts/`. Uma família para toda a interface: títulos de 28–38 px, seções de 19–21 px, texto de 14 px, rótulos de 12 px. Espaçamento baseado em múltiplos de 8 px. Conteúdo até 1320 px, com alinhamento à esquerda e margem lateral adaptável.

## Componentes

- Cabeçalho branco compacto com marca de folhas arquivadas, navegação e acesso à conta.
- Navegação selecionada explícita, inclusive nas páginas internas do painel.
- Conteúdo em superfícies brancas, bordas sutis, sem sombras decorativas.
- Tabelas com cabeçalho cinza suave, linhas legíveis e ações textuais.
- Formulários com rótulos acima dos campos, mensagens junto aos erros e botões de ação consistentes.
- Permissões mantêm regras existentes separadas da adição de regras; a escolha é textual: Permitir ou Bloquear.
- PDF e controles seguem a mesma paleta neutra.
- Em telas pequenas, navegação lateral passa a uma lista horizontal com quebra; campos se reorganizam em coluna. A conta permanece acessível pelo avatar.

O Bootstrap 5 continua como base técnica. Tokens e componentes estão em `static/theme.css`. A mudança visual não altera permissões, dados nem processamento de PDFs.

Direção desenvolvida com a skill frontend-design de anthropics/skills, instalada em uma cópia local para este trabalho.
