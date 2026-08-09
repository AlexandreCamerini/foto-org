# Immich — UI web

Fonte: `~/dev/fot/web` (Svelte 5 runes + SvelteKit + TS + Tailwind), versão
3.1.0, commit `5ad1e4e0f`. Levantado em 2026-08-08.

---

## 1. Componentes centrais

### 1.1 Núcleo de virtualização — três camadas de estado

| Arquivo:linha | Papel |
|---|---|
| `web/src/lib/managers/VirtualScrollManager/VirtualScrollManager.svelte.ts:8` | Classe abstrata base. Guarda `viewportWidth/Height`, `scrollTop`, e as três alturas somadas em `totalViewerHeight` (`:12`): `topSectionHeight` + `bodySectionHeight` (todos os meses) + `bottomSectionHeight`. `visibleWindow` (`:14`) é `{top, bottom}` derivado. `justifiedLayoutOptions` (`:29`) é `{spacing:2, heightTolerance:0.5, rowHeight, rowWidth: floor(viewportWidth)}`. `setLayoutOptions` (`:145`) recebe `rowHeight=235, headerHeight=48, gap=12` e só refaz layout se mudou. `scrolling`/`suspendTransitions` são flags com debounce de 1000 ms (`:27-28`) usadas para desligar animações durante o scroll |
| `web/src/lib/managers/timeline-manager/timeline-manager.svelte.ts:50` | `TimelineManager extends VirtualScrollManager`. É o "modelo" da grade inteira. `months: TimelineMonth[]` (`:71`), `assetCount` derivado (`:61`), `bodySectionHeight` = soma das alturas dos meses (`:53`). Um por página (instanciado em `Timeline.svelte:88`, destruído em `onDestroy`) |
| `web/src/lib/managers/timeline-manager/timeline-month.svelte.ts:31` | Um bucket = um mês. Guarda `isLoaded`, `timelineDays[]`, `height`, `top`, `percent`, e um `CancellableTask` como `loader`. O setter `viewportProximity` (`:87`) é o gatilho de I/O: entrar em "perto do viewport" chama `loadTimelineMonth`; sair chama `cancel()` |
| `web/src/lib/managers/timeline-manager/timeline-day.svelte.ts:29` | Um grupo de dia dentro do mês. Contém `viewerAssets: ViewerAsset[]`, `width`, `height`, `row`, `col`, `start`, `top` e — o ponto crítico — `activeViewerAssets` (`:41`), a fatia que realmente entra no DOM |
| `web/src/lib/managers/timeline-manager/viewer-asset.svelte.ts:4` | Wrapper `{asset, position}`. `position` é `$state.raw()` (`CommonPosition = {top,left,width,height}`) |

### 1.2 Cálculo de geometria

| Arquivo:linha | Papel |
|---|---|
| `.../internal/layout-support.svelte.ts:5` | `updateGeometry`. Para mês **não carregado**, estima a altura sem conhecer os assets: `unwrappedWidth = 1.5 * count * rowHeight * 0.7`, `rows = ceil(unwrappedWidth / viewportWidth)`, `height = headerHeight + max(1,rows)*rowHeight`. É essa heurística (razão média assumida ≈ 0.7·1.5) que permite dimensionar o scrollbar antes de qualquer fetch |
| mesmo arquivo `:22` | `layoutTimelineMonth`: chama `timelineDay.layout()` para cada dia e depois empacota os *dias* lado a lado como caixas (flow horizontal com `gap`), acumulando `cumulativeHeight`. Dois níveis de layout — justified dentro do dia, packing simples entre dias |
| `.../timeline-day.svelte.ts:161` | `layout(options, noDefer)`. Se o mês não está perto do viewport e não há scroll-para-asset em curso, marca `deferredLayout = true` e **retorna sem calcular nada**. Caso contrário chama `getJustifiedLayoutFromAssets` e escreve `position` em todos os `viewerAssets` |
| `web/src/lib/utils/layout-utils.ts:30` | `getJustifiedLayoutFromAssets`: por padrão usa `@immich/justified-layout-wasm` (`:40`, alimentado por um `Float32Array` de aspect ratios), com fallback para o pacote JS `justified-layout` via `Adapter` (`:57`, `:102`). Alternável por `localStorage['LAYOUT.WASM']` |
| `.../timeline-month.svelte.ts:269` | Setter de `height` — **o mecanismo anti-salto**. Ao mudar a altura de um mês, recalcula o `top` do mês anterior, propaga `heightDelta` para todos os meses seguintes e, se o mês alterado está **acima** do mês visível, chama `scrollBy(heightDelta)` ou `scrollTo(...)` para manter a âncora visual (usa `viewportTopMonthIntersection`, calculado em `timeline-manager.svelte.ts:213-243`) |

### 1.3 Janela deslizante / interseção

| Arquivo:linha | Papel |
|---|---|
| `.../internal/intersection-support.svelte.ts:33` | `calculateViewportProximity` → enum de 3 estados: `InViewport`, `NearViewport`, `FarFromViewport`, com margens `INTERSECTION_EXPAND_TOP/BOTTOM` (500 px cada). **Não usa `IntersectionObserver`**; é aritmética pura sobre `scrollTop` |
| `.../timeline-day.svelte.ts:177` | `updateAssetBoundaries` — segundo nível de virtualização, **dentro** do dia. Faz duas buscas binárias (`lowerBound`, `:15`) sobre as posições já ordenadas para achar o primeiro e o último asset dentro da janela expandida, e fatia `activeViewerAssets`. Custo O(log n) por dia por frame de scroll |
| `.../timeline-manager.svelte.ts:213` | `updateViewportProximities`: percorre todos os meses (O(nº meses), não O(nº assets)), atualiza proximidade e, para meses carregados e visíveis, chama `updateAssetBoundaries` em cada dia. Guardado por flag reentrante `#updatingViewportProximities` |

### 1.4 Componentes de renderização

| Arquivo:linha | Papel |
|---|---|
| `web/src/lib/components/timeline/Timeline.svelte:598` | `<section id="asset-grid">` — o elemento rolável real (`overflow-y-auto`, `contain: strict` em `:715`, scrollbar nativa escondida). `bind:clientHeight/clientWidth` alimentam o manager. `onscroll` (`:606`) chama três funções **síncronas** (comentário explícito em `:274`/`:256`: nada de throttle/debounce, causa flicker) |
| mesmo `:610` | `<section id="virtual-timeline">` com `height = totalViewerHeight` — o spacer que dá o tamanho da barra de rolagem |
| mesmo `:628-696` | `{#each months}`: cada mês é um `div` absoluto posicionado com `transform: translate3d(0, top, 0)`. Se `!isLoaded` → `<Skeleton>`; se `isInOrNearViewport` → `<Month>`; senão **nada é renderizado** (só o buraco de altura correta). `.timeline-month` usa `contain: layout size paint` (`:720`) |
| `web/src/lib/components/timeline/Month.svelte:60` | `{#each filterIsInOrNearViewport(timelineMonth.timelineDays)}` — filtra os dias; renderiza o cabeçalho do dia (com checkbox de seleção de grupo no hover) e delega ao `AssetLayout` |
| `web/src/lib/components/timeline/AssetLayout.svelte:37` | `{#each viewerAssets}` — recebe `timelineDay.activeViewerAssets`. Cada asset é um `div` absoluto com `top/left/width/height` em px vindos do justified layout, com `animate:flip` e `out:scale` (duração 0 quando `suspendTransitions`) |
| `web/src/lib/components/timeline/Scrubber.svelte:145` | Scrubber lateral (barra de datas). `calculateSegments` converte `scrubberMonths` (snapshot leve criado em `timeline-manager.svelte.ts:348`) em segmentos com altura proporcional, decidindo quais recebem rótulo de ano (`MIN_YEAR_LABEL_DISTANCE=16`) e quais recebem ponto (`MIN_DOT_DISTANCE=8`). Largura 60 px desktop / 20 px mobile |
| `web/src/lib/components/timeline/TimelineAssetViewer.svelte:1` | Ponte grade ↔ visualizador: mantém o `AssetCursor {current, nextAsset, previousAsset}` (`:65`), resolvendo vizinhos via `timelineManager.getEarlier/LaterAsset` + `assetCacheManager`. Importa o `AssetViewer` com `{#await import(...)}` (`:237`) — code splitting |

### 1.5 Thumbnails e carregamento de imagem

| Arquivo:linha | Papel |
|---|---|
| `web/src/lib/components/assets/thumbnail/Thumbnail.svelte:208` | Célula da grade. `tabindex=0`, `role="link"`, `data-asset={id}`, `data-thumbnail-focus-container` (`:227-232`) — esses atributos são a base da navegação por teclado. Contém `ImageThumbnail`, `VideoThumbnail` (hover playback), overlays de favorito/arquivo/stack/360°/GIF, botão de seleção, e um `<a>` "lazy" com a URL do asset só no hover (`:389`, evita milhares de links no DOM) |
| mesmo `:148` | `longPress` (350 ms) para seleção em touch, com cancelamento em scroll/wheel/contextmenu/pointermove>10 px (`:185-196`) |
| `.../ImageThumbnail.svelte:74` | Troca para `BrokenAsset` em erro; senão `Image` com `loading=eager|lazy` |
| `web/src/lib/components/Image.svelte:21` | Captura o `src` **uma única vez** (`capturedSource`) para evitar re-fetch em re-render; no Firefox espera `img.decode()` antes de marcar loaded (`:52`); em `onDestroy` chama `cancelImageUrl` (`:32`) |
| `web/src/lib/components/Thumbhash.svelte:21` | Decodifica thumbhash em `<canvas>` via `thumbHashToRGBA`; some com fade de 100 ms |
| `web/src/service-worker/index.ts:8` | SW intercepta `GET /api/assets/<uuid>/(original\|thumbnail)` |
| `web/src/service-worker/request.ts:19` | `handleFetch`: **deduplicação de requests em voo** por URL — se dois componentes pedem a mesma thumb, o segundo recebe `response.clone()` da promise pendente. Entradas ficam no mapa por 5 min. `handleCancel` (`:62`) aborta via `AbortController` e responde 204 sintético |
| `web/src/lib/utils/sw-messaging.ts:6` + `sw-messenger.ts:11` | `cancelImageUrl(url)` → `postMessage({type:'cancel', url})` ao SW. Chamado quando um `<img>` sai do DOM (scroll rápido) |
| `web/src/lib/managers/AssetCacheManager.svelte.ts:38` | Cache em memória (`Map` com chave `JSON.stringify(params)`) para `getAssetInfo`, `getAssetOcr`, `getFaces`. Invalidação por evento `AssetUpdate`/`AssetEditsApplied` (`:44`). Sem TTL |

**Não existe cache persistente (Cache Storage) de thumbnails.** O SW só faz dedup
+ cancelamento; o cache real é o cache HTTP do browser, viabilizado pela URL
determinística (ver §2.3).

### 1.6 Seleção múltipla e teclado

| Arquivo:linha | Papel |
|---|---|
| `web/src/lib/managers/asset-multi-select-manager.svelte.ts:10` | `SvelteMap<id, TimelineAsset>` para os selecionados, `SvelteSet<string>` para grupos-dia, `candidates[]` para o preview de range com Shift, `startAsset` como âncora. Derivados `selectionActive`, `isAllFavorite`, `isAllArchived`, `isAllUserOwned`. Instância global em `:108` com `resetOnNavigate: true` |
| `web/src/lib/components/timeline/Timeline.svelte:395` | `onSelectAssets` — seleção por range. Se há `startAsset` e Shift, calcula os índices dos meses inicial/final, **carrega os meses intermediários** (`await loadTimelineMonth`) e seleciona tudo; depois reconcilia o estado de cada grupo-dia |
| mesmo `:470` | `selectAssetCandidates` — preview do range no hover com Shift, via `timelineManager.retrieveRange` (`internal/search-support.svelte.ts:117`) |
| `web/src/lib/utils/asset-utils.ts:365` | `selectAllAssets` (Ctrl+A) — itera todos os meses carregando sob demanda, cancelável no meio pela flag `selectAll` |
| `web/src/lib/stores/keyboard-manager.svelte.ts:1` | Estado reativo global de Shift/Ctrl/Meta/Alt via listeners `keydown`/`keyup`/`blur` |
| `.../actions/TimelineKeyboardActions.svelte:112` | Lista de atalhos da grade, **derivada** — retorna `[]` quando busca está aberta, o visualizador está aberto ou um modal está aberto (`:113`). Registrada em `<svelte:document use:shortcuts>` (`:151`) |
| `.../actions/focus-actions.ts:36` | `setFocusTo(direction, interval)` — a navegação por teclado real. Lê o thumbnail focado por `document.activeElement.dataset.thumbnailFocusContainer`, pede ao manager o asset vizinho (`getEarlier/LaterAsset` com intervalo `asset\|day\|month\|year`), faz scroll, `await tick()`, e então `focusAsset(id)` (query por `[data-thumbnail-focus-container][data-asset="..."]`). Usa `InvocationTracker` (`web/src/lib/utils/invocationTracker.ts`) para descartar invocações obsoletas quando o usuário martela a seta |
| `web/src/lib/utils/focus-util.ts:15` | `moveFocus(selector, direction)` — usa `tabbable`/`focusable` sobre `document.body` e caminha circularmente até achar elemento que satisfaça o predicado |
| `web/src/lib/actions/shortcut.ts:1` | Reexporta `shortcut`/`shortcuts`/`matchesShortcut`/`shouldIgnoreEvent` de `@immich/ui` |
| `web/src/lib/actions/focus-trap.ts` | Focus trap usado no visualizador (`AssetViewer.svelte:243`) |

**Atalhos da grade** (`TimelineKeyboardActions.svelte:117-145`):

- `←`/`→`: asset anterior/próximo (com foco); `D`/`Shift+D`: dia; `M`/`Shift+M`:
  mês; `Y`/`Shift+Y`: ano
- `G`: modal "ir para data"; `/`: ir para Explore; `Shift+?`: modal de atalhos;
  `Ctrl+A`: selecionar tudo; `Esc`: limpar seleção
- Com seleção ativa: `Delete` (lixeira), `Shift+Delete` (permanente), `Ctrl+D`
  (limpar), `s` (empilhar), `Shift+A` (arquivar); `Shift+D` (download), `t`
  (tags)
- No thumbnail focado (`Thumbnail.svelte:215`): `Enter` abre, `x` seleciona,
  `Esc` sai do container
- No scrubber (`Timeline.svelte:582`): `↑`/`↓` rolam 50 px (500 px com Shift)

**Atalhos do visualizador**: `←`/`a` anterior e `→`/`d` próximo
(`asset-viewer/actions/PreviousAssetAction.svelte:18`,
`NextAssetAction.svelte:18`); `↑`/`↓` navegam dentro do stack
(`AssetViewer.svelte:493`); `z` zoom, `s` slideshow, `Ctrl/Cmd+C` copiar imagem
(`PhotoViewer.svelte:206`); `f` favoritar, `i` painel de info, `l` adicionar a
álbum, `t` tag, `p` marcar pessoas, `e` editor, `Shift+D` download, `0`–`5`
rating, `Delete` lixeira — declarados como `ActionItem.shortcuts` em
`web/src/lib/services/asset.service.ts:69,118,165,179,218,226,234,250`.

O inventário canônico exibido ao usuário está em
`web/src/lib/modals/ShortcutsModal.svelte:26-51`.

### 1.7 Visualizador em tela cheia

| Arquivo:linha | Papel |
|---|---|
| `.../asset-viewer/AssetViewer.svelte:240` | Shell: grid fixo `grid-cols-4 grid-rows-[64px_1fr]` sobre fundo preto, `use:focusTrap`. Escolhe o viewer por `viewerKind`: PhotoViewer / VideoViewer / LiveVideoViewer / ImagePanoramaViewer / CropArea / StackVideoViewer |
| mesmo `:211` | `navigateAsset(order)`: cancela o preloader do lado oposto, protege contra reentrância com `InvocationTracker`, e navega via URL (`navigateToAsset`) — prev/next é navegação de rota SvelteKit, não estado local |
| `.../asset-viewer/PreloadManager.svelte.ts:12` | **Prefetch de vizinhos**. Mantém `nextPreloader` e `previousPreloader` (instâncias de `AdaptiveImageLoader` com `loadImage` fora do DOM). `updateAfterNavigation` (`:67`) detecta se o usuário andou para frente/trás e recicla: ao avançar, destrói o preloader de trás e cria um novo para o novo "próximo"; se o salto foi arbitrário, recria os dois |
| `web/src/lib/utils/adaptive-image-loader.svelte.ts:34` | Escada de qualidade `thumbnail → preview → original`. Estado por qualidade (`unloaded\|success\|error`), `highestLoadedQualityIndex` impede regressão visual. `trigger(quality)` inicia a próxima etapa; erro em `preview` cai para `original` (`AdaptiveImage.svelte:117`) |
| `web/src/lib/components/AdaptiveImage.svelte:186` | Decide quais das 3 camadas `<img>` empilhadas ficam montadas — as camadas coexistem e a de maior qualidade cobre as anteriores. `:97` `afterThumbnail`: se já está com zoom > 1, pula `preview` e vai direto ao `original`. `:203` reage ao zoom pedindo o original |
| mesmo `:1-49` | Workaround Chromium de rasterização HDR: mede `MAX_TEXTURE_SIZE` do WebGL, dimensiona o container acima do tamanho de exibição e aplica `transform: scale(1/rasterRatio)` + `will-change: transform`, com teto de 4M/10M/16M pixels |
| `web/src/lib/actions/zoom-image.ts:11` | Action `use:zoomImageAction` sobre `@zoom-image/core` (`createZoomImageWheel`, `maxZoom: 10`). Grande parte do arquivo é interceptação em fase de captura de pointer/touch/wheel/dblclick para que overlays (`[data-overlay-interactive]`, ex.: caixas de OCR) não sejam capturados pelo zoom |
| `web/src/lib/managers/asset-viewer-manager.svelte.ts:145` | `animatedZoom` — interpolação com `requestAnimationFrame` + `cubicOut`, 300 ms, cancelável (qualquer `pointerdown` cancela). Duplo clique alterna 1↔2 (`PhotoViewer.svelte:103`) |
| mesmo `:45` | `isImageLoading` derivado: verdadeiro enquanto nem preview nem original carregaram, ou enquanto o original está pendente com zoom > 1 |
| `.../asset-viewer/PhotoViewer.svelte:214` | Container com `useSwipe` (svelte-gestures) → esquerda/direita navegam, desde que zoom ≤ 1 e overlay de OCR desligado. Overlays de rostos (com máscara SVG que escurece o resto) e OCR são desenhados sobre `overlaySize` calculado por `scaleToFit(getNaturalSize(imgRef), container)` |

### 1.8 Estados de carregamento / vazio / erro / progresso

| Arquivo:linha | Papel |
|---|---|
| `web/src/lib/elements/Skeleton.svelte:14` | Placeholder de mês não carregado: div com altura estimada + `animate-pulse` e background tileado (tile 235 px, 100 px no mobile). Aceita `invisible` para não piscar durante o scroll-para-asset inicial |
| `web/src/lib/components/Thumbhash.svelte` | Placeholder por asset (LQIP). Aparece enquanto `!loaded \|\| thumbError` (`Thumbnail.svelte:301`) e some com fade — exceto se o thumbnail já saiu da tela (`skipFade`, `:255`) |
| `web/src/lib/components/DelayedLoadingSpinner.svelte:16` | Spinner com `visibility:hidden` + animação que só o revela após **400 ms** — evita flash em cargas rápidas. Usado no `AdaptiveImage` apenas quando não há thumbhash |
| `web/src/lib/components/assets/BrokenAsset.svelte:18` | Estado de erro por asset: ícone + mensagem, com classes `@container` que escondem o ícone/encolhem o texto em thumbs pequenas |
| `.../shared-components/EmptyPlaceholder.svelte:23` | Estado vazio genérico. Injetado na timeline pelo snippet `empty` (`Timeline.svelte:622`), e a timeline considera vazio quando `isInitialized && months.length === 0` (`Timeline.svelte:104`) |
| `web/src/lib/utils/handle-error.ts:38` | Funil único de erro: ignora `AbortError`, extrai mensagem do servidor (`getServerErrorMessage`, `:4`, inclusive erros de validação Zod com path), trunca em 75 chars e emite `toastManager.danger`. Erros de carregamento de bucket passam por aqui (`timeline-month.svelte.ts:318`) |
| `web/src/lib/utils/cancellable-task.ts:1` | Máquina de estados de carregamento reutilizada por bucket e pelo init: `executed/loading`, promise `complete`, `execute(fn, cancellable)` retorna `'DONE'\|'WAITED'\|'CANCELED'\|'LOADED'\|'ERRORED'`, e `reset()`. É o que permite cancelar buckets que saíram do viewport sem propagar erro |
| `web/src/routes/NavigationLoadingBar.svelte:10` | Barra de progresso de navegação, com **delay de 100 ms** e tween até 90% |
| `web/src/routes/UploadPanel.svelte:36` | Painel flutuante de upload: contadores `success/errors/duplicates`, controle de concorrência (`uploadExecutionQueue`), wake lock enquanto há uploads (`:27`), toasts resumo no `onoutroend` (`:40`) |
| `web/src/routes/DownloadPanel.svelte:16` | Painel de download com barra de percentual por arquivo e botão de abort (`AbortController` por download) |
| `web/src/lib/managers/queue-manager.svelte.ts:27` | Progresso de jobs: **polling a cada 3 s** via `getQueues()`, mantendo uma janela de 30 snapshots (`:43`) usada para desenhar gráficos. `listen()` retorna unsubscribe e o polling só busca de fato se há ouvintes. Também reage ao evento websocket `QueueUpdate` (`:22`) |
| `web/src/routes/admin/queues/QueueCard.svelte:46` | Card por fila: badge Paused/Active, contadores `active` e `waiting` (= waiting+paused+delayed), badges de `failed`/`delayed`, botões start/pause/clear-failed |
| `.../timeline-manager/internal/websocket-support.svelte.ts:13` | Atualizações em tempo real: eventos `on_upload_success`, `on_asset_update`, `on_asset_trash`, `on_asset_delete` são acumulados e aplicados em lote com `throttle(2500)` — evita relayout a cada foto durante um import grande |

---

## 2. O contrato de API que a grade consome

### 2.1 Duas chamadas, duas formas — a chave da virtualização sem salto

**(a) Índice** — `GET /api/timeline/buckets`
(`server/src/controllers/timeline.controller.ts:15`), retorna
`TimeBucketsResponseDto[]`:

```
[{ timeBucket: "2024-01-01", count: 1284 }, { timeBucket: "2023-12-01", count: 97 }, ...]
```

Chamado uma única vez por configuração de timeline em
`timeline-manager.svelte.ts:256`. Com `{timeBucket, count}` a UI já consegue:
(i) saber quantos meses existem e em que ordem, (ii) estimar a altura de cada mês
pela fórmula heurística de `layout-support.svelte.ts:11-16`, (iii) somar tudo em
`totalViewerHeight` e (iv) desenhar o scrubber inteiro. **A barra de rolagem tem
o tamanho final antes de qualquer imagem ser buscada.**

**(b) Conteúdo** —
`GET /api/timeline/bucket?timeBucket=YYYY-MM-01T00:00:00.000Z`
(`timeline.controller.ts:26`), retorna `TimeBucketAssetResponseDto` num formato
**colunar (struct-of-arrays)**, não uma lista de objetos:

```
{ id: string[], ownerId: string[], ratio: number[], isFavorite: boolean[], visibility: [],
  isTrashed: boolean[], isImage: boolean[], thumbhash: (string|null)[],
  createdAt: string[], fileCreatedAt: string[], localOffsetHours: number[],
  duration: (number|null)[], projectionType: (string|null)[], livePhotoVideoId: (string|null)[],
  stack?: ([stackId, count] | null)[],
  city?, country?, latitude?, longitude? }
```

Esquema em `server/src/dtos/time-bucket.dto.ts:74-121`; tipos no cliente em
`packages/sdk/src/fetch-client.ts:2696`. O parsing coluna→objeto acontece em
`timeline-month.svelte.ts:175-221`.

Parâmetros de filtro compartilhados pelas duas chamadas
(`fetch-client.ts:6625` e `:6670`): `albumId, personId, tagId, userId,
visibility, isFavorite, isTrashed, withPartners, withStacked, withCoordinates,
bbox, order (asc|desc), orderBy (takenAt|createdAt), key, slug`. O
`TimelineManagerOptions` (`timeline-manager/types.ts:8`) é literalmente
`Omit<Parameters<getTimeBuckets>[0], 'size'>` mais três campos locais.

### 2.2 Por que esse formato elimina saltos de layout

Três propriedades, todas garantidas no servidor:

1. **`ratio` vem pronto e arredondado.**
   `server/src/repositories/asset.repository.ts:824-834`:
   `round(width::numeric / height::numeric, 3)`, com `coalesce(...,1)` quando
   `width=0 or height=0`. O cliente nunca mede a imagem para saber a altura da
   linha — logo, nenhuma linha muda de altura quando a imagem chega. É por isso
   que `TimelineAsset.ratio` é `number` obrigatório (`types.ts:21`).
2. **`thumbhash` vem no mesmo payload.** Todo asset tem seu LQIP disponível no
   instante em que a célula é criada — não há um segundo round-trip por foto para
   o placeholder.
3. **O bucket é atômico e pré-ordenado.** O SQL ordena por data truncada +
   `fileCreatedAt` na direção pedida (`asset.repository.ts:900-906`) e agrega com
   `array_agg` (`:909-930`); a resposta final é `to_json(agg)::text` (`:946`) — o
   serviço retorna a string bruta e o Nest só define o `Content-Type`
   (`timeline.service.ts:18` comenta "pre-jsonified response";
   `timeline.controller.ts:29`). Não há serialização objeto-a-objeto no Node. O
   cliente confia na ordem e usa `preSorted=true` (`load-support.svelte.ts:49`).

**Não há paginação.** Nem offset, nem cursor, nem `limit`. A unidade de paginação
*é* o mês. Um mês com 20 000 fotos vem em uma única resposta. Há um
`// TODO: use id cursor for pagination` em `timeline.service.ts:22`. O cliente
cancela via `AbortSignal` quando o mês sai do viewport durante o fetch
(`load-support.svelte.ts:24`, `timeline-month.svelte.ts:96`).

**Detalhe de timezone:** em vez de mandar `localDateTime` como string, o servidor
manda `fileCreatedAt` (UTC) + `localOffsetHours` (float, pode ser fracionário:
5.5, −9.75), computado em SQL (`asset.repository.ts:815`). O cliente reconstrói o
horário local com Luxon em `timeline-util.ts` (`getTimes`, `:66`). Menos bytes e
sem ambiguidade de zona.

### 2.3 Contrato de mídia

`web/src/lib/utils.ts:234` — `getAssetMediaUrl({id, size, cacheKey})` produz:

```
/api/assets/{id}/thumbnail?size=thumbnail|preview|fullsize&c={thumbhash}&edited=true
/api/assets/{id}/original?c={thumbhash}&edited=true
```

O `cacheKey` (`c`) **é o thumbhash do asset** (`utils.ts:205,215`). Como o
thumbhash muda quando a imagem é reprocessada/editada, a URL é
estável-mas-invalidável: dá para cachear agressivamente no browser sem
`no-cache`. Vídeo: `/api/assets/{id}/video/playback?c=...` (`utils.ts:241`) e HLS
em `/assets/{id}/video/stream/main.m3u8` (`:246`). Escolha de tamanho em
`targetImageSize` (`:225`): `preview` por padrão, `original`/`fullsize` se o
usuário optou por sempre carregar original ou se é GIF animado.

### 2.4 Contrato de URL (roteamento)

- Grade: `/photos`, com `?at=<assetId>` como alvo de scroll
  (`AssetGridRouteSearchParams`, `navigation.ts:7`).
- Visualizador: `/photos/<assetId>` — rota SvelteKit opcional `[[assetId=id]]`.
- Fechar o visualizador escreve `?at=<id>` e volta para a grade
  (`TimelineAssetViewer.svelte:99`); ao navegar, `Timeline.scrollAfterNavigate`
  (`:201`) carrega o mês do asset, rola até ele e devolve o foco. Deep-link
  desliga o layout preguiçoso durante a operação (`isScrollingOnLoad`, `:180`,
  com comentário explicando que senão `scrollHeight` fica dessincronizado).

---

## 3. Decisões de performance e o que elas custam

| Decisão | Onde | Custo |
|---|---|---|
| **Índice `{timeBucket,count}` separado do conteúdo** | `timeline-manager.svelte.ts:256` | Barra de rolagem correta desde o frame 0; scrubber completo. Custo: a altura inicial é uma *estimativa* (fator 1.5×0.7) — ao carregar o mês de verdade a altura muda, o que exige toda a maquinaria de re-ancoragem de `timeline-month.svelte.ts:269`. É a parte mais delicada do código |
| **Bucket mensal como unidade atômica** | `load-support.svelte.ts:8` | Uma request por mês; cancelável; dedup natural. Custo: meses gigantes (50k fotos num mês) geram uma resposta enorme e um `layout()` O(n) num único frame |
| **Resposta colunar pré-serializada em SQL** | `asset.repository.ts:909-946` | Payload muito menor (nomes de campo não se repetem por asset) e zero custo de serialização no Node. Custo: o cliente precisa de um loop de reconstrução manual (`timeline-month.svelte.ts:177-221`) fácil de dessincronizar do schema; o alinhamento entre colunas é uma invariante não verificável por tipo |
| **`ratio` calculado no servidor** | `asset.repository.ts:828-834` | Layout determinístico e idêntico entre reloads; nenhuma medição de DOM. Custo: precisa de `width/height` no banco para todo asset; assets sem dimensão caem em 1.0 (quadrado) e ficam com layout errado |
| **Justified layout em WASM** | `layout-utils.ts:34-46` | Layout de milhares de caixas fora do custo do JS, alimentado por `Float32Array`. Custo: binário WASM extra no bundle, e um segundo caminho de código (JS) para manter em paridade |
| **Layout preguiçoso (`deferredLayout`)** | `timeline-day.svelte.ts:161`, `timeline-manager.svelte.ts:245` | Meses fora do viewport nunca pagam o custo do justified layout. Custo: existe um estado "carregado mas sem geometria"; `findAssetAbsolutePosition` tem que forçar `clearDeferredLayout` antes de responder (`timeline-month.svelte.ts:336`), e o deep-link precisa desligar o mecanismo inteiro |
| **Virtualização em dois níveis (mês → dia com busca binária)** | `timeline-day.svelte.ts:177-197` | O laço de scroll é O(meses) + O(dias visíveis · log assets), não O(assets). Custo: `activeViewerAssets` é um `slice()` novo a cada atualização — pressão de GC; o código de fronteira é sutil |
| **Margem de 500 px acima/abaixo** | `tunables.ts:24-25` | Thumbs já estão no DOM e decodificadas quando entram na tela. Custo: ~2 telas extras de `<img>` montadas |
| **Handlers de scroll estritamente síncronos** | `Timeline.svelte:256`, `:274`, `:307` | Sem flicker (comentários explícitos proibindo throttle/debounce). Custo: todo o trabalho de proximidade acontece no thread principal durante o scroll |
| **`suspendTransitions` durante scroll/resize** | `VirtualScrollManager.svelte.ts:105`, `AssetLayout.svelte:31` | Desliga `animate:flip`/`transition` enquanto rola; volta após 1 s de silêncio. Custo: propagar a flag por 3 componentes |
| **`contain: strict` / `contain: layout size paint` + `translate3d`** | `Timeline.svelte:715,720` | Isola o browser de recalcular layout do documento inteiro. Custo: cada mês visível é potencialmente uma camada GPU |
| **Dedup e cancelamento de requests no Service Worker** | `service-worker/request.ts:19,62` | Scroll rápido não deixa dezenas de downloads órfãos competindo por conexões. Custo: SW é infraestrutura extra; o mapa de pendentes segura entradas por 5 min; só funciona em contexto seguro |
| **Escada thumbnail→preview→original + 3 `<img>` empilhados** | `adaptive-image-loader.svelte.ts:34`, `AdaptiveImage.svelte:252-287` | Algo aparece quase imediatamente e a qualidade sobe sem piscar. Custo: até 3 decodificações da mesma foto na memória |
| **Prefetch de exatamente 1 vizinho por lado, com reciclagem direcional** | `PreloadManager.svelte.ts:67-87` | Setas instantâneas em navegação linear. Custo: em salto arbitrário, os dois preloaders são destruídos e recriados |
| **Batching de eventos websocket em 2,5 s** | `websocket-support.svelte.ts:13` | Import de milhares de fotos não causa milhares de relayouts. Custo: até 2,5 s de latência para a foto nova aparecer |
| **Contraponto: nenhuma persistência** | — | Não há cache do índice de buckets em IndexedDB/localStorage. Toda navegação para `/photos` refaz `GET /timeline/buckets` e recarrega os meses visíveis. Trocado por simplicidade e correção |

---

## 4. Portabilidade para React/Vite/TS/Tailwind + FastAPI em 127.0.0.1

### 4.1 Portar quase sem alteração — o núcleo do valor

**a) O contrato de duas chamadas.** É a ideia mais valiosa e é agnóstica de
framework.

- `GET /timeline/buckets` → `[{bucket: "2024-01", count: n}]`
- `GET /timeline/bucket?bucket=2024-01` → colunas paralelas

Em FastAPI local isso é trivial e ainda mais barato: com SQLite você pode devolver
`orjson` de um dict de listas. Mantenha `ratio` calculado no backend e arredondado
(3 casas) — é o que garante layout estável. Mantenha um `thumbhash`/`blurhash` no
mesmo payload.

**b) Estimativa de altura antes do fetch.** A fórmula de
`layout-support.svelte.ts:11-16` é 5 linhas e resolve "scrollbar com o tamanho
certo desde o início". Porte literalmente, mas calibre o fator 0.7 para o seu
acervo.

**c) Virtualização em dois níveis com busca binária.**
`timeline-day.svelte.ts:15` (`lowerBound`) + `:177` são ~40 linhas de TS puro,
sem nada de Svelte. Porte como funções puras.

**d) Re-ancoragem de scroll ao mudar altura.** `timeline-month.svelte.ts:269-307`.
É o algoritmo que impede o salto quando a altura estimada vira altura real: se o
mês alterado está *acima* do mês visível → `scrollBy(delta)`; se *é* o mês visível
→ `scrollTo(top + height*ratio)`; se está abaixo → não faça nada.

**e) Justified layout.** `@immich/justified-layout-wasm` é um pacote npm público;
`justified-layout` (Flickr) também. A interface necessária é a de
`layout-utils.ts:13-21` (`containerWidth/Height` + `getPosition(i)`).

**f) Padrão de foco por atributo de dados.** `data-asset={id}` +
`data-thumbnail-focus-container` + `tabindex=0` (`Thumbnail.svelte:227-232`),
navegação via `tabbable`/`focusable` (`focus-util.ts:15`) e `focusAsset(id)` por
`querySelector` após `tick()`. Em React o equivalente é `flushSync` +
`requestAnimationFrame` antes do `.focus()`. Este é o padrão certo para uma UI
teclado-first: **o foco do DOM é a fonte da verdade da "célula atual"**, não um
índice em estado React. Dá acessibilidade e integração com o browser de graça.

**g) `InvocationTracker`.** `web/src/lib/utils/invocationTracker.ts` — descarta
resultados de navegações assíncronas obsoletas quando o usuário segura a seta.

**h) `CancellableTask`.** `web/src/lib/utils/cancellable-task.ts` é TS puro (148
linhas, zero dependência de Svelte). Cobre o ciclo bucket carregando → cancelado
por sair do viewport → recarregado, sem race conditions.

**i) Escada de qualidade `AdaptiveImageLoader`.** A regra
`highestLoadedQualityIndex` (nunca regredir de qualidade) é o detalhe que faz
funcionar.

**j) `PreloadManager` direcional.** `PreloadManager.svelte.ts:67` é TS puro.

**k) Atalhos.** A tabela de `TimelineKeyboardActions.svelte:117-145` e
`ShortcutsModal.svelte:26-51` é um design de teclado maduro: setas = asset,
`D`/`M`/`Y` = dia/mês/ano (Shift inverte), `G` = ir para data, `x` = selecionar,
`Shift+?` = ajuda. É convencional o bastante para não precisar ser aprendido.

**l) Lista de atalhos derivada e vazia quando algo tem prioridade.**
`TimelineKeyboardActions.svelte:113` retorna `[]` se busca/visualizador/modal
está aberto. Em React: um único hook `useShortcuts(list)` que recebe uma lista
recomputada, em vez de N `useEffect` com `addEventListener`. Evita a classe
inteira de bugs de atalho vazando.

**m) Placeholders com timing calibrado.** Thumbhash no payload + spinner com
delay de **400 ms** (`DelayedLoadingSpinner.svelte:16`) + barra de navegação com
delay de **100 ms** (`NavigationLoadingBar.svelte:10`). Porte os números, não
reinvente.

**n) Cache key = hash do conteúdo na query string.** `?c={thumbhash}`
(`utils.ts:238`). Em FastAPI: sirva thumbnails com
`Cache-Control: public, max-age=31536000, immutable` e invalide trocando o `c`.

### 4.2 Portar com adaptação

**Service Worker.** A dedup + cancelamento (`service-worker/request.ts`) resolve
um problema real, mas em 127.0.0.1 contra um FastAPI local a latência é ~0 e o
benefício encolhe. Alternativa sem SW: um `Map<url, AbortController>` no cliente,
cancelando no unmount do `<img>`. Faça a versão sem SW primeiro.

**Websocket + throttle 2,5 s.** Single-user local pode não precisar de websocket
nenhum. Se houver ingestão em background, o padrão de acumular mudanças e aplicar
em lote vale — mas SSE do FastAPI é mais simples e suficiente.

**Reatividade fina.** O maior ganho de perf da implementação Svelte é que
`activeViewerAssets` é estado por dia: mudar a fatia de um dia não re-renderiza os
outros. Em React o equivalente idiomático é store externo
(Zustand/`useSyncExternalStore`) com seletor por dia, `React.memo` nas células e
chave estável = `asset.id`. **Se você renderizar tudo a partir de um único
`useState` no topo, a virtualização de dois níveis não te salva — o reconciliador
vira o gargalo.** Isso precisa ser decidido no começo.

**Progresso de jobs.** `queue-manager.svelte.ts:27` faz polling de 3 s com janela
de 30 snapshots para gráfico. O padrão de guardar N snapshots para desenhar a
série temporal é o que vale copiar.

### 4.3 Não portar

- **Workaround de rasterização HDR do Chromium** (`AdaptiveImage.svelte:1-49`).
  Só adicione se observar as "seam lines" com zoom.
- **Interceptação de pointer/touch em fase de captura** (`zoom-image.ts:30-125`).
  Só existe por causa dos overlays interativos (OCR, rostos) sobre a imagem com
  zoom. Sem esses overlays, um zoom com wheel + pan é ~30 linhas.
- **`localOffsetHours` e a matemática de timezone** (`timeline-util.ts:33-100`)
  **no formato do wire** — faz sentido para servidor multiusuário com fotos de
  várias zonas. (Atenção: isso vale para o *transporte*. O modelo de
  **armazenamento** de dois instantes, descrito no mapa 03, continua valendo.)
- **Múltiplos caminhos de layout** (WASM + JS + `TUNABLES` para alternar).
  Escolha um.
- **Segundo grid** (`GalleryViewer.svelte`, 401 linhas) — implementação paralela
  para resultados de busca, com layout justified sobre lista plana e
  `onEndReached` debounced (`:108`). Se a busca também retorna por bucket, essa
  duplicação é evitável.
- **Camadas de shared link / álbuns / partners / OCR / faces / cast / slideshow**
  — cada uma injeta condicionais em `Thumbnail.svelte`, `AssetViewer.svelte` e
  nos options do bucket. Em single-user, `TimelineManagerOptions` pode ser só
  `{visibility, order}`.

### 4.4 Ordem sugerida de implementação

1. `GET /buckets` + `GET /bucket` colunar com `ratio` e `thumbhash` no backend.
2. Store externo com `months[] → days[] → assets[]`, altura estimada,
   `totalViewerHeight`.
3. Div spacer de altura total + meses absolutos com `translate3d` + `contain`.
4. Justified layout por dia + re-ancoragem de scroll ao trocar estimativa por
   altura real.
5. `activeViewerAssets` com busca binária + margem de 500 px.
6. `data-asset` + `tabindex=0` + `moveFocus`; depois setas / `D` / `M` / `Y` /
   `G` / `x` / `Ctrl+A` / `Esc`.
7. Thumbhash → thumbnail → (visualizador) preview → original; prefetch de 1
   vizinho por lado.
8. Estados: skeleton por mês, spinner com delay 400 ms, `BrokenAsset` por célula,
   empty placeholder, toast único de erro.

Os passos 4 e 5 são onde está a dificuldade real; o resto é mecânico.
