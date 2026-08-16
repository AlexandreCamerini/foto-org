# Codebase Structure

**Analysis Date:** 2026-08-16

## Directory Layout

```
foto-organizer/
├── fotoorganizer/          # Python backend — domain + server (the whole app minus UI/shell)
│   ├── app/                # Entrypoint, logging setup, maintenance tasks
│   ├── server/              # FastAPI app (app.py) + background JobManager (jobs.py)
│   ├── cli.py                # argparse CLI: scan/web/importar/planos/dry-run/executar/bench
│   ├── database/             # SQLAlchemy engine + Alembic migrations
│   │   └── migrations/versions/  # 0001..0017, one file per schema change
│   ├── models/                # ORM classes, one file per aggregate group
│   ├── repositories/          # One class per aggregate — DB read/write surface for server/cli
│   ├── scanner/                # Incremental, read-only filesystem discovery
│   ├── sources/                 # Source providers: pasta, Apple Photos, Google Takeout, Lightroom
│   ├── metadata/                 # MetadataExtractor Protocol + exiftool/pure-Python impls
│   ├── thumbnails/                # Thumbnail generation + disk cache
│   ├── classification/             # Evidence/suggestion engine, LLM advisor, templates
│   ├── grouping/                    # Temporal sessions, trips/events, cross-source correlation
│   ├── geolocation/                  # Offline reverse geocoding + opt-in external provider
│   ├── duplicates/                    # Exact/content/visual duplicate detection
│   ├── operations/                     # Plan → dry-run → verified copy executor
│   ├── faces/                           # FaceRecognitionProvider Protocol (stub only in MVP)
│   ├── vision/                           # VisionProvider Protocol (stub only in MVP)
│   ├── security/                          # Path validation, safe subprocess/HTTP, hashing, crypto
│   └── config/                             # TOML settings + defaults + path resolution
├── webapp/                  # React/Vite/TS/Tailwind — the only UI
│   └── src/
│       ├── components/        # One file per screen/widget + colocated *.test.tsx
│       ├── hooks/               # TanStack Query wrappers (useJob, useMidia)
│       ├── ui/                    # Small shared primitives (Botao.tsx)
│       ├── test/                   # Test harness (servidor.tsx mock server, setup.ts)
│       ├── api.ts                   # Typed HTTP client — mirrors fotoorganizer/server types
│       ├── data.ts, fontes.ts, sugestoes.ts  # Client-side data-shaping helpers
│       └── App.tsx                    # Tab shell, top-level state, keyboard shortcuts
├── src-tauri/                # Native macOS shell (Rust) — spawns/owns the Python backend
│   ├── src/main.rs
│   ├── capabilities/
│   └── icons/
├── tests/                     # Mirrors fotoorganizer/ modules; one test_*.py per concern
│   ├── conftest.py               # Shared fixtures
│   └── fixtures.py                # Synthetic media generators (never real personal photos)
├── scripts/                    # Ops/dev scripts: verificar.sh, executar.sh, benchmarks, packaging
├── docs/                        # Architecture, roadmap, decisions, UX direction, privacy
│   ├── ARQUITETURA.md, ROADMAP.md, DECISOES.md, CONFIANCA.md, DIRECAO_DE_ARTE.md, …
│   └── lib-preparatoria/, prompts/, prototipos/, referencia-immich/, referencia-photoprism/
├── .claude/skills/               # Project-specific Claude Code skills
│   ├── fatia-vertical/             # Standard "vertical slice" delivery workflow
│   └── orquestrar/                  # Multi-agent orchestration (territories per specialist)
├── .planning/codebase/              # This directory — generated codebase maps
├── pyproject.toml                     # Python package + deps + pytest config
├── CLAUDE.md / AGENTS.md               # Project instructions (identical content, two names)
└── README.md
```

## Directory Purposes

**`fotoorganizer/server/`:**
- Purpose: the local HTTP API — the only thing the webapp talks to.
- Contains: `app.py` (all REST handlers + Origin/Host guard + static file serving of `webapp/dist`), `jobs.py` (`JobManager`, one background job at a time).
- Key files: `fotoorganizer/server/app.py` (1422 lines — largest file in the backend), `fotoorganizer/server/jobs.py`.

**`fotoorganizer/repositories/`:**
- Purpose: intended single DB-access surface, one class per aggregate.
- Contains: `media.py`, `duplicates.py`, `operations.py`, `settings.py`, `suggestions.py`, `people.py`, `lexico.py`, `inventario.py`.
- Key files: `fotoorganizer/repositories/media.py` (588 lines — filters/facets for the main grid), `fotoorganizer/repositories/__init__.py` (re-export barrel).

**`fotoorganizer/scanner/`:**
- Purpose: read-only, incremental discovery + extraction pipeline that populates the catalog.
- Contains: `scanner.py` (`CatalogScanner`, `ScanControl`), `discovery.py` (filesystem walk), `elegibilidade.py` (filesystem-path vs external-reference discriminator, shared with reconciliation), `reconciliacao.py` (periodic "does this file still exist" pass).
- Key files: `fotoorganizer/scanner/scanner.py` (575 lines).

**`fotoorganizer/sources/`:**
- Purpose: pluggable catalog sources — local folders and external catalogs (Apple Photos, Google Takeout, Lightroom) as first-class `Source` rows in the same catalog.
- Contains: `apple_photos.py`, `google_takeout.py`, `lightroom.py`, `importer.py` (`ExternalCatalogImporter`), `disponibilidade.py` (is this source's volume currently reachable), `reapontar.py` (rewrite catalog paths when a volume remounts elsewhere).
- Key files: `fotoorganizer/sources/importer.py` (431 lines), `fotoorganizer/sources/reapontar.py` (343 lines).

**`fotoorganizer/classification/`:**
- Purpose: turns raw catalog data into evidence and destination suggestions.
- Contains: `engine.py` (main pipeline — deterministic cascade + LLM advisor), `advisor.py` (opt-in Claude-based classifier), `confidence.py` (weakest-link aggregation), `templates.py` (destination path templating), `tipo_imagem.py`, `lexico.py`.
- Key files: `fotoorganizer/classification/engine.py` (1138 lines — second largest file in the backend).

**`fotoorganizer/grouping/`:**
- Purpose: temporal/geographic grouping (sessions, trips, events) and cross-source correlation (clock drift, GPS inheritance).
- Contains: `temporal.py`, `eventos.py`, `eventos_temporais.py`, `correlacao.py`, `datas.py`, `albuns.py`, `origens.py`, `classifier.py`.
- Key files: `fotoorganizer/grouping/correlacao.py` (377 lines).

**`fotoorganizer/operations/`:**
- Purpose: the only module allowed to write outside the catalog. Plan → dry-run → verified copy.
- Contains: `planner.py` (builds `OperationPlan`/`OperationItem`, no filesystem writes), `executor.py` (dry-run + copy with SHA-256 verification and audit logging), `inventario.py` (reachability/inventory queries reused by dry-run).
- Key files: `fotoorganizer/operations/executor.py`, `fotoorganizer/operations/planner.py`.

**`fotoorganizer/security/`:**
- Purpose: every safety invariant that isn't purely a domain rule lives here.
- Contains: `paths.py` (traversal-safe path resolution), `http_seguro.py` (safe outbound HTTP for opt-in geocoding), `hashing.py` (xxhash/SHA-256), `crypto.py` (face embedding encryption via Keychain), `volumes.py` (volume identity for reapontar).
- Key files: `fotoorganizer/security/http_seguro.py` (445 lines), `fotoorganizer/security/paths.py`.

**`fotoorganizer/database/migrations/versions/`:**
- Purpose: append-only Alembic revision history for the SQLite schema.
- Contains: `0001_schema_inicial.py` through `0017_indice_trip_id_event_id.py` (as of this analysis) — each file named `NNNN_description.py`.
- Generated: yes, via `alembic revision`. Committed: yes.

**`webapp/src/components/`:**
- Purpose: one file per screen or reusable widget, matching the tab list in `App.tsx`.
- Contains: `PhotoGrid.tsx` (virtualized grid), `Loupe.tsx` (fullscreen viewer), `Inspector.tsx`, `Sidebar.tsx`, `ArvoreDePastas.tsx` (folder tree scope), `Duplicates.tsx`, `Operations.tsx`, `Review.tsx`, `Trips.tsx`, `Mapa.tsx`, `Panorama.tsx`, `LinhaDoTempo.tsx`, `TemplateEditor.tsx`, `RetomarScan.tsx`, `StatusBar.tsx`, `Confianca.tsx`.
- Key files: each component has a colocated `*.test.tsx` in the same directory — this is the enforced convention, not a separate `__tests__/` tree.

**`tests/`:**
- Purpose: mirrors `fotoorganizer/` — one `test_<module>.py` per concern, not one file per source file.
- Contains: synthetic fixtures only (`fixtures.py`, `conftest.py`) — CLAUDE.md explicitly forbids real personal photos in the repo.
- Key files: `tests/conftest.py`, `tests/fixtures.py`.

**`scripts/`:**
- Purpose: everything that isn't `pytest`/`vitest` but is part of the verification or release loop.
- Contains: `verificar.sh` (the gate — tests + grouping benchmark + webapp build; `--rapido` skips build), `executar.sh` (run the web server locally), `medir_*.py` (measurement/calibration scripts for classification quality), `empacotar_runtime.sh`/`assinar_runtime.sh`/`preparar_versao.sh` (packaging/signing for the Tauri bundle), `avaliar_agrupamento.py` (labeled-scenario benchmark for grouping/classification).
- Generated: no. Committed: yes.

**`docs/`:**
- Purpose: architecture record and product/UX decisions — read before touching classification, grouping, confidence, or UI.
- Contains: `ARQUITETURA.md` (schema + data flow + decision log), `ROADMAP.md` (M0-M7 milestones), `DECISOES.md` (numbered decisions, referenced as `D-0NN` elsewhere), `CONFIANCA.md`, `AGRUPAMENTO.md`, `DIRECAO_DE_ARTE.md`, `METODO_DE_TRABALHO.md`, `PRIVACIDADE.md`, `EMPACOTAMENTO.md`.
- Generated: no. Committed: yes.

## Key File Locations

**Entry Points:**
- `fotoorganizer/app/main.py`: process entrypoint, delegates to CLI.
- `fotoorganizer/cli.py`: all subcommands (`scan`, `web`, `importar`, `volumes`, `inventario`, `reapontar`, `verificar-arquivos`, `planos`, `plano`, `dry-run`, `executar`, `bench`).
- `src-tauri/src/main.rs`: native shell entrypoint, spawns the Python backend.
- `webapp/src/main.tsx`: React app mount point.

**Configuration:**
- `fotoorganizer/config/settings.py`: TOML settings + `UNSET` sentinel + layered override resolution (defaults < TOML < CLI/env).
- `fotoorganizer/config/paths.py`: default data/cache directory resolution (`~/Library/Application Support/FotoOrganizer`, `~/Library/Caches/FotoOrganizer`).
- `pyproject.toml`: Python package metadata, dependency groups (`xmp`, `dev`, `llm`, `apple`), pytest config.
- `webapp/vite.config.ts`, `webapp/tsconfig*.json`: frontend build config.
- `src-tauri/Cargo.toml`, `src-tauri/capabilities/`: native shell build + permissions config.

**Core Logic:**
- `fotoorganizer/classification/engine.py`: suggestion generation pipeline.
- `fotoorganizer/operations/executor.py`: the only file that writes photo files.
- `fotoorganizer/scanner/scanner.py`: cataloging pipeline.
- `fotoorganizer/server/app.py`: full HTTP API surface.

**Testing:**
- `tests/`: pytest suite, mirrors `fotoorganizer/` modules by concern.
- `webapp/src/**/*.test.tsx`: vitest suite, colocated with components.
- `scripts/verificar.sh`: the single verification gate (backend tests + grouping benchmark + frontend tests + build).

## Naming Conventions

**Files:**
- Python: `snake_case.py`, one module per concern; test files `tests/test_<module>.py` matching the concern name, not necessarily 1:1 with source files.
- TypeScript/React components: `PascalCase.tsx` (e.g. `PhotoGrid.tsx`), colocated `PascalCase.test.tsx`.
- Migrations: `NNNN_descricao_em_snake_case.py`, sequential 4-digit prefix.
- Domain vocabulary is Portuguese throughout (`grouping/datas.py`, `sources/reapontar.py`, `classification/lexico.py`) — code, comments, docstrings, commit messages, and docs are all PT-BR. Do not introduce English identifiers into `fotoorganizer/`/`webapp/` to match this codebase's convention.

**Directories:**
- Top-level `fotoorganizer/<domain>/` packages, one per bounded concern (see Directory Layout). Each has an `__init__.py` re-exporting its public surface (e.g. `fotoorganizer/repositories/__init__.py`, `fotoorganizer/models/__init__.py` — the latter imports every model so `Base.metadata` sees all tables for Alembic).
- `webapp/src/{components,hooks,ui,test}/` — flat, no nested feature folders.

## Where to Add New Code

**New backend feature (e.g. a new inference source, a new operation type):**
- Domain logic: new module under the relevant `fotoorganizer/<domain>/` package, or a new package if it's a genuinely new bounded concern (follow the Protocol pattern in `faces/base.py`/`vision/base.py` if it's a pluggable provider).
- Data access: add methods to the relevant class in `fotoorganizer/repositories/`, or extend the repository if the aggregate already has one.
- Schema change: new Alembic revision in `fotoorganizer/database/migrations/versions/`, next sequential number; add the model to `fotoorganizer/models/__init__.py` if it's a new ORM class.
- HTTP surface: new handler in `fotoorganizer/server/app.py` (no router-splitting convention exists yet — keep it in this file); if it's long-running, route it through `JobManager` in `fotoorganizer/server/jobs.py`.
- Tests: `tests/test_<concern>.py`, using synthetic fixtures from `tests/fixtures.py`/`tests/conftest.py` — never real photos.

**New UI screen/component:**
- Implementation: `webapp/src/components/<Name>.tsx` + colocated `<Name>.test.tsx`.
- Data fetching: add a method to `webapp/src/api.ts` (typed to mirror the FastAPI response), wrap it in a hook under `webapp/src/hooks/` if it needs polling/SSE (see `useJob.ts`) or reuse TanStack Query directly (see existing components).
- Wire into `webapp/src/App.tsx`: add to the `ABAS` tuple and `DICAS` map if it's a new top-level tab.

**Shared utilities:**
- Python: put cross-cutting helpers in `fotoorganizer/security/` (safety-related) or the specific domain package if not safety-related — there is no generic `fotoorganizer/utils/`.
- TypeScript: `webapp/src/ui/` for shared presentational primitives (see `Botao.tsx`); `webapp/src/data.ts`/`fontes.ts`/`sugestoes.ts` for shared client-side data-shaping helpers.

## Special Directories

**`fotoorganizer/database/migrations/versions/`:**
- Purpose: schema history, applied via `alembic upgrade head` (called from `upgrade_to_head()` in `fotoorganizer/database/migrate.py` on every catalog open).
- Generated: yes (by `alembic revision --autogenerate` or hand-authored). Committed: yes.

**`webapp/dist/` (not present until built):**
- Purpose: production frontend build, served directly by FastAPI's `StaticFiles` mount in `fotoorganizer/server/app.py`.
- Generated: yes (`npm run build` → `tsc -b && vite build`). Committed: no (build artifact).

**`~/Library/Application Support/FotoOrganizer/` (outside the repo, user machine):**
- Purpose: the single catalog SQLite database (`catalog.db`) and TOML config — never checked into the repo, never a fixture location.
- Generated: yes, at runtime. Committed: no.

**`~/Library/Caches/FotoOrganizer/thumbs` (outside the repo, user machine):**
- Purpose: on-disk thumbnail cache, generated in the background by `fotoorganizer/thumbnails/generator.py`.
- Generated: yes. Committed: no.

**`.claude/skills/`:**
- Purpose: project-specific Claude Code workflows — `fatia-vertical` (standard vertical-slice delivery: test-with-code, `scripts/verificar.sh`, screenshot proof, isolated-context review, single conventional commit) and `orquestrar` (multi-agent dispatch across four fixed territories: `agente-arquivos`, `agente-imagem`, `agente-ux`, `agente-arte`).
- Generated: no. Committed: yes.

---

*Structure analysis: 2026-08-16*
