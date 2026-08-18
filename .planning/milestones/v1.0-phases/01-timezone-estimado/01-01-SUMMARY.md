---
phase: 01-timezone-estimado
plan: 01
subsystem: classification
tags: [geolocation, timezone, zoneinfo, fastapi, sqlalchemy]

# Dependency graph
requires:
  - phase: none (primeira fase deste roadmap)
    provides: n/a
provides:
  - "TZ_POR_PAIS: dict[str, str] em fotoorganizer/geolocation/timezones.py — tabela estática país PT-BR -> fuso IANA, 250 entradas (toda a PAISES_PT)"
  - "media.tz_estimado gravado direto em _persistir_sugestao (engine.py), recalculado a cada gerar()"
  - "GET /api/midia/{id} (e a grade) devolvem tz_estimado"
affects: [futuras fases que consumam tz_estimado — ex. conversão de data_capturada para hora local em alguma tela, ainda não pedida]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Tabela estática de lookup país->valor, mesmo espírito de paises.py (docstring com o porquê, sem rede, não reexportada em __init__.py)"
    - "Escrita direta em MediaFile dentro de _persistir_sugestao, sem Evidence/Suggestion (mesmo padrão de gps_lat_estimado em _persistir_herancas)"

key-files:
  created:
    - fotoorganizer/geolocation/timezones.py
    - tests/test_timezones.py
  modified:
    - fotoorganizer/classification/engine.py
    - tests/test_suggestion_engine.py
    - fotoorganizer/server/app.py
    - tests/test_server_api.py

key-decisions:
  - "PAISES_PT tem 250 entradas na base atual, não os 98 citados no spec/CONTEXT.md da fase — a tabela cresceu desde que esse número foi escrito. A cobertura foi construída dinamicamente contra o valor real (todos os testes usam set-equality com PAISES_PT.values(), nunca o número 98), então nenhum país ficou de fora por causa da divergência."
  - "D-08 (capital ou maior população) precisou de 3 extensões não previstas explicitamente pelo spec para cobrir os ~150 territórios/dependências que os 98->250 adicionaram: território sem população permanente (Ilha Bouvet -> Etc/GMT por longitude; Heard/McDonald -> Indian/Kerguelen por proximidade), território sem IANA próprio (Kosovo -> Europe/Belgrade, mesma regra de horário da Sérvia), e o código genérico Antártida/AQ (-> Antarctica/McMurdo, referência estável sem país real por trás). Documentado no topo de timezones.py."
  - "Micronésia mapeada para Pacific/Pohnpei (capital Palikir), não Pacific/Chuuk (estado mais populoso) — segue o critério 'capital' quando capital e maior população divergem, mesma prioridade implícita nos 5 exemplos do spec (Brasil/EUA/Rússia/Canadá/Austrália)."

requirements-completed: [TZ-01]

# Metrics
duration: ~50min
completed: 2026-08-16
---

# Phase 1 Plan 01: Timezone estimado Summary

**Tabela estática TZ_POR_PAIS (250 países, IANA validado) alimentando `media.tz_estimado`, gravado direto em `_persistir_sugestao` e servido em `GET /api/midia/{id}` — fecha o modelo de dois instantes de D-038.**

## Performance

- **Duration:** ~50 min
- **Completed:** 2026-08-16
- **Tasks:** 3/3 completos
- **Files modified:** 4 (2 código, 2 teste) + 2 arquivos novos (1 código, 1 teste)

## Accomplishments

- `fotoorganizer/geolocation/timezones.py`: tabela `TZ_POR_PAIS` cobrindo a totalidade dos países de `PAISES_PT` (250, não os 98 citados no spec — ver Deviations), todo valor validado como identificador IANA real via `zoneinfo.available_timezones()`.
- `_persistir_sugestao` (`engine.py`) grava `media.tz_estimado` a partir de `evidencias["pais"].valor`, com `else None` explícito para nunca deixar sobreviver um valor obsoleto numa regeneração — os 4 cenários do spec (GPS próprio, herança temporal D-025, sem país, regeneração) cobertos por teste.
- `GET /api/midia/{id}` (e a grade, mesmo `_media_json`) devolvem `tz_estimado` como passthrough direto, sem query extra.

## Task Commits

Cada task seguiu RED→GREEN (TDD):

1. **Task 1: Tabela TZ_POR_PAIS + validação IANA**
   - `7771860` test(01-01): TZ_POR_PAIS cobre PAISES_PT e valida IANA (RED)
   - `a651138` feat(01-01): tabela estática TZ_POR_PAIS (país PT-BR -> fuso IANA) (GREEN)
2. **Task 2: Persistência direta em _persistir_sugestao**
   - `9abf99e` test(01-01): 4 cenários de tz_estimado em _persistir_sugestao (RED)
   - `700eeba` feat(01-01): grava media.tz_estimado em _persistir_sugestao (GREEN)
3. **Task 3: Serialização em GET /api/midia/{id}**
   - `f70fbbe` test(01-01): GET /api/midia/{id} devolve tz_estimado (RED)
   - `437cc85` feat(01-01): tz_estimado no JSON de _media_json (GREEN)

## Files Created/Modified

- `fotoorganizer/geolocation/timezones.py` (novo) — `TZ_POR_PAIS: dict[str, str]`, 250 entradas, regra D-08 documentada no topo.
- `tests/test_timezones.py` (novo) — cobertura completa + validação IANA.
- `fotoorganizer/classification/engine.py` — import de `TZ_POR_PAIS`, escrita de `media.tz_estimado` em `_persistir_sugestao`.
- `tests/test_suggestion_engine.py` — 4 testes novos (`test_tz_estimado_de_gps_proprio`, `test_tz_estimado_de_pais_herdado`, `test_tz_estimado_none_sem_pais_conhecido`, `test_tz_estimado_atualiza_ao_regenerar_sugestoes`).
- `fotoorganizer/server/app.py` — `"tz_estimado": m.tz_estimado` em `_media_json`.
- `tests/test_server_api.py` — `test_detalhe_traz_o_tz_estimado`.

## Decisions Made

- **Cobertura real (250) em vez do número do spec (98):** o spec/CONTEXT.md desta fase citam "98 países de PAISES_PT" repetidamente, mas a tabela atual no repositório tem 250 entradas (ISO 3166-1 completo, incluindo territórios/dependências). Como todo teste e critério de aceite usa `set(TZ_POR_PAIS) == set(PAISES_PT.values())` (comparação dinâmica, nunca o literal "98"), a implementação cobre o valor real sem ambiguidade — não há dois caminhos possíveis de implementação aqui, só um que satisfaz o teste. Ver "Deviations" abaixo.
- **`else None` em vez do snippet literal do spec:** conforme já sinalizado em `01-PATTERNS.md` "Flags for Planner" #1, usei `TZ_POR_PAIS.get(...) if "pais" in evidencias else None` em vez do snippet sem `else` do `docs/prompts/fase-11-timezone-estimado.md:117-119`. Sem o `else`, o próprio teste de regeneração exigido pelo spec ("regenerar sugestões atualiza tz_estimado") falharia.
- **Micronésia -> `Pacific/Pohnpei`** (capital Palikir), não `Pacific/Chuuk` (estado mais populoso) — capital tem prioridade quando os dois critérios de D-08 divergem, coerente com os 5 exemplos do spec.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1/2 — factual premise do spec desatualizada] `PAISES_PT` tem 250 países, não 98**
- **Found during:** Task 1, ao ler `fotoorganizer/geolocation/paises.py` na íntegra para construir `TZ_POR_PAIS`.
- **Issue:** O spec autoritativo (`docs/prompts/fase-11-timezone-estimado.md`), o `01-CONTEXT.md` e o `01-PATTERNS.md` desta fase citam repetidamente "98 países de PAISES_PT". A contagem real de `PAISES_PT` no código atual é 250 (ISO 3166-1 completo + territórios/dependências — Guernsey, Bermudas, Ilha Bouvet, Território Britânico do Oceano Índico, etc.). `git log` em `paises.py` não mostra nenhuma expansão recente que explicasse a divergência a partir de um estado anterior de 98; o número "98" nunca aparece em nenhum teste ou critério de aceite executável do plano — só em prosa.
- **Fix:** `TZ_POR_PAIS` foi construída para cobrir as 250 entradas reais de `PAISES_PT`, validada dinamicamente por `set(TZ_POR_PAIS) == set(PAISES_PT.values())` (o teste que o próprio spec pede). Isso ampliou a superfície de julgamento do D-08 (país multi-fuso -> capital/maior população) de ~5 exemplos citados para incluir também territórios sem população (Ilha Bouvet, Heard/McDonald) e sem IANA próprio (Kosovo) — resolvidos e documentados no comentário de topo do arquivo (ver "Key Decisions").
- **Files modified:** `fotoorganizer/geolocation/timezones.py`, `tests/test_timezones.py`.
- **Verification:** `pytest tests/test_timezones.py -x` verde; `set(TZ_POR_PAIS) == set(PAISES_PT.values())` e validação IANA completa (`zoneinfo.available_timezones()`) passam para as 250 entradas.
- **Committed in:** `a651138` (Task 1 GREEN commit, mensagem já documenta a divergência).

**2. [Rule 3 — bloqueio de ambiente] Worktree sem `.venv` próprio**
- **Found during:** início da execução, antes da Task 1.
- **Issue:** O worktree não tinha `.venv`/dependências instaladas (`sqlalchemy` ausente ao tentar importar `fotoorganizer.geolocation.paises`) — nota já registrada em MEMORY.md sobre worktrees precisarem de `.venv` próprio.
- **Fix:** `python3.12 -m venv .venv && .venv/bin/pip install -e ".[dev]"` (mesma versão de Python do `.venv` do repositório principal). Baseline confirmado: 830 passed / 1 failed (pré-existente, `test_apple_photos.py`, fora de escopo) / 1 skipped antes de qualquer mudança desta fase.
- **Files modified:** nenhum arquivo versionado (`.venv/` já está em `.gitignore`).
- **Verification:** `pytest tests/` rodou como baseline antes e depois das mudanças desta fase.
- **Committed in:** n/a (não versionado).

---

**Total deviations:** 2 auto-fixed (1 discrepância factual do spec resolvida com o dado real, 1 bloqueio de ambiente).
**Impact on plan:** Nenhum scope creep de comportamento — o objetivo e o design da fase (tabela estática, escrita direta, sem Evidence, serialização passthrough) permanecem exatamente como especificados. O único efeito é uma tabela ~2,5x maior que a prosa do spec sugeria, sem qualquer país fora de cobertura.

## Issues Encountered

Nenhum bloqueio não coberto pelas Deviations acima. `test_apple_photos.py::test_video_entra_junto_com_a_foto` falha na baseline e continua falhando após esta fase — não relacionado a `tz_estimado` (fora do escopo desta fase, dependência `osxphotos` provavelmente ausente/desatualizada no ambiente).

## User Setup Required

None — nenhuma configuração externa necessária. `tz_estimado` é dado técnico auxiliar, sem superfície de UI nova (D-09: nenhuma tela passa a converter hora usando este campo).

## Next Phase Readiness

- `tz_estimado IS NOT NULL` já é uma coluna gravável e servida pela API — pronta para qualquer fase futura que queira consumi-la (ex.: converter `data_capturada` para hora local em alguma tela, ou medir cobertura contra o catálogo real).
- Medição contra o catálogo real (quantas fotos ganhariam `tz_estimado`, quantas só por herança) fica pendente conforme D-13 (`01-CONTEXT.md`) — catálogo de produção foi zerado em 2026-08-16 e ainda não foi repovoado; não bloqueia esta fase, roda depois, fora do critério de pronto formal.
- Nenhum bloqueio para a próxima fase do roadmap.

## Self-Check: PASSED

- Todos os 7 arquivos citados (código + teste + este SUMMARY) confirmados no disco.
- Todos os 6 commits de task (`7771860`, `a651138`, `9abf99e`, `700eeba`, `f70fbbe`, `437cc85`) confirmados em `git log`.
- `pytest tests/` completo: 837 passed, 1 failed (pré-existente, fora de escopo), 1 skipped — mesma falha da baseline antes desta fase (830 passed, 1 failed, 1 skipped), +7 testes novos todos verdes.

---
*Phase: 01-timezone-estimado*
*Completed: 2026-08-16*
