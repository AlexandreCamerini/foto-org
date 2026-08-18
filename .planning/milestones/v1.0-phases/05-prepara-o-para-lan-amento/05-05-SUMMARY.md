---
phase: 05-prepara-o-para-lan-amento
plan: 05
subsystem: ui
tags: [tauri, react, tailwind, webkit, ux-testing, onboarding]

# Dependency graph
requires:
  - phase: 04-consist-ncia-visual-secund-ria
    provides: "ModalCaminho.tsx compartilhado + 4 pontos de entrada 'Adicionar pasta…' (plano 04-06)"
  - phase: 05-prepara-o-para-lan-amento
    provides: "05-03: .app empacotado (Marco 1) usado como artefato do teste de usuário"
provides:
  - "LANC-03 validado com teste de usuário real: achou um bloqueador genuíno, diagnosticado empiricamente e corrigido"
  - "docs/AVALIACAO_UX.md: rodada datada 2026-08-17 com causa raiz, fix e reverificação visual"
  - "Regressão em App.test.tsx travando a opacidade do backdrop do ModalCaminho"
affects: [onboarding, webapp-ui, lançamento]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Backdrop de modal fixed/inset-0 precisa de opacidade que realmente ocluí o conteúdo de trás (bg-black/95, mesmo valor de Loupe.tsx) — bg-black/60 não é suficiente quando o conteúdo atrás tem texto claro"
    - "Diagnóstico de defeito visual reportado por humano: screenshot real do app rodando antes de qualquer edição de código, nunca inferir causa só pela leitura do JSX/Tailwind"

key-files:
  created: []
  modified:
    - webapp/src/components/ModalCaminho.tsx
    - webapp/src/App.test.tsx
    - docs/AVALIACAO_UX.md

key-decisions:
  - "Bloqueador confirmado pelo dono ('travou ali, não passou desse ponto') foi corrigido dentro desta fase (mínimo, escopado ao backdrop do modal), conforme autorização explícita do resume — não ficou como achado documentado à espera de decisão"
  - "Fix verificado visualmente via Safari/WebKit (mesmo motor do WKWebView do Tauri no macOS) servindo webapp/dist reconstruído contra o backend Python direto, não via rebuild completo do .app (cargo tauri build falhou por faltar resources/runtime/**/* — runtime PBS não preparado neste worktree; rebuildar o runtime completo estava fora de escopo de uma verificação de CSS)"
  - "Seletor de pasta navegável (árvore de diretório) registrado como atrito não-bloqueador, já backlogado em outra sessão — não vira trabalho novo aqui (D-04/D-05)"

patterns-established:
  - "Regressão de defeito de CSS/opacidade não capturável por vitest/jsdom: trava a classe Tailwind do elemento como proxy do contrato visual, com comentário explicando a limitação"

requirements-completed: [LANC-03]

# Metrics
duration: ~76min (20:53–22:09, inclui sessão real de UAT fora deste agente)
completed: 2026-08-17
---

# Phase 5 Plan 5: Validação do onboarding de primeira execução (LANC-03) Summary

**Teste de usuário real revelou bloqueador genuíno no ModalCaminho (texto sobreposto por backdrop translúcido demais); diagnosticado por screenshot, corrigido com `bg-black/60` → `bg-black/95`, reverificado visualmente e travado por regressão em `App.test.tsx`.**

## Performance

- **Duration:** ~76 min de ponta a ponta (ambiente preparado às 20:53, última commit às 22:09) — inclui o tempo da sessão de UAT real conduzida fora deste agente
- **Started:** 2026-08-17T20:53:00-03:00 (aprox., preparo do ambiente na Task 1)
- **Completed:** 2026-08-17T22:09:36-03:00
- **Tasks:** 3/3 (Task 1 auto, Task 2 checkpoint:human-verify, Task 3 auto + fix autorizado pelo resume)
- **Files modified:** 3 (`ModalCaminho.tsx`, `App.test.tsx`, `docs/AVALIACAO_UX.md`)

## Accomplishments

- Critério 3 da Fase 5 (LANC-03/D-06) testado com um usuário real sem instrução, não com inspeção de código — e o resultado foi honesto: **não chegou** a uma grade populada nesta rodada.
- Bloqueador diagnosticado empiricamente (screenshot do `.app` empacotado rodando de verdade, antes de tocar em qualquer código) — não foi um "conserto por suposição a partir da leitura do JSX".
- Fix mínimo aplicado e reverificado visualmente (antes/depois), reusando um valor de opacidade já estabelecido no próprio código (`Loupe.tsx`).
- Achado de escopo maior (seletor de pasta navegável) separado corretamente do bug e registrado como não-bloqueador já backlogado — sem redesenhar o modal, conforme D-04/D-05.

## Task Commits

Commits desta continuação (a Task 1 original, ambiente descartável, não gerou commit — nenhum arquivo do repo foi alterado por ela):

1. **Task 2 (fix autorizado pelo bloqueador confirmado)** — `f820d1a` (fix): `ModalCaminho.tsx` backdrop `bg-black/60` → `bg-black/95`; regressão em `App.test.tsx`.
2. **Task 3: registrar a rodada e classificar os achados** — `4cf23a6` (docs): `docs/AVALIACAO_UX.md`.

_Nenhum commit de plan-metadata separado nesta entrega — STATE.md/ROADMAP.md ficam para o orquestrador após o merge (isolation="worktree" para o restante do fluxo, não para esta sessão de fix pontual)._

## Files Created/Modified

- `webapp/src/components/ModalCaminho.tsx` — backdrop do modal (`fixed inset-0 ... bg-black/95`, era `/60`), único ponto de mudança de código.
- `webapp/src/App.test.tsx` — novo teste de regressão (`describe("Adicionar pasta...")`) travando a classe do backdrop.
- `docs/AVALIACAO_UX.md` — nova seção `# Rodada de 2026-08-17 — teste de primeira execução (fase 5, LANC-03)`, prependada ao topo (arquivo é acumulativo, nenhuma linha anterior removida).

## Decisions Made

- **Corrigir, não só documentar.** O resume desta continuação autorizava explicitamente um fix mínimo se o bloqueador fosse confirmado pelo dono — e foi ("travou ali, não passou desse ponto"). Segui a mesma régua já usada em D-03 (LANC-01): defeito real no caminho crítico não fica documentado-e-adiado.
- **Diagnóstico visual antes de editar.** A leitura isolada de `ModalCaminho.tsx` não mostrava nada estruturalmente errado (sem z-index conflitante, sem espaçamento faltando) — o defeito só apareceu ao renderizar de verdade. Só depois de ver o screenshot real (texto do estado vazio do Panorama vazando através do modal) o fix ficou óbvio: opacidade do backdrop insuficiente, não um bug de layout.
- **Verificação via Safari em vez de rebuild completo do `.app`.** `cargo tauri build` falhou por faltar `resources/runtime/**/*` (o runtime Python empacotado não está presente neste worktree — é produzido por `scripts/empacotar_runtime.sh`, fora do escopo desta correção pontual de CSS). Como o webview do Tauri no macOS usa WKWebView (mesmo motor do Safari), servir `webapp/dist` reconstruído via o backend Python direto e abrir em Safari é uma reverificação visual equivalente, sem a complexidade/risco de montar o runtime completo só para confirmar uma mudança de opacidade Tailwind.
- **Não tocar em `Sidebar.tsx`.** Dois outros modais em `Sidebar.tsx` usam o mesmo padrão `bg-black/60` e teoricamente têm o mesmo risco estrutural — mas o defeito confirmado por este UAT foi especificamente no `ModalCaminho`, e o resume travava o fix "ONLY to the confirmed rendering defect". Registrado aqui para visibilidade, não corrigido: se um teste futuro confirmar o mesmo sintoma nesses modais, é o mesmo fix, com a mesma evidência a coletar antes.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug, autorizado explicitamente pelo resume] Backdrop translúcido demais no `ModalCaminho` causando sobreposição de texto**
- **Found during:** Task 2 (checkpoint:human-verify) — UAT real reportou bloqueador confirmado pelo dono
- **Issue:** `bg-black/60` no backdrop `fixed inset-0` do `ModalCaminho` não ocluía o conteúdo da tela por trás; o texto do estado vazio do Panorama e o botão "Adicionar pasta…" vazavam visualmente através do modal e se sobrepunham ao título/input, impedindo o testador de entender o que estava vendo — o único ponto onde ele travou e não avançou sozinho.
- **Fix:** `bg-black/60` → `bg-black/95` em `webapp/src/components/ModalCaminho.tsx`, mesmo valor já usado por `Loupe.tsx` para um backdrop que precisa ocluir por completo. Nenhum token de design alterado, nenhum outro componente tocado.
- **Files modified:** `webapp/src/components/ModalCaminho.tsx`, `webapp/src/App.test.tsx` (regressão)
- **Verification:** Screenshot real antes (bug visível, ghosting legível) e depois (ghosting imperceptível em visualização normal) via Safari/WebKit servindo `webapp/dist` reconstruído; `npm test` 151/151 verde (150 pré-existentes + 1 nova regressão).
- **Committed in:** `f820d1a`

---

**Total deviations:** 1 auto-fixed (Rule 1, explicitamente pré-autorizado pelo resume desta continuação por já ter confirmação direta do dono do produto de que o bloqueador era genuíno)
**Impact on plan:** Fix necessário para o próprio critério de aceite de LANC-03 (D-06) ser alcançável em rodadas futuras. Sem scope creep: não tocou no seletor de pasta navegável (achado separado, já backlogado) nem em qualquer outro componente.

## Issues Encountered

- `cargo tauri build` falhou (`resources/runtime/**/* path not found`) porque o runtime Python empacotado (`scripts/empacotar_runtime.sh`) não está presente neste worktree — não é um defeito do fix, é infraestrutura de empacotamento que pertence ao plano `05-03`, fora de escopo aqui. Contornado verificando o fix via Safari/WebKit direto contra o backend Python (mesmo motor de renderização, sem a complexidade do runtime PBS).
- `python3 -m fotoorganizer` do sistema não tinha as dependências do projeto instaladas (sem `.venv` próprio neste worktree, conforme já registrado na memória de fluxo de trabalho). Contornado reusando o `.venv` da raiz do repo (mesmas dependências instaladas) com `PYTHONPATH` apontando para este worktree, garantindo que o código executado era o do worktree com o fix, não o da raiz.

## Known Stubs

Nenhum. Este plano não introduziu UI nova nem dado mockado — só corrigiu um valor de opacidade Tailwind existente.

## Threat Flags

Nenhum. A mudança não introduz superfície nova: é um ajuste de opacidade CSS num modal já existente e já coberto pelo threat model do plano (T-05-40/T-05-41/T-05-42, ver `05-05-PLAN.md`).

## User Setup Required

None - nenhuma configuração de serviço externo.

## Next Phase Readiness

- **LANC-03 parcialmente fechado:** o bloqueador confirmado nesta rodada foi corrigido e reverificado visualmente por este agente, mas **não houve um reteste completo com um usuário real sem instrução após o fix** (a `docs/AVALIACAO_UX.md` registra essa recomendação explicitamente na seção "Recomendação"). Antes de marcar D-06 como definitivamente satisfeito, vale repetir a Task 2 (teste cego) uma vez com o fix em produção.
- **Achado 2 (seletor de pasta navegável)** continua como decisão pendente do dono, já em outra frente de trabalho — nenhuma ação necessária desta fase.
- Dois outros modais em `Sidebar.tsx` usam o mesmo `bg-black/60` original e não foram auditados nesta rodada (fora do escopo do bloqueador confirmado) — candidato a checagem rápida numa fase futura de UI, não urgente.

---
*Phase: 05-prepara-o-para-lan-amento*
*Completed: 2026-08-17*

## Self-Check: PASSED

- FOUND: `webapp/src/components/ModalCaminho.tsx`
- FOUND: `docs/AVALIACAO_UX.md`
- FOUND: `.planning/phases/05-prepara-o-para-lan-amento/05-05-SUMMARY.md`
- FOUND commit `f820d1a` (fix)
- FOUND commit `4cf23a6` (docs)
- Confirmed `bg-black/95` present in `ModalCaminho.tsx` (1 occurrence)
