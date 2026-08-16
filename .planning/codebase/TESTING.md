# Testing Patterns

**Analysis Date:** 2026-08-16

Two independent test suites, one per side of the stack, both mandatory
before commit (`scripts/verificar.sh`). There is also a third, non-unit
gate: a labeled-scenario benchmark for the classification/grouping engine
(`scripts/avaliar_agrupamento.py`) that must stay at 100% before any commit
touches grouping/classification thresholds.

## Test Framework

**Python:**
- Runner: `pytest` 8.x (`pyproject.toml` → `[project.optional-dependencies].dev`).
- Config: `pyproject.toml` → `[tool.pytest.ini_options]` → `testpaths = ["tests"]`.
- No plugins beyond `pytest` + `httpx` (for `TestClient`/API tests) +
  `defusedxml` (XMP parsing dependency, not test-only).
- No coverage tool configured (no `pytest-cov`, no coverage threshold).

**TypeScript/React:**
- Runner: `vitest` 4.x, config embedded in `webapp/vite.config.ts` (`test:`
  key, since `vitest/config`'s `defineConfig` — not plain Vite's — accepts it).
- Environment: `jsdom`.
- Assertion/DOM matchers: `@testing-library/jest-dom` (via
  `@testing-library/jest-dom/vitest` import in setup), `@testing-library/react`,
  `@testing-library/user-event`.
- Setup file: `webapp/src/test/setup.ts`.
- `css: false` (skip CSS processing in tests), `restoreMocks: true` (auto
  `vi.restoreAllMocks()` between tests, on top of manual `afterEach` cleanup).

**Run Commands:**
```bash
# Python — from repo root, using the project venv
.venv/bin/python -m pytest -q --no-header    # all tests, quiet
.venv/bin/python -m pytest tests/test_grouping.py -q   # single file
.venv/bin/python -m pytest -k "duplicat"      # filter by name

# TypeScript — from webapp/
npm test          # vitest run (single pass, used in CI/verificar.sh)
npm run test:watch  # vitest (watch mode)

# Full slice verification (both suites + grouping benchmark + UI build)
scripts/verificar.sh            # everything
scripts/verificar.sh --rapido   # skip the webapp build step
```

## Test File Organization

**Python:**
- Flat directory `tests/` (no subpackages), one file per source module:
  `tests/test_<modulo>.py` for `fotoorganizer/<pacote>/<modulo>.py`. Example:
  `fotoorganizer/scanner/discovery.py` → `tests/test_discovery.py`;
  `fotoorganizer/grouping/classifier.py` tested inline from
  `tests/test_grouping.py` via a local import.
- Shared fixtures: `tests/conftest.py` (pytest fixtures: `db_path`,
  `migrated_engine`) and `tests/fixtures.py` (synthetic-image generator
  functions, not pytest fixtures — plain factory functions imported
  explicitly: `make_jpeg`, `make_png`, `make_corrupt_jpeg`).
- `tests/__init__.py` exists — `tests` is an importable package.

**TypeScript:**
- Co-located: `Component.tsx` and `Component.test.tsx` live in the same
  directory (`webapp/src/components/Duplicates.tsx` +
  `webapp/src/components/Duplicates.test.tsx`).
- Shared test infra in `webapp/src/test/`: `servidor.tsx` (fetch mock +
  render helper + base fixture catalog) and `setup.ts` (global
  `EventSource` stub, cleanup).
- One suite file per hook that needs isolated testing
  (`webapp/src/hooks/useJob.test.tsx`).

**Structure:**
```
tests/
  __init__.py
  conftest.py          # pytest fixtures (db_path, migrated_engine)
  fixtures.py           # synthetic image/EXIF generators (make_jpeg, ...)
  test_<modulo>.py       # one per fotoorganizer/<pacote>/<modulo>.py

webapp/src/
  test/
    servidor.tsx         # fetch double, montar(), ROTAS_BASE fixture catalog
    setup.ts              # EventSource stub, afterEach cleanup
  components/
    Foo.tsx
    Foo.test.tsx          # co-located
  hooks/
    useJob.ts
    useJob.test.tsx
```

## Test Structure

**Python — plain functions, no class-based suites, Portuguese, behavior-named:**
```python
def test_lacuna_separa_viagens():
    itens = [
        (1, _dias(0)), (2, _dias(1)), (3, _dias(2)),   # viagem 1
        (4, _dias(10)), (5, _dias(11)),                # viagem 2 (gap 8d)
        (6, _dias(30)),                                # viagem 3 (gap 19d)
    ]
    viagens = agrupar_viagens(itens)
    assert [v.media_ids for v in viagens] == [[1, 2, 3], [4, 5], [6]]
```
Test names describe the behavior/regression in full Portuguese sentences,
not `test_<function>_<case>` mechanical naming
(`test_viagem_longa_nao_quebra_por_dia`,
`test_content_length_menor_que_o_corpo_e_rejeitado`). When a test guards
against a real bug found in the user's catalog, its docstring states the
concrete numbers (see `test_pasta_que_lista_destinos_nomeia_a_viagem_inteira`
in `tests/test_grouping.py`, citing "2.405 fotos", "106 com coordenada").

Related tests are grouped under a `# -- section ---` comment banner within
the same file rather than split into classes:
```python
# -- divisão por transição casa↔fora ----------------------------------------
FORA, CASA, SEM_GPS = False, True, None
```

**TypeScript — `describe`/`it`, async-first, Portuguese sentences:**
```typescript
describe("Duplicates", () => {
  it("grupo EXATO resolvido pelo algoritmo mostra rótulo distinto de decisão humana", async () => {
    servirApi({ "/api/duplicatas": [grupo({ resolvido_automaticamente: true, ... })] });
    montar(<Duplicates job={jobParado()} />);
    expect(await screen.findAllByText(/resolvido automaticamente/)).not.toHaveLength(0);
  });
});
```
`it(...)` descriptions are full sentences stating the observable UI
behavior, frequently including the *why* inline as a trailing clause.

**Setup/teardown:**
- Python: fixtures via `@pytest.fixture()` in `conftest.py`, function-scoped
  by default; `tmp_path` used pervasively for filesystem isolation, never a
  fixed path. `os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")` at
  module load time in `conftest.py` for headless runs (legacy from PySide6
  era; kept for CI safety even though the PySide6 UI itself is removed).
- TypeScript: global `afterEach` in `setup.ts` runs
  `cleanup()` (RTL), resets the fake `EventSource` instance registry, and
  `vi.restoreAllMocks()`.

## Mocking

**Python — `pytest`'s `monkeypatch`, no mocking framework (no `unittest.mock`
patterns observed as the primary style):**
```python
def test_destino_so_aparece_no_fim(base_url, tmp_path, monkeypatch):
    """Enquanto o corpo está sendo lido, o nome final não existe."""
    from fotoorganizer.security import http_seguro
    visto: list[bool] = []
    original = http_seguro._promover

    def espiao(temporario, alvo, sobrescrever):
        visto.append(alvo.exists())  # antes da promoção
        return original(temporario, alvo, sobrescrever)

    monkeypatch.setattr(http_seguro, "_promover", espiao)
    http_seguro.baixar_arquivo(f"{base_url}/ok", destino)
    assert visto == [False]
```
The "spy that wraps the original" pattern (`espiao` = "spy") is preferred
over a bare stub when the test needs both to observe a call *and* preserve
real behavior. Failure-injection uses the same `monkeypatch.setattr` pattern
to make a stdlib call raise (`os.link` raising `OSError(errno.EOPNOTSUPP,
...)` in `test_link_nao_suportado_vira_erro_do_modulo`).

**Python — real local servers instead of HTTP mocking libraries:** network
code is tested against a real, ephemeral, loopback-only `http.server`
instance (`ThreadingHTTPServer` on `127.0.0.1:0`), not `responses`/`httpretty`.
See `tests/test_http_seguro.py`'s `_Handler`/`_Servidor`/`base_url` fixture
(module-scoped, started once per file). This is the standard approach for
any code touching real network/subprocess boundaries in this codebase —
prefer a real minimal server/process over mocking the transport layer.

**TypeScript — `fetch` stubbed globally per test via `servirApi()`**
(`webapp/src/test/servidor.tsx`), not MSW or per-call `vi.fn()` chains:
```typescript
servirApi({ "/api/duplicatas": [grupo({ ... })] });
montar(<Duplicates job={jobParado()} />);
```
`servirApi` routes by pathname, returns JSON, and fails loudly (404 with
`rota não simulada: <path>`) for unrouted paths. Use `erro(status, detail)`
to simulate a business-logic error response (409/422) instead of only
testing the happy path. `EventSource` is globally stubbed in
`webapp/src/test/setup.ts` (`EventSourceFalso`) since jsdom has no native
implementation; tests that need to drive SSE messages call
`EventSourceFalso.instancias[i].emitir(dados)`.

**What to mock:** the network boundary (`fetch`, `EventSource`) on the
frontend; the filesystem call that's the actual point of the test (`os.link`)
on the backend, via `monkeypatch`, never broader than necessary.

**What NOT to mock:** the SQLite database (tests use a real, migrated,
`tmp_path`-scoped engine via the `migrated_engine` fixture), real image
files (generated on disk via `tests/fixtures.py`, not mocked file objects),
and — for HTTP-download code — the actual HTTP transport (real local
server, not a mocked `urlopen`).

## Fixtures and Factories

**Python — function-based synthetic data generators**, not `pytest`
fixtures, in `tests/fixtures.py`:
```python
def make_jpeg(path: Path, *, seed: int = 0, data_exif="2024:05:04 10:30:00",
              gps=None, make="TestMake", model="TestModel", ...) -> Path:
    ...
```
Called directly inside test bodies with `tmp_path`, not injected. Docstring
at module top: "Geradores de arquivos de teste sintéticos (nunca fotos
reais no repo)" — this is a hard project rule (`CLAUDE.md`): **never commit
real personal photos**.

**Python — pytest fixtures** for expensive/shared setup only
(`tests/conftest.py`):
```python
@pytest.fixture()
def db_path(tmp_path):
    return tmp_path / "catalog.db"

@pytest.fixture()
def migrated_engine(db_path):
    from fotoorganizer.database import create_db_engine, upgrade_to_head
    upgrade_to_head(db_path)
    engine = create_db_engine(db_path)
    yield engine
    engine.dispose()
```

**TypeScript — override-object factories** local to each test file:
```typescript
function membro(over: Record<string, unknown>) {
  return { member_id: 1, media_id: 1, nome: "a.jpg", ..., ...over };
}
function grupo(over: Record<string, unknown>) {
  return { id: 1, nivel: "exato", ..., membros: [membro({}), ...], ...over };
}
```
Base API-fixture catalog shared across all component tests:
`webapp/src/test/servidor.tsx`'s `ROTAS_BASE` — a minimal catalog making any
screen render without per-test boilerplate. Route payloads are deliberately
cross-consistent (e.g. `/api/funil` numbers match `/api/inventario`) so a
self-contradictory fixture surfaces as a failing assertion, not silently.

**Location:** `tests/fixtures.py` (Python, image generators), `tests/conftest.py`
(Python, pytest fixtures), `webapp/src/test/servidor.tsx` (TS, API/render
fixtures), local factory functions at the top of each `*.test.tsx` file for
component-specific shapes.

## Coverage

**Requirements:** None enforced. No `pytest-cov`, no `vitest --coverage`
threshold, no CI coverage gate found in this repo.

**View Coverage:** Not applicable — no coverage tooling installed. To add
ad hoc: `pytest --cov=fotoorganizer` (Python) or `vitest run --coverage`
(TS) after installing the respective coverage packages; not currently part
of the workflow.

## Test Types

**Unit tests:** the overwhelming majority — pure functions
(`fotoorganizer/grouping`, `fotoorganizer/classification`) and isolated
modules (`fotoorganizer/security/paths.py`) tested directly with
synthetic inputs.

**Integration tests:** repository/database tests use a real, migrated
SQLite engine (`migrated_engine` fixture) rather than mocking SQLAlchemy.
`tests/test_server_api.py`/`test_server_reapontar.py` exercise the FastAPI
app via `httpx`'s `TestClient` against a real (temp) database. Network code
(`test_http_seguro.py`) runs against a real local `ThreadingHTTPServer`.

**Benchmark/regression suite (not pytest):** `scripts/avaliar_agrupamento.py`
runs labeled real-world grouping/classification scenarios and must stay at
100% before any threshold change is committed — see
`.claude/skills/fatia-vertical/SKILL.md` step 3: "Se a fatia é de
classificação, adicione o cenário em `scripts/avaliar_agrupamento.py` ANTES
de mexer em qualquer limiar." Wired into `scripts/verificar.sh` step 2/4.

**E2E tests:** Not used. Manual UI verification via
`scripts/executar.sh web` + screenshot is the substitute, per
`.claude/skills/fatia-vertical/SKILL.md` step 6 — required for any
observable/behavioral UI change, in addition to (not instead of) the vitest
smoke test.

**UI smoke coverage requirement:** any new screen or behavior change in the
webapp must ship with a smoke test under `webapp/src/**/*.test.tsx`
(project rule, `CLAUDE.md` and `fatia-vertical` SKILL step 5).

## Common Patterns

**Async testing (TypeScript, waiting on React Query + fetch):**
```typescript
servirApi({ "/api/duplicatas": [grupo({ ... })] });
montar(<Duplicates job={jobParado()} />);
expect(await screen.findByText(/marcar uma exclui a outra do plano/))
  .toBeInTheDocument();
```
Use `findBy*`/`findAllBy*` (async, awaits appearance) for anything behind a
`fetch`; use `getBy*`/`queryBy*` only for synchronous assertions after the
initial `find` has resolved. Prefer `getAllByText`/`queryAllByText` when the
same text can legitimately appear twice (list item + detail panel) —
comment explains why singular vs. plural query was chosen when it's not
obvious.

**Timing-sensitive tests (Python):**
```python
def test_timeout(base_url, tmp_path):
    inicio = time.monotonic()
    with pytest.raises(TempoEsgotado):
        baixar_arquivo(f"{base_url}/lento", destino, timeout=0.5)
    assert time.monotonic() - inicio < 4  # não esperou os 5s do servidor
```
Assert an upper bound on elapsed wall-clock time to prove a timeout fired
early, rather than only asserting the exception type.

**Error/exception testing (Python) — assert both type and structured
attributes:**
```python
with pytest.raises(TamanhoExcedido) as info:
    baixar_arquivo(f"{base_url}/grande", destino, tamanho_maximo_bytes=1024)
assert info.value.limite == 1024
assert not destino.exists()
assert _restos(tmp_path) == []   # no partial file left behind
```
Every failure-path test in `test_http_seguro.py` also asserts the
filesystem is left clean (`_restos(tmp_path) == []` or `not destino.exists()`)
— matches the project's non-destructive invariant: a failed operation must
never leave a partial/corrupt artifact.

**Parametrized tests (Python):**
```python
@pytest.mark.parametrize("bruto", ["", None, "meio-dia", "+25:00", "+02:99"])
def test_offset_invalido_e_ignorado(bruto):
    ...
```

**Error/business-failure testing (TypeScript):** use `erro(status, detail)`
from `servidor.tsx` to make a route return 409/422 and assert the UI's
degraded/error state, not just the success path.

---

*Testing analysis: 2026-08-16*
