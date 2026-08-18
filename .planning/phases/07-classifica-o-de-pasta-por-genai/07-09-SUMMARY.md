---
phase: 07-classifica-o-de-pasta-por-genai
plan: 09
subsystem: classification
tags: [confidence-scoring, measurement, anthropic-sdk, docs]

# Dependency graph
requires:
  - phase: "07-02"
    provides: "location_advisor.py: PastaPayload, corpo_da_chamada, classificar — payload/schema de produção reusado pela medição"
  - phase: "07-03"
    provides: "candidatas_de_pasta.py: como pasta e metadado são agregados"
  - phase: "07-05"
    provides: "SCORES_REFERENCIA['llm_pasta'] = 0.55 marcado PROVISÓRIO, degrau na cascata"
provides:
  - "scripts/medir_score_llm_pasta.py: medição de acerto/recusa/erro contra verdade determinística do catálogo, mesmo payload/schema de produção"
  - "SCORES_REFERENCIA['llm_pasta'] medido (não mais PROVISÓRIO) — 0.55, com comentário citando D-081 e os números"
  - "D-081 em docs/DECISOES.md: método, resultado, alternativas descartadas, limitação de escala"
  - "docs/CONFIANCA.md: origem llm_pasta documentada na tabela de referência"
affects: [07-10]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Medição de score contra verdade determinística do próprio catálogo (mesmo método de D-074/D-059/D-060): amostra só aceita quando origens determinísticas concordam por unanimidade; campo em medição fica ausente do payload enviado ao modelo"
    - "Protocolo classe C respeitado: dono roda o script no próprio terminal com a própria chave; a sessão de desenvolvimento nunca manuseia ANTHROPIC_API_KEY (grep -c \"api_key\" no script = 0)"

key-files:
  created:
    - scripts/medir_score_llm_pasta.py
  modified:
    - fotoorganizer/classification/confidence.py
    - docs/DECISOES.md
    - docs/CONFIANCA.md

key-decisions:
  - "D-081: score de llm_pasta permanece 0.55, agora medido em vez de provisório. Medição real (--limite 60, 4 pastas de amostra): categoria acertou 2/2 (100%), cidade/país recusou 2/2 (100%, null — comportamento seguro de D-06, não falha). Zero erros observados nos dois campos — o sinal que mais importa (o padrão 'afirma sem base' que D-049 mediu e motivou trocar Haiku por Sonnet) não apareceu. Dono decidiu manter em 0.55 (igualando ao advisor de cluster llm) em vez de subir para 0.60 (pasta, que é parse determinístico, não julgamento) ou descer abaixo de 0.50."
  - "Amostra pequena e explicitamente preliminar: 4 pastas, 2 itens por campo. Base de medição da Fase 7 tem só ~1.400 arquivos e 2 fontes cadastradas em catalog.db de produção (.planning/STATE.md § Blockers/Concerns) — as duas fontes que formam o grosso do acervo real (Apple Fotos só-iCloud, Lightroom em volume desmontado) não estão cadastradas (ARCH-01, deferido). Revisitar o número quando/se ARCH-01 reconectar os volumes maiores."
  - "GENAI-03 NÃO foi marcado completo em REQUIREMENTS.md, mesmo estando no `requirements:` do frontmatter deste plano — mesmo padrão de 07-04 a 07-08. 07-10-PLAN.md reserva explicitamente a marcação dos três requisitos GENAI para depois do checkpoint humano com evidência real (mesmo rigor da Fase 6). `requirements.mark-complete` não foi chamado neste plano."

requirements-completed: []  # GENAI-03 segue Pending até 07-10 — ver key-decisions

# Metrics
duration: ~20min
completed: 2026-08-18
---

# Phase 7 Plan 09: Medição do score de llm_pasta Summary

**`scripts/medir_score_llm_pasta.py` mede o classificador de pasta contra verdade determinística do catálogo (mesmo payload/schema de produção); o dono rodou a medição real no próprio terminal (4 pastas, zero erros nos dois campos) e decidiu manter `SCORES_REFERENCIA["llm_pasta"]` em 0.55 — agora medido, não mais provisório (D-081).**

## Performance

- **Duration:** ~20min
- **Tasks:** 3/3
- **Files modified:** 4 (1 criado, 3 editados)

## Accomplishments

- **Task 1 — Script de medição**: `scripts/medir_score_llm_pasta.py` monta a amostra a partir das pastas onde a cascata determinística já resolveu categoria e/ou cidade/país (origens `pasta`, `gps`, `geocoding_offline`, `exif`), exigindo unanimidade entre elas antes de aceitar um valor como verdade — duas pastas com evidência conflitante (ver `deferred-items.md` item 1) foram corretamente excluídas por design, não por bug. Envia ao modelo o MESMO `PastaPayload`/schema de `location_advisor.py`, com o campo em medição ausente. Três baldes por campo (acertou/recusou/errou), categoria e cidade/país relatados separados (nunca somados — regra de `docs/CONFIANCA.md`). `--dry-run` monta amostra e imprime custo estimado sem chamar a API; `grep -c "api_key" scripts/medir_score_llm_pasta.py` = 0.
- **Task 2 — Medição real e decisão do dono**: dono rodou `--limite 60` no próprio terminal com a própria chave (esta sessão nunca manuseou a credencial). Relatório real: `categoria` 2 itens, acertou 2 (100%); `cidade`/`país` 2 itens cada, recusou 2 (100%, `null`). Zero erros nos dois campos. Dono decidiu manter o score em `0.55`, explicitamente registrado como preliminar dado o tamanho da amostra.
- **Task 3 — Score travado e decisão registrada**: `SCORES_REFERENCIA["llm_pasta"]` permanece `0.55`, mas o comentário `PROVISÓRIO` foi substituído por um que cita D-081, os números medidos e a limitação de escala — o status epistêmico mudou mesmo com o número igual. D-081 registrado em `docs/DECISOES.md` (contexto, método, resultado, alternativas descartadas — 0.60 por igualar a `pasta`, e abaixo de 0.50 — e como reverter). `docs/CONFIANCA.md` ganha a linha `llm_pasta` na tabela de referência e um parágrafo distinguindo-a de `llm` (advisor de cluster) e `pasta` (parse determinístico).
- Suíte completa verde: 992 passed (nenhum teste dependia de `0.55` como literal fora da tabela — todos os testes de `test_cascata_llm_pasta.py` verificam a string de origem, não o valor do score).

## Task Commits

Each task was committed atomically:

1. **Task 1: Script de medição contra verdade determinística do catálogo** - `4218b25` (feat)
2. **Task 2: Rodar a medição e decidir o score** - checkpoint humano, sem arquivo/commit próprio (dono rodou o script no terminal dele; relatório e decisão entram no Task 3, conforme `<files>` do plano)
3. **Task 3: Travar o score medido e registrar a decisão** - `396ff6b` (docs)

**Plan metadata:** (este commit — SUMMARY.md, STATE.md, ROADMAP.md, REQUIREMENTS.md)

## Files Created/Modified

- `scripts/medir_score_llm_pasta.py` - Script de medição executável (`.venv/bin/python`), argparse, `--limite`/`--dry-run`, sem dependência nova
- `fotoorganizer/classification/confidence.py` - `SCORES_REFERENCIA["llm_pasta"]` permanece 0.55, comentário `PROVISÓRIO` substituído por um citando D-081 e os números medidos
- `docs/DECISOES.md` - D-081 acrescentada (contexto, método, resultado numérico, alternativas descartadas, limitação de escala, como reverter)
- `docs/CONFIANCA.md` - linha `llm_pasta` na tabela de referência + parágrafo de prosa distinguindo de `llm` e `pasta`

## Decisions Made

Ver `key-decisions` no frontmatter e D-081 em `docs/DECISOES.md` para o registro completo. Resumo: score medido, mantido em 0.55, explicitamente preliminar.

## Deviations from Plan

None - plano executado exatamente como escrito. A Task 2 (checkpoint) foi respondida pelo dono em chat direto com o relatório real da medição (não via resume de checkpoint formal), conforme instruído no contexto de despacho desta execução — o conteúdo entregue (relatório + decisão numérica) satisfaz integralmente a `acceptance_criteria` da Task 2.

## Issues Encountered

None.

## User Setup Required

None - a medição real já foi executada pelo dono antes desta sessão retomar a Task 3; nenhuma configuração adicional pendente.

## Next Phase Readiness

- `llm_pasta` sai de provisório para medido — a Fase 10 (índice de saúde) pode citar este score sem herdar um número não verificado (o próprio risco que este plano existia para fechar, T-07-09-01).
- `07-10-PLAN.md` fecha a Fase 7: documentação de arquitetura/privacidade e checkpoint humano com evidência real antes de marcar GENAI-01/02/03 como completos em `REQUIREMENTS.md`.
- Achado fora de escopo já registrado em `deferred-items.md` (13 linhas de evidência espúria `categoria`/`geocoding_offline` no catálogo real) segue não corrigido — não bloqueia esta medição, mas vale revisitar ao ampliar a amostra.

---
*Phase: 07-classifica-o-de-pasta-por-genai*
*Completed: 2026-08-18*

## Self-Check: PASSED

- FOUND: scripts/medir_score_llm_pasta.py
- FOUND: fotoorganizer/classification/confidence.py
- FOUND: docs/DECISOES.md
- FOUND: docs/CONFIANCA.md
- FOUND: .planning/phases/07-classifica-o-de-pasta-por-genai/07-09-SUMMARY.md
- FOUND commit: 4218b25 (Task 1)
- FOUND commit: 396ff6b (Task 3)
