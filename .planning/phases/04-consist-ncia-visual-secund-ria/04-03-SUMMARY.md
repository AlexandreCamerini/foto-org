---
phase: 04-consist-ncia-visual-secund-ria
plan: 03
subsystem: ui
tags: [react, vitest, testing-library, tailwind]

# Dependency graph
requires:
  - phase: 04-consist-ncia-visual-secund-ria
    provides: "04-01 — migração font-titulo (Loupe.tsx:38 já usava font-titulo antes desta plan) e tokens de tipografia/cor da 04-UI-SPEC.md"
provides:
  - "Estado de erro explícito (glifo ⊘ + duas frases) na prévia em tela cheia do Loupe, com reset ao navegar e zoom guardado"
  - "Subcomponente MembroFigura em Duplicates.tsx com estado de falha de prévia por membro, bg-cartao no erro e explicação completa via title"
affects: [04-04, 04-05, 04-06, 04-07]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Estado de erro de <img> via onError + useState local, reset no mesmo useEffect que já limpa outro estado de UI (Loupe: setZoom100/setFalhouPreview juntos no efeito de troca de índice)"
    - "Extração de subcomponente para dar useState por item de .map() (MembroFigura, mesma convenção de Trips.tsx Card)"

key-files:
  created:
    - webapp/src/components/Loupe.test.tsx
  modified:
    - webapp/src/components/Loupe.tsx
    - webapp/src/components/Duplicates.tsx
    - webapp/src/components/Duplicates.test.tsx

key-decisions:
  - "Segunda frase do Loupe mantida em uma única linha de JSX (não quebrada em duas) para bater com o grep de acceptance criteria que exige a frase completa numa linha de arquivo"
  - "Testes usam container.querySelector pelo src de api.previewUrl/thumbUrl para desambiguar entre o <img> principal e as miniaturas do rodapé/figcaption, que compartilham o mesmo alt"

patterns-established:
  - "MembroFigura: subcomponente por item de grid quando o item precisa de estado local — hook não roda dentro de .map()"

requirements-completed: [CONS-04]

# Metrics
duration: 20min
completed: 2026-08-16
---

# Phase 4 Plan 3: Estado de Erro de Prévia (Loupe/Duplicatas) Summary

**Loupe e Duplicatas ganham estado de erro explícito (glifo `⊘` + cópia travada no UI-SPEC) quando `api.previewUrl` falha, substituindo o ícone quebrado do browser (Loupe) e o retângulo preto (Duplicatas); `Duplicates.tsx` extrai `MembroFigura` para dar a cada membro do grid seu próprio estado de falha.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-08-16T23:10:00-03:00 (aprox., leitura de contexto)
- **Completed:** 2026-08-16T23:27:00-03:00
- **Tasks:** 2
- **Files modified:** 4 (1 criado, 3 modificados)

## Accomplishments
- Loupe: `<img>` principal troca para bloco de erro (`⊘` + duas frases da Copywriting Contract) no `onError`, reseta a cada troca de índice junto com `setZoom100(false)`, e o clique de zoom é guardado (`!falhouPreview && ...`)
- Duplicates: extraído `MembroFigura` do `.map()` da grade de comparação — cada membro tem `useState` próprio, o card de erro usa `bg-cartao` (não `bg-black`) com `title` carregando a explicação completa
- 5 testes novos em `Loupe.test.tsx` (arquivo criado) + 3 testes novos em `Duplicates.test.tsx` (8 no total, 5 pré-existentes intactos)
- Suite completa do webapp: 135/135 testes verdes em 17 arquivos; `npm run build` (tsc -b + vite build) sem erro

## Task Commits

Each task was committed atomically:

1. **Task 1: Estado de erro da prévia em tela cheia (Loupe)** - `21ce1b0` (feat)
2. **Task 2: Estado de erro por membro na comparação de Duplicatas** - `7539481` (feat)

**Plan metadata:** commit deste SUMMARY (a seguir)

_Note: sem separação RED/GREEN — as duas tasks já eram `tdd="true"` mas o texto do plano especifica teste+implementação juntos por task; cada commit contém o par código+teste verificado verde antes de commitar._

## Files Created/Modified
- `webapp/src/components/Loupe.tsx` - `falhouPreview` (useState), reset no `useEffect` de troca de índice, ramo condicional de erro no `<img>` principal, `onClick` de zoom guardado
- `webapp/src/components/Loupe.test.tsx` (novo) - 5 testes: prévia ok, erro com as duas frases + `⊘`, clique não alterna zoom no erro, reset ao navegar (rerender com índice diferente), cabeçalho/rodapé intocados no erro
- `webapp/src/components/Duplicates.tsx` - `MembroFigura` extraído do `.map()`, `falhouPreview` por instância, `bg-cartao text-texto-3` + `title` no card de erro
- `webapp/src/components/Duplicates.test.tsx` - 3 testes novos: erro isolado por membro (o outro `<img>` do grupo continua no documento), `title` com a explicação completa, `bg-cartao` em vez de `bg-black` no erro, `figcaption`/botão de papel continuam renderizando

## Decisions Made
- Segunda frase de erro do Loupe ("O arquivo pode ter sido movido...") mantida numa única linha de JSX — quebrá-la em duas linhas (mais legível no editor) faria o `grep -c` da acceptance criteria falhar, já que grep casa por linha
- Testes desambiguam `<img>` principal vs. miniatura/thumb via `container.querySelector` pelo `src` exato (`api.previewUrl`/`api.thumbUrl`), não por `alt` — `alt` é o mesmo nome do arquivo nos dois `<img>` (prévia e miniatura), então `getByAltText` lançava erro de múltiplos elementos

## Deviations from Plan

None - plan executado exatamente como escrito.

## Issues Encountered
- `webapp/node_modules` não existia neste worktree (cada worktree precisa da própria instalação — conhecido, ver memória do projeto). Rodei `npm install` dentro de `webapp/` antes de qualquer teste; não fez parte do diff commitado (gitignored).
- A verificação de plano nº 3 (`grep -rn '⊘' ... | grep -v test` deve mostrar 4 arquivos) na prática mostra 5: além de `Miniatura.tsx`, `Trips.tsx`, `Loupe.tsx`, `Duplicates.tsx`, também `Mapa.tsx:247` usa o glifo — mas essa ocorrência é de `b2ff5b6` ("mapa do lugar estimado"), um commit anterior a toda a Fase 4, para o estado vazio "nenhuma foto tem lugar" (não é a prévia 404 de CONS-04, é um empty-state diferente que já reusava o mesmo vocabulário). Não é uma regressão desta plan nem está no `files_modified` — documentado aqui em vez de "consertado" silenciosamente ou ignorado.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- CONS-04 fechado: as duas telas de prévia grande (Loupe, Duplicates) agora explicam a falha em vez de ficar mudas ou mostrar artefato de browser
- Faixa de miniaturas do rodapé do Loupe (`api.thumbUrl`) permanece fora de escopo, intocada, conforme delimitado pelo objective
- Sem bloqueios para 04-04/04-05/04-06/04-07 — este plano não tocou nenhum arquivo fora de `Loupe.tsx`/`Duplicates.tsx` e seus testes

## Self-Check: PASSED

- `[ -f webapp/src/components/Loupe.test.tsx ]` → existe
- `git log --oneline --all --grep="04-03"` → 2 commits (`21ce1b0`, `7539481`)
- Acceptance criteria de ambas as tasks re-executadas (greps + `npx vitest run`) → todas PASS
- `cd webapp && npm test -- --run` → 135/135 verde (17 arquivos)
- `cd webapp && npm run build` → exit 0
- `grep -rn '⊘' webapp/src/components --include='*.tsx' | grep -v '\.test\.'` → 5 arquivos (4 esperados pelo plano + `Mapa.tsx`, pré-existente e fora de escopo — ver "Issues Encountered")

---
*Phase: 04-consist-ncia-visual-secund-ria*
*Completed: 2026-08-16*
