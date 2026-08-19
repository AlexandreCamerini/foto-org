# Phase 1: Timezone estimado - Pattern Map

**Mapped:** 2026-08-16
**Files analyzed:** 6 (1 new, 5 modified)
**Analogs found:** 6 / 6

## Flags for Planner (read before assigning actions)

1. **`_persistir_sugestao` insertion deviates from the spec's verbatim snippet — deliberately, flag this to the executor.**
   `docs/prompts/fase-11-timezone-estimado.md:116-119` and `01-CONTEXT.md` D-03 both give:
   ```python
   if "pais" in evidencias:
       media.tz_estimado = TZ_POR_PAIS.get(evidencias["pais"].valor)
   ```
   with no `else`. That literal snippet leaves a stale `tz_estimado` from a
   previous run when a later `gerar()` no longer resolves `"pais"` for that
   media (e.g. its GPS/heritage donor changed) — the same failure mode
   `_persistir_herancas` explicitly guards against for `gps_lat_estimado`
   (`engine.py:340-347`, `if heranca is None: media.gps_lat_estimado = None`).
   The spec's own test list requires "regenerar sugestões atualiza
   tz_estimado" (spec line 144), which only passes with an explicit `else`.
   Recommended, still literally matching D-04 ("nunca inventa, nunca lança
   erro"):
   ```python
   media.tz_estimado = (
       TZ_POR_PAIS.get(evidencias["pais"].valor) if "pais" in evidencias else None
   )
   ```
   Planner: pick one and say so explicitly in the plan — don't leave the
   executor to silently choose between the spec's snippet and this one.

2. **`zoneinfo.available_timezones()` needs OS tzdata; no `tzdata` PyPI package pinned.**
   `pyproject.toml` has no `tzdata` dependency, and there's no `.github/`
   CI config in this repo. `zoneinfo.available_timezones()` reads the
   system's IANA database — present on macOS (this project's only runtime
   target per `CLAUDE.md`, "App desktop macOS") and confirmed working in
   this environment (598 zones). If `pytest` ever runs on a bare Linux
   container without the OS tzdata package, `test_todo_valor_e_identificador_iana_valido`
   could fail or (worse) silently pass against an empty set. Not a blocker
   for this phase (macOS-only app), but worth one line in the plan/test file
   so a future CI setup doesn't get a mystery failure.

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|----------------|
| `fotoorganizer/geolocation/timezones.py` (new file) | config (static table) | transform (lookup) | `fotoorganizer/geolocation/paises.py` | exact |
| `fotoorganizer/classification/engine.py` (existing file; `_persistir_sugestao` function modified) | service | CRUD (direct write, no Evidence) | same file, `_persistir_herancas` (`engine.py:328-351`) + `location_id` write in `_evidencias_geo` (`engine.py:811-833`) | exact (self-analog) |
| `fotoorganizer/server/app.py` (existing file; `_media_json` function modified) | controller (JSON serializer) | request-response | same function, existing fields (`gps_lat_efetivo`/`gps_estimado`, `app.py:275-308`) | exact (self-analog) |
| `tests/test_timezones.py` (new file) | test | transform/validation | `tests/test_paises.py` | exact |
| `tests/test_suggestion_engine.py` (existing file; new test cases added) | test | CRUD | same file, `ambiente` fixture + `test_estimativa_some_quando_a_foto_ganha_gps_proprio` (`test_suggestion_engine.py:1026-1057`) | exact (self-analog) |
| `tests/test_server_api.py` (existing file; new test case added) | test | request-response | `test_detalhe_traz_a_foto_que_doou_a_coordenada` (`test_server_api.py:862-887`) | exact |

Note for planner: only `timezones.py` and `test_timezones.py` are brand-new
files; `engine.py`, `app.py`, `test_suggestion_engine.py`, `test_server_api.py`
are large existing files getting a small, localized addition each — the
role/data-flow labels above describe the touched function/section, not a
rewrite of the whole file.

No files with missing analogs — this phase is entirely "extend an existing,
well-established pattern," per D-03/D-05 (explicit precedent, not new
mechanism).

---

## Pattern Assignments

### `fotoorganizer/geolocation/timezones.py` (new — config/static table)

**Analog:** `fotoorganizer/geolocation/paises.py` (full file read, 234 lines)

**Module shape to copy** (`paises.py:1-21`):
```python
"""Nome canônico de país, em português, a partir de qualquer entrada.
...
Nenhuma rede: é tabela estática, como manda o invariante 4.
"""

from __future__ import annotations

import re
import unicodedata

# ISO 3166-1 alfa-2 → nome em português do Brasil.
PAISES_PT: dict[str, str] = {
    "AD": "Andorra", "AE": "Emirados Árabes Unidos", ...
}
```

**What to copy for `timezones.py`:**
- Module docstring explaining the "why" (grosseira granularidade, zero rede, invariante 4) — same voice as `paises.py`'s docstring.
- `from __future__ import annotations` (project convention, present in every module read this pass).
- One flat `dict[str, str]` literal, no builder logic needed (unlike `paises.py`'s `_CANONICO`/`_APELIDOS` machinery — `timezones.py` per spec is just the table, no normalization/lookup helpers required beyond `TZ_POR_PAIS.get(...)`).
- A comment block at the top documenting the "multi-timezone country → capital/largest-city" rule once (D-08), not per-entry — mirrors how `paises.py` documents its ISO-key-not-name-key rule once in the docstring rather than per country.
- Keys are the exact strings `PAISES_PT.values()` produces (Portuguese names), **not** the ISO alfa-2 codes that key `PAISES_PT` itself — this is the one structural difference from `paises.py`, called out explicitly in D-05/spec §1.

**No helper functions needed:** unlike `paises.py` (`pais_por_codigo`, `canonizar_pais`, `identificar_paises`, `limpar_regiao`), the consumer in `engine.py` does a plain `TZ_POR_PAIS.get(nome)` — no normalization layer, because the key is already the canonical PT-BR string produced by `paises.py` itself (see D-05: "não precisa recodificar").

---

### `fotoorganizer/classification/engine.py` — `_persistir_sugestao` (modified)

**Analog 1 (direct-write-no-Evidence precedent):** `_persistir_herancas` (`engine.py:328-351`)

```python
@staticmethod
def _persistir_herancas(midias, herancas: dict[int, Heranca]) -> None:
    """Grava a coordenada herdada — quem doou e a que distância no tempo.
    ...
    """
    for media in midias:
        heranca = herancas.get(media.id)
        if heranca is None or media.gps_lat is not None:
            media.gps_lat_estimado = None
            media.gps_lon_estimado = None
            media.gps_estimado_de_id = None
            media.gps_estimado_delta_s = None
            continue
        media.gps_lat_estimado = heranca.lat
        media.gps_lon_estimado = heranca.lon
        media.gps_estimado_de_id = heranca.doador_id
        media.gps_estimado_delta_s = int(heranca.delta.total_seconds())
```

**Analog 2 (write inside the ORM object mid-computation, not via `Evidence`):** `location_id` assignment inside `_evidencias_geo` (`engine.py:811-814`, `830-833`):

```python
if media.gps_lat is not None and self._resolver is not None:
    location = self._resolver.resolve(session, media.gps_lat, media.gps_lon)
    if location is not None:
        media.location_id = location.id
        ...
```

**Exact insertion point — inside `_persistir_sugestao`** (`engine.py:1052-1063`, current code):
```python
evidencias: dict[str, Evidence] = {}
for draft in drafts:
    evidencia = Evidence(
        media_id=media.id, campo=draft.campo, origem=draft.origem,
        valor=draft.valor, nivel=nivel_para_score(draft.score),
        score=draft.score, justificativa=draft.justificativa,
        versao_logica=VERSAO_LOGICA,
    )
    session.add(evidencia)
    evidencias[draft.campo] = evidencia

campos = {campo: ev.valor for campo, ev in evidencias.items()}
```

**Core pattern to add** (insert right after the `evidencias[draft.campo] = evidencia` loop, before `campos = {...}`) — **see "Flags for Planner" #1 above before picking one of these two forms:**

Spec's verbatim snippet (`docs/prompts/fase-11-timezone-estimado.md:116-119`, D-03):
```python
if "pais" in evidencias:
    media.tz_estimado = TZ_POR_PAIS.get(evidencias["pais"].valor)
```

Recommended alternative (matches `_persistir_herancas`'s "always reflects
current run" discipline and the spec's own recompute-test requirement,
spec line 144):
```python
media.tz_estimado = (
    TZ_POR_PAIS.get(evidencias["pais"].valor) if "pais" in evidencias else None
)
```
Both forms satisfy D-04's "never invent, never raise" — `.get()` on an
unknown-but-present country name already degrades to `None` without
exception. The difference only shows up on a *second* `gerar()` call where
`"pais"` was present before and is absent now.

**Error handling pattern:** none needed beyond `dict.get()` — this whole phase's error philosophy is "missing data degrades to `None`, never raises" (D-04), already the shape of every other `_estimado` field in this file. No try/except precedent to copy; there isn't one in `_persistir_herancas` or `_evidencias_geo` either for this class of lookup.

**Import to add** (follow the existing submodule-direct-import convention — `paises.py` helpers are **not** re-exported via `fotoorganizer/geolocation/__init__.py`, and `engine.py` already imports another geolocation submodule directly the same way):
```python
# engine.py:44 (existing, same convention):
from fotoorganizer.geolocation.folder_names import _normalizar
# new, same pattern:
from fotoorganizer.geolocation.timezones import TZ_POR_PAIS
```
(`fotoorganizer/geolocation/__init__.py` only exports `GeocodingProvider`, `GeoResult`, `LocationResolver`, `extrair_hierarquia_da_pasta`, `identificar_pais` — `paises.py` itself is never added there, so `timezones.py` shouldn't be either; import directly from the submodule.)

---

### `fotoorganizer/server/app.py` — `_media_json` (modified)

**Analog:** the function itself — `gps_estimado`/`gps_lat_efetivo` fields already follow the exact shape needed (`app.py:275-308`):

```python
def _media_json(m: MediaFile, fontes_off: frozenset[int] = frozenset()) -> dict:
    return {
        "id": m.id,
        "nome": m.nome,
        ...
        "gps_estimado": m.coordenada_estimada,
        "gps_lat_efetivo": m.coordenada[0] if m.coordenada else None,
        "gps_lon_efetivo": m.coordenada[1] if m.coordenada else None,
        "source_id": m.source_id,
        ...
    }
```

**Core pattern to add:** a single new key, plain attribute passthrough (like `source_id`/`trip_id`/`event_id`, not a computed one like `gps_lat_efetivo`) — insert anywhere in the dict literal, e.g. next to the other GPS/estimate fields:
```python
"tz_estimado": m.tz_estimado,
```

`_media_json` is shared by both the grid list endpoint (`app.py:602`, `"itens": [_media_json(m, fora) for m in itens]`) and `GET /api/midia/{media_id}` (`app.py:686`, `detalhe = _media_json(media, _fontes_fora_de_alcance())`) — adding the field here (not in the `detalhe_midia`-only block at `app.py:687-739`, which only handles fields requiring an extra query like `local`/`estimativa`/`sugestao`) satisfies spec §3 for both surfaces with one change, matching how `gps_lat`/`gps_lon`/`gps_estimado` already do.

**No auth/validation pattern needed:** `_media_json` has none (local-only FastAPI server, per project constraint "serve apenas 127.0.0.1") — no guard to copy.

---

### `tests/test_timezones.py` (new)

**Analog:** `tests/test_paises.py` (full file read, 60 lines shown, structurally short)

**Shape to copy** (`test_paises.py:1-33`):
```python
"""Nome canônico de país: uma grafia só, venha de onde vier.
...
"""

import pytest

from fotoorganizer.geolocation.folder_names import identificar_pais
from fotoorganizer.geolocation.paises import (
    PAISES_PT,
    canonizar_pais,
    limpar_regiao,
    pais_por_codigo,
)


@pytest.mark.parametrize(
    "codigo,nome",
    [("TH", "Tailândia"), ("VN", "Vietnã"), ...],
)
def test_codigo_iso_da_nome_em_portugues(codigo, nome):
    assert pais_por_codigo(codigo) == nome


def test_codigo_desconhecido_ou_vazio_nao_explode():
    assert pais_por_codigo(None) is None
    assert pais_por_codigo("") is None
    assert pais_por_codigo("ZZ") is None
```

**Two required assertions per spec §4** (no existing IANA-validation test in the codebase to copy verbatim — this is new territory for this repo, only the module-docstring/import/plain-function-test *shape* is reused from `test_paises.py`; see "Flags for Planner" #2 on the `zoneinfo`/`tzdata` platform dependency this introduces):
```python
import zoneinfo

from fotoorganizer.geolocation.paises import PAISES_PT
from fotoorganizer.geolocation.timezones import TZ_POR_PAIS


def test_cobre_todos_os_paises_de_paises_pt():
    assert set(TZ_POR_PAIS) == set(PAISES_PT.values())


def test_todo_valor_e_identificador_iana_valido():
    disponiveis = zoneinfo.available_timezones()
    for pais, fuso in TZ_POR_PAIS.items():
        assert fuso in disponiveis, f"{pais}: {fuso!r} não é IANA válido"
```

---

### `tests/test_suggestion_engine.py` (modified — add tz_estimado cases)

**Analog:** same file — `ambiente` fixture (`test_suggestion_engine.py:28-77`) + `test_estimativa_some_quando_a_foto_ganha_gps_proprio` (`test_suggestion_engine.py:1026-1057`)

**Fixture/media-builder pattern already in file, reuse as-is:**
```python
def _media(source_id, nome, pasta, data=None, mtime=None, gps=None,
           make=None, model=None, hash_rapido=None, phash=None):
    return MediaFile(
        source_id=source_id, caminho=f"{pasta}/{nome}", pasta=pasta, nome=nome,
        extensao="jpg", tamanho=100, data_capturada=data, mtime=mtime,
        gps_lat=gps[0] if gps else None, gps_lon=gps[1] if gps else None,
        make=make, model=model, hash_rapido=hash_rapido,
        hash_perceptual=phash,
    )
```
`FakeGeocoder` (`test_suggestion_engine.py:28-33`) already resolves GPS `(40,46)`-ish latitudes to `GeoResult("França", "Provence", "Avignon", "fake")` — since `TZ_POR_PAIS["França"]` will exist, this fixture/geocoder combo can drive both the "GPS próprio" and "herança" test cases from spec §4 without a new fake.

**Recompute-clears-stale pattern to copy** (`test_suggestion_engine.py:1026-1057`, same shape needed for "regenerar sugestões atualiza tz_estimado" — this test is also the concrete case that decides Flag #1 above: without the `else None` branch, this test's second assertion would fail if a media loses its `"pais"` evidence between runs):
```python
def test_estimativa_some_quando_a_foto_ganha_gps_proprio(migrated_engine):
    """Reprocessar um arquivo pode trazer o GPS que faltava. A estimativa
    antiga não pode sobreviver a isso."""
    factory = create_session_factory(migrated_engine)
    ...
    engine = SuggestionEngine(factory, LocationResolver(FakeGeocoder()))
    engine.gerar()
    with factory() as session:
        cam = session.scalar(select(MediaFile).where(MediaFile.nome == "cam.jpg"))
        assert cam.gps_lat_estimado is not None
        cam.gps_lat, cam.gps_lon = 43.96, 4.81   # reprocessado, agora com EXIF
        session.commit()

    engine.gerar()
    with factory() as session:
        cam = session.scalar(select(MediaFile).where(MediaFile.nome == "cam.jpg"))
        assert cam.gps_lat_estimado is None
```
Same two-call-to-`gerar()`, re-fetch-in-new-session shape applies directly to a `tz_estimado`-recompute test.

**Retrieval helper to reuse:** `_sugestao_de` (`test_suggestion_engine.py:80-91`) for reading back `Evidence`/`Suggestion` if a test needs to confirm `evidencias["pais"]` was the source; for `tz_estimado` itself, query `MediaFile` directly (it's not an `Evidence`, per D-03) — same session-scoped `session.scalar(select(MediaFile).where(...))` idiom used throughout this file.

---

### `tests/test_server_api.py` (modified — add tz_estimado assertion)

**Analog:** `test_detalhe_traz_a_foto_que_doou_a_coordenada` (`test_server_api.py:862-887`)

```python
def test_detalhe_traz_a_foto_que_doou_a_coordenada(client, migrated_engine):
    """A estimativa só é auditável se a doadora for alcançável a partir de
    quem herdou — id, nome, câmera e Δt, não só uma frase."""
    from fotoorganizer.models import MediaFile

    factory = create_session_factory(migrated_engine)
    with factory() as session:
        fotos = list(session.scalars(select(MediaFile).order_by(MediaFile.nome)))
        doadora, herdeira = fotos[0], fotos[1]
        doadora.make, doadora.model = "Apple", "iPhone 15 Pro"
        herdeira.gps_lat = herdeira.gps_lon = None
        herdeira.gps_lat_estimado, herdeira.gps_lon_estimado = 43.95, 4.81
        herdeira.gps_estimado_de_id = doadora.id
        herdeira.gps_estimado_delta_s = 120
        ids = (doadora.id, herdeira.id)
        session.commit()

    detalhe = client.get(f"/api/midia/{ids[1]}").json()
    assert detalhe["gps_lat"] is None
    assert detalhe["gps_estimado"] is True
    assert detalhe["gps_lat_efetivo"] == 43.95
```

**Pattern for the new assertion:** since `tz_estimado` is a plain `MediaFile` column (like `gps_lat`, not a computed/joined field like `local`), the simplest analog is to set it directly on a fixture `MediaFile` via `session` and assert the raw passthrough in the response — no `client`/engine `gerar()` round trip required to test the serializer in isolation:
```python
def test_detalhe_traz_o_fuso_estimado(client, migrated_engine):
    from fotoorganizer.models import MediaFile

    factory = create_session_factory(migrated_engine)
    with factory() as session:
        media = session.scalar(select(MediaFile))
        media.tz_estimado = "America/Sao_Paulo"
        media_id = media.id
        session.commit()

    detalhe = client.get(f"/api/midia/{media_id}").json()
    assert detalhe["tz_estimado"] == "America/Sao_Paulo"
```
The `client`/`migrated_engine` fixtures and `from fotoorganizer.models import MediaFile` local import inside the test function are this file's established convention (seen identically at `test_server_api.py:865, 893`).

---

## Shared Patterns

### "Nunca inventa, nunca lança erro" (degrade-to-None, no exceptions)
**Source:** `_persistir_herancas` (`engine.py:328-351`), `.get()`-based lookups project-wide
**Apply to:** `timezones.py` consumer code in `engine.py` — `TZ_POR_PAIS.get(nome)` returns `None` for unknown country, never raises. No try/except needed anywhere in this phase.

### Direct-write-to-ORM-object bypassing Evidence/Suggestion
**Source:** `gps_lat_estimado`/`gps_lon_estimado`/`gps_estimado_de_id`/`gps_estimado_delta_s` (`_persistir_herancas`, `engine.py:328-351`) and `media.location_id` (`_evidencias_geo`, `engine.py:811-833`)
**Apply to:** `media.tz_estimado = ...` inside `_persistir_sugestao` — same "technical auxiliary field, not a reviewed decision" category (D-03), explicitly not entering `docs/CONFIANCA.md`.

### Static lookup table module (docstring-driven, no external dependency)
**Source:** `fotoorganizer/geolocation/paises.py:1-21`
**Apply to:** `fotoorganizer/geolocation/timezones.py` — module docstring states the "why" once, `from __future__ import annotations`, flat `dict[str, str]` literal, zero network/dependency, not re-exported through `geolocation/__init__.py`.

### Serializer field passthrough
**Source:** `_media_json` (`app.py:275-308`) — `"source_id": m.source_id` / `"trip_id": m.trip_id` style plain-attribute keys
**Apply to:** `"tz_estimado": m.tz_estimado` — no transformation, no extra query, added once and shared by both the grid endpoint (`app.py:602`) and the detail endpoint (`app.py:686`).

### Test structure: module-level `_media()`/fixture builder + parametrized/plain assert functions
**Source:** `tests/test_paises.py` (parametrized), `tests/test_suggestion_engine.py` (`_media`, `ambiente` fixture, `_sugestao_de` helper), `tests/test_server_api.py` (`client`/`migrated_engine` fixtures + local model import)
**Apply to:** all three test files touched in this phase — no new test infrastructure needed, everything reuses existing fixtures/helpers.

---

## No Analog Found

None in the sense of "closest existing file to imitate" — every file in scope
has an exact or self-referential analog already in the codebase, per D-03/D-05
(this phase extends established, named precedents rather than introducing a
new mechanism).

The one genuinely novel piece is the `zoneinfo.available_timezones()`
IANA-validation assertion in `tests/test_timezones.py` — no prior test in the
repo validates against Python's `zoneinfo` stdlib module (confirmed by grep:
`zoneinfo` is not currently imported anywhere in `fotoorganizer/` or `tests/`).
This isn't a missing analog for *structure* (the parametrize/plain-assert
shape comes straight from `test_paises.py`) — it's a new stdlib dependency
with a platform caveat, see "Flags for Planner" #2 above.

## Metadata

**Analog search scope:** `fotoorganizer/geolocation/`, `fotoorganizer/classification/`, `fotoorganizer/server/`, `fotoorganizer/models/`, `tests/`
**Files read in full or by targeted section:** `fotoorganizer/geolocation/paises.py` (full), `fotoorganizer/classification/engine.py` (imports block, `gerar()`, `_persistir_herancas`, `_resolver_locations` docstring, `_evidencias_geo`, `_persistir_sugestao`, `_salvar_sugestao`), `fotoorganizer/server/app.py` (`_media_json`, `detalhe_midia`), `fotoorganizer/models/catalog.py` (`tz_estimado`/`data_capturada_utc` column region), `docs/prompts/fase-11-timezone-estimado.md` (full, authoritative spec per D-01), `tests/test_paises.py` (full), `tests/test_suggestion_engine.py` (imports, fixtures, `test_estimativa_some_quando_a_foto_ganha_gps_proprio`), `tests/test_server_api.py` (`test_detalhe_traz_a_foto_que_doou_a_coordenada` region)
**Pattern extraction date:** 2026-08-16
