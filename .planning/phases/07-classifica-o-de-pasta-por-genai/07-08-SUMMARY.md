---
phase: 07-classifica-o-de-pasta-por-genai
plan: 08
subsystem: frontend
tags: [react, react-query, vitest, genai, review]

# Dependency graph
requires:
  - phase: "07-06"
    provides: "ClassificacaoPasta.tsx, contrato de props `{ onFechar }`"
  - phase: "07-07"
    provides: "Assistente completo (passos 0-5) pronto para ser montado"
provides:
  - "Review.tsx: ponto de entrada do assistente GenAI de pasta (botão + modal montado)"
  - "Review.tsx: pastilha 'IA · pasta' no PorQue para evidências de origem llm_pasta"
affects: [07-10]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Ponto de montagem verificado por leitura íntegra do arquivo (git show do commit anterior à Task 1) antes de editar — não assumido do 07-PATTERNS.md, que registrava o item como não verificado"

key-files:
  created: []
  modified:
    - webapp/src/components/Review.tsx
    - webapp/src/components/Review.test.tsx

key-decisions:
  - "GENAI-03 NÃO foi marcado completo em REQUIREMENTS.md apesar de estar no `requirements:` do frontmatter deste plano. 07-10-PLAN.md (wave 5, depends_on inclui 07-08 e 07-09) reserva explicitamente para si a marcação dos três requisitos GENAI, com must_have próprio: 'Os três requisitos GENAI só são marcados completos depois da verificação com evidência real' — um checkpoint humano com chave de API real, mesmo rigor da Fase 6. Marcar GENAI-03 aqui anteciparia uma conclusão que o próprio roadmap da fase reserva para depois da verificação humana. `requirements.mark-complete` não foi chamado neste plano."
  - "Backend/api.ts não precisaram de mudança para a Task 2 — `ev.origem` já chegava ao frontend (`Evidencia.origem` em api.ts, serializado em `fotoorganizer/server/app.py:776/1282/1356`). O read_first da Task 2 cogitava essa mudança como possivelmente necessária; não foi."

requirements-completed: []  # GENAI-03 seguirá Pending até 07-10 — ver key-decisions

# Metrics
duration: ~25min
completed: 2026-08-18
---

# Phase 7 Plan 08: Ponto de entrada em Review.tsx Summary

**Review.tsx ganha o botão "Classificar pastas por IA…" e a montagem condicional de `ClassificacaoPasta`, e o `PorQue` passa a mostrar a pastilha "IA · pasta" para evidências de origem `llm_pasta` — o assistente construído em 07-06/07-07 fica, pela primeira vez, alcançável pelo dono.**

## Performance

- **Duration:** ~25min
- **Tasks:** 3/3
- **Files modified:** 2

## Accomplishments

- **Ponto de montagem verificado por leitura, não assumido**: `07-PATTERNS.md` § Open Items item 5 registrava explicitamente que o ponto de montagem do modal não tinha sido conferido. Leitura íntegra do arquivo (antes de qualquer edição) confirmou: componente principal retorna em `Review.tsx:134` (`return (`), elemento de raiz `<div className="flex h-full flex-col">` abre em `Review.tsx:135` e fecha em `Review.tsx:380` (`</div>`), com `);`/`}` do componente em 381/382 — arquivo com exatamente 500 linhas antes desta task. Esses números **batem** com o que o plano assumia (nenhuma divergência real a reportar, ao contrário do que o commit da Task 1 registrou de forma imprecisa — ver Deviations).
- **Task 1**: `useState<boolean>` `classificacaoAberta` junto dos demais estados locais do componente; botão `<Botao variante="contorno" tamanho="md">Classificar pastas por IA…</Botao>` inserido imediatamente antes de "Gerar/atualizar sugestões" na barra de cabeçalho; `ClassificacaoPasta` montado condicionalmente como último filho do elemento de raiz verificado (linha 135-393 pós-edição), sem nenhuma entrada nova em `ABAS`/`App.tsx`.
- **Task 2**: pastilha condicional `ev.origem === "llm_pasta"` no `PorQue`, classes literais do UI-SPEC (`rounded-full border border-herdado/40 bg-herdado/10 px-1.5 py-0.5 text-[11px] text-herdado`), texto `"IA · pasta"`. Nenhuma mudança de backend/`api.ts` foi necessária — `ev.origem` já trafegava ponta a ponta.
- **Task 3**: 4 testes vitest novos em `Review.test.tsx` — disparo abre o modal (dublê `vi.mock` de `ClassificacaoPasta`, isolando este arquivo do assistente inteiro, que já tem suíte própria em 07-06/07-07), fechar o modal preserva a Revisão por baixo, evidência `llm_pasta` ganha a pastilha (exercitando o `PorQue` REAL, sem dublê), evidência de outra origem (`gps`) não ganha.
- `npx tsc -b --noEmit` limpo, `npm run build` verde, suíte inteira do webapp: 186 testes (182 herdados + 4 novos), 19 arquivos, todos verdes.
- `git diff` de cada task confirmado como estritamente aditivo (nenhuma linha pré-existente alterada em `Review.tsx` ou `Review.test.tsx`).

## Task Commits

Each task was committed atomically:

1. **Task 1: Verificar a árvore de render e montar o modal** - `55fab10` (feat)
2. **Task 2: Pastilha de origem llm_pasta no PorQue** - `817d661` (feat)
3. **Task 3: Testes do disparo e da pastilha** - `d800296` (test)

**Plan metadata:** (este commit) `docs: complete 07-08 plan`

## Files Created/Modified

- `webapp/src/components/Review.tsx` - botão de disparo, `useState` de abertura, montagem condicional de `ClassificacaoPasta`, pastilha "IA · pasta" no `PorQue`
- `webapp/src/components/Review.test.tsx` - 4 testes novos (24 no arquivo), `vi.mock` de `ClassificacaoPasta`

## Decisions Made

- **GENAI-03 permanece Pending nesta execução** — ver key-decisions no frontmatter. 07-10 é o plano que fecha os três requisitos GENAI após checkpoint humano com evidência real (mesmo padrão da Fase 6); marcar aqui anteciparia essa conclusão.
- **`ev.origem` já existia ponta a ponta** — nenhuma mudança de `api.ts`/backend na Task 2, ao contrário do que o `read_first` cogitava como possível.
- **Comentário inline explicando a escolha de paleta `herdado`** para a pastilha, em vez de reusar a paleta neutra do selo de fonte (CONS-01, `Review.tsx:312-319`) — exigência explícita do `<action>` da Task 2.

## Deviations from Plan

### Correção de registro (não uma mudança de código)

**1. Números de linha do commit da Task 1 estavam imprecisos**
- O commit `55fab10` registrou "divergência de +2 linhas vs. os 500 assumidos" — isso estava ERRADO. Reconferido via `git show 55fab10^:webapp/src/components/Review.tsx | wc -l`: o arquivo pré-edição tinha exatamente 500 linhas, com `return (` em 134, raiz abrindo em 135 e fechando (`</div>`) em 380 — **batendo exatamente** com o que o plano assumia. Não houve divergência real entre o arquivo e o plano nesta task; o commit apenas registrou mal a comparação. Este SUMMARY é o registro correto e definitivo, conforme a acceptance criteria da Task 1 exige ("O SUMMARY do plano registra os números de linha reais... confirmados por leitura").
- **Impacto:** nenhum — é um erro de narrativa no commit message, não no código. Não amendado (política do executor é criar commit novo, não reescrever histórico); corrigido aqui.

### Discrepância documentada na acceptance criteria da Task 1 (grep case-sensitive)

**2. `grep -n "classificacaoAberta" webapp/src/components/Review.tsx` retorna 2 linhas, não 3**
- A acceptance criteria da Task 1 esperava 3 linhas (declaração, `onClick`, montagem condicional). O setter segue a convenção padrão de camelCase já usada por TODOS os outros `useState` deste arquivo (`setStatus`, `setAbertos`, `setPorque`, `setEditando`, `setValorEdicao`, `setErroEdicao`): `setClassificacaoAberta`, com "C" maiúsculo depois de "set". `grep` sem `-i` não casa `classificacaoAberta` (minúsculo) dentro de `setClassificacaoAberta` (maiúsculo) — por case-sensitivity, não por ausência do disparo.
- As 3 ocorrências semânticas exigidas pela acceptance criteria EXISTEM no arquivo: declaração (linha 59), disparo via `onClick={() => setClassificacaoAberta(true)}` (linha 158-159) e montagem condicional (linha 387). `grep -ni "classificacaoAberta"` confirma as 3 linhas. Renomear o setter para bater com o grep case-sensitive quebraria a convenção de nomenclatura do próprio arquivo — não foi feito.
- **Impacto:** nenhum no comportamento; é uma imprecisão do comando de aceite literal do plano, documentada aqui em vez de silenciosamente ignorada.

---

**Total deviations:** 2, ambas de documentação/registro — nenhuma mudança de comportamento, nenhum código alterado por causa delas.

## Known Stubs

None — o botão dispara um componente já completo (07-06/07-07); a pastilha lê um campo (`ev.origem`) que já existe ponta a ponta no payload real.

## Threat Flags

None — as três mitigações do `<threat_model>` deste plano (T-07-08-01 a T-07-08-03) foram implementadas exatamente como especificado: pastilha condicional testada positivo/negativo (T-07-08-01), mudança estritamente aditiva verificada por `git diff` em cada task e ponto de montagem confirmado por leitura (T-07-08-02), botão só abre o modal — nenhuma chamada de rede nova disparada pelo clique em si (T-07-08-03, o gate de dois consentimentos e o passo 0 do modal continuam sendo o único portão, herdado de 07-04/07-06).

## Issues Encountered

None.

## User Setup Required

None — frontend puro, nenhuma configuração de serviço externo neste plano.

## Next Phase Readiness

- **GENAI-03 continua Pending em REQUIREMENTS.md** — ver key-decisions. O comportamento que o requisito descreve (Evidence própria, distinguível na Revisão) está implementado e testado ponta a ponta a partir deste plano, mas a marcação formal fica para 07-10, que exige checkpoint humano com evidência real de uma sessão com chave de API de verdade.
- **GENAI-01 e GENAI-02** também dependiam de 07-08 para ficarem alcançáveis pelo dono (07-06/07-07 já documentavam isso) — agora o dono tem, pela primeira vez, como abrir o assistente a partir da Revisão. Ainda assim, nenhum dos três é marcado aqui, pela mesma razão: 07-10 é o plano designado para a verificação humana e a marcação formal.
- Interface pronta para 07-09: a medição de `SCORES_REFERENCIA["llm_pasta"]` não toca `Review.tsx` nem este plano — segue isolada em `ClassificacaoPasta.tsx` (`NIVEL_LLM_PASTA`), sem dependência daqui.
- Interface pronta para 07-10: `Review.tsx` já expõe o caminho completo (opt-in → disparo → assistente → aprovação → evidência distinguível na Revisão), o objeto de prova que 07-10 precisa documentar em `docs/ARQUITETURA.md`/`docs/PRIVACIDADE.md` e verificar numa sessão real antes de marcar os três requisitos GENAI.

---
*Phase: 07-classifica-o-de-pasta-por-genai*
*Completed: 2026-08-18*

## Self-Check: PASSED

All modified files found on disk (`webapp/src/components/Review.tsx`,
`webapp/src/components/Review.test.tsx`); all 3 task commits (`55fab10`,
`817d661`, `d800296`) confirmed in git log.
