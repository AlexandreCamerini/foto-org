# External Integrations

**Analysis Date:** 2026-08-16

This app is local-first by design (`CLAUDE.md` invariant 4: "nenhum dado sai
da máquina por padrão"). Every network-touching integration below is
opt-in, off by default, and gated by `[privacidade] servicos_externos = true`
(or `FOTOORG_SERVICOS_EXTERNOS`). There is no telemetry, analytics, crash
reporting, or hosted backend anywhere in the codebase.

## APIs & External Services

**LLM classification advisor (opt-in):**
- Anthropic Claude API — `fotoorganizer/classification/advisor.py` (`ClaudeAdvisor`), also referenced in `fotoorganizer/classification/lexico.py`.
  - SDK/Client: `anthropic` Python SDK `>=0.116` (`pyproject.toml` `[project.optional-dependencies].llm`), imported lazily inside `ClaudeAdvisor.__init__` — not a hard dependency of the core install.
  - Auth: `ANTHROPIC_API_KEY` env var or local `ant auth` CLI profile — read directly by the SDK, never stored/handled in app code (`fotoorganizer/classification/advisor.py:108`).
  - Model: `claude-sonnet-5` (`MODELO_PADRAO`, `fotoorganizer/server/app.py`/`advisor.py`), with `thinking={"type": "disabled"}` and a strict JSON-schema `output_config` (`_SCHEMA`) constraining output to `categoria`/`evento`/`justificativa`.
  - Data sent: metadata only — folder names, up to 8 example filenames, date range, photo count, already-geocoded place names (`ClusterInfo` dataclass). Never image bytes.
  - Failure handling: any exception (network/auth/rate-limit) is caught and logged (`log.warning`), returns `None` — never raises into the classification pipeline. A `stop_reason == "refusal"` from the model is also treated as "no opinion".
  - Gating: requires `pip install -e ".[llm]"`, `[privacidade] servicos_externos = true`, and the credential in the environment. Default provider is `NullAdvisor` (always returns `None`, `local == True`).
  - Result is always the lowest-confidence evidence tier and subject to human review (`docs/AGRUPAMENTO.md §3`, `docs/DECISOES.md` D-047–D-060).

**No other outbound API integrations exist.** No payment, email, SMS, analytics, or search-service SDKs found in either `pyproject.toml` or `webapp/package.json`.

## Data Storage

**Databases:**
- SQLite, WAL mode — the sole catalog store, `fotoorganizer/database/engine.py`.
  - Path: `~/Library/Application Support/FotoOrganizer/catalog.db` (`fotoorganizer/config/paths.py::default_db_path`), overridable via `FOTOORG_DATA_DIR`/`--data-dir`.
  - Client/ORM: SQLAlchemy 2 (declarative models in `fotoorganizer/models/`), migrations via Alembic (`fotoorganizer/database/migrations/`, 17 revisions).
  - No remote/hosted database. `CLAUDE.md` documents Railway/Postgres as a possible *future* optional adapter for sync/backup/collaboration — not present in the current codebase (`fotoorganizer/sync/` directory does not exist yet).

**External read-only catalogs (local files, not APIs):**
- Apple Photos library — `fotoorganizer/sources/apple_photos.py`, via `osxphotos` (optional extra `apple`). Reads `~/Pictures/Photos Library.photoslibrary` directly; requires macOS Full Disk Access; read-only, no network.
- Adobe Lightroom Classic catalog (`.lrcat`) — `fotoorganizer/sources/lightroom.py`. Opened as SQLite with `immutable=1` (no lock/journal/write) so Lightroom can stay open concurrently.
- Google Takeout export (local folder, not the Google Photos API) — `fotoorganizer/sources/google_takeout.py`. Explicitly chosen because the hosted Google Photos Library API (since March 2025) only accesses app-created media; Takeout is the local-first path. Reads sidecar `.json` files (`photoTakenTime`, `geoData`, `description`, `favorited`, tagged people) — no network calls.

**File Storage:**
- Local filesystem only. No S3/GCS/Azure Blob or similar object storage integration.

**Caching:**
- Thumbnail disk cache: `~/Library/Caches/FotoOrganizer/thumbs` (`fotoorganizer/thumbnails/`).
- Geocoding cache: `locations` table in the catalog DB, keyed by rounded lat/lon (`fotoorganizer/geolocation/resolver.py`, `cache_key()` at 3-decimal precision, ~110m grid). Cache rows are versioned via a `fonte` string (e.g. `"offline:reverse_geocode/2"`) so a provider/nomenclature change forces re-resolution.
- No external cache service (Redis/Memcached).

## Authentication & Identity

**Auth Provider:**
- None. Single-user local desktop app — no login, no session, no user accounts.

**Server-side protection (not identity, but access control):**
- FastAPI app binds only to `127.0.0.1`/loopback (`fotoorganizer/server/app.py`).
- Additional origin/host check to defend against "simple request" CSRF-style calls from any page open in the user's browser (POSTs without a body skip preflight): `_HOSTS_LOCAIS = {"127.0.0.1", "localhost", "::1"}`, validated against both `Host` and `Origin` headers (`fotoorganizer/server/app.py:88-124`). No token/API-key scheme — the mitigation is host/origin allowlisting, not credentials.
- Physical file operations require explicit confirmation in the request body (`ReapontarBody.confirmar`, `AcaoSugestoesBody`) mirroring the CLI's `--confirmar` flag — defense-in-depth for invariant 2 (no destructive action without explicit approval), not an auth mechanism.

## Monitoring & Observability

**Error Tracking:**
- None (no Sentry/Bugsnag/similar). Errors are caught and logged locally.

**Logs:**
- Python stdlib `logging`, structured but local-only — `fotoorganizer/app/logsetup.py`. Written to `~/Library/Application Support/FotoOrganizer/logs` (`fotoorganizer/config/paths.py::default_log_dir`). No content deemed sensitive is logged per `CLAUDE.md` ("logging estruturado sem conteúdo sensível").

## CI/CD & Deployment

**Hosting:**
- None — distributed as a native macOS app bundle (Tauri `.app`/`.dmg`), not deployed to any server/cloud target.

**CI Pipeline:**
- None found — no `.github/workflows/`, no other CI config detected in the repo. Verification is local/manual via `scripts/verificar.sh` (pytest suite + `scripts/avaliar_agrupamento.py` labeled-scenario benchmark + `webapp` vitest + `webapp` build), explicitly designed to also be usable as a CI or pre-commit hook ("para poder ser usado em hook ou CI") even though no such hook/CI currently invokes it.
- Release/packaging scripts are shell-based and manual: `scripts/preparar_versao.sh`, `scripts/empacotar_runtime.sh`, `scripts/assinar_runtime.sh` (macOS code signing), `scripts/atualizar.sh`.

## Environment Configuration

**Required env vars:**
- None are required for core (offline) functionality — everything has a local default (`fotoorganizer/config/paths.py`, `fotoorganizer/config/settings.py`).

**Optional env vars (all `FOTOORG_` prefixed, `fotoorganizer/cli.py`):**
- `FOTOORG_DATA_DIR`, `FOTOORG_CACHE_DIR`, `FOTOORG_WORKERS`, `FOTOORG_INCLUIR_OCULTOS`, `FOTOORG_SEGUIR_SYMLINKS`, `FOTOORG_SERVICOS_EXTERNOS` — override the `[geral]`/`[scanner]`/`[privacidade]` TOML sections.
- `ANTHROPIC_API_KEY` — only consumed if the LLM advisor extra is installed and explicitly enabled.

**Secrets location:**
- Face-recognition embedding encryption key: macOS Keychain by default (`security` CLI via subprocess, service `"FotoOrganizer"`, account `"embeddings-key"` — `fotoorganizer/security/crypto.py`, `KeychainKeyStore`). Falls back to a `0600`-permission file (`embeddings.key` in the app data dir) when Keychain is unavailable (CI/tests) — `FileKeyStore`.
- No `.env` file or committed secrets found in the repo.
- Anthropic API key is expected to live outside the repo/app entirely (shell env or `ant auth` profile).

## Webhooks & Callbacks

**Incoming:**
- None — the local FastAPI server exposes a REST-style API for the webapp/Tauri shell only (catalog reads, background job status, suggestion actions, operation planning/execution). No external service calls into it.

**Outgoing:**
- None currently active besides the opt-in Anthropic advisor call described above.
- `fotoorganizer/security/http_seguro.py` is a hardened generic HTTP-download utility (scheme allowlist re-checked on every redirect, hard byte cap enforced independent of `Content-Length`, atomic temp-file-then-link write, never overwrites an existing destination) built explicitly **in advance of any consumer** — it exists to back a future opt-in external reverse-geocoding provider (`docs/ROADMAP.md`) and has zero callers today. Documented gaps (SSRF/DNS-rebinding protection, total-transfer-time budget) are deliberately deferred until a real consumer with untrusted input appears.

---

*Integration audit: 2026-08-16*
