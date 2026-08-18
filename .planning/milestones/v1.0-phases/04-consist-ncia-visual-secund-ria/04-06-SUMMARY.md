---
phase: 04-consist-ncia-visual-secund-ria
plan: 06
subsystem: ui
tags: [react, typescript, tailwind, vitest, modal, empty-state]

# Dependency graph
requires:
  - phase: 04-consist-ncia-visual-secund-ria
    provides: 04-UI-SPEC.md contract (Dependencies/Blocks Planning item 2) locking one shared modal, reachable from four screens
provides:
  - ModalCaminho extracted to its own module (webapp/src/components/ModalCaminho.tsx), export default, optional `erro` prop
  - App.tsx owns the "Adicionar pasta…" modal state (modalPasta/erroPasta) and distributes onAdicionarPasta by prop, same pattern as useJob
  - Sidebar no longer owns the pasta modal — dispatches via onAdicionarPasta callback, narrowed local state to "takeout" | "apple" | null
  - Panorama, PhotoGrid and Trips empty states each render the same "Adicionar pasta…" button (Botao defaults: contorno/md, no cheio), original diagnostic phrases untouched
  - POST /api/scan failure surfaces inside the modal via `erro` prop; modal stays open instead of swallowing the failure
  - Integration tests in App.test.tsx proving all four entry points resolve to the same modal, and the error path
affects: [04-07, future phases touching Sidebar/App.tsx modal ownership or empty-state patterns]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Shared modal ownership lifted to App.tsx and distributed by prop to N siblings — same pattern already proven by useJob (one owner in App, prop distribution), no new context/store introduced for 4 consumers"
    - "Modal error state (erro prop) lives with the modal, not with the trigger — because the trigger multiplied to 4 call sites and only one (App) can own it"

key-files:
  created:
    - webapp/src/components/ModalCaminho.tsx
  modified:
    - webapp/src/components/Sidebar.tsx
    - webapp/src/App.tsx
    - webapp/src/components/Panorama.tsx
    - webapp/src/components/PhotoGrid.tsx
    - webapp/src/components/Trips.tsx
    - webapp/src/App.test.tsx
    - webapp/src/components/Sidebar.test.tsx
    - webapp/src/components/Trips.test.tsx

key-decisions:
  - "Modal ownership moved to App.tsx (not React context/store) — only 4 consumers, and the project has zero precedent for either pattern; useJob's App-owns/prop-distributes precedent was reused as-is"
  - "Error from POST /api/scan renders inside ModalCaminho via new optional `erro` prop, not in Sidebar's old inline error line — the disparo no longer always originates from Sidebar, so the old location stopped covering the case that matters most (pasta)"
  - "Button sizing in empty states: Botao defaults (contorno/md, no cheio) — cheio existed in Sidebar because that button fills a narrow fixed column; a centered empty-state button with cheio would render as a window-wide bar"

requirements-completed: [CONS-05]

# Metrics
duration: 65min
completed: 2026-08-17
---

# Phase 4 Plan 06: Botão "Adicionar pasta…" nos três estados vazios Summary

**ModalCaminho extraído para módulo próprio e sua posse movida de `Sidebar.tsx` (estado privado) para `App.tsx` (dono único, distribuído por prop aos quatro pontos que precisam dele — Sidebar e os três estados vazios), fechando CONS-05/D-07 com erro de scan visível no próprio modal.**

## Performance

- **Duration:** ~65 min
- **Started:** 2026-08-17T11:32:46-03:00 (first task commit)
- **Completed:** 2026-08-17T12:36:35-03:00 (last task commit)
- **Tasks:** 3/3
- **Files modified:** 9 (1 created, 8 modified)

## Accomplishments
- `ModalCaminho` deixou de ser uma função privada dentro de `Sidebar.tsx` — agora é um módulo próprio (`webapp/src/components/ModalCaminho.tsx`), reusável e com um `erro?: string | null` opcional que renderiza a falha do servidor acima dos botões.
- O modal de "Adicionar pasta…" pertence ao `App.tsx`, o único componente que alcança as quatro telas que precisam dele (Sidebar, Panorama, PhotoGrid, Trips) — mesmo padrão já provado pelo `useJob` (um dono, prop distribuída).
- Os três estados vazios (Panorama, PhotoGrid, Trips) ganharam o botão "Adicionar pasta…", com as frases diagnósticas originais intactas — inclusive a do Trips, que fala de gerar sugestões enquanto o botão adiciona pasta (deliberado, D-07 trava a mesma ação nas três telas).
- Falha do `POST /api/scan` aparece dentro do modal (que permanece aberto) em vez de ser engolida — o `.catch` de `job.escanear` escreve em `erroPasta`, repassado ao modal.
- Testes de integração em `App.test.tsx` provam os quatro pontos de entrada resolvendo para o mesmo modal (mesmo título "Caminho da pasta de fotos") e o caminho de erro.

## Task Commits

Each task was committed atomically:

1. **Task 1: Extrair ModalCaminho e mover a posse do modal "pasta" para o App** - `bd5d704` (refactor)
2. **Task 2: Botão "Adicionar pasta…" nos três estados vazios** - `7179860` (feat)
3. **Task 3: Teste de que os quatro pontos abrem o mesmo modal e disparam o mesmo scan** - `7185d28` (test)

_Nenhum commit de metadados do plano separado — SUMMARY.md commitado junto com REQUIREMENTS.md em worktree mode; STATE.md/ROADMAP.md ficam com o orquestrador._

## Files Created/Modified
- `webapp/src/components/ModalCaminho.tsx` - Modal de caminho compartilhado, `export default`, prop `erro` opcional
- `webapp/src/components/Sidebar.tsx` - Importa `ModalCaminho`; estado local estreitado para `"takeout" | "apple" | null`; botão "Adicionar pasta…" dispara `onAdicionarPasta` (nova prop)
- `webapp/src/App.tsx` - Dono de `modalPasta`/`erroPasta`; `abrirAdicionarPasta` distribuída para Sidebar/Panorama/PhotoGrid/Trips; renderiza `ModalCaminho` junto do `Loupe` no fim do componente; `.catch` de `job.escanear` popula `erroPasta`
- `webapp/src/components/Panorama.tsx` - Prop `onAdicionarPasta`; botão no estado `data.total === 0`
- `webapp/src/components/PhotoGrid.tsx` - Prop `onAdicionarPasta`; botão no estado `total === 0`
- `webapp/src/components/Trips.tsx` - Prop `onAdicionarPasta`; botão no bloco `{vazio && ...}` (independente do selo de CONS-02 já presente ali)
- `webapp/src/App.test.tsx` - 5 novos testes de integração: Panorama vazio → modal → POST /api/scan; mesmo modal pelo botão da Sidebar na Biblioteca; grade vazia da Biblioteca com o botão; Trips vazio com o botão; erro do POST mantém o modal aberto com a mensagem
- `webapp/src/components/Sidebar.test.tsx` - `onAdicionarPasta` acrescentada às 6 montagens existentes
- `webapp/src/components/Trips.test.tsx` - Teste de catálogo vazio estendido com a asserção do botão (clique dispara `onAdicionarPasta`)

## Decisions Made
- Ownership do modal movida para `App.tsx`, reusando o padrão já provado do `useJob` (D-07/UI-SPEC deixava o mecanismo a critério do plano — ver `key-decisions` do frontmatter).
- Erro do scan migrou para dentro do modal (prop `erro`), não mais para a linha da Sidebar — a Sidebar deixou de ser o único disparador.
- Botão dos três estados vazios usa os defaults do `Botao` (contorno/md, sem `cheio`) — decisão explicitamente delegada ao plano pelo Pattern Map, já que nenhum documento anterior tinha travado o dimensionamento.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `Trips.test.tsx` precisou da prop `onAdicionarPasta` em todas as 13 montagens para manter `tsc -b` verde**
- **Found during:** Task 2 (botão nos três estados vazios)
- **Issue:** `Trips` ganhou uma prop obrigatória nova (`onAdicionarPasta`); `tsconfig.app.json` inclui `src` inteiro (sem exclude de `*.test.tsx`), então `tsc -b` falhava com `TS2741` nas 13 montagens de `<Trips ... />` em `Trips.test.tsx` que ainda não passavam a prop.
- **Fix:** Acrescentado `onAdicionarPasta={vi.fn()}` a todas as montagens de `Trips.test.tsx` (via replace_all nos dois padrões existentes, `onAbrir={vi.fn()}` e `onAbrir={onAbrir}`), desbloqueando o build antes da Task 2 ser considerada completa. A asserção real do botão (clique → callback) ficou para a Task 3, como o plano já previa.
- **Files modified:** `webapp/src/components/Trips.test.tsx`
- **Verification:** `npx tsc -b` voltou a sair com código 0; `npx vitest run src/components/Trips.test.tsx` — 14/14 passaram.
- **Committed in:** `7179860` (parte do commit da Task 2)

---

**Total deviations:** 1 auto-fixed (1 blocking/Rule 3)
**Impact on plan:** Correção mecânica e prevista pelo próprio plano ("Task 3 vira teste de App.test.tsx na ponta a ponta" — a asserção de comportamento ficou onde o plano já mandava; só a assinatura de tipo precisou ser corrigida uma task antes). Sem escopo adicional.

## Issues Encountered

- **04-PATTERNS.md não existia neste worktree.** O plano referencia linhas específicas desse arquivo (seções Sidebar.tsx/dimensionamento de botão) nos blocos `<read_first>`, mas o arquivo era untracked no checkout principal do orquestrador e não fazia parte do commit-base compartilhado com worktrees. Resolvido lendo diretamente os arquivos-fonte que o Pattern Map teria resumido (`Sidebar.tsx`, `App.tsx`, `useJob.ts`, `Botao.tsx`) — o `<action>` de cada task já continha instrução suficientemente detalhada para não depender do resumo.
- **Worktree HEAD divergia da base esperada no início da execução.** `git merge-base HEAD 383af2f9...` não batia com a base esperada (branch apontava para um commit muito mais antigo, não relacionado à Fase 4). Corrigido com `git reset --hard 383af2f9...` conforme o protocolo `<worktree_branch_check>` — working tree estava limpo antes do reset, nenhum trabalho perdido.
- **`webapp/node_modules` ausente no worktree** (nota de memória confirmada: worktree precisa de `node_modules` próprio, symlink quebraria `tsc -b`). Resolvido com `npm ci` dentro de `webapp/` no início da execução.
- **`scripts/verificar.sh` não rodado por completo** — exige `.venv/bin/python` (pytest + benchmark de agrupamento), ausente neste worktree e fora do escopo deste plano (todos os `files_modified` são `webapp/*`, nenhum arquivo Python tocado). Rodei o equivalente completo do lado webapp em vez disso: `npx tsc -b`, `npm test` (148/148 testes, 17 arquivos) e `npm run build`, que cobrem os itens [3/4] e [4/4] do script — os únicos que este plano poderia afetar.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- CONS-05 fechado: os três estados vazios oferecem a mesma ação, o modal tem um dono único, e a falha de scan é visível em vez de engolida.
- `ModalCaminho.tsx` fica disponível como precedente de "extrair modal para módulo próprio + posse no App" para qualquer futuro consumo adicional (nenhum outro achado da Fase 4 depende disso hoje).
- Plano 04-07 roda em paralelo, em worktree separado, sem tocar nos arquivos deste plano (`files_modified` não se sobrepõem).
- Nenhum bloqueio conhecido para o merge deste worktree de volta à branch principal da Fase 4.

## Self-Check: PASSED

- `[ -f webapp/src/components/ModalCaminho.tsx ]` → FOUND
- `git log --oneline --all | grep -q bd5d704` → FOUND
- `git log --oneline --all | grep -q 7179860` → FOUND
- `git log --oneline --all | grep -q 7185d28` → FOUND
- Todos os `<acceptance_criteria>` das 3 tasks re-executados e verdes (grep counts e `tsc -b`/`vitest`/`npm run build` reportados acima)
- `<verification>` do plano: checks 2 e 3 (grep de rótulo/título únicos) verdes; `scripts/verificar.sh` não roda por completo neste worktree (sem `.venv`, fora do escopo Python) — substituído pelo equivalente webapp completo (`tsc -b` + `npm test` 148/148 + `npm run build`), que é o que este plano poderia quebrar

---
*Phase: 04-consist-ncia-visual-secund-ria*
*Completed: 2026-08-17*
