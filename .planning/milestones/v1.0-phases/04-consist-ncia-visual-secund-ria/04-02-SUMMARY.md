---
phase: 04-consist-ncia-visual-secund-ria
plan: 02
subsystem: ui
tags: [react, tailwind, botao, tdd]

# Dependency graph
requires:
  - phase: 04-01
    provides: "font-titulo token e migração de peso de ênfase (CONS-08), base sobre a qual este plano continua a reconciliação visual da fase"
provides:
  - "Retomar (RetomarScan) e Gerar/atualizar sugestões (Review) migrados para o contorno padrão de Botao.tsx, sem override de cor (D-04/CONS-03)"
  - "Cancelar de cópia em andamento (Operations) neutro em repouso, vermelho só no hover — mesmo padrão de StatusBar.tsx (D-05/CONS-07)"
  - "3 testes de classificação de botão que travam a regressão (RetomarScan.test.tsx, Review.test.tsx, Operations.test.tsx)"
affects: [04-03, 04-04, 04-05]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Asserção de classificação de botão por token exato (className.split(' ') + toContain/not.toContain), não substring — evita falso positivo quando o hover legítimo (hover:border-acento, hover:text-erro) contém a mesma substring que o override proibido"

key-files:
  created: []
  modified:
    - webapp/src/components/RetomarScan.tsx
    - webapp/src/components/Review.tsx
    - webapp/src/components/Operations.tsx
    - webapp/src/components/RetomarScan.test.tsx
    - webapp/src/components/Review.test.tsx
    - webapp/src/components/Operations.test.tsx

key-decisions:
  - "Testes de classificação usam className.split(' ') + comparação de token exato, não .toContain em string bruta — a variante contorno default já contém 'hover:border-acento' (substring 'border-acento') e a mudança de Cancelar já contém 'hover:text-erro' (substring 'text-erro'), então checagem por substring geraria falso positivo/negativo dependendo do sentido da asserção"
  - "tsconfig.app.tsbuildinfo (artefato de build, regenerado por npm run build) foi revertido antes do commit — não está em files_modified do plano e não é código de tarefa"

requirements-completed: [CONS-03, CONS-07]

duration: ~25min
completed: 2026-08-17
---

# Phase 4 Plan 2: Hierarquia de botão importante e hover de Cancelar Summary

**"Retomar" e "Gerar/atualizar sugestões" caem no contorno padrão de `Botao.tsx` (zero `variante="solido"`/override de acento fora do único preenchido legítimo), e o "Cancelar" de cópia em andamento de Operações vira `variante="fantasma"` + `className="hover:text-erro"` — vermelho só na intenção, igual ao StatusBar.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-08-17T02:03:00Z (aprox.)
- **Completed:** 2026-08-17T02:28:03Z
- **Tasks:** 2 (ambas TDD)
- **Files modified:** 6 (3 fonte + 3 teste)

## Accomplishments

- Fechado D-04/CONS-03: o único botão preenchido (`variante="solido"`) que resta fora dos modais de confirmação (`Sidebar.tsx`) é "Copiar N arquivos" em `Operations.tsx` — a ação que de fato copia arquivo de verdade. `grep -rn 'variante="solido"' webapp/src --include='*.tsx' | grep -v '\.test\.'` retorna exatamente as 4 linhas esperadas (1 Operations + 3 Sidebar).
- Fechado D-05/CONS-07: "Cancelar" de cópia em andamento (`Operations.tsx`) usa o mesmo par `variante="fantasma"` + `hover:text-erro` que `StatusBar.tsx` já usava para cancelar o mesmo tipo de job — neutro em repouso, vermelho só na intenção.
- 3 testes novos travam a classificação (um por arquivo), escritos em TDD RED→GREEN: cada um falhou contra o código antigo antes da mudança de fonte, e passa depois.

## Task Commits

Cada task seguiu RED→GREEN (TDD), sem REFACTOR (diffs mínimos, sem limpeza necessária):

1. **Task 1: Retomar e Gerar sugestões migram para o contorno padrão**
   - RED: `e61201f` — `test(04-02): trava contorno padrão em Retomar e Gerar sugestões`
   - GREEN: `bba7117` — `feat(04-02): Retomar e Gerar sugestões migram para o contorno padrão`
2. **Task 2: Cancelar de cópia em andamento fica vermelho só no hover**
   - RED: `f4c1b02` — `test(04-02): trava Cancelar de cópia neutro em repouso, vermelho no hover`
   - GREEN: `97a68f6` — `feat(04-02): Cancelar de cópia fica vermelho só no hover`

**Plan metadata:** (este commit, a seguir)

## Files Created/Modified

- `webapp/src/components/RetomarScan.tsx` — remove `className="border-acento text-acento hover:bg-cartao"` do botão "Retomar"; cai no `contorno` default de `Botao.tsx`
- `webapp/src/components/Review.tsx` — remove `variante="solido"` do botão "Gerar/atualizar sugestões"; cai no `contorno` default
- `webapp/src/components/Operations.tsx` — troca `<Botao tom="erro">` por `<Botao variante="fantasma" className="hover:text-erro">` no "Cancelar" de cópia em andamento
- `webapp/src/components/RetomarScan.test.tsx` — teste de classificação: token exato sem `border-acento`/`text-acento`, com `border-borda`/`bg-cartao`/`text-texto`
- `webapp/src/components/Review.test.tsx` — teste de classificação: token exato sem `bg-acento`/`text-texto-invertido`, com `border-borda`/`bg-cartao`
- `webapp/src/components/Operations.test.tsx` — cenário novo `executando` (job rodando, `estado.tipo === "operacao"`): checa `hover:text-erro` presente, `bg-erro/10`/`border-erro/40` ausentes, clique chama `cancelar()` uma vez

## Decisions Made

- **Asserção por token exato, não substring.** A plan-level `<behavior>` da Task 1 dizia "className renderizado NÃO contém `border-acento`", mas a variante `contorno` default de `Botao.tsx` já inclui `hover:border-acento` (que contém a substring `border-acento` legitimamente). Uma checagem `.not.toContain("border-acento")` ingênua teria dado falso negativo mesmo com a mudança correta aplicada. Resolvido fazendo `className.split(" ")` e comparando tokens exatos — `"border-acento"` (token isolado, do override antigo) é diferente de `"hover:border-acento"` (token do default correto). O mesmo raciocínio já estava explícito no plano para a Task 2 (`hover:text-erro` contém `text-erro`); apliquei a mesma disciplina à Task 1 por consistência, já que o risco de falso positivo/negativo é idêntico.
- **`tsconfig.app.tsbuildinfo` revertido antes do commit final.** `npm run build` (parte da verificação do plano) regenera esse artefato de build, que por acaso está rastreado no git. Não está em `files_modified` do plano; revertido com `git checkout --` para não poluir os commits de tarefa com um artefato não relacionado.

## Deviations from Plan

None - plan executado exatamente como especificado. As únicas interpretações acima (token exato vs. substring; reversão do build artifact) são detalhamento de como cumprir a intenção do plano, não desvio de escopo — nenhum arquivo fora de `files_modified` foi alterado como código de tarefa.

## Issues Encountered

- `webapp/node_modules` não existia neste worktree (worktrees do Claude Code não compartilham `node_modules` do checkout principal — nota já registrada na memória do projeto). Resolvido com `npm install` (172 pacotes, ~1s) antes de rodar qualquer teste. Não é uma mudança de código, não foi commitado (node_modules está no `.gitignore`).

## TDD Gate Compliance

Ambas as tasks são `type="auto" tdd="true"`. Gate verificado:

```
$ git log --oneline --grep="^test(04-02)"
f4c1b02 test(04-02): trava Cancelar de cópia neutro em repouso, vermelho no hover
e61201f test(04-02): trava contorno padrão em Retomar e Gerar sugestões

$ git log --oneline --grep="^feat(04-02)"
97a68f6 feat(04-02): Cancelar de cópia fica vermelho só no hover
bba7117 feat(04-02): Retomar e Gerar sugestões migram para o contorno padrão
```

RED precede GREEN em ambas as tasks. Nenhum REFACTOR commitado — os diffs de GREEN já ficaram mínimos (remoção de prop / troca de duas props), sem limpeza adicional necessária.

## User Setup Required

None - no external service configuration required.

## Verification (plan-level, all commands run and passed)

1. `cd webapp && npm test` → **130/130 testes passando** (16 arquivos), incluindo os 3 novos.
2. `cd webapp && npm run build` → **exit 0** (tsc -b + vite build, sem erros de tipo).
3. `grep -rn 'variante="solido"' webapp/src --include='*.tsx' | grep -v '\.test\.'` → exatamente 4 linhas: `Operations.tsx:194` (Copiar N arquivos) + `Sidebar.tsx:270/306/346` (confirmações de modal) — a lista fechada de D-04, nenhuma a mais nem a menos.

Acceptance criteria por task, todos verificados via grep/vitest literal (não por leitura):
- `grep -c 'border-acento' webapp/src/components/RetomarScan.tsx` → 0
- `grep -c 'variante="solido"' webapp/src/components/Review.tsx` → 0
- `grep -c 'variante="solido"' webapp/src/components/Operations.tsx` → 1
- `grep -c 'variante="solido"' webapp/src/components/Sidebar.tsx` → 3
- `grep -c 'tom="erro"' webapp/src/components/Operations.tsx` → 0
- `grep -c 'hover:text-erro' webapp/src/components/Operations.tsx` → 1

**Not run:** `scripts/verificar.sh` completo (pytest + benchmark de agrupamento) — fora do escopo deste plano, que só toca 3 componentes React (`files_modified` do frontmatter). Nenhum arquivo Python foi tocado; os 3 comandos de `<verification>` do próprio plano (que são a definição operacional de "verde" aqui) passaram integralmente. Rodar o `verificar.sh` completo cabe à verificação de fase, não de plano individual, especialmente em execução paralela onde workers irmãos (04-03/04/05) também estão com o `webapp/` em estado transitório em seus próprios worktrees.

## Next Phase Readiness

- Plano 02 completo: CONS-03 e CONS-07 fechados, testes de regressão no lugar.
- Sem bloqueios para os planos irmãos da wave 2 (04-03/04/05) nem para a wave 3 — este plano não tocou `Sidebar.tsx`, `StatusBar.tsx`, `CORES_STATUS`, nem nenhum arquivo fora da lista declarada.
- Escopo explicitamente fora deste plano permanece aberto para fases futuras se o dono do produto decidir expandir: os 3 `variante="solido"` de `Sidebar.tsx` (modais de confirmação) e `CORES_STATUS.executando` (indicador de status, não botão) não foram tocados, por decisão do UI-SPEC (D-04/CONS-03/CONS-07 nomeiam só os call sites migrados aqui).

---
*Phase: 04-consist-ncia-visual-secund-ria*
*Completed: 2026-08-17*
