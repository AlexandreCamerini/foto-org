---
phase: 07-classifica-o-de-pasta-por-genai
plan: 06
subsystem: frontend
tags: [react, react-query, vitest, genai, wizard-modal]

# Dependency graph
requires:
  - phase: "07-04"
    provides: "Sete endpoints /api/genai-pasta/* (config, candidatas, estimar-custo, rodar, propostas, aprovar), gate de dois consentimentos"
provides:
  - "api.ts: 5 tipos + 7 funções cliente de /api/genai-pasta/*"
  - "ClassificacaoPasta.tsx: passos 0 (gate) a 3 (rodando) do assistente"
affects: [07-07, 07-08]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Passo inicial do assistente semeado UMA vez a partir da consulta de config (useEffect com guarda passo===null), nunca reagindo a refetches subsequentes — mesmo padrão de semeadura única de EscritaExif.tsx"
    - "Seleção de candidatas nasce TODA marcada (Set<string> de caminhos, opt-out D-01), semeada só quando a referência de `candidatas` muda"
    - "Passo 3 desabilita todo caminho de fechar por uma flag `podeFechar` compartilhada entre o listener global de Esc e o onClick do backdrop — não duas checagens divergentes"
    - "pastaCurta reproduzida localmente em vez de importada de Review.tsx: evita ciclo de módulos, já que Review.tsx importa este componente no plano 07-08"

key-files:
  created:
    - webapp/src/components/ClassificacaoPasta.tsx
    - webapp/src/components/ClassificacaoPasta.test.tsx
  modified:
    - webapp/src/api.ts

key-decisions:
  - "GENAI-01 continua Pending em REQUIREMENTS.md — este plano entrega os passos 0-3 (consentimento, seleção, custo, chamada em voo), mas o componente ainda não está montado em lugar nenhum acessível ao dono (07-08 conecta o botão de entrada em Review.tsx) e os passos 4/5 (revisão/aprovação) ainda não existem (07-07). Sem os três, o dono não consegue de fato completar o fluxo — mesma disciplina de 07-04/07-05."
  - "Passos revisao/concluido são marcadores mínimos nesta entrega (texto simples com a contagem de propostas recebidas), só para não quebrar a máquina de estados — implementação real é 07-07, conforme a divisão de escopo do próprio bloco <interfaces> do plano."

requirements-completed: []  # GENAI-01 continua Pending — ver key-decisions

# Metrics
duration: ~35min
completed: 2026-08-18
---

# Phase 7 Plan 06: Cliente tipado e assistente GenAI de pasta (passos 0-3) Summary

**`api.ts` ganha 5 tipos e 7 funções espelhando literalmente os endpoints `/api/genai-pasta/*` de 07-04; `ClassificacaoPasta.tsx` entrega o portão de consentimento, a lista opt-out de candidatas, o custo honestamente estimado (D-079) e a chamada síncrona não-cancelável, todos presos ao Copywriting Contract por 9 testes vitest.**

## Performance

- **Duration:** ~35min
- **Tasks:** 3/3
- **Files modified:** 3 (2 criados, 1 modificado)

## Accomplishments

- `api.ts`: `ConfigGenaiPasta`, `CandidataGenaiPasta`, `CustoGenaiPasta`, `PropostaGenaiPasta`, `RodadaGenaiPasta` (tipos com união literal onde o backend expõe enum, mesmo raciocínio de exaustividade de `StatusCampoExif`) e as sete funções `configGenaiPasta`/`habilitarGenaiPasta`/`candidatasGenaiPasta`/`estimarCustoGenaiPasta`/`rodarGenaiPasta`/`propostasGenaiPasta`/`aprovarGenaiPasta` — todas reusando `json`/`post`/`put` já existentes, `put<T>` já estava disponível (não precisou ser criado)
- `ClassificacaoPasta.tsx`: máquina de estados de 7 passos (`gate`/`candidatas`/`custo`/`rodando`/`revisao`/`concluido`/`erro`); passo 0 bifurca entre caixa de opt-in (mestre ligado) e mensagem não-acionável (mestre desligado, sem caixa nenhuma); passo 1 pré-filtrado e opt-out com etiqueta de campo ausente por linha e link "Desligar"; passo 2 com as três linhas de custo sempre prefixadas "até" e a nota de honesticidade D-079 literal; passo 3 sem NENHUM caminho de fechar ativo (Esc global e backdrop guardados pela mesma flag `podeFechar`), contador de segundos honesto sem barra de progresso falsa; estado de erro dedicado com a cópia exata do contrato
- 9 testes vitest cobrindo todo o `<behavior>` do plano, incluindo um dublê de `fetch` próprio (`servirApiComRodarPendente`) que nunca resolve a rota `/api/genai-pasta/rodar` — necessário para observar o passo 3 sem corrida entre o clique e a resposta simulada
- `npm run build` e a suíte inteira do webapp (172 testes, 19 arquivos) verdes após as três tasks

## Task Commits

Each task was committed atomically:

1. **Task 1: Tipos e funções cliente em api.ts** - `7cd6aa5` (feat)
2. **Task 2: ClassificacaoPasta.tsx — passos 0 a 3** - `3dd7a51` (feat)
3. **Task 3: Testes vitest dos passos 0 a 3** - `5b34119` (test)

**Plan metadata:** (este commit) `docs: complete 07-06 plan`

_Nota: como em 07-04, a Task 3 é `tdd="true"` mas os testes foram escritos depois da implementação (Task 2 precedeu o arquivo de teste) — os 9 testes passaram já na primeira execução. Mesma disciplina sequencial já documentada nos planos anteriores desta fase: os testes ainda provam exatamente o que o `<behavior>` pedia, incluindo o caso mais fácil de esquecer (Esc inerte durante a chamada em voo)._

## Files Created/Modified

- `webapp/src/api.ts` - 5 tipos + 7 funções de `/api/genai-pasta/*`
- `webapp/src/components/ClassificacaoPasta.tsx` - assistente modal, passos 0-3 implementados, 4-5 com marcador mínimo
- `webapp/src/components/ClassificacaoPasta.test.tsx` - 9 testes, dublê de fetch próprio para o passo 3

## Decisions Made

- **`pastaCurta` reproduzida localmente, não importada de `Review.tsx`**: a função não é exportada lá, e como `Review.tsx` vai importar este componente no plano 07-08, importar `pastaCurta` de volta de `Review.tsx` criaria um ciclo de módulos (`Review.tsx` → `ClassificacaoPasta.tsx` → `Review.tsx`). A leitura obrigatória do plano pedia reuso verbatim da lógica — cumprida copiando as duas linhas com comentário explicando o porquê de não importar, em vez de arriscar o ciclo ou expandir o escopo de arquivos deste plano para incluir `Review.tsx` (fora de `files_modified`).
- **`put<T>` já existia em `api.ts`** (adicionado num plano anterior para `salvarTemplate`) — o `<action>` da Task 1 previa criá-lo condicionalmente; não foi necessário.
- **Passo de erro dedicado (`passo="erro"`), não inline** — o `<behavior>` do plano exige que uma falha na chamada de `rodar()` leve a "um estado de erro com a cópia do contrato, não silenciosamente de volta ao passo 2". Implementado como um passo próprio da máquina de estados (`PassoErro`), com botão "Voltar" que retorna ao passo de custo reusando o `custo` já calculado (sem nova consulta).
- **Estimativa de custo via `useMutation`, não `useQuery`** — seguindo literalmente o `<action>` do plano ("mutações com `useMutation` (habilitarGenaiPasta, estimarCustoGenaiPasta, rodarGenaiPasta)"), disparada pelo clique em "Avançar"/"Confirmar e classificar" em vez de reagir automaticamente à seleção — evita uma chamada ao servidor a cada toggle de checkbox no passo 1.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - erro de tipo] Parâmetro `init` não utilizado no dublê de fetch do teste**
- **Found during:** Task 3, `npx tsc -b --noEmit`
- **Issue:** `servirApiComRodarPendente` declarava um parâmetro `init?: RequestInit` nunca lido (a rota de `rodar` nunca resolve, então o corpo do POST nunca precisa ser inspecionado) — `noUnusedParameters` acusou.
- **Fix:** Removido o parâmetro da assinatura do mock; comportamento idêntico.
- **Files modified:** `webapp/src/components/ClassificacaoPasta.test.tsx`
- **Commit:** `5b34119`

---

**Total deviations:** 1 auto-fixed (Rule 1, erro de tipo puro — nenhuma mudança de comportamento).
**Impact on plan:** Nenhum.

## Issues Encountered

None além do item acima.

## User Setup Required

None — nenhuma configuração de serviço externo neste plano (frontend puro, mesma credencial de ambiente que 07-04 já documenta para o backend).

## Next Phase Readiness

- **GENAI-01 continua Pending em REQUIREMENTS.md.** Este plano entrega os passos 0-3 do assistente (consentimento, seleção pré-filtrada, custo honesto, chamada em voo não-cancelável), mas dois requisitos ainda faltam para o comportamento ficar completo e acionável pelo dono: (1) os passos 4-5 (revisão antes/depois, aprovação) — plano 07-07, e (2) um ponto de entrada real na UI (botão em `Review.tsx` que monta este componente) — plano 07-08. Sem os dois, o dono não tem hoje como sequer abrir este modal. Mesma disciplina de 07-04/07-05.
- Interface pronta para 07-07: `passo` já inclui `"revisao"`/`"concluido"` na união de tipos, `rodada: RodadaGenaiPasta | null` já guarda o resultado de `rodar()` (propostas achatadas por campo, `pastas_sem_resposta`, `custo_real`) — 07-07 só precisa substituir o marcador mínimo pelos dois passos reais, reusando o mesmo estado.
- Interface pronta para 07-08: `export function ClassificacaoPasta({ onFechar })` é o único contrato de props exposto — `Review.tsx` só precisa `useState` de um booleano de "aberto" e renderizar condicionalmente, exatamente como o UI-SPEC descreve (`setClassificacaoAberta(true)`).
- `api.propostasGenaiPasta()` e `api.aprovarGenaiPasta()` já estão tipados e prontos, mas nenhum passo desta entrega os chama ainda — ficam para 07-07.

---
*Phase: 07-classifica-o-de-pasta-por-genai*
*Completed: 2026-08-18*

## Self-Check: PASSED

All created/modified files found on disk; all 3 task commits (`7cd6aa5`,
`3dd7a51`, `5b34119`) confirmed in git log.
