---
phase: 07-classifica-o-de-pasta-por-genai
plan: 05
subsystem: classification
tags: [suggestion-engine, evidence, confidence-model, genai]

# Dependency graph
requires:
  - phase: 07-01
    provides: "ClassificacaoPastaRepository.aprovadas(), PropostaDePasta"
provides:
  - "Degrau llm_pasta em SuggestionEngine._evidencias_geo (país/cidade) e _categoria (categoria/evento)"
  - "SuggestionEngine(pastas_classificadas=...) — carga em lote de propostas aprovadas, uma leitura por gerar()"
  - "jobs.py::_rodar_sugestoes lê ClassificacaoPastaRepository.aprovadas() do cache local"
affects: [07-06, 07-07, 07-09, 07-10]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Parâmetro de dicionário lido em lote no construtor (pastas_classificadas), mesmo padrão de lexico — nenhuma consulta nova dentro do laço de mídia"
    - "Degrau de cascata como FALLBACK explícito: só decide quando todos os passos determinísticos e o advisor de cluster já falharam"

key-files:
  created:
    - tests/test_cascata_llm_pasta.py
  modified:
    - fotoorganizer/classification/confidence.py
    - fotoorganizer/classification/engine.py
    - fotoorganizer/server/jobs.py

key-decisions:
  - "SCORES_REFERENCIA['llm_pasta'] = 0.55 é PROVISÓRIO — não medido, ponteiro explícito para o plano de medição 07-09 (D-074/D-059/D-060 exigem medir contra o acervo real antes de travar score)"
  - "llm_pasta é chave separada de llm mesmo com o mesmo número provisório: afirmações de natureza diferente (nome da pasta vs. metadado de mídia via Advisor de cluster) — docs/CONFIANCA.md proíbe fundir origens"
  - "Degrau de país/cidade entra em _evidencias_geo no passo 2c, entre a hierarquia da pasta (2) e a vizinhança (3) — as duas condições (hierarquia vazia E proposta existe) coincidem por construção porque D-01 do 07-03 só oferece candidatas cuja hierarquia já veio vazia"
  - "Degrau de categoria entra em _categoria no passo 3b, depois do advisor de cluster (3) — fallback nunca substituição"
  - "Evento da proposta só preenche quando nenhum draft de campo 'evento' já existe (a sessão de viagem/evento sempre tem precedência)"

patterns-established:
  - "PropostaDePasta passa pelos três pontos da cascata (_evidencias_para, _evidencias_geo, _categoria) como parâmetro opcional resolvido uma vez por mídia em gerar(), nunca re-consultado"

requirements-completed: []  # GENAI-03 span múltiplos planos (07-01..07-10) — ver nota abaixo

# Metrics
duration: ~15min
completed: 2026-08-18
---

# Phase 7 Plan 05: Integração do GenAI de pasta na cascata do SuggestionEngine Summary

**Proposta aprovada de cidade/país/categoria/evento vira `Evidence` própria com origem `llm_pasta`, re-derivada a cada `gerar()` a partir da tabela — sempre como último recurso da cascata, atrás de todo degrau determinístico e do advisor de cluster.**

## Performance

- **Duration:** ~15min
- **Started:** 2026-08-18T21:21:13Z (após fechamento de 07-04)
- **Completed:** 2026-08-18T21:30:49Z
- **Tasks:** 3/3
- **Files modified:** 4 (1 criado, 3 modificados)

## Accomplishments
- `SCORES_REFERENCIA["llm_pasta"]` adicionado com comentário `PROVISÓRIO` inequívoco e ponteiro para o plano de medição 07-09 — nenhuma entrada existente alterada
- `SuggestionEngine` ganhou o parâmetro `pastas_classificadas`, lido em lote no `__init__` (mesmo tratamento de `lexico`), resolvido uma vez por mídia em `gerar()` via `self._pastas_classificadas.get(media.pasta)` — zero consultas novas dentro do laço
- `_evidencias_geo` ganhou o passo 2c (país/cidade da proposta) entre a hierarquia da pasta e a vizinhança de sessão; `_categoria` ganhou o passo 3b (categoria da proposta) depois do advisor de cluster; `_evidencias_para` preenche `evento` da proposta só quando a sessão ficou em silêncio
- `jobs.py::_rodar_sugestoes` lê `ClassificacaoPastaRepository.aprovadas()` do cache local (nenhuma chamada externa em `gerar()`) e passa como `pastas_classificadas=`
- 7 testes em `tests/test_cascata_llm_pasta.py`: origem própria, durabilidade entre rodadas (sem chamada externa), proposta não-aprovada não vira evidência, determinismo vence o llm, advisor de cluster vence na categoria, evento da sessão prevalece, resultado idêntico ao de hoje sem proposta passada

## Task Commits

Each task was committed atomically:

1. **Task 1: Entrada provisória llm_pasta em SCORES_REFERENCIA** - `0694c0d` (feat)
2. **Task 2: Degrau llm_pasta em _categoria e _evidencias_geo, com carga em lote** - `e65d2ac` (feat)
3. **Task 3: Testes de origem própria, durabilidade e não-regressão** - `73f070d` (test)

## Files Created/Modified
- `fotoorganizer/classification/confidence.py` - chave `llm_pasta=0.55`, comentário `PROVISÓRIO` com ponteiro para 07-09
- `fotoorganizer/classification/engine.py` - `SuggestionEngine.__init__(pastas_classificadas=...)`, degrau 2c em `_evidencias_geo`, degrau 3b em `_categoria`, evento condicional em `_evidencias_para`
- `fotoorganizer/server/jobs.py` - `_rodar_sugestoes` lê `ClassificacaoPastaRepository.aprovadas()` e repassa ao `SuggestionEngine`
- `tests/test_cascata_llm_pasta.py` - 7 testes cobrindo origem, durabilidade, precedência determinística e não-regressão

## Decisions Made
- Score provisório (`0.55`) confirmado exatamente como o plano especificou — chave separada de `llm` mesmo com número igual, por natureza de afirmação distinta (docs/CONFIANCA.md proíbe fundir origens de natureza diferente mesmo com score idêntico)
- Posição do degrau de país/cidade (2c) e de categoria (3b) seguiu literalmente o `<action>` do plano: sempre depois do determinístico correspondente falhar, nunca por cima

## Deviations from Plan

None - plano executado exatamente como escrito.

## Issues Encontrados

Nenhum. Os 7 testes passaram na primeira execução contra a implementação de Task 2 (não houve fase RED isolada — mesma estrutura sequencial já documentada em `07-01-SUMMARY.md`: Task 2 implementa, Task 3 prova). A suíte inteira (992 testes) segue verde, sem regressão. `scripts/avaliar_agrupamento.py` mantém os 19 cenários (18/19 na melhor variante, achado pré-existente não relacionado a este plano).

## User Setup Required

None - nenhuma configuração de serviço externo neste plano; `gerar()` continua 100% local (`grep -c "location_advisor" fotoorganizer/classification/engine.py` = 0).

## Next Phase Readiness

- **GENAI-03 continua Pending em REQUIREMENTS.md** — este plano entrega o degrau na cascata (o "resultado vira Evidence"), mas o comportamento fim-a-fim de GENAI-03 exige que o dono consiga ver e revisar essa evidência: falta a UI (07-06/07-07) para o fluxo ficar visível/acionável. Não marcado como completo, por instrução explícita do plano.
- `SCORES_REFERENCIA["llm_pasta"]` permanece PROVISÓRIO — 07-09 precisa medir contra o acervo real antes de qualquer consumidor (ex.: índice de saúde da Fase 10) tratar 0.55 como calibrado.
- Contrato pronto para 07-06/07-07 (frontend de revisão) consumirem: `Evidence.origem == "llm_pasta"` já chega distinguível de `"llm"` em qualquer mídia cuja pasta tenha proposta aprovada.

---
*Phase: 07-classifica-o-de-pasta-por-genai*
*Completed: 2026-08-18*

## Self-Check: PASSED

All created/modified files found on disk; all 3 task commits (`0694c0d`, `e65d2ac`, `73f070d`) confirmed in git log.
