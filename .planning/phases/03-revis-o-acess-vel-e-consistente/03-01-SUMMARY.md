---
phase: 03-revis-o-acess-vel-e-consistente
plan: 01
subsystem: ui
tags: [react, vitest, testing-library, webapp, navegacao]

# Dependency graph
requires:
  - phase: 02-corre-o-de-dados-medidos
    provides: baseline verde do webapp (App.tsx, App.test.tsx) sem regressão pendente
provides:
  - "5/5 pontos de entrada de navegação da Biblioteca limpam a busca de texto (REV-03 fechado)"
  - "4 testes de regressão para os 3 pontos restantes + guarda da aba já ativa"
affects: [03-revis-o-acess-vel-e-consistente]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "setBusca(\"\") inserido em todo handler de navegação que troca o
      conjunto visível na Biblioteca — padrão já estabelecido em
      Panorama.aoRecortar/Trips.onAbrir, agora nos 5/5 pontos"

key-files:
  created: []
  modified:
    - webapp/src/App.tsx
    - webapp/src/App.test.tsx

key-decisions:
  - "Botão de troca de aba só limpa a busca quando nome !== aba: reclicar a
    aba já ativa é no-op e não pode apagar o que o usuário acabou de
    digitar (decisão de Claude's Discretion do CONTEXT.md, travada por
    teste)"
  - "Teste de onSelecionarPasta precisa navegar um nível na árvore antes de
    clicar 'ver na grade' — o botão é gated por estado local `aberta` de
    ArvoreDePastas (inicializado a partir de pastaAtual, null no mount),
    não pela presença de `caminho` na fixture de /api/pastas; a instrução
    original do plano assumia visibilidade imediata, corrigido por leitura
    do código-fonte (ArvoreDePastas.tsx:31,73) e confirmado contra o
    mesmo contrato já testado em ArvoreDePastas.test.tsx"

patterns-established:
  - "setBusca(\"\") em qualquer novo ponto de entrada de navegação futuro
    deve seguir o mesmo padrão: inserido junto dos outros resets de estado
    do handler, sem estado/import/prop novos"

requirements-completed: [REV-03]

# Metrics
duration: ~35min
completed: 2026-08-16
---

# Phase 3 Plan 01: Busca não sobrevive à navegação (REV-03) Summary

**Os 3 pontos de entrada restantes (botão de troca de aba, `Sidebar.onSelecionarPasta`, `StatusBar.aoIrPara`) agora chamam `setBusca("")`, fechando REV-03 com 5/5 pontos cobertos e 4 testes de regressão novos.**

## Performance

- **Duration:** ~35 min
- **Tasks:** 2/2 completed
- **Files modified:** 2

## Accomplishments
- REV-03 fechado: `webapp/src/App.tsx` limpa a busca em todos os 5 pontos
  de entrada de navegação da Biblioteca (2 pré-existentes + 3 novos).
- Guarda de UX travada por teste: reclicar a aba já ativa preserva a
  busca que o usuário acabou de digitar.
- Suíte inteira do webapp verde (124/124, 15 arquivos de teste),
  `tsc -b` sem diagnóstico, zero dependência nova.
- `scripts/verificar.sh --rapido` confirma que o motor Python (843 testes)
  e o benchmark de agrupamento (19/19) continuam no baseline — fase é
  100% frontend, sem regressão no core.

## Task Commits

Each task was committed atomically (TDD RED → GREEN):

1. **Task 1: Testes de regressão dos 3 pontos de busca (RED)** - `e8be38a` (test)
2. **Task 2: setBusca("") nos 3 pontos de navegação (GREEN)** - `4c5e776` (feat)

**Plan metadata:** (pending — final metadata commit deferred to orchestrator per multi-agent wave protocol)

## Files Created/Modified
- `webapp/src/App.tsx` - `setBusca("")` inserido no botão de troca de aba
  (condicionado a `nome !== aba`), em `onSelecionarPasta` (ao lado de
  `setSelIndex(null)`) e em `aoIrPara` (junto de `setRecorte(null)`/
  `setFonte(null)`)
- `webapp/src/App.test.tsx` - 4 testes novos (`it(...)`): botão de aba,
  `onSelecionarPasta` via "ver na grade", `aoIrPara` via degrau
  "conhecidas" do funil, e guarda da aba já ativa; comentário adicionado
  ao teste pré-existente de Viagens registrando que ele deixou de isolar
  só `Trips.onAbrir`

## Decisions Made
- **Botão de aba condicional (`nome !== aba`):** resolve o item de
  discretion do CONTEXT.md — trocar de aba de fato sempre limpa a busca;
  reclicar a aba ativa é no-op e não limpa. Travado pelo teste "clicar na
  aba já ativa não apaga a busca recém-digitada".
- **Fixture do Teste 2 exige navegação de um nível:** o plano assumia que
  uma fixture de `/api/pastas` com `caminho` não vazio já revelava o
  botão "ver na grade" no mount. Leitura de `ArvoreDePastas.tsx:31,73`
  mostrou que a visibilidade do botão depende do estado local `aberta`
  (inicializado a partir da prop `pastaAtual`, que é `null` no primeiro
  mount da Biblioteca — `App.tsx` só define `pasta` depois que o próprio
  callback dispara), não do campo `caminho` da resposta da API. O teste
  foi escrito clicando primeiro no filho "photo" (mesmo contrato já
  provado em `ArvoreDePastas.test.tsx`, teste "navegar não filtra a grade
  — só o botão explícito filtra") para então revelar e clicar "ver na
  grade". Confirmado empiricamente: as 3 falhas do RED reportam
  exatamente `received "IMG"` (busca sobrevivente), não erro de elemento
  não encontrado — a asserção certa falhando pelo motivo certo.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug in plan's test design] Corrigida a sequência de interação do Teste 2 (`onSelecionarPasta`)**
- **Found during:** Task 1 (RED)
- **Issue:** O plano instruía fixture de `/api/pastas` com `caminho` não
  vazio bastando para o botão "ver na grade" aparecer de imediato após
  mount. Leitura do código-fonte de `ArvoreDePastas.tsx` mostrou que a
  visibilidade do botão depende do estado local `aberta`
  (`useState(pastaAtual)`), que é `null` no primeiro mount da Biblioteca
  — a fixture por si só não altera esse estado.
- **Fix:** Teste 2 passou a clicar no filho "photo" da árvore (setando
  `aberta`) antes de clicar "ver na grade", replicando o fluxo já provado
  em `ArvoreDePastas.test.tsx`. Nenhuma mudança de escopo — mesmo
  contrato de saída (`onSelecionarPasta` chamado, busca limpa), só a
  sequência de cliques do teste corrigida.
- **Files modified:** `webapp/src/App.test.tsx`
- **Verification:** RED reporta a falha esperada (`received "IMG"`), não
  "elemento não encontrado"; GREEN (Task 2) faz o teste passar.
- **Committed in:** `e8be38a` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — correção de suposição
incorreta no design do teste do plano, sem mudança de escopo ou
comportamento).
**Impact on plan:** Nenhum. Contrato de saída idêntico ao especificado;
só a sequência de interação do teste foi corrigida contra o comportamento
real do componente já existente.

## Issues Encountered
None além do deviation acima.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
REV-03 está 100% fechado (5/5 pontos). REV-02 (`texto-3`→`texto-2` em
Review/Inspector/Operations) é o plano irmão 03-02, executado em paralelo
em worktree separado, sem overlap de arquivos com este plano. Nenhum
bloqueio identificado para o fechamento da Fase 3.

---
*Phase: 03-revis-o-acess-vel-e-consistente*
*Completed: 2026-08-16*

## Self-Check: PASSED

- FOUND: webapp/src/App.tsx
- FOUND: webapp/src/App.test.tsx
- FOUND: .planning/phases/03-revis-o-acess-vel-e-consistente/03-01-SUMMARY.md
- FOUND: e8be38a (test commit, Task 1)
- FOUND: 4c5e776 (feat commit, Task 2)
- FOUND: c01634e (SUMMARY.md commit)
