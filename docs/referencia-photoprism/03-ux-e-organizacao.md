# PhotoPrism — UX e Organização

Fonte: `~/dev/photoprism-develop` (Go + Vue 3/Vuetify 3), checkout local sem
metadata de commit neste ambiente. Levantado em 2026-08-12, a partir dos
achados já ancorados em `.local/audit/photoprism/03-api-e-autorizacao.md`,
`04-frontend-navegacao.md` e `05-frontend-design-system.md`, mais leitura
direta do código-fonte para os mecanismos que aqueles domínios só citam de
passagem.

Par de [`docs/referencia-immich/05-ui-web.md`](../referencia-immich/05-ui-web.md)
neste projeto: mesmo recorte de "mecanismo, não estilo". A régua de valor aqui
é UX de revisão/decisão em massa — Lightroom Classic / Photo Mechanic, a
mesma referência que `.claude/agents/agente-ux.md` usa —, não "o PhotoPrism
tem uma tela para X".

## Licença — leia antes de propor qualquer porte

PhotoPrism é **AGPLv3**. Ler para entender o mecanismo e reimplementar: livre.
Copiar código para o foto-organizer contamina o projeto inteiro com a AGPL —
não fazer. Este documento descreve mecanismo (estrutura de dado, sequência de
estados, invariante), nunca transcreve implementação, e não toca em estilo
visual — isso é direção de arte própria (`docs/DIRECAO_DE_ARTE.md`), fora do
escopo deste mapa.

## Por que este recorte

O PhotoPrism é multiusuário, cliente-servidor, com um acervo onde a foto
quase sempre existe (diferente do foto-organizer, que trata um acervo onde o
pixel é raro — ver a mesma ressalva no README do `referencia-immich`). O que
vale aqui não é a arquitetura de dados ou autenticação (fora de escopo desta
leitura), é como a Web UI resolve **decidir sobre um volume grande de fotos
rapidamente**: um campo de busca que também é uma linguagem de filtro, uma
seleção que sobrevive à paginação e não recria a grade inteira a cada clique,
uma barra de ação que se comporta como a do Lightroom (contagem, ação em
lote, desabilita durante o trabalho), e uma edição em lote que deixa o
usuário refinar o lote *antes* de aplicar a mudança.

---

## 1. Componentes centrais

### 1.1 Busca em campo único como DSL, com round-trip simétrico

| Arquivo:linha | Papel |
|---|---|
| `internal/form/search_photos.go:11-99` | `SearchPhotos`, struct com ~70 campos tipados (`Camera`, `Label`, `Before`, `Stack`, `Face`, `Quality`...), cada um com tag `form:"..."` que é literalmente o nome do token na DSL (`camera:canon`, `before:2024-01-02`) |
| `internal/form/search.go:10` | `ParseQueryString` — ponto de entrada, delega para `Unserialize` |
| `internal/form/serialize.go:80-191` | `Unserialize`: parser char-a-char do campo de busca único. Reconhece `chave:valor` (`:` fora de aspas vira separador), aspas (`"..."`) para escapar espaço, e qualquer token sem `:` vira parte do texto livre (`clean.SearchQuery`, acumulado em `queryStrings` e reunido no final). Erro de campo desconhecido ou de parse de tipo (data, float, int) é reportado, não silenciado |
| `internal/form/serialize.go:16-77` | `Serialize`: o inverso — dado o struct preenchido, reconstrói a mesma string de busca (aspas automáticas se o valor tem espaço/`:`/parênteses). Isso é o que torna a busca **linkável**: o estado inteiro do filtro cabe numa única string reversível |
| `internal/form/search_photos.go:80` (campo `Label`) | Um único campo de texto pode carregar uma expressão booleana: `label:"cat|dog&!blurry"` — `|` é OU dentro de um grupo, `&` é AND entre grupos, `!` no início nega um grupo, `\` escapa `&`/`|`/`!` literais (documentado no `notes` da tag) |

**Por que isso importa para revisão em massa:** o usuário não abre um
formulário de filtro para segmentar um lote — digita `camera:iPhone
before:2023-06-01 review:true` numa única caixa e a URL resultante é
compartilhável/salvável. É o oposto do padrão "filtro = estado de componente
que não sobrevive a um refresh".

### 1.2 Painel de filtros estruturados como segunda vista do mesmo estado

| Arquivo:linha | Papel |
|---|---|
| `frontend/src/component/photo/toolbar.vue:31-35` | Campo de busca livre (`input-search`), sem autocomplete de token — o usuário digita a DSL de cabeça ou usa o painel |
| `frontend/src/component/photo/toolbar.vue:106-258` | Painel expansível com dropdowns (`countryOptions`, `cameraOptions`, `yearOptions()`, `monthOptions()`, `colorOptions()`, `categoryOptions`, `lensOptions`, `sortOptions`, `viewOptions`) — cada um escreve no mesmo objeto de filtro que a DSL popula |
| `frontend/src/page/photos.vue:307-312` | `Shift+F` abre o painel de filtros **e** foca o campo de busca na mesma tecla — não são dois modos concorrentes, são duas entradas para o mesmo estado |

O ponto portável não é o dropdown em si (isso é UI convencional), é o
**contrato**: texto livre e formulário estruturado gravam no mesmo objeto de
filtro, então a URL da busca é sempre a fonte de verdade, nunca o widget.

### 1.3 Seleção persistente fora da árvore reativa da grade

| Arquivo:linha | Papel |
|---|---|
| `frontend/src/common/clipboard.js:35-50` | Classe `Clipboard`: `selection` é um array reativo do Vue, mas `selectionMap` (lookup O(1) por id) é um objeto plano fora da reatividade — evita que o Vue rastreie profundamente um mapa que só serve para `hasId()` |
| `frontend/src/common/clipboard.js:70-80` | Persistência automática em `storage` (localStorage) a cada mutação (`saveToStorage`) — a seleção sobrevive a navegação, reload de página e paginação |
| `frontend/src/common/clipboard.js:153-187` | `addRange(rangeEnd, models)`: seleção por intervalo ancorada em `lastId` (o último item tocado), não em índice absoluto — inverte start/end automaticamente se o usuário fez shift-click "para trás" |
| `frontend/src/common/clipboard.js:253-269` | `updateDom(uid, selected)`: em vez de deixar o Vue re-renderizar a célula, faz `document.querySelectorAll(`.uid-${uid}`)` e alterna a classe `is-selected` diretamente no DOM. Numa grade de milhares de células, alternar 1 seleção não dispara reconciliação de árvore nenhuma |

**Custo:** `updateDom` é uma fuga deliberada do modelo reativo — funciona
porque a seleção é puramente visual (uma classe CSS), não estado que afeta
layout/geometria. Um port para React com `TanStack Virtual` replicaria isso
com um `Set` fora de `useState` + mutação direta de `classList` nas células
montadas, exatamente como o próprio mapa do Immich recomenda para
`activeViewerAssets` (ver `referencia-immich/05-ui-web.md` §4.1-f/n) — aqui
o mesmo princípio aparece aplicado a *seleção*, não a *dados carregados*.

### 1.4 Classificador de clique/toque unificado

| Arquivo:linha | Papel |
|---|---|
| `frontend/src/common/input.js:31-104` | Classe `Input`: `touchStart`/`mouseDown` gravam índice do item, `scrollY` no momento do toque e timestamp. `clickType(ev, index)` calcula o veredito no `up`/`touchend`: se o índice mudou, ou a página rolou (`scrollY` diferente), ou (em touch) o dedo se moveu mais de 4px, é `InputInvalid` — descarta como scroll acidental, não como clique. Caso contrário, duração < 333 ms = `ClickShort` (abrir), ≥ 333 ms = `ClickLong` (entra em modo seleção) |
| `frontend/src/component/photo/view/mosaic.vue:291-345` | Consumo: clique curto abre a foto; clique longo ou clique com `Shift` seleciona (`selectRange`/`toggle`); em mobile, `contextmenu` (long-press nativo) também vira `selectRange` (`onContextMenu:335-341`) |

O mesmo veredito (`ClickShort`/`ClickLong`/`InputInvalid`) é consumido
identicamente em `view/list.vue:306,326` e `view/cards.vue:476-527` — três
layouts de grade compartilham uma única fonte de verdade para "isso foi um
clique ou um gesto de rolagem", em vez de cada view reimplementar sua própria
heurística de threshold.

### 1.5 Barra de ação por contagem de seleção

| Arquivo:linha | Papel |
|---|---|
| `frontend/src/component/photo/clipboard.vue:3-17` | A barra só existe no DOM quando `selection.length > 0` (`v-if`) — nada de barra desabilitada ocupando espaço permanentemente; o badge mostra a contagem |
| `frontend/src/component/photo/clipboard.vue:29-139` | Cada ação (approve/edit/private/album/archive/delete) é `:disabled="selection.length === 0 || busy"` — um único flag `busy` trava a barra inteira durante qualquer chamada em voo, evitando duplo-submit em lote |
| `frontend/src/component/photo/clipboard.vue:203-217` | Cada botão tem seu próprio gate de ACL + feature flag calculado uma vez em `data()` (`canEdit`, `canArchive`, `canDelete`, `canBatchEdit`...) — a barra nunca mostra uma ação que o backend vai rejeitar |
| `frontend/src/component/photo/clipboard.vue:244-308` | Ações batem em `POST batch/photos/{approve,archive,private,delete}` com `{ photos: this.selection }` — a UI nunca itera item a item; o backend processa o lote (`internal/api/batch_photos.go`, ver domínio API) |

### 1.6 Edição em lote: estado tri-state por campo + sub-seleção dentro do lote

| Arquivo:linha | Papel |
|---|---|
| `frontend/src/component/input/chip-selector.vue:199-234` | `handleChipClick`/`updateItemAction`: cada chip (label/tag) cicla um estado. Item **normal** (igual em toda a seleção): `none → remove → none`. Item **`mixed`** (presente em algumas fotos da seleção, ausente em outras): `none → add → remove → none` — o terceiro estado existe só quando há divergência, e o rótulo do tooltip muda de acordo (`"Add to all selected photos"` vs. `"Part of some selected photos"`) |
| `frontend/src/component/photo/batch-edit.vue:1005-1104` | Cada campo do formulário (`Title`, `Country`, `Albums`, `Labels`...) carrega seu próprio `{ value, action, mixed }` computado a partir da seleção real — a divergência é detectada campo a campo, não é um "modo lote" global |
| `frontend/src/component/photo/batch-edit.vue:1327-1357` | **Sub-seleção dentro do lote**: o dialog renderiza uma tira de miniaturas da seleção com checkbox por item (`toggle`/`toggleAll`) — o usuário pode excluir 2 de 40 fotos selecionadas *depois* de abrir o editor, sem fechar e refazer a seleção na grade |
| `frontend/src/component/photo/batch-edit.vue:1363-1370` | `onClose`: se há alterações não salvas (`hasUnsavedChanges()`), o dialog não fecha — dispara `animateClick()` (shake), a mesma reação de um `v-dialog persistent` rejeitando um Escape. Fechamento acidental de um lote com edição em andamento é bloqueado, não silenciosamente descartado |
| `frontend/src/component/photo/batch-edit.vue:1463-1469` | O save final usa `this.model.selection.filter(p => p.selected)` — ou seja, aplica ao subconjunto ainda marcado na sub-seleção, não à seleção original inteira |

### 1.7 Fila de revisão por qualidade e triagem de rostos não identificados

| Arquivo:linha | Papel |
|---|---|
| `frontend/src/app/routes.js:427` | Rota `/review` com `staticFilter: { review: "true" }` — a fila de revisão é a mesma grade de fotos, só com um filtro fixo pré-aplicado, não uma tela separada |
| `internal/api/photos.go:282` | `ApprovePhoto` — aprova um item individual, tirando-o do filtro `review` |
| `internal/api/batch_photos.go:220` (via `internal/server/routes.go`, capability `operacoes-lote`) | `BatchPhotosApprove` — mesma barra de ação do §1.5, aplicada ao contexto de revisão |
| `frontend/src/page/people/new.vue:31-32,90-91` | Página "New Faces": mesma DSL de busca reaproveitada como atalho — botão "Show all new faces" navega para `{ name: 'all', query: { q: 'face:new' } }`, não para um endpoint dedicado |
| `frontend/src/page/people/new.vue:607-614` | `toggleHidden(model)` — rejeita um rosto detectado **inline**, direto no grid de triagem, sem abrir um detalhe. É o padrão "descartar sugestão sem sair da lista", aplicado a clusters de rosto em vez de fotos |

### 1.8 Empilhamento (stack) como unidade de revisão

| Arquivo:linha | Papel |
|---|---|
| `internal/api/photos.go:335` | `PhotoPrimary` — define qual arquivo de um grupo empilhado (RAW+JPEG, burst) é a versão exibida por padrão |
| `internal/api/photo_unstack.go:33` | `PhotoUnstack` — remove um arquivo do stack, tornando-o uma foto independente; não apaga nada |
| `internal/form/search_photos.go:27-30` | A DSL de busca tem filtros dedicados para segmentar por estado de empilhamento: `stack:true` (tem mais de um arquivo), `unstacked:true` (arquivo removido do stack), `stackable:true` (pode ser empilhado), `primary:true` (só os arquivos principais) |

O ponto portável é o par mecanismo+filtro: "qual é o arquivo principal" é
uma decisão reversível e explicitamente nomeada (não um efeito colateral de
ordenação), e a mesma DSL usada para busca serve para **auditar** o próprio
resultado do agrupamento (`stack:true` mostra todos os grupos; `unstacked:true`
mostra o que já foi desfeito).

### 1.9 Atalhos de teclado por página, sem sistema genérico

| Arquivo:linha | Papel |
|---|---|
| `frontend/src/page/photos.vue:296-319` | `onShortCut(ev)`: `Escape` limpa foco/fecha painel, `R` recarrega, `Shift+F` foca a busca **e** abre o painel de filtros, `U` abre o dialog de upload (se permitido) — um `switch` simples, não uma tabela de bindings configurável |
| `frontend/src/common/view.js:465-477` (citado em `05-frontend-design-system.md`) | O forwarder central: só repassa `Escape` e combinações `Ctrl`/`⌘` do documento inteiro para o `onShortCut` do componente atualmente ativo — teclas soltas (`R`, `F`) só funcionam se o componente também as escuta, o forwarder não é genérico |
| `frontend/src/component/action/menu.vue:26-27` | Cada item de menu de ação mostra seu atalho de teclado associado (`action.shortcut`) como hint visual ao lado do rótulo, escondido em mobile — descoberta de atalho embutida na própria UI, não só em modal de ajuda dedicado |
| `frontend/src/common/util.js:473-476` | `shouldOpenOnHover()`: preferência do usuário (`settings.ui.openOnHover`, default `true`) para abrir menus ao passar o mouse em vez de clicar — desligada automaticamente em dispositivos touch (`!$util.hasTouch()`) |

### 1.10 Preservação de posição ao voltar da grade

| Arquivo:linha | Papel |
|---|---|
| `frontend/src/common/view.js:967-1051` | `saveRestoreState`/`getRestoreState`/`consumeRestoreState` — grava em `sessionStorage`, com chave por rota, quantos itens estavam carregados e a posição de scroll; expira em 30 minutos |
| `frontend/src/common/view.js:1140-1264` | `restoreWindowScrollPos` — até 20 tentativas com tolerância de 2px, porque a altura do layout pode mudar enquanto imagens ainda estão carregando (retry, não timer fixo) |
| `frontend/src/page/photos.vue:683-685` | `search()` só zera `offset`/scroll quando a navegação **não** foi "voltar" (`!this.$view.wasBackwardNavigation()`) — abrir uma foto e apertar Voltar preserva a página de rolagem inteira já carregada, não recomeça do topo |

---

## 2. Gramática da DSL — exemplos extraídos das tags `example`

Todos vêm de `internal/form/search_photos.go`, campo a campo (a tag `example`
é a própria documentação usada para gerar o Swagger):

```
camera:canon                          # filtro simples
before:2024-01-02 after:2023-06-01    # intervalo de datas
label:"cat|dog&!blurry"               # OU dentro do grupo, AND entre grupos, NOT no grupo
iso:200-400 mm:28-35 f:2.8-4.5        # faixas numéricas com "-"
color:"red|blue"                      # múltiplos valores com "|"
person:"Jane Doe & John Doe"          # AND explícito entre pessoas
stack:true unstacked:true             # estado de empilhamento
review:true quality:3                 # fila de revisão + piso de qualidade
face:new                              # alias para rostos ainda não nomeados
name:"IMG_9831-112*"                  # wildcard * em nome de arquivo
```

Todo valor com espaço, `:`, `-` ou parênteses precisa de aspas (regra em
`internal/form/serialize.go:60`); o parser (`serialize.go:171-179`) trata
`:` como separador chave/valor só fora de aspas, e espaço como fim de token
só fora de aspas — o mesmo par de regras que faz o `Serialize` reconstruir a
string exatamente reversível.

---

## 3. Decisões e o que custam

| Decisão | Onde | Ganho | Custo |
|---|---|---|---|
| DSL de campo único com round-trip simétrico | `internal/form/serialize.go:16-191` | Busca linkável/salvável sem estado de UI; um único parser serve API e URL da SPA | Parser char-a-char próprio (não usa lib de query language); erro de tipo (data inválida, float inválido) é reportado mas a mensagem não aponta a posição do erro na string |
| Seleção fora da reatividade + toggle de classe DOM direto | `frontend/src/common/clipboard.js:253-269` | Selecionar/desselecionar não recalcula a árvore de componentes da grade, mesmo com milhares de células | Selection e DOM podem divergir se um componente re-renderiza a célula sem reconsultar `hasId()` — é um contrato implícito, não garantido pelo tipo |
| Classificador de clique único para mouse+touch | `frontend/src/common/input.js:31-104` | Três layouts de grade (mosaic/list/cards) compartilham a mesma heurística de "isso foi um clique ou um scroll" | Threshold de 333ms e 4px são hardcoded, não expostos como preferência; calibrados empiricamente, não documentados o porquê do valor |
| Sub-seleção dentro do dialog de edição em lote | `frontend/src/component/photo/batch-edit.vue:1327-1357` | Usuário refina o lote sem fechar/reabrir; erros de seleção na grade não obrigam recomeçar | Duplica o conceito de "seleção" (a da grade vs. a do dialog) — dois `selected` diferentes coexistem na sessão, risco de confundir qual é a fonte de verdade num porte apressado |
| Estado tri-state (`mixed`) só quando há divergência real | `frontend/src/component/input/chip-selector.vue:199-234` | Edição em lote não força "tudo ou nada" — permite reconciliar tags divergentes com 3 cliques em vez de editar foto a foto | A máquina de estados tem dois caminhos diferentes (normal vs. mixed) que se cruzam — qualquer novo tipo de campo editável em lote precisa decidir explicitamente em qual dos dois entra |
| Guarda de fechamento por alterações não salvas | `frontend/src/component/photo/batch-edit.vue:1363-1370` | Edição em lote (potencialmente afetando centenas de fotos) não se perde por Escape acidental | Reusa a animação de rejeição de `v-dialog persistent`, acoplando UX de "erro de validação" e "confirmação de descarte" ao mesmo feedback visual |
| Fila de revisão como filtro, não como tela própria | `frontend/src/app/routes.js:427` | Zero duplicação de grade/toolbar/seleção entre "todas as fotos" e "fotas para revisar" | Qualquer capability nova da grade (nova coluna, novo atalho) automaticamente aparece na fila de revisão também — não dá para especializar a UX de revisão sem afetar a grade geral |

---

## 4. Portabilidade para o foto-organizer (React/TS/Tailwind, TanStack Virtual, single-user local)

### 4.1 Vale considerar

**a) Sub-seleção dentro do dialog de edição em lote, com guarda de
fechamento.** `batch-edit.vue:1327-1370`. O foto-organizer já modela revisão
como lista origem→destino com badges (não formulário) — este mecanismo
resolve o próximo problema óbvio dessa lista: quando o usuário seleiona 40
sugestões e quer excluir 2 sem perder a seleção das outras 38, e quer que um
Escape acidental não jogue fora uma decisão em lote quase pronta. Portar como
tira de thumbnails com checkbox + `hasUnsavedChanges()` bloqueando o
fechamento do painel de plano (diff origem→destino).

**b) DSL de busca em campo único, com round-trip simétrico.** Complementa
diretamente o modelo de evidência do foto-organizer (origem + confiança +
justificativa, já mais rico que o do PhotoPrism, conforme o README do
`referencia-immich`): uma sintaxe `confianca:baixa camera:iPhone
antes:2023-06` sobre esse modelo de evidência dá ao usuário um jeito de
segmentar o volume de sugestões sem esperar uma tela de filtro dedicada —
e, como o estado cabe numa string, uma busca "confiança baixa desta viagem"
vira um link salvável/compartilhável de graça. Não portar o parser char-a-char
literal — em TS um parser de tokenização com biblioteca ou regex bem testada
resolve o mesmo contrato (`campo:valor` + texto livre + aspas) com menos
risco de bug de borda.

**c) Seleção fora da árvore reativa + classificador de clique unificado.**
`clipboard.js:253-269` + `input.js:31-104`. Isso ataca exatamente o risco que
`referencia-immich/05-ui-web.md` §4.2 já sinalizou para o React: "se você
renderizar tudo a partir de um único `useState` no topo, a virtualização de
dois níveis não te salva". Aqui o PhotoPrism mostra o padrão do lado da
*seleção*, complementando o padrão do lado dos *dados* que o mapa do Immich
já cobre. Portar como um `Set` fora do estado do React (ref/store externo) +
mutação direta de `classList` nas células montadas pelo TanStack Virtual, e
um classificador de gesto único (`pointerdown`/`pointerup` com threshold de
tempo/distância) compartilhado entre grade e loupe, em vez de cada view
reimplementar sua própria lógica de "foi clique ou foi scroll".

### 4.2 Vale considerar com adaptação (menor prioridade)

- **Tri-state `mixed` no chip-selector** (`chip-selector.vue:199-234`) — só
  se o foto-organizer ganhar edição de tags/álbuns em lote sobre uma seleção
  heterogênea; hoje a revisão é aprovar/rejeitar papéis, não editar metadado
  arbitrário, então este mecanismo fica em espera até essa feature existir.
- **Hint de atalho embutido no item de menu** (`action/menu.vue:26-27`) e
  **abrir menu ao passar o mouse, autodesligado em touch**
  (`util.js:473-476`) — polimento de densidade profissional, barato de
  portar, mas não resolve nenhum problema estrutural; fazer só se sobrar
  tempo depois dos itens de §4.1.
- **Preservação de posição de scroll ao voltar** (`view.js:967-1051`,
  `photos.vue:683-685`) — útil, mas o `referencia-immich` já cobre o
  problema geral de virtualização/scroll com mais profundidade técnica
  (re-ancoragem, `deferredLayout`); usar aquele mapa como base e conferir
  contra este só se o comportamento "voltar preserva a página inteira
  carregada" não sair de graça da implementação React escolhida.

### 4.3 Não vale

- **Fila de revisão implementada como filtro sobre a grade geral**
  (`routes.js:427`) — faz sentido no PhotoPrism porque a UI é uma grade
  genérica com dezenas de filtros; o foto-organizer já tem revisão como tela
  própria (lista origem→destino), decisão correta para o caso de uso — virar
  "mais um filtro" perderia a especialização que a régua de UX pede.
- **Triagem de rostos não identificados como página dedicada**
  (`people/new.vue`) — o mecanismo de "rejeitar item inline sem abrir
  detalhe" é genérico (§1.7) e já vale a pena, mas a feature completa
  (clustering facial) não está no escopo atual do foto-organizer; não portar
  a tela, só reaproveitar o padrão de "descarte inline" se/quando outro tipo
  de sugestão precisar dele.
- **Painel de filtros estruturados com um dropdown por campo de busca**
  (`toolbar.vue:106-258`) — 12 dropdowns redundantes com a DSL textual. Se a
  DSL (§4.1-b) for portada, um segundo formulário espelhando os mesmos
  campos é manutenção duplicada sem ganho — a barra lateral de filtros que o
  foto-organizer já tem cobre o caso de uso de forma mais direta.
- **Empilhamento (stack) como conceito de dados** — o foto-organizer já
  resolve duplicata/rajada via comparação lado a lado com papel ACERVO/SINAL
  (mais preciso que "arquivo primário de um stack", conforme o README do
  `referencia-immich`); os filtros de busca dedicados a stack (`stack:`,
  `unstacked:`, `stackable:`) são um sintoma da modelagem do PhotoPrism, não
  algo a replicar.
- **Sistema de atalhos por método opcional (`onShortCut`) sem tabela
  configurável** — funciona no PhotoPrism porque só existem ~4 atalhos soltos
  por página; o `agente-ux` já pede "atalho novo precisa estar visível na
  interface", o que empurra para um registro central (mais parecido com o
  `TimelineKeyboardActions` do Immich, já recomendado em
  `referencia-immich/05-ui-web.md` §4.1-l) em vez deste padrão ad-hoc.
