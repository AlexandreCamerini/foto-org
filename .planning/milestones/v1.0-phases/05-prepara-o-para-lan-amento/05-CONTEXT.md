# Phase 5: Preparação para lançamento - Context

**Gathered:** 2026-08-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Fechar os 4 pré-requisitos de lançamento (LANC-01 a LANC-04) que faltam
para entregar o app a um primeiro usuário real fora da máquina do
desenvolvedor: empacotamento distribuível, performance de navegação sem
table scan, um caminho de primeira execução testado, e um baseline de
performance medido e documentado. Sem dependência estrutural das fases
1-4 (pode rodar em paralelo), mas roda depois porque é onde o roadmap
está agora.

</domain>

<decisions>
## Implementation Decisions

### LANC-01 — Empacotamento (Marco 1 apenas)
- **D-01:** Escopo desta fase é só o Marco 1 de `docs/EMPACOTAMENTO.md`
  (`.app` funcional sem assinatura, uso pessoal). Marco 2 (assinado +
  notarizado) fica fora — exige certificado Developer ID e aprovação do
  custo recorrente do Apple Developer Program (US$99/ano), que
  `PROJECT.md` § Constraints trava como decisão do dono, não default.
  Não pedir esse custo nesta fase.
- **D-02:** O scaffold Tauri v2 já existe no repo (`src-tauri/`, commits
  `5a797e1` "scaffold Tauri v2 + runtime PBS + docs (Marco 1)" e `30ba735`
  "watchdog anti-órfão, glob de resources e ícones do build") mas nunca
  foi verificado contra o critério de aceite do Marco 1 documentado em
  `docs/EMPACOTAMENTO.md` § Marcos: abrir num catálogo novo, escanear
  fixtures, ver a grade; ao fechar, nenhum processo Python órfão (`ps` /
  `~/.claude/scripts/portas.py`). O trabalho desta fase é **verificar**
  esse critério, não construir do zero.
- **D-03:** Se a verificação achar um bug real no caminho crítico
  (processo órfão, crash ao abrir, falha ao servir o webapp) — corrigir
  dentro desta fase, mesmo que não estivesse no plano original. Não
  documentar-e-adiar um defeito que bloqueia o próprio critério de
  aceite do Marco 1.

### LANC-03 — Onboarding do primeiro acervo (validar, não redesenhar)
- **D-04:** A Fase 4 (plano `04-06`, commit `d0c3839`) já entregou boa
  parte do caminho: botão "Adicionar pasta…" nos 3 estados vazios
  (`Panorama.tsx`, `PhotoGrid.tsx`, `Trips.tsx`), todos abrindo o modal
  compartilhado `ModalCaminho.tsx` (extraído nessa mesma fase) com
  progresso de scan e erro surfaced. Esta fase **valida** esse caminho
  com um teste de usuário genuinamente sem instrução, não desenha um
  fluxo novo nem um wizard multi-etapa.
- **D-05:** Explicitamente fora de escopo: mensagem/texto específico
  para "primeira vez" (distinguir de estado vazio genérico) e feedback
  de progresso mais rico (contagem de arquivos, tempo estimado) além do
  que já existe. Se a validação revelar que esses realmente bloqueiam um
  usuário novo, viram achado a ser decidido, não trabalho pré-aprovado.
- **D-06:** Critério de sucesso de LANC-03 (do ROADMAP.md) continua:
  "Um usuário de primeira vez consegue adicionar sua primeira fonte/pasta
  e chegar a uma grade populada sem ler documentação" — a verificação
  precisa ser um teste real desse caminho, não uma inspeção de código.

### LANC-04 — Baseline de performance (acervo real, não fixture)
- **D-07:** Medir contra o acervo real de produção, não uma fixture
  sintética. `catalog.db` foi zerado em 2026-08-16 (backup em
  `catalog-antes-do-reset-20260816-013503.db`) e ainda não rodou uma
  varredura completa nova — essa rescan é a própria oportunidade de
  medir a baseline, não um passo separado.
- **D-08:** Métricas: taxa de indexação (varredura), tempo de geração de
  sugestões, tempo de detecção de duplicatas — as três citadas em
  LANC-04 no ROADMAP.md. Medir contra o volume real (histórico de
  auditoria chegou a ~422.738 registros de catálogo; ~99 mil registros
  conhecidos de acervo real, ver `PROJECT.md` § Context).
- **D-09:** Registrar os números em `docs/PERFORMANCE.md`, documento
  novo, no mesmo padrão de `docs/AVALIACAO_UX.md` — vira a referência
  canônica para medir regressão de performance em fases futuras (não
  anexar como texto solto em `REQUIREMENTS.md`).

### LANC-02 — Índices de FK ausentes (sem área cinzenta — técnico)
- **D-10:** Sem decisão de produto a capturar aqui. `docs/PLANO_IA_E_PRODUTO.md`
  §6 item 3 já resume "8 índices, migração de 2 linhas";
  `.planning/codebase/CONCERNS.md` já identifica o caso concreto mais
  urgente: `MediaFile.pasta` sem índice, usado em `LIKE 'prefixo%'` tanto
  no filtro de mídia quanto em `/api/pastas` (árvore de pastas clicada a
  cada nível). Índices em `trip_id`/`event_id`/`papel`/`arquivo_offline`
  já existem, mesmo padrão a seguir. Cabe ao pesquisador/planejador
  enumerar a lista completa a partir do modelo (`fotoorganizer/models/catalog.py`),
  não ao dono decidir.

### Claude's Discretion
- Ordem de execução dos 4 LANC dentro da fase (podem ser waves paralelas
  ou sequenciais — nenhuma dependência estrutural entre eles foi
  levantada na discussão).
- Formato exato do `docs/PERFORMANCE.md` (tabelas, gráficos, ou só
  números com contexto) — seguir o padrão que `docs/AVALIACAO_UX.md` já
  estabelece no repo.
- Se a rescan do acervo real (LANC-04) for lenta o suficiente para
  travar o fluxo de trabalho da fase, decidir se roda em background
  enquanto LANC-01/02/03 avançam, ou se bloqueia — nenhuma preferência
  do dono foi expressa sobre paralelismo interno da fase.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Empacotamento (LANC-01)
- `docs/EMPACOTAMENTO.md` — plano completo de empacotamento Tauri v2 +
  python-build-standalone, incluindo os critérios de aceite exatos do
  Marco 1 e Marco 2, passo-a-passo de build, e contingências documentadas
  (guard de origem, catálogo/cache, exiftool como dependência opcional)
- `docs/PLANO_IA_E_PRODUTO.md` §6 — tabela de pré-requisitos de
  lançamento (item 1: empacotamento; item 3: índices; item 4: onboarding;
  item 7: performance)
- `.planning/INGEST-CONFLICTS.md` — registra `docs/EMPACOTAMENTO.md` como
  decisão DOC-precedence aprovada para uso

### Índices e performance (LANC-02, LANC-04)
- `.planning/codebase/CONCERNS.md` § Performance Bottlenecks — o achado
  específico de `pasta` sem índice, com arquivos e linhas exatos
- `.planning/codebase/STACK.md` — stack completo (Python/TS/Rust), engine
  SQLAlchemy 2 + Alembic, plataforma alvo (macOS 12.0+)
- `.planning/PROJECT.md` § Context — composição real do acervo (~99 mil
  registros conhecidos, ~5% com pixel local alcançável, histórico de
  auditoria com ~422.738 registros) e § Constraints (limite de escala já
  medido, custo recorrente exige aprovação do dono)

### Onboarding (LANC-03)
- `.planning/phases/04-consist-ncia-visual-secund-ria/04-06-SUMMARY.md` —
  o que a Fase 4 já entregou (ModalCaminho extraído, 3 pontos de entrada
  wired, erro de scan surfaced sem fechar o modal)
- `webapp/src/components/ModalCaminho.tsx`, `Panorama.tsx`,
  `PhotoGrid.tsx`, `Trips.tsx` — os componentes já existentes que formam
  o caminho a validar

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src-tauri/` — projeto Tauri v2 completo (main.rs, tauri.conf.json,
  Entitlements.plist, capabilities/default.json), não construir do zero
- `scripts/empacotar_runtime.sh` e `scripts/assinar_runtime.sh` — já
  automatizam runtime PBS e assinatura de dylibs
- `ModalCaminho.tsx` — modal compartilhado de adicionar pasta/scan,
  reusar para qualquer ajuste de onboarding, não recriar
- `fotoorganizer/cli.py` `cmd_web` — já suporta `--porta 0` (porta
  efêmera) e anuncia `FOTOORG_READY` no stdout, usado pelo shell Tauri

### Established Patterns
- Índices existentes em `fotoorganizer/models/catalog.py` para
  `trip_id`/`event_id`/`papel`/`arquivo_offline` são o precedente a
  seguir para `pasta` — "índice quando o custo de escrita se justifica
  por um consumidor real e mensurável" (já documentado em comentário no
  próprio código, per CONCERNS.md)
- `docs/AVALIACAO_UX.md` é o padrão de documento de medição/achados a
  espelhar em `docs/PERFORMANCE.md`

### Integration Points
- Front (`webapp/src/api.ts`) usa só URLs relativas — o shell Tauri sobe
  o backend numa porta efêmera e a UI descobre sozinha; guard de origem
  local (`server/app.py`, `_HOSTS_LOCAIS`) já cobre isso, sem mudança
  necessária na arquitetura atual

</code_context>

<specifics>
## Specific Ideas

Nenhuma referência específica adicional além do que já está documentado
em `docs/EMPACOTAMENTO.md`, `docs/PLANO_IA_E_PRODUTO.md` e
`.planning/codebase/CONCERNS.md` — a discussão confirmou o caminho já
traçado nesses documentos em vez de introduzir ideias novas.

</specifics>

<deferred>
## Deferred Ideas

- **Marco 2 (assinatura + notarização)** — explicitamente adiado até o
  dono aprovar o custo do Apple Developer Program (US$99/ano). Quando
  aprovado, `docs/EMPACOTAMENTO.md` já documenta o passo-a-passo
  completo; não é trabalho de pesquisa nova, só execução.
- **Reconexão de volumes desmontados/iCloud (Lightroom + Apple Fotos,
  ~90 mil registros)** — mencionado em `PROJECT.md` § Context como
  candidato de maior alavancagem do backlog, mas fora do escopo desta
  fase e ainda sem decisão do dono; ver `docs/prompts/fase-12-alcance-e-tempo.md`
  e `REQUIREMENTS.md` v2.
- **Mensagem específica de "primeira vez" e feedback de progresso mais
  rico no onboarding** — não pré-aprovado nesta discussão; só entra se a
  validação de LANC-03 revelar que bloqueiam um usuário novo de verdade.

</deferred>

---

*Phase: 5-Preparação para lançamento*
*Context gathered: 2026-08-17*
