# Phase 3: Revisão acessível e consistente - Context

**Gathered:** 2026-08-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Dois defeitos restantes da rodada de UX de 2026-08-06
(`docs/AVALIACAO_UX.md` §A/§B), depois de confirmar que 5 dos 7 achados
originais (REV-01, REV-04, REV-05, REV-06, REV-07) já estavam corrigidos
no código antes desta sessão:

1. **REV-02 (parcial)**: `texto-3` (contraste ≈3,46:1) ainda usado como
   texto de conteúdo real em alguns pontos de Review/Inspector/Operations,
   depois que o commit `ae60319` (06/08) já corrigiu as 4 instâncias
   originalmente citadas.
2. **REV-03 (parcial)**: busca de texto não é limpa em 3 pontos de
   navegação que ainda faltam, depois que 2 pontos (Panorama→Biblioteca,
   Viagens→Biblioteca) já foram corrigidos.

Um `UI-SPEC.md` já existe e foi aprovado pro escopo original (7 REV) —
já tratava REV-01/04/05 como feitos antes desta sessão confirmar os
outros dois (REV-06/07) também. Continua válido como contrato de design
pros 2 itens restantes.

</domain>

<decisions>
## Implementation Decisions

### REV-02 — critério de classificação texto-3 vs texto-2
- **D-01:** Critério travado: **texto-3 vira texto-2 quando o usuário
  precisa LER aquele texto pra decidir algo** (é a única fonte daquela
  informação). Fica texto-3 quando é **auxílio secundário ao lado de um
  rótulo/valor já legível em outra cor**, ou estado transiente
  (carregando), ou convenção universal (placeholder de input). Decisão
  do dono, 2026-08-16, entre este critério e um mais agressivo ("tudo
  vira texto-2 exceto genuinamente desabilitado") — rejeitado por
  competir mais com a foto (princípio "a foto é a cor da interface" de
  `docs/DIRECAO_DE_ARTE.md`).

- **D-02:** Auditoria completa dos 19 usos restantes de `texto-3` em
  `Review.tsx`/`Inspector.tsx`/`Operations.tsx` (todos os que sobraram
  depois do commit `ae60319`), classificados pelo critério de D-01:

  **Viram `texto-2`** (9 — conteúdo real):
  - `Review.tsx:145` — total da fila ("5.048 em 10 grupos"): única fonte
    dessa informação, não decorativo.
  - `Review.tsx:253` — nome do arquivo (`s.nome`) no subtítulo da
    miniatura de comparação: é o identificador do arquivo, não anotação.
  - `Review.tsx:447` — "Sem evidência registrada para esta sugestão.":
    mensagem de estado vazio, conteúdo informativo.
  - `Inspector.tsx:202` — rótulo do botão "desfazer": texto de uma ação
    clicável, usuário precisa ler pra saber o que o clique faz.
  - `Inspector.tsx:239` — "Este arquivo não trouxe metadado nenhum.":
    mensagem de estado vazio.
  - `Inspector.tsx:246` — rótulo de namespace de metadado (`ns.rotulo`,
    ex. "EXIF", "IPTC"): contextualiza os pares chave/valor abaixo, sem
    ele o agrupamento não tem sentido.
  - `Inspector.tsx:250` — nome da chave de metadado (`item.chave`, ex.
    "ISO", "FNumber") num `<dt>`: é o rótulo do dado, parte do par
    chave/valor que o usuário lê.
  - `Operations.tsx:152` — "N/M copiados" (o texto de progresso dentro
    da div; o `<span>` do status já tem cor própria via `CORES_STATUS` e
    não muda).
  - `Operations.tsx:223` — `veredito(plano)` (resumo do dry-run: "prontos
    com problema", "nenhum arquivo copiável" etc.): conteúdo que decide
    se o plano está pronto pra executar.

  **Ficam `texto-3`** (10 — decorativo/secundário/transiente):
  - `Review.tsx:141` — contador em badge ao lado do rótulo do filtro
    (rótulo já legível em outra cor).
  - `Review.tsx:190` — caret de disclosure ("▾"/"▸"), puramente
    decorativo.
  - `Review.tsx:198` — seta "→" entre origem e destino, `aria-hidden`
    (não é lido por leitor de tela nem pelo usuário como texto).
  - `Review.tsx:316` — ícone "✎" dentro de botão com `title` acessível
    já explicando a ação.
  - `Review.tsx:403`, `Review.tsx:443` — "carregando…": estado
    transiente, não decisório.
  - `Inspector.tsx:196` — anotação "classificado por você" ao lado de
    `{rotulo}`, que já está em `texto-2`.
  - `Inspector.tsx:232` — contador entre parênteses ao lado do cabeçalho
    "Metadados do arquivo", já legível.
  - `Inspector.tsx:236` — "lendo…": estado transiente.
  - `Operations.tsx:122` — `placeholder:text-texto-3`: convenção
    universal de placeholder, fora do escopo de REV-02.
  - `Operations.tsx:291` — fallback de cor de `CORES_STATUS` quando o
    status não está no dict: mesma família de REV-07 (cor por estado),
    não é problema de contraste de conteúdo.

  Não auditar/mudar nenhum outro arquivo além destes três — REV-02 no
  ROADMAP.md nomeia só Review/Inspector/Operations.

### REV-03 — pontos de busca restantes
- **D-03:** Os 3 pontos que faltam usam o **mesmo padrão** (`setBusca("")`)
  já aplicado nos 2 pontos corrigidos (`Panorama.aoRecortar`,
  `Trips.onAbrir`, ambos em `App.tsx`) — consistência, não uma segunda
  abordagem ("chips removíveis", a alternativa que
  `docs/AVALIACAO_UX.md` A.2 também cogitava, mas que o app já decidiu
  não usar nos 2 pontos já corrigidos). Pontos a corrigir, todos em
  `webapp/src/App.tsx`:
  1. Botão de troca de aba (`onClick={() => setAba(nome)}`, ~linha 210)
     — trocar QUALQUER aba deveria limpar a busca, não só entrar em
     Biblioteca via os dois caminhos já cobertos.
  2. `onSelecionarPasta` (callback passado a `Sidebar`, ~linhas 231-237)
     — hoje só limpa `selIndex`, não `busca`.
  3. `aoIrPara` (callback passado a `StatusBar`/`Funil`, ~linhas 438-443)
     — hoje não limpa `busca`.

### Claude's Discretion
- Exato texto/estrutura do diff em cada uma das 19 linhas de D-02 — só a
  classificação (texto-2 vs texto-3) está travada, não a formatação da
  linha.
- Se o botão de troca de aba (D-03 item 1) deve limpar busca sempre, ou
  só quando a aba de destino não é Biblioteca (evitar limpar busca que o
  usuário acabou de digitar, se ele already está em Biblioteca e clica
  em Biblioteca de novo) — decisão de UX fina, planner decide com base
  no comportamento mais previsível pro usuário.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Achados originais e estado atual
- `docs/AVALIACAO_UX.md` §A.2, §B.1 — achados originais de REV-03 e
  REV-02 (medido 2026-08-06).
- `docs/DIRECAO_DE_ARTE.md` — "a foto é a cor da interface" (base do
  critério de D-01, por que não aplicar texto-2 agressivamente).
- `.planning/phases/03-revis-o-acess-vel-e-consistente/03-UI-SPEC.md` —
  contrato de UI já aprovado (6/6 dimensões), inclui o peso de fonte
  canônico (`font-medium`) e a escala de espaçamento pra qualquer
  elemento tocado nesta fase.

### Commits de referência (já corrigidos, não tocar de novo)
- `ae60319` — fix(arte) texto-3/Aprovar-Rejeitar (REV-02 parcial, REV-06
  completo).
- `a7d6e5e` — fix(arte) acento não decora coluna (REV-07).
- `5c7b36d`, `1b125f7` — commits de referência de fases anteriores
  (não relacionados a esta fase, citados por padrão de investigação).

### Código existente a reaproveitar
- `webapp/src/App.tsx` — `setBusca` (linha ~73), os 2 pontos já
  corrigidos (`Panorama.aoRecortar` ~linha 261, `Trips.onAbrir` ~linha
  271) são o molde exato pros 3 pontos de D-03.
- `webapp/src/components/Review.tsx`, `Inspector.tsx`, `Operations.tsx`
  — arquivos da auditoria D-02, linhas exatas listadas ali.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Padrão `setBusca("")` já estabelecido em 2 dos 5 pontos de entrada —
  D-03 só estende o mesmo padrão, não inventa um novo.

### Established Patterns
- `texto-2`/`texto-3` já são tokens do `@theme` (`webapp/src/index.css`)
  — troca é só de classe Tailwind, sem token novo.
- `CORES_STATUS` (Operations.tsx) é o padrão já estabelecido pra cor por
  estado — não confundir com o problema de contraste de REV-02 (são
  categorias de problema diferentes, mesmo token `texto-3` aparecendo
  nos dois contextos).

### Integration Points
- Nenhum endpoint novo, nenhuma mudança de backend — fase 100% frontend,
  arquivos já listados em `<decisions>`.

</code_context>

<specifics>
## Specific Ideas

Nenhuma referência visual nova — `03-UI-SPEC.md` já cobre o contrato de
design (cor, tipografia, espaçamento) pro que esta fase toca.

</specifics>

<deferred>
## Deferred Ideas

Nenhuma — discussão ficou dentro do escopo restrito (REV-02 parcial,
REV-03 parcial).

</deferred>

---

*Phase: 03-revisão-acessível-e-consistente*
*Context gathered: 2026-08-16*
