---
phase: 01-timezone-estimado
verified: 2026-08-16T00:00:00Z
status: passed
score: 9/9 must-haves verified
overrides_applied: 0
---

# Phase 1: Timezone estimado Verification Report

**Phase Goal:** Fotos ganham `tz_estimado` — fuso IANA estimado a partir do
país já atribuído à foto por qualquer origem (GPS próprio, herança
temporal de D-025, ou nome de pasta) — fechando o modelo de dois instantes
de D-038: `tz_estimado IS NOT NULL` passa a ser o sinal de "fuso conhecido"
do catálogo.

**Verified:** 2026-08-16
**Status:** passed
**Re-verification:** No — initial verification (post code-review-fix cycle)

**Verification approach note:** this phase went through PLAN → SUMMARY →
REVIEW (found CR-01 critical, WR-01 warning) → REVIEW-FIX (commits
`3352fd3`, `93d1216`). Verification below checks the CURRENT state of
`engine.py` after both fixes, not the pre-fix code the original SUMMARY.md
describes. Both fixes were verified by (a) line-by-line comparison against
the cascade they claim to replicate (`_evidencias_geo`) and (b) an
independent, non-committed reproduction script run against the real
`SuggestionEngine`/`FakeGeocoder` — not just re-reading REVIEW-FIX's prose.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Foto com país resolvido (GPS próprio, herança D-025, ou pasta) ganha `tz_estimado` depois de `gerar()` | ✓ VERIFIED | `tests/test_suggestion_engine.py::test_tz_estimado_de_gps_proprio`, `::test_tz_estimado_de_pais_herdado` pass; independently reproduced via script (GPS→`Europe/Paris`) |
| 2 | Sem país conhecido, `tz_estimado=None` — nunca inventa, nunca lança erro (D-04) | ✓ VERIFIED | `::test_tz_estimado_none_sem_pais_conhecido` passes; `_pais_efetivo` returns `None` through all 4 cascade branches, `_atualizar_tz_estimado` uses `TZ_POR_PAIS.get(pais) if pais else None` — no exception path |
| 3 | Regenerar sugestões atualiza `tz_estimado` — não deixa valor obsoleto (incl. mídia com sugestão já decidida — CR-01) | ✓ VERIFIED | `::test_tz_estimado_atualiza_ao_regenerar_sugestoes` (pending media) AND `::test_tz_estimado_atualiza_mesmo_com_sugestao_decidida` (APROVADA media) both pass. Confirmed `_midias_com_decisao` filters `status != PENDENTE` so the APROVADA test genuinely exercises the "already-decided" path the original CR-01 bug missed. Independently reproduced: GPS moved outside geocoder coverage between two `gerar()` calls → `tz_estimado` went `Europe/Paris` → `None` on the second call, decision preserved |
| 4 | `GET /api/midia/{id}` devolve `tz_estimado` | ✓ VERIFIED | `fotoorganizer/server/app.py:302` `"tz_estimado": m.tz_estimado` inside `_media_json`, used by both grid (`app.py:605`) and detail (`app.py:689`); `tests/test_server_api.py::test_detalhe_traz_o_tz_estimado` passes |
| 5 | Toda entrada de `TZ_POR_PAIS` é IANA válida (D-06), tabela cobre `PAISES_PT` por completo com chave PT-BR (D-05) | ✓ VERIFIED | `tests/test_timezones.py` — `set(TZ_POR_PAIS) == set(PAISES_PT.values())` and full `zoneinfo.available_timezones()` validation, both pass. Table has 250 entries (current `PAISES_PT` size, not the "98" cited in stale spec prose — dynamic set-equality means no country is missed regardless of the count) |
| 6 | `tz_estimado` gravado direto em `MediaFile`, sem `Evidence`/`Suggestion`, sem entrada em `docs/CONFIANCA.md` (D-03) | ✓ VERIFIED | No `Evidence`/`Suggestion` object created for `tz_estimado` anywhere in `engine.py`; `git diff` since baseline (`40d78ae..HEAD`) touches no file under `docs/CONFIANCA.md` |
| 7 | Nenhuma dependência nova instalada (D-07) | ✓ VERIFIED | `pyproject.toml` unchanged in phase diff; `timezones.py` is a pure stdlib literal dict, validated only via `zoneinfo` (stdlib) |
| 8 | País multi-fuso (Brasil, EUA, Rússia, Canadá, Austrália) resolve para fuso da capital/maior população, documentado em comentário no topo do arquivo (D-08) | ✓ VERIFIED | `timezones.py:1-47` docstring documents the rule with the 5 named examples plus extensions (Kosovo, Antarctica, uninhabited territories); table values match exactly: Brasil→`America/Sao_Paulo`, EUA→`America/New_York`, Rússia→`Europe/Moscow`, Canadá→`America/Toronto`, Austrália→`Australia/Sydney` |
| 9 | `data_capturada`/`data_capturada_utc` não reescritos nesta fase (D-09) | ✓ VERIFIED | `git diff 40d78ae..HEAD -- fotoorganizer/classification/engine.py fotoorganizer/server/app.py \| grep data_capturada` returns nothing |

**Score:** 9/9 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `fotoorganizer/geolocation/timezones.py` | `TZ_POR_PAIS: dict[str, str]`, PT-BR name → IANA zone | ✓ VERIFIED | 250 entries, not reexported in `geolocation/__init__.py` (grep confirms 0 hits), D-08 rule documented in module docstring |
| `tests/test_timezones.py` | Coverage + IANA validation | ✓ VERIFIED | 2 tests, both pass, exact form specified in PLAN |
| `fotoorganizer/classification/engine.py` | Direct write of `media.tz_estimado` | ✓ VERIFIED (relocated post-fix) | Original write site (`_persistir_sugestao`) removed by CR-01 fix; write now happens unconditionally in new `_atualizar_tz_estimado` (engine.py:437-451), called from `gerar()` on the full `organizaveis` list (not just pending). Still no `Evidence`/`Suggestion` involved |
| `fotoorganizer/server/app.py` | `tz_estimado` in `_media_json` | ✓ VERIFIED | `app.py:302`, passthrough, no extra query |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `engine.py` | `geolocation/timezones.py` | `TZ_POR_PAIS.get(...)` | ✓ WIRED | Present at `engine.py:451`, inside `_atualizar_tz_estimado` (relocated from `_persistir_sugestao` by the CR-01 fix; PLAN's literal pattern `TZ_POR_PAIS.get(evidencias["pais"].valor)` no longer exists verbatim, but the functional link — engine consumes the table to resolve country→zone — is intact and more correct than the original) |
| `server/app.py` | `models/catalog.py` (`MediaFile.tz_estimado`) | passthrough in `_media_json` | ✓ WIRED | `app.py:302`, and `catalog.py:209` confirms the column exists |

### Behavioral Spot-Checks (independent, non-test-suite reproduction)

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| CR-01 fix: `tz_estimado` updates for media with an APROVADA suggestion when effective country changes | Standalone script: create media w/ GPS → `gerar()` → approve suggestion → move GPS out of geocoder coverage → `gerar()` again | `tz_estimado`: `Europe/Paris` → `None`; suggestion stayed `APROVADA` | ✓ PASS |
| WR-01 fix: `location_id` clears to `None` when coordinate stops resolving | Same script, direct DB read of `MediaFile.location_id` | `location_id`: `1` → `None` after 2nd `gerar()` | ✓ PASS |
| Full test suite regression | `.venv/bin/pytest tests/ -q` | `840 passed, 0 failed, 0 skipped` (up from 830 passed/1 failed/1 skipped baseline before this phase; the phase's own SUMMARY reported 837/1/1 pre-fix — the previously-failing `test_apple_photos.py` test now also passes, unrelated to this phase) | ✓ PASS |
| Scoped test suite (`test_timezones.py` + `test_suggestion_engine.py` + `test_server_api.py`) | `.venv/bin/pytest tests/test_timezones.py tests/test_suggestion_engine.py tests/test_server_api.py -q` | `118 passed` | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|--------------|--------|----------|
| TZ-01 | 01-01-PLAN.md | Sistema infere `tz_estimado` a partir do país já atribuído, gravado direto em `MediaFile`, sem Evidence/revisão | ✓ SATISFIED | All 9 truths above; `REQUIREMENTS.md:33-39` and `:194` both mark it complete; no orphaned requirements found for Phase 1 (TZ-01 is the only ID mapped) |

### Anti-Patterns Found

None. Scanned all 6 phase-modified files (`timezones.py`, `test_timezones.py`, `engine.py`, `test_suggestion_engine.py`, `server/app.py`, `test_server_api.py`) for `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER`/stub markers. Only hits were pre-existing, unrelated `_PLACEHOLDER`/`PLACEHOLDERS_TEMPLATE_VALIDOS` identifiers in `app.py` (a template-variable feature, not a stub marker).

### Human Verification Required

None required to close the phase. See Gaps Summary below for a documented, non-blocking residual concern (WR-01 test coverage) and how it was resolved without deferring to a human check.

### Gaps Summary

No gaps against the phase's must-haves. Two items surfaced during verification that are worth recording even though neither blocks the phase goal:

1. **CR-01 cascade parity — resolved, not deferred.** `01-REVIEW-FIX.md` explicitly flagged the `_pais_efetivo` cascade (duplicated from `_evidencias_geo` to avoid touching evidence justification text) as "fixed: requires human verification." This verification pass did that check: line-by-line comparison against `_evidencias_geo` (including confirming `Heranca.fator_de("pais")` is non-`None` for any `Heranca` that exists at all, since país's 12h window equals the herança search window `JANELA_HERANCA` — so the herdado branch's stopping condition is practically always satisfied when a `Heranca` exists, matching the original), confirmation that `Location.pais` is nullable (`models/geo.py:17`) and that both old and new code paths stop the cascade unconditionally on a resolved GPS-próprio location regardless of whether `pais` is populated (so the final `tz_estimado` outcome is identical even in that edge case), plus an independent runtime reproduction of the exact scenario the fix targets (approved suggestion, country changes, `tz_estimado` follows). This is treated as closing the fixer's request for human review, not as an open item — no human_verification entry added.

2. **WARNING — WR-01 fix has no dedicated regression test.** `git show 3352fd3` touches only `engine.py`; no test asserts that `media.location_id` returns to `None` when a previously-resolving coordinate stops resolving. The fix is correct (independently reproduced above), and the full suite (840 tests) passes, but none of those 840 tests would fail if `3352fd3`'s one-line change were reverted — the only assertion exercising this exact path is the throwaway script written during this verification, which is not committed to the repo. Recommend a follow-up test (e.g. extending `test_location_id_resolvido_mesmo_para_sugestao_ja_decidida` or a new test) asserting `location_id` clears to `None` in a second `gerar()` when the coordinate moves outside geocoder coverage. Not a phase blocker — WR-01 was never a PLAN must-have, it's an adjacent bug the reviewer found and fixed as a bonus — but flagged so it doesn't silently regress.

3. **Key-link text drift (informational, not a gap).** The PLAN's `key_links` pattern (`TZ_POR_PAIS\.get`) still matches, but the literal snippet cited in the PLAN (`TZ_POR_PAIS.get(evidencias["pais"].valor)`) was removed by the CR-01 fix — the call now lives in the new `_atualizar_tz_estimado` method as `TZ_POR_PAIS.get(pais)`. Functionally equivalent and more correct (fixes the frozen-value bug the PLAN's own snippet would have had), just noting the code moved since SUMMARY.md was written.

4. **D-13 (deferred by design, not a gap):** measuring `tz_estimado` coverage against the real catalog (~2,235 photos cited in ROADMAP) is explicitly out of scope for this phase's Definition of Done — `catalog.db` was reset 2026-08-16 and hasn't been repopulated. Confirmed this is documented as deferred in `01-CONTEXT.md` D-13, not silently dropped.

---

_Verified: 2026-08-16_
_Verifier: Claude (gsd-verifier)_
