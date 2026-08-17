---
phase: 04-consist-ncia-visual-secund-ria
plan: 04
subsystem: ui
tags: [react, typescript, trips, badges, consistencia-visual]

# Dependency graph
requires:
  - phase: 04-01
    provides: token de peso de ênfase / convenções visuais da fase 04
provides:
  - Selo "Álbum" / "Evento detectado" no card da seção Eventos, visível só
    quando o nome colide com outro card da mesma seção
affects: [Trips.tsx, futuras fatias de CONS-* que tocam a família visual de badges do card]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Discriminador de seção explícito (secao: 'viagens' | 'eventos') em vez
      de derivar da string do título — título é texto de UI, discriminador é
      contrato"
    - "Colisão de nome computada localmente no componente que já tem o array
      completo (Secao), sem requisição nova nem campo novo de API"
    - "Selo informativo como <span> irmão do role=\"button\" do card, nunca
      filho — mesmo padrão já estabelecido pelo badge 'Mapa' para não vazar
      nome acessível"

key-files:
  created: []
  modified:
    - webapp/src/components/Trips.tsx
    - webapp/src/components/Trips.test.tsx

key-decisions:
  - "Selo lê Agrupamento.metodo (já tipado e servido pela API) — zero mudança
    de backend, confirmado por git diff --name-only não tocar api.ts nem
    server/app.py"
  - "Critério determinístico travado por D-03: LLM para decidir álbum vs.
    evento fica adiado (04-CONTEXT.md § Deferred), não implementado aqui"
  - "Família visual do badge 'Mapa' (border-borda, bg-janela/80,
    backdrop-blur-sm, text-texto-2), deliberadamente sem
    text-acento/border-acento — acento é reservado a seleção/foco/progresso/
    CTA (D-017)"

patterns-established:
  - "Placeholder `void prop;` para satisfazer noUnusedParameters/
    noUnusedLocals quando uma task de plumbing declara props que só a task
    seguinte consome — documentado inline, removido assim que a prop
    ganha uso real"

requirements-completed: [CONS-02]

# Metrics
duration: 25min
completed: 2026-08-17
---

# Phase 4 Plan 4: Selo Álbum/Evento Detectado Summary

**Cards da seção Eventos que colidem no nome ganham, cada um, um selo "Álbum" ou "Evento detectado" derivado de `Agrupamento.metodo` — zero mudança de backend, TDD com RED confirmado antes do GREEN.**

## Performance

- **Duration:** 25 min
- **Started:** 2026-08-17T23:15:00Z
- **Completed:** 2026-08-17T23:29:30Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- `Secao` ganhou o discriminador `secao: "viagens" | "eventos"` e computa
  localmente (sem requisição nova) o conjunto de nomes colidindo no array
  `itens` já buscado, comparação case-insensitive com `.trim().toLowerCase()`
- `Card` recebeu as props `secao`/`colideNome` e renderiza o selo no canto
  superior esquerdo (`left-2 top-2`, o direito já é do badge "Mapa"), visível
  só quando `secao === "eventos" && colideNome`
- Rótulo determinístico: `grupo.metodo === "album_externo" ? "Álbum" :
  "Evento detectado"` — sem lista de exceções, sem consultar mais nada
- 4 testes novos cobrindo os casos do `<behavior>`: colisão mostrando os dois
  rótulos, ausência de colisão sem selo, colisão em Viagens sem selo, colisão
  case-insensitive — ciclo RED confirmado (2 dos 4 falhando antes da
  implementação) antes do GREEN

## Task Commits

Cada task foi commitada atomicamente:

1. **Task 1: Secao computa colisão de nome e discrimina a seção** - `1da8cc6` (feat)
2. **Task 2 RED: testes do selo (ainda falhando)** - `4c4f985` (test)
3. **Task 2 GREEN: selo implementado** - `3eedea1` (feat)

_Nenhum REFACTOR commit — implementação já limpa na primeira passada GREEN._

**Plan metadata:** commit deste SUMMARY (a seguir)

## Files Created/Modified
- `webapp/src/components/Trips.tsx` - discriminador de seção, computação de
  colisão de nome em `Secao`, selo condicional em `Card`
- `webapp/src/components/Trips.test.tsx` - 4 testes novos cobrindo colisão em
  Eventos (com os dois rótulos), ausência de colisão, colisão em Viagens
  (sem selo) e colisão case-insensitive

## Decisions Made
- Nenhuma decisão nova além das já travadas em D-03 e 04-CONTEXT.md — plano
  seguido como escrito, incluindo a recusa explícita ao caminho de LLM

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Task 1 exigia `tsc -b` verde com props declaradas mas não
lidas, o que colide com `noUnusedParameters`/`noUnusedLocals` do
`tsconfig.app.json`**
- **Found during:** Task 1 (verificação do critério de aceite `npx tsc -b`)
- **Issue:** O plano pede que `Card` declare `secao`/`colideNome` na
  assinatura sem renderizar nada com elas ainda (o selo é a Task 2), mas o
  projeto tem `noUnusedParameters: true` e `noUnusedLocals: true` — TS6133
  bloqueia o build com as props destructuradas e não lidas. Testei o
  convencional prefixo `_` (não isenta destructuring de objeto neste TS) e
  confirmei que só uma leitura real da variável satisfaz o checker.
- **Fix:** Adicionado `void secao; void colideNome;` no topo do corpo de
  `Card`, com comentário explicando que é placeholder até a task seguinte
  consumir as props de verdade. Removido na Task 2 assim que o selo passou a
  ler as duas props na JSX condicional.
- **Files modified:** `webapp/src/components/Trips.tsx`
- **Verification:** `npx tsc -b` sai com exit code 0 na Task 1; os 10 testes
  pré-existentes de `Trips.test.tsx` continuam verdes
- **Committed in:** `1da8cc6` (Task 1 commit)

**2. [Rule 1 - Bug] Comentário da Task 1 continha a string literal "Evento
detectado", inflando `grep -c 'Evento detectado'` de 1 (esperado pela
Task 2) para 2**
- **Found during:** Task 2 (verificação do critério de aceite
  `grep -c 'Evento detectado' webapp/src/components/Trips.tsx` retorna 1)
- **Issue:** O comentário explicativo da computação de colisão em `Secao`
  citava "Álbum/Evento detectado" por extenso, o que o grep do critério de
  aceite contava como uma segunda ocorrência
- **Fix:** Reescrito o comentário para "Selo de origem (CONS-02, D-03)" sem
  repetir o rótulo literal, preservando a explicação
- **Files modified:** `webapp/src/components/Trips.tsx`
- **Verification:** `grep -c 'Evento detectado' webapp/src/components/Trips.tsx`
  retorna 1; os 14 testes continuam verdes
- **Committed in:** `3eedea1` (Task 2 GREEN commit)

---

**Total deviations:** 2 auto-fixed (2 bugs de plano encontrados durante
verificação de critério de aceite)
**Impact on plan:** Ambos os ajustes são de nível "wording"/tooling, sem
mudança de comportamento nem de escopo. O selo final é idêntico ao markup
travado no UI-SPEC.

## Issues Encountered
- `webapp/node_modules` e `.venv` não existiam neste worktree (isolado do
  checkout principal) — `npm install` e a criação de `.venv` +
  `pip install -e ".[dev]"` foram necessários antes de rodar
  `scripts/verificar.sh` (item 5 do `<success_criteria>` do plano).
- `scripts/verificar.sh` reporta `pytest falhou` — 1 falha
  (`tests/test_apple_photos.py::test_video_entra_junto_com_a_foto`), 841
  passaram, 1 pulado. Causa: `ModuleNotFoundError: No module named
  'osxphotos'` — o pacote vive no extra opcional `apple` de `pyproject.toml`,
  que nem `scripts/instalar.sh` nem este plano instalam por padrão.
  Pré-existente e fora de escopo: este plano não toca nenhum arquivo Python
  (`files_modified` do frontmatter lista só `Trips.tsx`/`Trips.test.tsx`),
  e é a mesma falha, mesma causa raiz, já documentada em
  `04-01-SUMMARY.md` § Issues Encountered. Benchmark de agrupamento (19/19),
  testes da UI web (131/131) e build (`✓ built`) saem 100% verdes — os 3
  itens restantes de `scripts/verificar.sh` mais os 2 itens do
  `<verification>` do próprio plano.

## User Setup Required
None - no external service configuration required. Para rodar a suíte Python
completa incluindo os testes que tocam osxphotos: `pip install -e ".[apple]"`
— fora do escopo desta fatia.

## Next Phase Readiness
- CONS-02 fechado: `webapp/src/components/Trips.tsx` e
  `webapp/src/components/Trips.test.tsx` são os únicos arquivos tocados;
  `webapp/src/api.ts` e `fotoorganizer/server/app.py` continuam intocados
  (confirmado por `git diff --name-only`), provando que a fatia não precisou
  de backend
- Suite completa do webapp: 131 testes / 16 arquivos, todos verdes;
  `npm run build` sai com exit code 0
- `scripts/verificar.sh` verde exceto a falha pré-existente de `osxphotos`
  (ver "Issues Encountered"), que não bloqueia nenhum plano da Fase 4 — nenhum
  deles toca `fotoorganizer/sources/apple_photos.py` ou equivalente
- Nenhum bloqueio para os planos irmãos 04-02/04-03/04-05 (arquivos
  disjuntos) nem para o próximo plano da fase

---
*Phase: 04-consist-ncia-visual-secund-ria*
*Completed: 2026-08-17*
