# Phase 2: Correção de dados medidos - Pattern Map

**Mapped:** 2026-08-16
**Files analyzed:** 3 (1 source + 2 test files touched/verified)
**Analogs found:** 3 / 3 (all in-file or same-package siblings — no cross-cutting search needed)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `fotoorganizer/repositories/media.py` (`_query`, `tudo` branch, lines 201-206) | repository (query builder) | CRUD (read/filter) | same file, same method — `organizaveis`/`faltantes` branches (lines 201-204) | exact (sibling code, same function) |
| `fotoorganizer/repositories/media.py` (`ALCANCES["tudo"]` label, line 70) | config (label dict) | — | same file — `organizaveis`/`faltantes` entries (lines 71-72) | exact |
| `tests/test_repository.py` (extend `repo` fixture or add new test) | test | CRUD (read/filter assertions) | `tests/test_sources_importer.py:397-433` (`alcance=` assertion style) + `tests/test_media_model.py:60-77` (SINAL/ausente/offline fixture construction) | role-match, combined |
| `tests/test_sources_importer.py:428-430` (existing assertions, must be re-verified, not necessarily edited) | test | CRUD (read/filter assertions) | itself (regression anchor) | exact |

## Pattern Assignments

### `fotoorganizer/repositories/media.py` — `_query()` tudo branch (repository, CRUD)

**Analog:** the immediate sibling branches in the same method, `fotoorganizer/repositories/media.py:196-206`

**Structural pattern to copy** (lines 196-206, current state):
```python
def _query(self, filters: MediaFilters):
    # Testemunhas ficam fora da biblioteca visível, das contagens e de
    # qualquer filtro. Existem só para doar GPS e horário à correlação.
    # Junto delas fica o acervo cuja fonte não responde: é foto do dono,
    # e mesmo assim não há o que abrir, revisar ou copiar agora.
    if filters.alcance == "organizaveis":
        stmt = select(MediaFile).where(_acervo_ao_alcance())
    elif filters.alcance == "faltantes":
        stmt = select(MediaFile).where(~_acervo_ao_alcance())
    else:
        stmt = select(MediaFile)
    ...
```

The shape to reuse for the `else` branch (which becomes the explicit `tudo` case) is exactly the `if`/`elif` pattern already there: `stmt = select(MediaFile).where(X)`. Both `organizaveis` and `faltantes` already demonstrate "filter, don't leave the branch bare" — the fix is making `tudo` follow the same shape instead of being the one branch with no `.where(...)` at all.

**Named-predicate convention to reuse (if a new predicate is introduced):** `_acervo_ao_alcance()` at lines 45-64 is the established style for "boolean predicate as a small named function with a docstring explaining why it exists and what it's NOT (the docstring explicitly contrasts it with the simpler `_ACERVO`)." If the fix introduces a new predicate (rather than reusing `_ACERVO` verbatim), follow this docstring convention — same file, same section, immediately above.

**Existing predicates already in file** (lines 40-42, imports already present at line 20 — `MediaRole` is already imported, no new import needed):
```python
_ACERVO = MediaFile.organizavel
_TESTEMUNHA = ~_ACERVO
```

### ⚠️ Flag: `_ACERVO` is not the same thing as "papel == ACERVO" — evidence, not a resolution

CONTEXT.md's D-01 says `tudo` should mean `papel == MediaRole.ACERVO` (alcançável ou não), "mesmo critério de `_ACERVO`/organizavel." But `_ACERVO = MediaFile.organizavel`, and `organizavel` (`fotoorganizer/models/catalog.py:250-276`) is:

```python
@hybrid_property
def organizavel(self) -> bool:
    return (
        self.papel == MediaRole.ACERVO
        and not self.arquivo_ausente
        and not self.arquivo_offline
    )
```

That's stricter than bare `papel == MediaRole.ACERVO` — it already excludes cloud-only references (`arquivo_ausente=True`) and files that went offline (`arquivo_offline=True`), regardless of papel.

This is empirically load-bearing: `tests/test_sources_importer.py:398-433` (`test_referencia_aparece_na_biblioteca_e_fica_fora_do_organizavel`) builds a `papel=ACERVO` (default), `arquivo_ausente=True` record and asserts:
```python
assert repo.contar(MediaFilters(alcance="tudo")) == 1   # line 428
```
- If the `tudo` branch predicate reuses `_ACERVO` (i.e. `MediaFile.organizavel`) verbatim → this becomes `0`, and the existing test breaks.
- If the `tudo` branch predicate uses bare `MediaFile.papel == MediaRole.ACERVO` → this stays `1`, test still passes.

Secondary (weaker) evidence pointing the same direction: `webapp/src/App.tsx:343` has a hardcoded tooltip for the `tudo` button reading `"tudo que o app conhece, inclusive sem arquivo local"` — "inclusive sem arquivo local" is consistent with keeping `arquivo_ausente` records in `tudo`, i.e. with the bare-`papel` reading, not the `organizavel` reading.

CONTEXT.md's own "Claude's Discretion" section already anticipated this fork ("reutilizar `_ACERVO` diretamente ou uma pequena função nomeada — desde que o resultado seja idêntico e o teste cubra o caso testemunha-excluída-de-tudo") and left it to planner/executor. Not resolving it here — surfacing the discriminating fact (`test_sources_importer.py:428`) so whichever predicate is chosen, the executor knows which existing test is the tripwire.

### `ALCANCES["tudo"]` label (config, D-02)

**Analog:** sibling entries in the same dict, `fotoorganizer/repositories/media.py:69-73`
```python
ALCANCES: dict[str, str] = {
    "tudo": "tudo que o app conhece",
    "organizaveis": "acervo com o arquivo ao alcance agora",
    "faltantes": "o resto: sem arquivo, fora de alcance ou não é acervo",
}
```
Style to match: short, no verb "conhece", starts describing scope directly (`"acervo com..."`, `"o resto: ..."`). New `tudo` label should follow the same terse, non-promissory register — e.g. structured as `"<scope>, <qualifier>"` like the `organizaveis`/`faltantes` entries, per D-02's constraints (no "conhece", no double "acervo").

### `tests/test_repository.py` — add/extend coverage for tudo excluding SINAL (test, CRUD)

**Analog 1 (fixture construction — SINAL/ausente/offline records):** `tests/test_media_model.py:11-77`
```python
def _fonte(session, caminho="/Users/eu/Pictures", apelido="Pictures"):
    source = Source(caminho=caminho, apelido=apelido)
    session.add(source)
    session.flush()
    return source


def _arquivo(session, source, nome, **kw):
    media = MediaFile(
        source_id=source.id, caminho=f"/Users/eu/Pictures/{nome}",
        pasta="/Users/eu/Pictures", nome=nome,
        extensao=nome.rsplit(".", 1)[-1].lower(), tamanho=1, **kw
    )
    session.add(media)
    session.flush()
    return media


def test_arquivo_offline_e_ortogonal_a_papel_e_ausente(migrated_engine):
    ...
    testemunha = _arquivo(session, f, "testemunha.jpg", papel=MediaRole.SINAL)
    ausente = _arquivo(session, f, "ausente.jpg", arquivo_ausente=True)
    offline = _arquivo(session, f, "offline.jpg", arquivo_offline=True)
```
This is the established pattern for constructing a `papel=MediaRole.SINAL` record via `**kw` passthrough — directly reusable for the new "testemunha excluída de tudo" test case that CONTEXT.md's Claude's Discretion section requires.

**Analog 2 (repository-level fixture + assertion style, same file being extended):** `tests/test_repository.py:10-33` (existing `repo` fixture) is built the same way (`Source` + `MediaFile` rows via `session.add`), and `tests/test_repository.py` already has `MediaFilters`/`MediaRepository` imported (line 7). The new test should follow this file's existing fixture idiom rather than importing `test_media_model.py`'s helpers directly — same repo pattern, just needs a `papel=MediaRole.SINAL` row added (requires adding `MediaRole` to the existing import at line 6: `from fotoorganizer.models import MediaFile, Source` → add `MediaRole`).

**Analog 3 (alcance= assertion style):** `tests/test_sources_importer.py:422-433`
```python
repo = MediaRepository(factory)
assert repo.contar(MediaFilters(alcance="tudo")) == 1
assert repo.contar(MediaFilters(alcance="faltantes")) == 1
assert repo.contar(MediaFilters(alcance="organizaveis")) == 0
```
This is the established idiom for asserting `contar()` counts per `alcance` value — three parallel assertions, one per filter value, no loop. Reuse this shape for the new SINAL-exclusion test: assert `tudo` includes the ACERVO-but-unreachable record and excludes the SINAL record, while `organizaveis`/`faltantes` behavior is unchanged.

### `tests/test_sources_importer.py:428` (regression anchor, not necessarily edited)

No pattern extraction needed — this is the existing assertion that becomes the tripwire described in the flag above. Whatever predicate the executor picks for the `tudo` branch, this line must be run and re-verified; if it fails, that confirms the `_ACERVO`/`organizavel` reading was chosen and needs reconciling with D-01's "alcançável ou não."

## Shared Patterns

### Repository filter branches (CRUD read)
**Source:** `fotoorganizer/repositories/media.py:196-206` (`_query`, `organizaveis`/`faltantes` branches)
**Apply to:** the `tudo` branch edit
```python
if filters.alcance == "organizaveis":
    stmt = select(MediaFile).where(_acervo_ao_alcance())
elif filters.alcance == "faltantes":
    stmt = select(MediaFile).where(~_acervo_ao_alcance())
```
Every branch filters explicitly via `.where(...)`; the bug is the `else` branch not doing so. Same shape applies to the fix.

### Named boolean predicate with docstring
**Source:** `fotoorganizer/repositories/media.py:45-64` (`_acervo_ao_alcance`)
**Apply to:** any new predicate introduced for the `tudo` branch, if the executor opts for "pequena função nomeada" over reusing `_ACERVO` inline.

### Test fixture: constructing SINAL / arquivo_ausente / arquivo_offline records
**Source:** `tests/test_media_model.py:60-77` (`test_arquivo_offline_e_ortogonal_a_papel_e_ausente`)
**Apply to:** new test in `tests/test_repository.py` covering "testemunha excluída de tudo."

### Test assertion: `contar(MediaFilters(alcance=...))` per-value checks
**Source:** `tests/test_sources_importer.py:428-430`
**Apply to:** new test in `tests/test_repository.py`.

## No Analog Found

None — all files/edits map to close in-package or in-file analogs.

## Note for planner (out of CONTEXT.md's named scope, informational only)

`webapp/src/App.tsx:341-347` has a hardcoded `title` tooltip for the `tudo` selector button reading `"tudo que o app conhece, inclusive sem arquivo local"` — same "conhece" wording D-02 flags for the backend `ALCANCES["tudo"]` label, but in a location `canonical_refs` didn't name. Confirmed via grep that `/api/midia/alcances` (backed by `ALCANCES`) is not fetched anywhere in `webapp/src/*.ts(x)` — the frontend button labels/tooltips are hardcoded independently of the backend dict. No test asserts this exact string (checked `webapp/src/App.test.tsx`). CONTEXT.md's specifics section ("só o texto do rótulo do seletor já existente") is ambiguous about whether it means this frontend string or the backend dict entry — flagging for planner to decide scope, not deciding it here.

## Metadata

**Analog search scope:** `fotoorganizer/repositories/media.py`, `fotoorganizer/models/catalog.py`, `tests/test_repository.py`, `tests/test_sources_importer.py`, `tests/test_media_model.py`, `webapp/src/App.tsx`
**Files scanned:** 6
**Pattern extraction date:** 2026-08-16
