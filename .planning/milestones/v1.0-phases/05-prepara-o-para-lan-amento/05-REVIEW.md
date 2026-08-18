---
phase: 05-prepara-o-para-lan-amento
reviewed: 2026-08-18T01:21:57Z
depth: standard
files_reviewed: 14
files_reviewed_list:
  - docs/AVALIACAO_UX.md
  - docs/EMPACOTAMENTO.md
  - docs/PERFORMANCE.md
  - fotoorganizer/database/engine.py
  - fotoorganizer/database/migrations/versions/0018_indices_de_fk_ausentes.py
  - fotoorganizer/models/catalog.py
  - fotoorganizer/models/duplicates.py
  - fotoorganizer/models/inference.py
  - fotoorganizer/models/operations.py
  - fotoorganizer/models/people.py
  - scripts/medir_baseline_producao.py
  - tests/test_indices.py
  - webapp/src/App.test.tsx
  - webapp/src/components/ModalCaminho.tsx
findings:
  critical: 0
  warning: 2
  info: 2
  total: 4
status: issues_found
---

# Phase 05: Code Review Report

**Reviewed:** 2026-08-18T01:21:57Z
**Depth:** standard
**Files Reviewed:** 14
**Status:** issues_found

## Summary

Reviewed the migration/index slice (`0018_indices_de_fk_ausentes.py`, the five
touched `models/*.py` files, `database/engine.py`, `tests/test_indices.py`)
and the two Fase 5 deliverables that ship actual runtime code
(`scripts/medir_baseline_producao.py`, `webapp/src/components/ModalCaminho.tsx`
+ its `App.test.tsx` regression coverage), plus the three narrative docs
(`AVALIACAO_UX.md`, `EMPACOTAMENTO.md`, `PERFORMANCE.md`).

The index/migration slice holds up under adversarial reading: the 9 new
indices in migration 0018 match their model-level `Index()` mirrors with no
duplicate-index collisions against migrations 0005/0006/0007/0011/0017; the
`PRAGMA case_sensitive_like=ON` claim in `engine.py` (that only
`MediaFile.pasta.like()` is affected, everything else is `.ilike()` or
`.not_like("%://%")` with no leading alphabetic character) was verified by
grepping every `.like(`/`.not_like(` call site in production code — it holds.
The LIKE-escaping in `_sob_a_pasta` (referenced by `test_indices.py`) escapes
backslash before `%`/`_`, which is the correct order. `test_indices.py`
itself correctly exercises the real compiled query via `EXPLAIN QUERY PLAN`
against a `migrated_engine` fixture that goes through `create_db_engine`
(so the PRAGMA is actually active during the assertion), rather than
asserting on `sqlite_master` alone — this is the right test for what
Pitfall 3 in RESEARCH.md warns about.

Two real issues found outside that slice: a non-atomic snapshot of a live,
concurrently-writable SQLite database in the baseline-measurement script,
and an incomplete keyboard-close path in `ModalCaminho` that undercuts this
project's own "teclado-first" / "navegação por teclado" commitment
(`CLAUDE.md`). Both are demonstrable from the code, not speculative.

## Warnings

### WR-01: Non-atomic file copy of a live WAL-mode production database

**File:** `scripts/medir_baseline_producao.py:261-269`
**Issue:** `_copiar_catalogo_descartavel()` snapshots the production catalog
with three sequential, unlocked `shutil.copy2()` calls — first the main
`.db` file, then (in a loop) `-wal` and `-shm` if present:

```python
def _copiar_catalogo_descartavel(settings: Settings) -> Path:
    ts = time.strftime("%Y%m%d-%H%M%S")
    destino = settings.data_dir / f"baseline-{ts}.db"
    shutil.copy2(settings.db_path, destino)
    for sufixo in ("-wal", "-shm"):
        origem_extra = Path(str(settings.db_path) + sufixo)
        if origem_extra.exists():
            shutil.copy2(origem_extra, Path(str(destino) + sufixo))
    return destino
```

This runs against `settings.db_path`, which — per the script's own CLI
contract (`--data-dir` is optional and "sem isto usa o real de produção") and
per `docs/PERFORMANCE.md`'s documented reproduction command (run with no
`--data-dir`, explicitly "aponta para o `data_dir` real de produção") — is
the live production `catalog.db`. The script's own docstring (P-2) already
identifies *why* a copy is needed at all: `SuggestionEngine.gerar()` and
`DuplicateDetector.detectar()` write as a side effect, and running them
in-place "deixaria produção com um lote de sugestões auto-geradas que
ninguém pediu nem revisou" — so the author was already reasoning about
correctness/safety here, just with the wrong primitive for a WAL-mode
SQLite file.

`database/engine.py` opens every connection with `PRAGMA journal_mode=WAL`.
In WAL mode, the `.db`, `-wal`, and `-shm` files only form a consistent
snapshot together at a single instant; three separate `copy2()` calls with
no locking, no `BEGIN IMMEDIATE`, and no use of SQLite's Online Backup API
give no such guarantee. If any other process holds the production catalog
open and writes between these three copies — the normal state of this app
during a dev/ops session, since the FastAPI server (`fotoorganizer/server/`)
is the primary consumer of this exact `catalog.db` and nothing in this
script checks for or warns about a running server — the resulting three-file
set can be internally inconsistent: SQLite may refuse to open the copy, or
worse, open it silently with a partially-applied WAL relative to the base
file. Because this copy is what `_medir_sugestoes_e_duplicatas()` then reads
metrics from, a torn copy produces wrong baseline numbers without any error
signal.

**Fix:** Use SQLite's built-in backup API for an atomic, consistent
snapshot instead of raw file copies:

```python
def _copiar_catalogo_descartavel(settings: Settings) -> Path:
    ts = time.strftime("%Y%m%d-%H%M%S")
    destino = settings.data_dir / f"baseline-{ts}.db"
    origem = sqlite3.connect(f"file:{settings.db_path}?mode=ro", uri=True)
    try:
        alvo = sqlite3.connect(destino)
        try:
            origem.backup(alvo)
        finally:
            alvo.close()
    finally:
        origem.close()
    return destino
```

(`sqlite3.Connection.backup()` uses SQLite's Online Backup API, which is
safe against concurrent writers by design.) `VACUUM INTO` from a single
connection is an equally valid alternative.

### WR-02: `ModalCaminho` only closes on Escape when focus is inside the text input

**File:** `webapp/src/components/ModalCaminho.tsx:34-37`
**Issue:** The `Escape`-to-cancel handler is wired exclusively to the
`<input>`'s `onKeyDown`:

```tsx
onKeyDown={(e) => {
  if (e.key === "Enter" && valor.trim()) onConfirmar(valor.trim());
  if (e.key === "Escape") onCancelar();
}}
```

Nothing else in the component (the backdrop `<div>`, the panel `<div>`, or
the `Botao` component used for "Cancelar"/"Confirmar") has any keydown
handler. `webapp/src/ui/Botao.tsx` forwards
`ButtonHTMLAttributes<HTMLButtonElement>` but `ModalCaminho` never passes an
`onKeyDown` to either `Botao`. Since both buttons are natively focusable and
reachable via `Tab` from the auto-focused input, a user who tabs to
"Cancelar" (or "Confirmar") and presses `Escape` — the standard, expected
way to abort any modal — gets no response. This is a demonstrable behavioral
gap, not a style nit, in a codebase whose `CLAUDE.md` explicitly commits to
validating "navegação por teclado; foco visível" as part of UX acceptance,
and whose own `docs/AVALIACAO_UX.md` (same phase) calls out the *general*
pattern of "só abre com mouse" / keyboard-incomplete interaction elsewhere
in the app (finding A.1) as a defect worth fixing.

**Fix:** Attach the same handler at the modal container level so it fires
regardless of which element inside has focus, e.g.:

```tsx
<div
  className="fixed inset-0 z-50 flex items-center justify-center bg-black/95"
  onKeyDown={(e) => {
    if (e.key === "Escape") onCancelar();
  }}
>
```

(keep the `Enter`-to-confirm behavior scoped to the input, since only the
input should submit on Enter).

## Info

### IN-01: `_varrer_pastas` always returns `None` for its second tuple element

**File:** `scripts/medir_baseline_producao.py:221-258`
**Issue:** The function is typed `-> tuple[list[ResultadoPasta], ScanMetrics | None]`
and its single `return resultados, None` statement always returns `None` for
the second element — no code path can produce a `ScanMetrics` there. The one
caller (`medir()`) discards it (`resultado.pastas, _ = _varrer_pastas(...)`).
It's dead surface area that misleads a reader into thinking aggregate
`ScanMetrics` are available from this call.
**Fix:** Drop the second return value and the `ScanMetrics` import/type
annotation if nothing downstream needs it, or actually aggregate/return the
last `ScanMetrics` if that was the original intent.

### IN-02: `ModalCaminho` has no focus trap or dialog semantics

**File:** `webapp/src/components/ModalCaminho.tsx:26-54`
**Issue:** The outer `<div>` has no `role="dialog"`, no `aria-modal="true"`,
and no focus trap — `Tab`/`Shift+Tab` can move focus out of the modal to
elements behind the (visually opaque, but not DOM-isolated) backdrop while
it's open. This is a lesser, distinct gap from WR-02 (which is about
`Escape` not firing from inside the modal); this one is about focus being
able to leave the modal entirely.
**Fix:** Add `role="dialog"` and `aria-modal="true"` to the outer container,
and either trap focus with a small hook/library or set `aria-hidden` on the
rest of the app tree while the modal is mounted.

---

_Reviewed: 2026-08-18T01:21:57Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
