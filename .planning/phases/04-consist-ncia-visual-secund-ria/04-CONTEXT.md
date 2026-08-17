# Phase 4: Consistência visual secundária - Context

**Gathered:** 2026-08-16
**Status:** Ready for planning

<domain>
## Phase Boundary

As inconsistências visuais/interação restantes deixam de diferenciar "em
que tela eu estou" de "o que o design system manda" — 8 achados medidos em
`docs/AVALIACAO_UX.md` (2026-08-06), confirmados AINDA ABERTOS por
verificação direta de código em 2026-08-16 (diferente das 3 fases
anteriores, nenhum dos 8 já tinha sido corrigido).

CONS-01/02 (selos de identidade em Revisão/Eventos), CONS-03/07
(hierarquia visual de botão — o que é "importante" vs. o que é
"cancelar"), CONS-04/05 (recuperação de estado ruim — imagem quebrada e
vazio acionável), CONS-06 (responsividade ~1000px) e CONS-08 (token de
peso de ênfase, reconciliação full-codebase já anunciada como trabalho
desta fase pelo `03-UI-SPEC.md`).

</domain>

<decisions>
## Implementation Decisions

### CONS-01/02 — Selos de identidade
- **D-01:** Selo de CONS-01 (Revisão, sugestões adjacentes colididas em
  nome+data+câmera mas `media_id` diferente) mostra o **nome da fonte de
  origem** (ex.: "Apple Fotos", "Lightroom"), não um rótulo genérico —
  exige resolver `MediaFile.source_id` → nome da `Source` na sugestão.
- **D-02:** O selo aparece **em cada sugestão colidida individualmente**,
  não como aviso único no cabeçalho do grupo.
- **D-03:** CONS-02 usa o critério determinístico já disponível:
  `Agrupamento.metodo == "album_externo"` (constante `ORIGEM_ALBUM` em
  `fotoorganizer/grouping/classifier.py:95`) vira selo **"Álbum"**;
  qualquer outro valor de `metodo` vira **"Evento detectado"**. Campo já
  exposto por `GET /api/.../grupos` (`server/app.py:869`) e já tipado em
  `webapp/src/api.ts:198`, nunca lido no `Trips.tsx` — zero mudança de
  backend necessária.

### CONS-03/07 — Hierarquia visual de botão
- **D-04:** "Ação mais comprometedora" (única que fica `solido`/preenchida)
  = **só operação física de copiar arquivo** — alinhado ao princípio do
  CLAUDE.md "primeiro catalogar, depois sugerir, então revisar e somente
  por último executar operações físicas". Hoje só `Operations.tsx:194`
  ("Executar plano") e confirmações de modal destrutivo se qualificam.
  `Review.tsx:151-158` ("Gerar/atualizar sugestões") reescreve estado do
  catálogo mas não copia arquivo — migra pra contorno neutro+hover, mesmo
  padrão já usado em `RetomarScan.tsx`.
- **D-05:** Hover de "cancelar" segue o critério: **job em andamento
  (perde progresso real) = vermelho; edição/modal (nada foi feito ainda) =
  neutro**. Isso já bate com `StatusBar.tsx` (`hover:text-erro`) e
  `Review.tsx`/`Sidebar.tsx` (`hover:bg-cartao`) hoje — só
  `Operations.tsx:213-215` (`tom="erro"` fixo, vermelho mesmo fora do
  hover, não só no hover) sai do padrão e precisa ajustar pra vermelho
  **só no hover**, não permanente.

### CONS-04/05 — Recuperação de estado ruim
- **D-06:** Imagem 404 no Loupe e na comparação de Duplicatas ganha
  **tratamento visual dedicado** (não a réplica literal do padrão de
  `Trips.tsx:106-147`) — Loupe é tela cheia, Duplicatas é comparação lado
  a lado, contextos diferentes o bastante pra justificar desenho próprio.
  Exato ícone/layout/texto fica a critério do **UI researcher desta fase**
  (`/gsd:ui-phase 4`) — trava aqui apenas que (a) nunca pode ser o ícone
  de imagem quebrada cru do browser ou texto cru, tem que ser estado
  explícito; (b) Loupe e Duplicatas podem ter tratamentos diferentes entre
  si, não precisam ser idênticos.
- **D-07:** Os 3 estados vazios (Panorama, PhotoGrid, Trips) ganham **a
  mesma ação** — botão que abre o fluxo "Adicionar pasta" já existente na
  Sidebar. Não inventar ação própria por tela.

### CONS-06 — Responsividade ~1000px
- **D-08:** Abaixo do breakpoint, a **barra superior empilha em 2 linhas**
  — o Inspetor continua sempre visível, nada colapsa/desaparece. Custo
  aceito: consome mais altura vertical em tela já apertada.
- **D-09:** Breakpoint usa o token padrão do Tailwind **`lg` (1024px)**,
  não um valor customizado — hoje zero classe responsiva existe em
  `App.tsx`/`Inspector.tsx` (confirmado por grep), então não há precedente
  de breakpoint customizado a seguir.

### CONS-08 — Token de peso de ênfase
- **D-10 [informational, revisado 2026-08-16 após BLOCK do gsd-ui-checker
  na Fase 4]:** Confirmado migrar TODO `font-semibold`/`font-medium` do
  webapp — **sem exceção** — para um token único `--font-weight-titulo:
  500` no `@theme` de `webapp/src/index.css`, mesmo valor que
  `font-medium` (500) já travado como peso canônico de ênfase na Fase 3
  (`03-UI-SPEC.md` linhas 88-106, que já anunciava essa reconciliação
  full-codebase como trabalho desta fase). Afeta 9 arquivos: `App.tsx`,
  `Loupe.tsx`, `Trips.tsx`, `Inspector.tsx`, `Sidebar.tsx`,
  `Duplicates.tsx`, `TemplateEditor.tsx`, `Review.tsx`, `Operations.tsx`,
  `Mapa.tsx`. **Revisão da decisão original:** a versão anterior deste
  D-10 excluía `Inspector.tsx:38` (cabeçalho de nome de arquivo,
  `font-semibold`/600) por ser "papel de título de página" — o checker de
  UI (`gsd-ui-checker`) bloqueou o `04-UI-SPEC.md` por isso: a exceção
  deixava o projeto com 3 pesos de ênfase em uso simultâneo (400/500/600)
  em vez do teto de 2, e — diferente da Fase 3, onde `Inspector.tsx`
  estava genuinamente fora de escopo — CONS-08 é justamente a
  reconciliação full-codebase, então a exceção não pode ficar de fora da
  contagem. Perguntado ao dono explicitamente entre "migrar tudo" e
  "tornar a exceção uma regra permanente do design system" — escolheu
  migrar tudo. `Inspector.tsx:38` também vira `font-titulo` (500); o
  projeto fecha com 2 pesos reais (400 corpo, 500 ênfase/título), sem
  exceção.

### Claude's Discretion
- Nome exato da classe/prop CSS usada para aplicar o token (`font-medium`
  redefinido para apontar no token, ou uma nova classe utilitária) — desde
  que o valor computado final seja 500 em todo lugar migrado.
- Estrutura exata de como a barra superior empilha em 2 linhas (CONS-06,
  D-08) — que elementos vão pra linha 2, ordem — desde que Inspetor
  continue visível e nada se sobreponha abaixo de `lg` (1024px).
- Layout/ícone exato do estado 404 (CONS-04, D-06) — delegado ao UI
  researcher (`/gsd:ui-phase 4`).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Achados originais e estado atual
- `docs/AVALIACAO_UX.md` A.3, A.4, A.6, A.7, B.3, B.6, B.7, B.8 — achados
  originais dos 8 itens desta fase (medido 2026-08-06), todos confirmados
  ainda abertos em 2026-08-16 antes desta discussão.
- `docs/DECISOES.md` — invariantes gerais de confiança/UI já estabelecidos
  (D-017, D-018, referenciados em PROJECT.md).

### Precedente direto da Fase 3
- `.planning/phases/03-revis-o-acess-vel-e-consistente/03-UI-SPEC.md`
  linhas 88-106 — trava `font-medium` (500) como peso canônico de ênfase
  e anuncia explicitamente que a reconciliação full-codebase (CONS-08) é
  trabalho desta fase (D-10).

### Código existente a reaproveitar
- `fotoorganizer/grouping/classifier.py:95` (`ORIGEM_ALBUM =
  "album_externo"`) e `:137-138` — origem do critério de D-03.
- `fotoorganizer/server/app.py:869` (`"metodo": grupo.metodo`) — campo já
  exposto pela API.
- `webapp/src/api.ts:198` (`metodo: string`) — campo já tipado no
  frontend, nunca lido em `Trips.tsx`.
- `webapp/src/components/Trips.tsx:106-147` — padrão de erro de imagem já
  implementado (`onError` + `setCapaFalhou` + mensagem "capa fora de
  alcance") — referência de comportamento pra D-06, mesmo não sendo
  replicado literalmente.
- `webapp/src/components/RetomarScan.tsx` — já usa o padrão de botão
  contorno (default do `Botao`) que D-04 estende a "Gerar sugestões".
- `webapp/src/components/Panorama.tsx:150`, `PhotoGrid.tsx:73-75`,
  `Trips.tsx:48-51` — os 3 textos de estado vazio que ganham botão (D-07).
- `webapp/src/components/StatusBar.tsx:100-106`,
  `Operations.tsx:213-215`, `Review.tsx:279-282`,
  `Sidebar.tsx:266-268,302-304,342-344` — os 3 tratamentos de "cancelar"
  hoje divergentes (D-05).
- `webapp/src/index.css` bloco `@theme` (linhas 5-68) — onde o novo token
  `--font-weight-titulo` entra (D-10).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Padrão de erro de imagem de `Trips.tsx` (onError + estado + mensagem) —
  não replicado literalmente (D-06), mas é a referência de comportamento
  mínimo esperado (nunca ícone quebrado cru).
- Fluxo "Adicionar pasta" da Sidebar — já existe, D-07 só liga um botão
  novo a ele em 3 lugares.
- `Botao` (componente compartilhado) já tem variante contorno — CONS-03
  não cria variante nova, só reclassifica quais botões usam qual.

### Established Patterns
- `font-medium` (500) já é o peso canônico de ênfase desde a Fase 3 —
  CONS-08 é reconciliação, não uma decisão nova de design.
- Testemunha/sinal nunca aparece em Revisão/Viagens/Operações (D-024) —
  não relevante para os selos de CONS-01/02, que operam sobre acervo
  organizável.

### Integration Points
- Nenhum endpoint novo — `metodo` (CONS-02) e o nome de fonte (CONS-01)
  já chegam ou são deriváveis do que a API já expõe. Fase é
  majoritariamente frontend; D-01 pode exigir 1 campo adicional
  (nome da fonte) na serialização de sugestão se ainda não vier — revisar
  no research/planning.

</code_context>

<specifics>
## Specific Ideas

Nenhuma referência visual nova além do que já está travado em
`03-UI-SPEC.md` (peso, espaçamento) — o design do estado 404 (D-06) fica
para o UI researcher desta fase.

</specifics>

<deferred>
## Deferred Ideas

- **Classificação de viagem/evento (e não-fotos/vídeo) via LLM lendo os
  dados disponíveis, quando a regra determinística não alcança** — o dono
  levantou isso de novo durante a discussão de CONS-02 (queria que o selo
  "álbum vs. evento" viesse de uma decisão de LLM, não do campo
  determinístico `metodo`). **Segunda vez que essa ideia aparece** — já
  tinha sido levantada e adiada na discussão da Fase 1
  (`01-CONTEXT.md`, seção `<deferred>`). Duas aparições independentes é
  sinal de que isso merece fase própria ou revisão de arquitetura da
  classificação, não mais um adendo a uma fase de polimento visual. Para
  esta fase, CONS-02 usa o critério determinístico já disponível (D-03).

</deferred>

---

*Phase: 04-consistência-visual-secundária*
*Context gathered: 2026-08-16*
