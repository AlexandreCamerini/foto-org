# Technology Stack

**Analysis Date:** 2026-08-16

## Languages

**Primary:**
- Python 3.12+ (`requires-python = ">=3.12"` in `pyproject.toml`) — engine/core: scanner, classification, grouping, geolocation, operations, server API. Interpreter present in this environment: 3.14.6.
- TypeScript 5.6 (`webapp/tsconfig.app.json`, `webapp/tsconfig.node.json`) — web UI (`webapp/src/`).
- Rust (edition 2021, `rust-version = "1.77"`) — desktop shell (`src-tauri/`), thin wrapper around the FastAPI backend + webview.

**Secondary:**
- Shell (bash) — dev/ops scripts, `scripts/*.sh` (`scripts/verificar.sh`, `scripts/instalar.sh`, `scripts/executar.sh`, `scripts/empacotar_runtime.sh`, `scripts/assinar_runtime.sh`, `scripts/atualizar.sh`, `scripts/preparar_versao.sh`).
- SQL — Alembic migration scripts in `fotoorganizer/database/migrations/versions/` (17 revisions as of this analysis).

## Runtime

**Environment:**
- Python 3.12+ (backend/engine).
- Node.js (version not pinned via `.nvmrc`/`engines`) for the `webapp/` Vite build.
- Rust toolchain (stable, edition 2021) for the Tauri shell build.
- Target platform: macOS only (`src-tauri/tauri.conf.json` → `macOS.minimumSystemVersion: "12.0"`; app icons are `.icns`; entitlements file present).

**Package Manager:**
- Python: no lockfile — dependencies declared directly in `pyproject.toml` (setuptools build backend, `[tool.setuptools.packages.find] include = ["fotoorganizer*"]`). Installed into a project-local `.venv` (`scripts/instalar.sh`, `scripts/verificar.sh` check for `.venv/bin/python`).
- JavaScript: npm. No `package-lock.json` found at the time of this scan under `webapp/` — verify presence before assuming reproducible installs.
- Rust: Cargo, with `src-tauri/Cargo.lock` committed (locked deps).

## Frameworks

**Core:**
- FastAPI `>=0.115` (`fotoorganizer/server/app.py`) — local HTTP API, binds to `127.0.0.1` only.
- Uvicorn `>=0.30` — ASGI server running FastAPI (invoked from `fotoorganizer/cli.py`, `web` subcommand).
- SQLAlchemy `>=2.0` (ORM + Core) — models in `fotoorganizer/models/`, engine setup in `fotoorganizer/database/engine.py`.
- Alembic `>=1.13` — schema migrations, `fotoorganizer/database/migrate.py` + `fotoorganizer/database/migrations/`.
- React 18.3 + React DOM 18.3 (`webapp/package.json`) — UI components in `webapp/src/`.
- Vite 6 (`webapp/vite.config.ts`) — dev server (port 5173, proxies `/api` to `http://127.0.0.1:8765`) and production bundler; output consumed by both FastAPI (`StaticFiles`) and Tauri (`frontendDist: "../webapp/dist"`).
- Tauri 2 (`src-tauri/Cargo.toml`, `src-tauri/tauri.conf.json`) — native macOS shell (`.app`/`.dmg` bundle), spawns/manages the Python backend and displays the webview.
- Tailwind CSS 4 (`@tailwindcss/vite`) — styling, tokens in `webapp/src/index.css`.
- TanStack Query 5 (`@tanstack/react-query`) — server-state/data-fetching in the webapp.
- TanStack Virtual 3 (`@tanstack/react-virtual`) — virtualized photo grid.

**Testing:**
- pytest `>=8.0` — Python test suite in `tests/` (mirrors `fotoorganizer/` module layout).
- httpx `>=0.27` (dev dependency) — used to exercise the FastAPI app in tests (`TestClient`/async client).
- Vitest 4 (`webapp/package.json`, config embedded in `webapp/vite.config.ts` under `test:`) — TS/React unit + component tests, jsdom environment, setup file `webapp/src/test/setup.ts`.
- @testing-library/react 16, @testing-library/jest-dom 7, @testing-library/user-event 14 — component-level testing utilities for the webapp.

**Build/Dev:**
- setuptools `>=68` — Python build backend (`[build-system]` in `pyproject.toml`).
- `tsc -b` (TypeScript project references, `composite: true`) + `vite build` — webapp production build (`webapp/package.json` → `"build"` script).
- `tauri-build` (Rust build script, `src-tauri/build.rs`) — Tauri bundling.
- `@vitejs/plugin-react` — React JSX transform for Vite.

## Key Dependencies

**Critical:**
- SQLAlchemy 2 / Alembic — sole persistence layer and schema evolution mechanism; the catalog DB (`catalog.db`) is the single source of truth.
- Pillow `>=11.0` + pillow-heif `>=0.20` + rawpy `>=0.27` + exifread `>=3.0` — pure-Python metadata/image fallback stack (`fotoorganizer/metadata/purepython.py`), used when `exiftool` is not installed.
- ImageHash `>=4.3` (`imagehash.phash`) — perceptual-hash duplicate detection (`fotoorganizer/duplicates/`).
- xxhash `>=3.4` — fast content hashing pass; paired with stdlib SHA-256 for exact/full hashing.
- reverse-geocode `>=1.6` — offline dataset-based reverse geocoding (`fotoorganizer/geolocation/offline.py`), default and only enabled geocoding path.
- cryptography `>=42.0` (`cryptography.fernet.Fernet`) — encrypts biometric/face embeddings at rest (`fotoorganizer/security/crypto.py`).

**Infrastructure:**
- exiftool (external binary, not a Python package — invoked via `subprocess` in `-stay_open` persistent-process mode, `fotoorganizer/metadata/exiftool.py`). Optional but strongly preferred over the pure-Python fallback (386 tags vs. 8).
- `security` CLI (macOS Keychain, invoked via `subprocess`, no shell) — stores the Fernet key for face-embedding encryption (`fotoorganizer/security/crypto.py`); falls back to a 0600 file when Keychain is unavailable (CI/tests).

**Optional (extras in `pyproject.toml`):**
- `[project.optional-dependencies].xmp` → `defusedxml>=0.7` — hardened XMP/XML parsing; without it XMP reading silently degrades (EXIF/IPTC still work).
- `[project.optional-dependencies].dev` → `pytest`, `httpx`, `defusedxml`.
- `[project.optional-dependencies].llm` → `anthropic>=0.116` — opt-in classification advisor SDK (`fotoorganizer/classification/advisor.py`, `fotoorganizer/classification/lexico.py`).
- `[project.optional-dependencies].apple` → `osxphotos>=0.70` — Apple Photos library importer (`fotoorganizer/sources/apple_photos.py`), requires Full Disk Access.

## Configuration

**Environment:**
- Env-var overrides prefixed `FOTOORG_` (`fotoorganizer/cli.py`, `_ENV_PREFIX = "FOTOORG_"`): `FOTOORG_DATA_DIR`, `FOTOORG_CACHE_DIR`, `FOTOORG_WORKERS`, `FOTOORG_INCLUIR_OCULTOS`, `FOTOORG_SEGUIR_SYMLINKS`, `FOTOORG_SERVICOS_EXTERNOS`. An unset var and an empty exported var are treated identically (both mean "not set") — see `fotoorganizer/cli.py:53`.
- `ANTHROPIC_API_KEY` (or local `ant auth` profile) — read directly by the `anthropic` SDK when the LLM advisor is enabled; never read from code or the repo (`fotoorganizer/classification/advisor.py:108`).
- No `.env` file present in the repo at analysis time.
- Local app config: TOML file at `~/Library/Application Support/FotoOrganizer/config.toml` (optional; defaults apply if absent), loaded via stdlib `tomllib` — `fotoorganizer/config/settings.py`. Sections: `[geral]`, `[scanner]`, `[privacidade]`. Precedence and explicit-vs-default field tracking implemented via a private `UNSET` sentinel + `campos_explicitos` set (not plain `None`/falsy checks).

**Build:**
- Python: `pyproject.toml` (PEP 621 project metadata, dependencies, pytest config `[tool.pytest.ini_options] testpaths = ["tests"]`).
- Webapp: `webapp/vite.config.ts`, `webapp/tsconfig.json` + `webapp/tsconfig.app.json` + `webapp/tsconfig.node.json` (TS project references).
- Tauri: `src-tauri/tauri.conf.json`, `src-tauri/Cargo.toml`, `src-tauri/build.rs`, `src-tauri/capabilities/`, `src-tauri/Entitlements.plist` (macOS hardened-runtime entitlements).

## Platform Requirements

**Development:**
- macOS (Keychain-backed crypto, Apple Photos import, `.icns` bundling all macOS-specific).
- Python 3.12+ in a project-local `.venv` (`scripts/instalar.sh` bootstraps it; `scripts/verificar.sh` refuses to run without `.venv/bin/python`).
- Node.js + npm for `webapp/` (optional at verification time — `scripts/verificar.sh` skips webapp checks gracefully if `npm` or `node_modules` are missing).
- Optional external binary: `exiftool` (metadata extraction upgrade path).
- Optional native tooling for packaging: Rust/Cargo (Tauri build), Xcode command-line tools (macOS code signing, `scripts/assinar_runtime.sh`).

**Production:**
- Distributed as a native macOS app bundle (`.app`/`.dmg`, Tauri `bundle.targets`), minimum macOS 12.0.
- No server/cloud deployment target — fully local-first; the FastAPI process is spawned and supervised by the Tauri shell (or run standalone via `python -m fotoorganizer web`) and only listens on loopback (`127.0.0.1`).
- Catalog database lives at `~/Library/Application Support/FotoOrganizer/catalog.db`; thumbnail cache at `~/Library/Caches/FotoOrganizer/thumbs`.

---

*Stack analysis: 2026-08-16*
