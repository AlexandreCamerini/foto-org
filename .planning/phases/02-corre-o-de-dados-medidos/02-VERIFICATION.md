---
phase: 02-corre-o-de-dados-medidos
verified: 2026-08-16T19:23:39Z
status: human_needed
score: 8/8 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Com um catálogo de produção populado, abrir a Biblioteca em alcance=tudo (o default) e conferir visualmente: miniatura/derivado de outro app (ex. thumbnail interno do Apple Fotos/Lightroom com arquivo local) não aparece mais na grade; foto do iCloud sem arquivo local (referência externa) continua aparecendo."
    expected: "A grade padrão ('Tudo') mostra o acervo real mais referências externas sem arquivo, e não mostra mais miniaturas/derivados internos de outro app com arquivo local real."
    why_human: "Confirmação visual de UI num catálogo real — grep/teste automatizado já cobre a lógica do predicado (843/843 testes verdes, incluindo os 3 testes novos que travam os dois lados), mas o item foi explicitamente declarado como <human-check> na Task 3 do 02-01-PLAN.md e o catalog.db de produção foi zerado em 2026-08-16 (STATE.md, seção Blockers), então não pôde ser executado até agora. Harvestado do PLAN.md conforme o padrão de verificação humana adiada para fim de fase."
---

# Phase 2: Correção de dados medidos Verification Report

**Phase Goal:** O filtro "Tudo" da Biblioteca distingue `SINAL` de `ACERVO` em vez de misturar os dois numa tabela sem `WHERE`.
**Verified:** 2026-08-16T19:23:39Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Com um registro `papel=SINAL` e arquivo local real (`arquivo_ausente=False`), `alcance=tudo` não o conta nem o lista (D-01) | ✓ VERIFIED | `fotoorganizer/repositories/media.py:60-63` defines `_ACERVO_OU_REFERENCIA = or_(papel==ACERVO, arquivo_ausente.is_(True))`, used in `_query`'s `else` branch (line ~225). `tests/test_repository.py:131-145` (`test_alcance_tudo_inclui_acervo_e_referencia_sem_testemunha_com_arquivo`) asserts `testemunha_com_arquivo.jpg` (papel=SINAL, arquivo_ausente=False) is absent from `listar(alcance="tudo")`. Test passes. |
| 2 | Registro `papel=SINAL` SEM arquivo local (referência externa) continua contado/listado em `alcance=tudo` — predicado é `or_(papel==ACERVO, arquivo_ausente==True)`, não `papel` puro nem `_ACERVO`/organizável (D-01, corrigido); tripwire `tests/test_sources_importer.py:428-430` continua passando sem edição | ✓ VERIFIED | Same predicate. `git diff --exit-code tests/test_sources_importer.py` against pre-phase base is clean (file untouched). `pytest tests/test_sources_importer.py::test_referencia_aparece_na_biblioteca_e_fica_fora_do_organizavel -q` → 1 passed. `test_repository.py:145` asserts `referencia_externa.jpg` IS in `listar(tudo)`. |
| 3 | Registro `papel=ACERVO` com `arquivo_ausente=True` continua contado em `alcance=tudo` (D-01) | ✓ VERIFIED | Predicate's first OR-term is `papel == ACERVO` unconditionally (no arquivo_ausente exclusion). Fixture's `acervo_ausente` record (papel=ACERVO, arquivo_ausente=True) is counted in `contar(tudo)==3` in `test_alcance_tudo_inclui_acervo_e_referencia_sem_testemunha_com_arquivo`. |
| 4 | `organizaveis` e `faltantes` mantêm exatamente a contagem de hoje — `faltantes` continua incluindo os dois tipos de testemunha, por desenho (D-01) | ✓ VERIFIED | `_query`'s `organizaveis`/`faltantes` branches unchanged (still `_acervo_ao_alcance()` / negation). `git diff` of `media.py` shows no change to those two `ALCANCES` label entries. `test_alcance_organizaveis_inalterado` asserts `==1`; `test_alcance_faltantes_inclui_os_dois_tipos_de_testemunha` asserts `==3` with both SINAL records present in `listar(faltantes)`. |
| 5 | Rótulo `ALCANCES['tudo']` no backend não usa mais "conhece" (D-02) | ✓ VERIFIED | `media.py:91` → `"tudo": "acervo inteiro, ao alcance ou não"`. `grep -rn "tudo que o app conhece" fotoorganizer/ webapp/src/` → exit code 1 (zero matches). |
| 6 | Tooltip do botão Tudo em `webapp/src/App.tsx` não promete mais "tudo que o app conhece" (D-04) | ✓ VERIFIED | `App.tsx:344` → `"seu acervo inteiro, com arquivo local ou sem — miniatura de outro app fica fora"`. Same grep confirms zero occurrences repo-wide. `git diff --numstat webapp/src/App.tsx` against pre-phase base shows exactly 1 line added/1 removed. |
| 7 | Nenhuma contagem de sidebar/painel foi alterada por esta fase; divergência entre `fontes_com_contagem`/`arvore_de_pastas` e o novo total de "tudo" fica documentada no SUMMARY, não corrigida (D-03) | ✓ VERIFIED | Read `arvore_de_pastas()` (media.py:391-468) and `fontes_com_contagem()` (493-508) directly: neither references `_ACERVO`, `_TESTEMUNHA`, `_ACERVO_OU_REFERENCIA` or `_query` — both count all rows unconditionally, unchanged by this phase. `estatisticas()` (593-611) and `panorama()` (510+) use `_ACERVO`/`_TESTEMUNHA` as before, untouched. SUMMARY's 8-row audit table matches source directly; the "sem justificativa" finding for `arvore_de_pastas` is accurate (no code comment there, unlike `fontes_com_contagem`'s comment at line 499-502). |
| 8 | O comentário de `_query()` descreve a regra que o código realmente aplica | ✓ VERIFIED | `grep -n "de qualquer filtro" fotoorganizer/repositories/media.py` → exit 1 (phrase removed). Comment at media.py:216-222 accurately states "tudo" shows acervo (any) plus external reference without local file, not testemunha with real file; correctly describes `organizaveis`/`faltantes` behavior. |

**Score:** 8/8 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `fotoorganizer/repositories/media.py` | `_ACERVO_OU_REFERENCIA` predicate applied in `tudo` branch, backend label fixed, `_query` comment rewritten | ✓ VERIFIED | All three present and correct (lines 60-63, 91, 216-222). `grep -c "_ACERVO_OU_REFERENCIA"` → 3 occurrences (definition + comment mention + usage in `_query`), ≥2 as required. |
| `tests/test_repository.py` | Test locking testemunha-com-arquivo out of `tudo` and referência-sem-arquivo inside `tudo` | ✓ VERIFIED | `repo_com_testemunha` fixture (4 records) + 3 new tests (lines 89-164). `MediaRole.SINAL` used correctly (2 occurrences in fixture). All assertions match plan's `<behavior>` spec exactly. |
| `webapp/src/App.tsx` | Tooltip without "tudo que o app conhece" promise | ✓ VERIFIED | Line 344, new text confirmed; diff is a single-line string swap, no structural change. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `fotoorganizer/repositories/media.py::_query` | `or_(papel==ACERVO, arquivo_ausente.is_(True))` | `.where(_ACERVO_OU_REFERENCIA)` in `else` branch | ✓ WIRED | Confirmed by direct read of `_query` (line ~225): `else: stmt = select(MediaFile).where(_ACERVO_OU_REFERENCIA)`. No `select(MediaFile)` without WHERE remains — `grep -n "stmt = select(MediaFile)$"` matches nothing inside `_query`. |
| `tests/test_sources_importer.py:428` | `MediaRepository.contar(MediaFilters(alcance='tudo'))` | tripwire regression, unedited | ✓ WIRED | File untouched (`git diff --exit-code` clean); test passes in isolation and in full suite. |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full backend test suite green | `.venv/bin/python -m pytest -q` | `843 passed, 272 warnings in 69.84s` | ✓ PASS |
| Targeted repository + importer + model tests | `pytest tests/test_repository.py tests/test_sources_importer.py tests/test_media_model.py -q` | `39 passed` | ✓ PASS |
| Tripwire test in isolation | `pytest tests/test_sources_importer.py::test_referencia_aparece_na_biblioteca_e_fica_fora_do_organizavel -q` | `1 passed` | ✓ PASS |
| Webapp TypeScript build | `cd webapp && npx tsc -b --noEmit` | exit code 0, no output | ✓ PASS |
| Full slice gate | `scripts/verificar.sh` | `[1/4] 843 passed` / `[2/4] 19/19 cenários` / `[3/4] 120 passed` / `[4/4] built in 669ms` / `✅ Fatia verde` | ✓ PASS |
| Only expected files touched | `git diff --stat` (post-phase-start base `0936f47`) vs current | `media.py`, `test_repository.py`, `App.tsx` only — matches plan's `files_modified` exactly | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|--------------|--------|----------|
| BUG-03 | 02-01-PLAN.md | Filtro "Tudo" (`alcance=tudo`) passa a filtrar de fato, em vez de `select(MediaFile)` sem `WHERE` | ✓ SATISFIED | `_ACERVO_OU_REFERENCIA` predicate now applied; `select(MediaFile)` without WHERE no longer exists in `_query`'s else branch; new tests lock both directions of the fix; tripwire test protecting the pre-existing "referência externa visível" feature (commit `1b125f7`) still passes unedited. REQUIREMENTS.md traceability table updated status would move BUG-03 from "Pending" to complete (not yet edited in REQUIREMENTS.md itself — file still shows `[ ]`/"Pending", a doc-sync item, not a code gap). |

No orphaned requirements: REQUIREMENTS.md maps only BUG-03 to Phase 2, and it is the sole `requirements:` entry declared in `02-01-PLAN.md` frontmatter.

Note: `.planning/REQUIREMENTS.md` line 59 still shows `- [ ] **BUG-03**` (unchecked) and the traceability table (line 208) still shows `Pending`. This is a documentation-sync gap, not a code/functional gap — flagging for the phase-closure step, not blocking this verification's `human_verification`-driven status.

### Anti-Patterns Found

None. Scanned all three modified files (`media.py`, `test_repository.py`, `App.tsx`) for `TBD|FIXME|XXX|TODO|HACK|PLACEHOLDER` and placeholder-language patterns — zero matches.

### Human Verification Required

#### 1. Visual confirmation of "Tudo" filter on a populated catalog

**Test:** Open the Biblioteca with `alcance=tudo` (the default view) on a populated `catalog.db`, and confirm: (a) thumbnails/derivatives belonging to another app's internal package (e.g. an Apple Fotos/Lightroom-internal miniature with a real local file) no longer appear in the grid; (b) a photo that only exists as an external reference (iCloud-only, no local file) still appears.

**Expected:** The default Library grid shows the real acervo plus file-less external references, and no longer shows internal thumbnails/derivatives that have a real local file.

**Why human:** This is a visual/UI confirmation on real data, explicitly declared as an optional `<human-check>` in Task 3 of `02-01-PLAN.md`. It could not be run because the production `catalog.db` was zeroed on 2026-08-16 (see `STATE.md`, Blockers section). Automated coverage (843/843 tests, including 3 new tests that lock both directions of the predicate on a synthetic 4-record fixture) gives high confidence the logic is correct, but the plan itself calls for a visual pass once a populated catalog exists. Harvested per the end-of-phase human-verification-deferral pattern.

### Gaps Summary

No functional gaps found. All 8 derived must-haves (roadmap goal decomposed into observable truths per PLAN.md frontmatter) are verified directly against the current, final state of the code — not against the plan's original (superseded) `papel == ACERVO` predicate description, which was corrected in-place per the documented mid-execution checkpoint. All artifacts exist, are substantive, and are wired. The full automated gate (`scripts/verificar.sh`) closes green with all four steps passing. The only reason this report is not `passed` is a single deferred human-check item (visual confirmation on a populated catalog) that the plan itself declared optional and could not run due to an unrelated, already-documented blocker (production catalog reset). This does not indicate the phase goal is unachieved — it indicates one visual confirmation step is still outstanding and should be run the next time a full catalog scan is available.

---

*Verified: 2026-08-16T19:23:39Z*
*Verifier: Claude (gsd-verifier)*
