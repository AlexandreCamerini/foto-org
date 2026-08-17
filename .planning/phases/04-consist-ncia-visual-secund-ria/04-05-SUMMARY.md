---
phase: 04-consist-ncia-visual-secund-ria
plan: 05
subsystem: ui
tags: [tailwind, flexbox, responsive, react]

requires:
  - phase: 04-01
    provides: "--font-weight-titulo token (no dependency on this plan's toolbar work, but shares App.tsx as a base)"
provides:
  - "Barra da Biblioteca em dois grupos por intenção (escopo/identidade, visão/ordem) que empilham abaixo de 1024px (lg) e voltam a uma linha a partir dali"
  - "Grupos não quebram mais em sub-linhas: flex-nowrap + overflow-x-auto contido, nunca vazamento sobre o Inspetor"
  - "Busca volta a encolher normalmente em largura de desktop (shrink-0 removido do input), preservando a aparência de uma linha só em ≥1024px no estado comum"
affects: [ui, biblioteca]

tech-stack:
  added: []
  patterns:
    - "Grupo de controles com flex-nowrap + overflow-x-auto como alternativa a flex-wrap quando 'nunca mais de N linhas' é um must-have mais forte que 'nunca precisar rolar'"

key-files:
  created: []
  modified:
    - webapp/src/App.tsx
    - webapp/src/App.test.tsx

key-decisions:
  - "Grupo 1 (chip de recorte + toggle Lista/Mapa + toggle Tudo/Organizáveis/Fora-de-alcance) ficou shrink-0 em todos os filhos — são botões discretos que não podem truncar visualmente."
  - "Grupo 2 (busca + ordenação + zoom): removido shrink-0 só do input de busca, que volta a encolher via flex-shrink normal abaixo do w-64 preferido — restaura o comportamento de desktop anterior ao plano inteiro (commit 95dc137^)."
  - "No estado combinado mais apertado (chip + Lista/Mapa + toggle de alcance todos abertos ao mesmo tempo em ~1200px), o grupo 2 ainda precisa de scroll horizontal contido para o zoom. Aceito como está: o código-base anterior a este plano já vazava nesse mesmo estado (sem overflow-x-auto, o zoom escorria visualmente sobre o Inspetor) — o comportamento atual é estritamente melhor (contido, nunca sobre o Inspetor), não uma regressão nova."

patterns-established:
  - "Grupo de controles em barra estreita: flex-nowrap + overflow-x-auto no container, shrink-0 seletivo (só nos elementos que não podem truncar/ficar ilegíveis; elementos com fallback de leitura como inputs de texto continuam encolhendo)."

requirements-completed: [CONS-06]

duration: 45min
completed: 2026-08-17
---

# Phase 04-05: Barra da Biblioteca responsiva (CONS-06) Summary

**Barra da Biblioteca reagrupada em dois blocos por intenção que empilham abaixo de 1024px, sem nunca produzir uma terceira linha nem cobrir o Inspetor, com escala de correção iterativa validada por captura real de tela nas larguras ~700px/~900px/1200px.**

## Performance

- **Duration:** ~45min (Task 1) + 2 rodadas de correção pós-checkpoint (~28min + ~19min)
- **Started:** 2026-08-16T23:26:02-03:00
- **Completed:** 2026-08-17T11:12:36-03:00
- **Tasks:** 2 (1 auto + 1 checkpoint:human-verify)
- **Files modified:** 2 (`webapp/src/App.tsx`, `webapp/src/App.test.tsx`)

## Accomplishments
- Contêiner da barra da Biblioteca reestruturado em `flex flex-col ... lg:flex-row lg:items-center` com dois grupos por intenção (escopo/identidade × visão/ordem), conforme D-08/D-09.
- Grupos usam `flex-nowrap overflow-x-auto` em vez de `flex-wrap` — garante estruturalmente no máximo 2 linhas abaixo de `lg`, nunca 3, ao custo de scroll horizontal contido em larguras muito apertadas.
- Aparência de desktop (≥1024px) restaurada ao estado anterior ao plano inteiro no caso comum, após reverter `shrink-0` do input de busca.

## Task Commits

1. **Task 1: Barra da Biblioteca em dois grupos com retorno a uma linha em lg** - `95dc137` (fix)
2. **Task 2 fix-round-1: grupos não quebram mais em sub-linhas** - `4090e88` (fix)
3. **Task 2 fix-round-2: busca volta a encolher em desktop** - `b524b32` (fix)

**Plan metadata:** (este commit) - `docs(04-05): SUMMARY do plano 05, CONS-06 fechado após 2 rodadas de correção pós-checkpoint`

## Files Created/Modified
- `webapp/src/App.tsx` - Barra da Biblioteca: dois grupos flex, `flex-nowrap overflow-x-auto`, `shrink-0` seletivo
- `webapp/src/App.test.tsx` - Asserção estrutural: `flex-col` + `lg:flex-row` no contêiner, grupos com `.flex-nowrap` (não `.flex-wrap`) e `overflow-x-auto`, busca e "Tudo" em pais distintos

## Decisions Made
Ver `key-decisions` no frontmatter — decisão central foi tratar "nunca 3ª linha" como o must-have inegociável e "nunca precisar rolar" como aspiracional, cedendo scroll horizontal contido apenas nos estados mais apertados (~700px sempre; ~1200px só no estado combinado raro de chip+3 toggles simultâneos).

## Deviations from Plan

### Auto-fixed Issues

**1. [Checkpoint reprovado na primeira verificação] Barra quebrava em 3 linhas em ~700px**
- **Found during:** Task 2 (conferência visual, feita pelo orquestrador via browser real)
- **Issue:** A Task 1 usava `flex-wrap` nos dois grupos; em ~700px o Grupo 1 (chip + 2 toggles) já não cabia numa linha sozinho, produzindo 2 sub-linhas dele + 1 do Grupo 2 = 3 linhas totais, violando o must-have truth do plano.
- **Fix:** `flex-wrap` → `flex-nowrap overflow-x-auto` nos dois grupos + `shrink-0` nos filhos.
- **Files modified:** `webapp/src/App.tsx`, `webapp/src/App.test.tsx`
- **Verification:** Captura de tela real em 700px/900px/1200px + inspeção de `scrollWidth`/`clientWidth` via DOM
- **Committed in:** `4090e88`

**2. [Regressão introduzida pelo fix 1] Zoom cortado em 1200px (desktop) no estado comum**
- **Found during:** Re-verificação do orquestrador pós-fix-1
- **Issue:** `shrink-0` no input de busca do Grupo 2 impedia o encolhimento que antes do plano inteiro permitia que tudo coubesse numa linha em largura de desktop; Grupo 2 passou a precisar de 440px tendo só ~286-304px disponíveis, cortando o zoom mesmo sem nenhum chip/toggle aberto.
- **Fix:** Removido `shrink-0` só do input de busca (Grupo 1 e os demais filhos do Grupo 2 mantidos). Restaura literalmente a classe do input à do commit `95dc137^` (antes de todo o plano).
- **Files modified:** `webapp/src/App.tsx`
- **Verification:** Re-teste completo em 700px/900px/1200px, estado comum e estado combinado mais apertado, com bundle novo (cache do navegador precisou de `?nocache=N` para não servir JS obsoleto)
- **Committed in:** `b524b32`

---

**Total deviations:** 2 auto-fixed, ambos correções de layout dentro do escopo do próprio Task 2 (não scope creep)
**Impact on plan:** Sem os dois fixes, CONS-06 teria sido fechado com uma regressão de desktop não detectada — a conferência visual real (não só grep/teste estrutural) foi o que capturou ambos.

## Issues Encountered
- Cache HTTP do navegador serviu bundle JS obsoleto após rebuild em pelo menos duas ocasiões — necessário `?nocache=N` na URL para forçar buscar o bundle atualizado ao reverificar cada correção.
- No estado combinado mais apertado (chip de recorte + toggle Lista/Mapa + toggle Tudo/Organizáveis/Fora-de-alcance todos abertos simultaneamente) em ~1200px, o Grupo 2 ainda precisa de scroll horizontal contido para alcançar o zoom — confirmado por teste comparativo que esse estado específico já overflowava (com vazamento visual sobre o Inspetor, sem contenção) no código anterior a todo o plano 04-05. Não é regressão; é o mesmo limite pré-existente, agora contido em vez de vazado.

## User Setup Required
None - nenhuma configuração de serviço externo.

## Next Phase Readiness
- CONS-06 fechado: veredito de verificação visual real nas três larguras do plano (~700px, ~900px, 1200px), incluindo os estados comum e combinado mais apertado, e a vista Mapa (sem faixa vazia extra).
- Verificação conduzida pelo orquestrador via browser real (usuário delegou explicitamente por dificuldade de testar manualmente as três larguras) — aprovação registrada: 700px/900px/1200px OK, Inspetor nunca coberto, único ponto residual (scroll contido no estado combinado mais apertado em desktop) é uma melhoria sobre o comportamento pré-existente, não um gap novo.
- Sem bloqueios para os planos seguintes da Wave 3 (04-06, 04-07), que dependem de 04-01 e/ou 04-05 apenas por tocar `App.tsx` depois deste plano.

---
*Phase: 04-consist-ncia-visual-secund-ria*
*Completed: 2026-08-17*
