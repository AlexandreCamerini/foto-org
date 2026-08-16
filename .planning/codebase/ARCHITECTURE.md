<!-- refreshed: 2026-08-16 -->
# Architecture

**Analysis Date:** 2026-08-16

## System Overview

```text
┌─────────────────────────────────────────────────────────────┐
│  Tauri shell (native window, macOS)                          │
│  `src-tauri/src/main.rs` — spawns embedded Python, opens     │
│  WKWebView at the URL the backend prints (FOTOORG_READY)     │
└───────────────────────────┬───────────────────────────────────┘
                             │ spawns + owns lifecycle
                             ▼
┌─────────────────────────────────────────────────────────────┐
│  React/TS webapp (built assets)          `webapp/src/`       │
│  App.tsx tabs: Panorama · Biblioteca · Viagens · Revisão ·   │
│  Duplicatas · Operações — TanStack Query for all server state│
└───────────────────────────┬───────────────────────────────────┘
                             │ HTTP/SSE, 127.0.0.1 only, relative URLs
                             ▼
┌─────────────────────────────────────────────────────────────┐
│  FastAPI server (loopback only)      `fotoorganizer/server/` │
│  app.py: REST handlers + Origin/Host guard + StaticFiles     │
│  jobs.py: JobManager — one background job at a time (thread) │
└───────────────────────────┬───────────────────────────────────┘
                             │ calls (never raw SQL/filesystem in handlers)
                             ▼
┌─────────────────────────────────────────────────────────────┐
│  Domain services                                              │
│  scanner/ · sources/ · metadata/ · thumbnails/ ·              │
│  classification/ · grouping/ · geolocation/ · duplicates/ ·  │
│  operations/ · faces/ (stub) · vision/ (stub)                │
└───────────────┬─────────────────────────────┬─────────────────┘
                │                             │
                ▼                             ▼
┌───────────────────────────┐   ┌─────────────────────────────┐
│  repositories/             │   │  security/                  │
│  one class per aggregate,  │   │  path validation, safe      │
│  only DB access surface    │   │  subprocess, hashing, crypto│
└───────────────┬─────────────┘   └─────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────────┐
│  models/ (SQLAlchemy ORM) ── database/ (engine, Alembic)      │
│  SQLite WAL, single catalog.db, `~/Library/Application        │
│  Support/FotoOrganizer/catalog.db`                            │
└─────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| Tauri shell | Spawn embedded Python backend, open native window at announced URL, kill backend on exit | `src-tauri/src/main.rs` |
| FastAPI app | HTTP surface for the webapp: read catalog, drive jobs, run operations, enforce loopback/Origin guard | `fotoorganizer/server/app.py` |
| JobManager | One background job at a time (scan, import, plan execution), snapshot state polled/streamed via SSE | `fotoorganizer/server/jobs.py` |
| CatalogScanner | Incremental, read-only filesystem discovery + metadata extraction into the catalog | `fotoorganizer/scanner/scanner.py` |
| ExternalCatalogImporter | Imports Apple Photos / Google Takeout / Lightroom as additional sources of the same catalog | `fotoorganizer/sources/importer.py` |
| MetadataExtractor (Protocol) | EXIF/IPTC/XMP/RAW extraction; exiftool subprocess or pure-Python fallback | `fotoorganizer/metadata/base.py`, `exiftool.py`, `purepython.py` |
| Classification engine | Evidence + suggestion generation (deterministic cascade + opt-in LLM advisor) | `fotoorganizer/classification/engine.py` |
| Grouping / correlation | Temporal sessions, trips/events, cross-source clock drift + GPS inheritance | `fotoorganizer/grouping/correlacao.py`, `temporal.py`, `eventos.py` |
| DuplicateDetector | Exact hash / same-content / visual-similarity duplicate grouping | `fotoorganizer/duplicates/detector.py` |
| OperationPlanner | Builds copy plans from approved suggestions (no filesystem writes) | `fotoorganizer/operations/planner.py` |
| OperationExecutor | The only component that writes outside the catalog — dry-run gated, hash-verified copy | `fotoorganizer/operations/executor.py` |
| Repositories | One class per aggregate; the only DB access surface for server/services | `fotoorganizer/repositories/*.py` |
| security/ | Path traversal guards, safe subprocess, hashing, crypto (face embeddings), volume identity | `fotoorganizer/security/*.py` |
| database/ | SQLite engine (WAL, FKs on), Alembic migrations | `fotoorganizer/database/engine.py`, `migrations/` |
| webapp/App.tsx | Tab shell, keyboard-first navigation, cross-tab "recorte" (scope) state | `webapp/src/App.tsx` |

## Pattern Overview

**Overall:** Layered service architecture behind a local HTTP API, single desktop process. Not microservices — one FastAPI process, one SQLite file, one background-job slot. The Tauri shell is a thin native wrapper; the real application logic lives entirely in the Python backend and is UI-agnostic.

**Key Characteristics:**
- Strict read-only/write-only separation: cataloging (`scanner/`, `sources/`) never writes files; `operations/` is the only module allowed to write outside the catalog.
- Everything physical is staged as a plan (dry-run) before execution — no direct "act now" path exists in the domain layer.
- Replaceable infrastructure via `Protocol` classes (`MetadataExtractor`, `VisionProvider`, `FaceRecognitionProvider`, `GeocodingProvider`, `SyncProvider`), with stub implementations (`faces/stub.py`, `vision/stub.py`) so the core works without them.
- Evidence-based inference: every inferred field (date, country, event, category) is a row in `evidence` with origin, confidence, rationale, logic version — never a bare value.
- Single writer thread discipline: the scanner writes to the DB from one thread even though extraction runs in a `ThreadPoolExecutor`; the JobManager allows only one background job at a time.

## Layers

**Presentation (webapp/):**
- Purpose: keyboard-first, virtualized grid UI for tens of thousands of photos.
- Location: `webapp/src/`
- Contains: React components (`webapp/src/components/`), hooks wrapping TanStack Query (`webapp/src/hooks/`), a typed API client (`webapp/src/api.ts`).
- Depends on: FastAPI HTTP/SSE endpoints only, via relative URLs (never a hardcoded host, so the Tauri-assigned ephemeral port works transparently).
- Used by: end user, inside the Tauri WKWebView or a plain browser during development.

**Server (fotoorganizer/server/):**
- Purpose: expose the domain as a local HTTP API; own background job orchestration.
- Location: `fotoorganizer/server/app.py` (handlers), `fotoorganizer/server/jobs.py` (JobManager)
- Contains: FastAPI route handlers, Pydantic request bodies, an Origin/Host allowlist guard (`_HOSTS_LOCAIS`), SSE progress streaming.
- Depends on: repositories, services (scanner, operations, sources, classification via repositories), never touches the filesystem/DB directly beyond what services expose.
- Used by: webapp exclusively (loopback-only; no external network exposure).

**Domain services (fotoorganizer/{scanner,sources,metadata,classification,grouping,geolocation,duplicates,operations,thumbnails,faces,vision}/):**
- Purpose: the actual product logic — discovery, extraction, inference, grouping, deduplication, physical operations.
- Location: top-level packages under `fotoorganizer/`
- Contains: stateless-ish service classes/functions operating on a `sessionmaker` factory passed in, not a global session.
- Depends on: `repositories/` (via direct ORM queries in some services, e.g. scanner) and `models/`; `security/` for path/subprocess safety.
- Used by: `server/app.py`, `cli.py`.

**Data access (fotoorganizer/repositories/):**
- Purpose: one class per aggregate (media, duplicates, operations, settings, suggestions, people, lexico, inventario) — the intended single point of DB reads for the server layer.
- Location: `fotoorganizer/repositories/*.py`
- Depends on: `models/`, SQLAlchemy `Session`.
- Used by: `server/app.py`, `cli.py`. Note: some services (`scanner/scanner.py`, `operations/executor.py`) query the ORM directly rather than through a repository — see Anti-Patterns.

**Persistence (fotoorganizer/models/, fotoorganizer/database/):**
- Purpose: ORM schema (SQLAlchemy 2) and migrations (Alembic).
- Location: `fotoorganizer/models/*.py` (one file per aggregate group: `catalog.py`, `geo.py`, `inference.py`, `operations.py`, `people.py`, `duplicates.py`, `tagging.py`, `lexico.py`, `settings.py`), `fotoorganizer/database/engine.py`, `fotoorganizer/database/migrations/versions/` (17 revisions as of this analysis).
- Depends on: nothing above it.
- Used by: everything.

## Data Flow

### Primary Cataloging Path (read-only)

1. User picks a folder in the webapp → `POST /scan` → `server/app.py` hands off to `JobManager.iniciar_scan` (`fotoorganizer/server/jobs.py`)
2. `CatalogScanner.scan_source` walks the tree, extracts metadata in a thread pool, computes xxhash, generates thumbnails, writes `MediaFile`/`MetadataEntry` rows incrementally with checkpointed `ScanSession` (`fotoorganizer/scanner/scanner.py`)
3. Classification engine derives evidence + destination suggestions per session cluster, cascading through deterministic rules then an opt-in LLM advisor (`fotoorganizer/classification/engine.py`, `advisor.py`)
4. Grouping/correlation assigns trips/events and cross-source GPS/clock corrections (`fotoorganizer/grouping/correlacao.py`)
5. Progress is polled/streamed over SSE back to the webapp (`server/jobs.py` → `App.tsx` via `useJob`)

### Suggestion Review → Physical Operation Path

1. User reviews suggestions in the "Revisão" tab; approve/reject/edit → `SuggestionRepository` (`fotoorganizer/repositories/suggestions.py`)
2. `OperationPlanner.criar_plano` turns approved suggestions into an `OperationPlan` + `OperationItem` rows, resolving destination collisions — no file is touched (`fotoorganizer/operations/planner.py`)
3. `OperationExecutor.dry_run` validates every item (space, conflicts, offline volumes) without copying (`fotoorganizer/operations/executor.py`)
4. `OperationExecutor.executar` requires the dry-run to have run; copies via exclusive-create (`open('xb')`), verifies SHA-256 before and after, writes `AuditLog`; execution is always COPY, never move/delete (`fotoorganizer/operations/executor.py`)

**State Management:**
- Server-side: `JobManager` holds one in-memory job snapshot (`self._estado`) guarded by a `threading.Lock`; no job queue.
- Client-side: TanStack Query owns all server state/cache in the webapp; local component state (`useState`) only for UI-only concerns (selected tab, selected index, zoom).

## Key Abstractions

**Protocol-based provider swapping:**
- Purpose: let core cataloging work fully offline, with heavier/optional providers pluggable behind the same interface.
- Examples: `fotoorganizer/metadata/base.py` (`MetadataExtractor`, chosen via `criar_extrator()`), `fotoorganizer/geolocation/base.py`, `fotoorganizer/faces/base.py` + `stub.py`, `fotoorganizer/vision/base.py` + `stub.py`.
- Pattern: `typing.Protocol` interface + a factory function that picks the concrete implementation based on availability/config.

**Evidence / Confidence model:**
- Purpose: every inferred field is auditable — origin, confidence enum+score, human-readable rationale, logic version.
- Examples: `fotoorganizer/models/inference.py` (`Evidence`, `Suggestion`, `ConfidenceLevel`), `fotoorganizer/classification/confidence.py` (`elo_mais_fraco` — weakest-link aggregation, never additive).
- Pattern: confidence never sums across evidence; final confidence is the weakest single evidence's confidence (documented rule, not just code — see `docs/CONFIANCA.md`).

**Session factory injection:**
- Purpose: testability and thread-safety — no global DB session.
- Examples: every service constructor takes a `sessionmaker[Session]` (e.g. `CatalogScanner(factory, ...)`, `OperationExecutor(factory)`).
- Pattern: services open a short-lived `Session` per operation from the injected factory, never hold one across calls.

**Dry-run-gated physical writes:**
- Purpose: enforce invariant 2 (nothing physical without explicit approval) at the type level, not just convention.
- Examples: `fotoorganizer/operations/executor.py` raises `DryRunObrigatorio` if `executar()` is called before `dry_run()`; `server/app.py` and `cli.py` both re-check `--confirmar`/`confirmar: bool` before calling it.
- Pattern: double gate — caller-level flag AND callee-level exception, so no caller can accidentally skip it.

## Entry Points

**`python -m fotoorganizer` / `fotoorganizer` console script:**
- Location: `fotoorganizer/app/main.py` → delegates to `fotoorganizer/cli.py:main`
- Triggers: no args → starts `web` subcommand (desktop default); with args → CLI subcommand (`scan`, `web`, `importar`, `volumes`, `inventario`, `reapontar`, `verificar-arquivos`, `planos`, `plano`, `dry-run`, `executar`, `bench`)
- Responsibilities: config layering (defaults < TOML < CLI/env), opens the catalog, dispatches to services.

**`fotoorganizer web` (`cmd_web` in `fotoorganizer/cli.py`):**
- Location: `fotoorganizer/cli.py` (`cmd_web`) → `fotoorganizer.server.create_app`
- Triggers: launched directly by a user, or spawned by the Tauri shell with `--porta 0 --encerrar-com-pai`
- Responsibilities: binds loopback socket (ephemeral or fixed port), prints `FOTOORG_READY <url>` for the supervisor, runs uvicorn, self-terminates if reparented (parent-death watchdog thread).

**Tauri shell (`src-tauri/src/main.rs`):**
- Location: `src-tauri/src/main.rs`
- Triggers: user launches the packaged macOS app.
- Responsibilities: spawn the embedded Python backend as a subprocess, wait for `FOTOORG_READY`, open a native window at that URL, kill the backend on window close.

**webapp dev server (`webapp/`):**
- Location: `webapp/vite.config.ts`, `npm run dev`
- Triggers: developer running the frontend standalone against a locally running `fotoorganizer web` backend.
- Responsibilities: hot-reload UI development; production build (`vite build`) is what FastAPI serves via `StaticFiles`.

## Architectural Constraints

- **Threading:** Single FastAPI/uvicorn process; scan extraction parallelized via `ThreadPoolExecutor` in `fotoorganizer/scanner/scanner.py`, but all DB writes happen from one thread (the scan thread) in discovery order. `JobManager` runs the active job in its own `threading.Thread`, capped at one job at a time (`fotoorganizer/server/jobs.py`).
- **Global state:** `JobManager._estado` is an in-memory dict guarded by a `threading.Lock` — not persisted, lost on server restart (a job in flight when the process dies leaves no "still running" record, only whatever checkpoint the underlying scan/reconciliation already wrote to SQLite).
- **Single catalog:** exactly one SQLite file is the source of truth (`~/Library/Application Support/FotoOrganizer/catalog.db`), opened via WAL with `check_same_thread=False` — concurrency is delegated to SQLite's WAL + `busy_timeout=5000` (`fotoorganizer/database/engine.py`).
- **Loopback-only network surface:** the FastAPI server binds `127.0.0.1` exclusively and additionally checks `Origin`/`Host` headers against `_HOSTS_LOCAIS` in `server/app.py`, because binding to loopback alone does not stop a malicious page open in the user's own browser from issuing simple (no-preflight) POSTs.
- **External catalog references are not filesystem paths:** rows from Apple Photos/Lightroom/Takeout use `scheme://id` style paths (`apple://uuid`); `fotoorganizer/scanner/elegibilidade.py` is the single source of truth for distinguishing these from real filesystem paths, shared between `scanner.py` and `reconciliacao.py` — the two must never diverge on this check.

## Anti-Patterns

### Direct ORM queries in services instead of repositories

**What happens:** `fotoorganizer/scanner/scanner.py` and `fotoorganizer/operations/executor.py`/`planner.py` issue SQLAlchemy `select`/`update`/`delete` directly against models rather than going through a `Repository` class.
**Why it's wrong:** `repositories/` exists specifically to be "the only DB access surface" per the architecture doc, but scanning/operations bypass it — two different data-access conventions coexist in the same codebase.
**Do this instead:** When adding new read/write paths in `scanner/`, `operations/`, or similar service modules, follow the existing local convention within that module rather than mixing repository calls and raw ORM calls in the same file. New cross-cutting reads used by the server layer should go through `repositories/`.

### 1400-line single-file HTTP handler module

**What happens:** `fotoorganizer/server/app.py` is 1422 lines — nearly every REST endpoint, Pydantic body, and the origin-guard logic live in one file.
**Why it's wrong:** hard to navigate, high merge-conflict surface, no per-domain boundary (media, operations, sources, duplicates all interleaved).
**Do this instead:** New endpoints should still land in `app.py` to match current convention (there is no router-splitting pattern established yet), but keep handlers thin and delegate logic to services/repositories immediately — don't grow business logic inline in the handler.

## Error Handling

**Strategy:** Fail loud on programming errors, fail soft on expected environmental issues (missing file, offline volume, unreadable metadata) — never let a single bad file abort a scan.

**Patterns:**
- Read errors during scan/metadata extraction are caught, logged, and recorded per-file (`erro_leitura` column on `MediaFile`); the scan continues (per `CLAUDE.md`: "Erros de leitura de arquivo nunca derrubam a varredura").
- Domain-specific exceptions gate unsafe operations: `DryRunObrigatorio` (`operations/executor.py`), `CaminhoInvalido` (`security/paths.py`), `ApplePhotosError`/`LightroomError` (`sources/`), `ReapontamentoInaplicavel`/`ValidacaoFalhou`/`ColisaoDeCaminho` (`sources/reapontar.py`) — caught explicitly at the CLI/server boundary and turned into user-facing messages, not tracebacks.
- `server/app.py` converts domain exceptions to `HTTPException` with specific status codes at the handler boundary.

## Cross-Cutting Concerns

**Logging:** Standard library `logging`, structured setup in `fotoorganizer/app/logsetup.py`, written to a log directory (not just stderr) because the server process is often killed silently along with its parent terminal/Tauri shell — content is never sensitive (no photo content/paths policy documented in `docs/PRIVACIDADE.md`).

**Validation:** Path safety centralized in `fotoorganizer/security/paths.py` (`caminho_relativo_seguro`, `resolver_destino`) — segment normalization, rejects `..` and `~`, and re-verifies the resolved path stays under the root after resolution (defense in depth). Pydantic models validate request bodies at the FastAPI boundary in `server/app.py`.

**Authentication:** None — trust boundary is "runs as the logged-in user on localhost only." Enforced by binding to `127.0.0.1` plus the `Origin`/`Host` allowlist guard (`_HOSTS_LOCAIS` in `server/app.py`) to block browser-originated cross-site requests.

---

*Architecture analysis: 2026-08-16*
