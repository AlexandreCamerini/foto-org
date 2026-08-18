# Phase 5: Preparação para lançamento - Research

**Researched:** 2026-08-17
**Domain:** Desktop packaging (Tauri v2 + embedded Python), SQLite/SQLAlchemy indexing, first-run UX validation, performance baselining
**Confidence:** HIGH (all four LANC sub-domains verified by direct code/DB inspection, empirical SQLite experiments, or environment probing — no area relies on training-data recall alone)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**LANC-01 — Empacotamento (Marco 1 apenas)**
- **D-01:** Escopo desta fase é só o Marco 1 de `docs/EMPACOTAMENTO.md` (`.app` funcional sem assinatura, uso pessoal). Marco 2 (assinado + notarizado) fica fora — exige certificado Developer ID e aprovação do custo recorrente do Apple Developer Program (US$99/ano), que `PROJECT.md` § Constraints trava como decisão do dono, não default. Não pedir esse custo nesta fase.
- **D-02:** O scaffold Tauri v2 já existe no repo (`src-tauri/`, commits `5a797e1` "scaffold Tauri v2 + runtime PBS + docs (Marco 1)" e `30ba735` "watchdog anti-órfão, glob de resources e ícones do build") mas nunca foi verificado contra o critério de aceite do Marco 1 documentado em `docs/EMPACOTAMENTO.md` § Marcos: abrir num catálogo novo, escanear fixtures, ver a grade; ao fechar, nenhum processo Python órfão (`ps` / `~/.claude/scripts/portas.py`). O trabalho desta fase é **verificar** esse critério, não construir do zero.
- **D-03:** Se a verificação achar um bug real no caminho crítico (processo órfão, crash ao abrir, falha ao servir o webapp) — corrigir dentro desta fase, mesmo que não estivesse no plano original. Não documentar-e-adiar um defeito que bloqueia o próprio critério de aceite do Marco 1.

**LANC-03 — Onboarding do primeiro acervo (validar, não redesenhar)**
- **D-04:** A Fase 4 (plano `04-06`, commit `d0c3839`) já entregou boa parte do caminho: botão "Adicionar pasta…" nos 3 estados vazios (`Panorama.tsx`, `PhotoGrid.tsx`, `Trips.tsx`), todos abrindo o modal compartilhado `ModalCaminho.tsx` (extraído nessa mesma fase) com progresso de scan e erro surfaced. Esta fase **valida** esse caminho com um teste de usuário genuinamente sem instrução, não desenha um fluxo novo nem um wizard multi-etapa.
- **D-05:** Explicitamente fora de escopo: mensagem/texto específico para "primeira vez" (distinguir de estado vazio genérico) e feedback de progresso mais rico (contagem de arquivos, tempo estimado) além do que já existe. Se a validação revelar que esses realmente bloqueiam um usuário novo, viram achado a ser decidido, não trabalho pré-aprovado.
- **D-06:** Critério de sucesso de LANC-03 (do ROADMAP.md) continua: "Um usuário de primeira vez consegue adicionar sua primeira fonte/pasta e chegar a uma grade populada sem ler documentação" — a verificação precisa ser um teste real desse caminho, não uma inspeção de código.

**LANC-04 — Baseline de performance (acervo real, não fixture)**
- **D-07:** Medir contra o acervo real de produção, não uma fixture sintética. `catalog.db` foi zerado em 2026-08-16 (backup em `catalog-antes-do-reset-20260816-013503.db`) e ainda não rodou uma varredura completa nova — essa rescan é a própria oportunidade de medir a baseline, não um passo separado.
- **D-08:** Métricas: taxa de indexação (varredura), tempo de geração de sugestões, tempo de detecção de duplicatas — as três citadas em LANC-04 no ROADMAP.md. Medir contra o volume real (histórico de auditoria chegou a ~422.738 registros de catálogo; ~99 mil registros conhecidos de acervo real, ver `PROJECT.md` § Context).
- **D-09:** Registrar os números em `docs/PERFORMANCE.md`, documento novo, no mesmo padrão de `docs/AVALIACAO_UX.md` — vira a referência canônica para medir regressão de performance em fases futuras (não anexar como texto solto em `REQUIREMENTS.md`).

**LANC-02 — Índices de FK ausentes (sem área cinzenta — técnico)**
- **D-10:** Sem decisão de produto a capturar aqui. `docs/PLANO_IA_E_PRODUTO.md` §6 item 3 já resume "8 índices, migração de 2 linhas"; `.planning/codebase/CONCERNS.md` já identifica o caso concreto mais urgente: `MediaFile.pasta` sem índice, usado em `LIKE 'prefixo%'` tanto no filtro de mídia quanto em `/api/pastas` (árvore de pastas clicada a cada nível). Índices em `trip_id`/`event_id`/`papel`/`arquivo_offline` já existem, mesmo padrão a seguir. Cabe ao pesquisador/planejador enumerar a lista completa a partir do modelo (`fotoorganizer/models/catalog.py`), não ao dono decidir.

### Claude's Discretion
- Ordem de execução dos 4 LANC dentro da fase (podem ser waves paralelas ou sequenciais — nenhuma dependência estrutural entre eles foi levantada na discussão).
- Formato exato do `docs/PERFORMANCE.md` (tabelas, gráficos, ou só números com contexto) — seguir o padrão que `docs/AVALIACAO_UX.md` já estabelece no repo.
- Se a rescan do acervo real (LANC-04) for lenta o suficiente para travar o fluxo de trabalho da fase, decidir se roda em background enquanto LANC-01/02/03 avançam, ou se bloqueia — nenhuma preferência do dono foi expressa sobre paralelismo interno da fase.

### Deferred Ideas (OUT OF SCOPE)
- **Marco 2 (assinatura + notarização)** — explicitamente adiado até o dono aprovar o custo do Apple Developer Program (US$99/ano). Quando aprovado, `docs/EMPACOTAMENTO.md` já documenta o passo-a-passo completo; não é trabalho de pesquisa nova, só execução.
- **Reconexão de volumes desmontados/iCloud (Lightroom + Apple Fotos, ~90 mil registros)** — mencionado em `PROJECT.md` § Context como candidato de maior alavancagem do backlog, mas fora do escopo desta fase e ainda sem decisão do dono.
- **Mensagem específica de "primeira vez" e feedback de progresso mais rico no onboarding** — não pré-aprovado nesta discussão; só entra se a validação de LANC-03 revelar que bloqueiam um usuário novo de verdade.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| LANC-01 | App empacotado como `.app` assinado e notarizado via Tauri v2 com Python embarcado via python-build-standalone — **nesta fase, só Marco 1 (não assinado)**, per D-01 | § Architectural Responsibility Map, § Standard Stack, § Architecture Patterns (Pattern 1), § Common Pitfalls (Pitfall 1, 2), § Code Examples |
| LANC-02 | Índices de FK ausentes adicionados, incluindo índice em `MediaFile.pasta` | § Common Pitfalls (Pitfall 2, 3 — the load-bearing findings), § Code Examples, § Don't Hand-Roll |
| LANC-03 | Fluxo de onboarding do primeiro acervo existe e é validado | § Architecture Patterns (existing assets), § Validation Architecture |
| LANC-04 | Série de métricas de desempenho medida e registrada como baseline formal | § Architecture Patterns (Pattern 2), § Common Pitfalls (Pitfall 4), § Code Examples |
</phase_requirements>

## Summary

Phase 5 is four largely independent, already-scoped technical tasks — none require new library research, all four require **verification of existing groundwork against a stated acceptance criterion**, not net-new construction. The Tauri v2 + python-build-standalone scaffold, the onboarding UI, and a synthetic-fixture benchmark CLI already exist in the repo; this phase's job is to close the gap between "built" and "verified/measured/indexed."

The single most consequential finding of this research is **not** in CONTEXT.md and changes how LANC-02 must be planned: adding a plain `Index("ix_media_files_pasta", "pasta")` to `MediaFile.pasta` will **not** by itself make SQLite use that index for the existing `.like(f"{prefixo}/%", escape="\\")` query in `_sob_a_pasta()`. This was verified empirically (not assumed) with a live SQLite `EXPLAIN QUERY PLAN`: SQLite only uses an index to optimize `LIKE 'prefix%'` when either the column is indexed `COLLATE NOCASE` (with `case_sensitive_like` off, the default) or `PRAGMA case_sensitive_like=ON` is set for the connection (with a plain `BINARY`-collation index). Without one of those two changes, the new index is created but the query planner still reports `SCAN media_files` — success criterion #2 of this phase ("usam índice, não table scan") would silently fail even though an index technically exists. The fix is a one-line addition to the existing `_set_sqlite_pragmas` connect hook in `fotoorganizer/database/engine.py`, verified safe against **every** LIKE-family query in the codebase — `.like()`, `.not_like()`, and `.ilike()` alike (see Pitfall 3) — not just the one call site that motivated the finding.

A second, independent finding widens Pitfall 2 beyond a single instance: a full audit of all 17 Alembic migrations against the current model files found **four** indexes that exist in the live database schema but are absent from the corresponding `__table_args__`/model declarations (`ix_media_files_gps_estimado_de_id`, `ix_media_files_tipo_imagem`, `ix_media_files_tipo_confirmado`, `ix_sources_volume_id`). This means the ORM model files cannot be trusted alone as an inventory of "which columns already have an index" — LANC-02's enumeration had to be built by reading the migration chain directly, and the fix should include reconciling all four, not just the one this research started from.

The other three LANC items are lower-risk but not zero-risk: LANC-01's scaffold has a real, testable acceptance criterion (`docs/EMPACOTAMENTO.md` § Marcos) that has literally never been run; the environment has everything needed to run it (Rust/Cargo/Tauri CLI installed, no "Developer ID Application" identity present — confirming Marco 2 is correctly out of scope). LANC-03's onboarding path is code-complete per the Phase 4 summary but has zero end-to-end verification — this phase's job is a real, uninstructed user test, not a code read. LANC-04 has a precedent CLI pattern (`fotoorganizer bench`) for indexing throughput but nothing for suggestion-generation or duplicate-detection timing, and both of those operations mutate the database as a side effect (full-recompute writes, per `.planning/codebase/CONCERNS.md`) — the plan must decide whether to measure against a throwaway copy of the freshly-rescanned `catalog.db` or in place.

**Primary recommendation:** Treat all four LANC items as *verification-and-fix* work, not *build* work — run the existing scaffolds/paths against their already-documented acceptance criteria first, and only write new code for the specific gap each verification exposes (the `pasta` index/pragma fix plus the 4-index model/migration reconciliation for LANC-02, whatever LANC-01 verification turns up per D-03, whatever LANC-03's uninstructed user test turns up per D-05, and the suggestion/duplicate timing instrumentation that doesn't yet exist for LANC-04).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| App packaging / process lifecycle (LANC-01) | Native shell (Tauri/Rust) | Backend (Python CLI `cmd_web`) | Tauri owns window + process spawn/kill; the Python side owns clean shutdown (SIGTERM → uvicorn drain → WAL checkpoint) and self-termination watchdog (`_vigia_pai`) — split already exists and is correct, this phase only verifies it |
| Query indexing (LANC-02) | Database / Storage (SQLite schema + Alembic migration) | API/Backend (repository query shape, e.g. `LIKE` vs `GLOB`, and the connection-level PRAGMA) | An index alone is a storage-tier change; whether SQLite's planner *uses* it for a given query is decided by the query shape and connection PRAGMAs the backend tier controls — both tiers must change together for `pasta` |
| First-run onboarding (LANC-03) | Browser/Client (React components, already built) | API/Backend (`/api/scan` failure surfacing) | UI tier already owns the full path (`ModalCaminho.tsx` + 3 empty states); backend tier only needs to keep returning actionable errors, no new work implied here |
| Performance baseline (LANC-04) | API/Backend (engine timing instrumentation) | Database/Storage (catalog size/shape being measured) | Timing wraps existing backend entry points (`scanner.scan_source`, `SuggestionEngine.gerar`, `DuplicateDetector.detectar`); the database tier is the *subject* measured, not the tier doing the measuring |

## Standard Stack

No new libraries are introduced by this phase. All four LANC items build on dependencies already pinned in the repo.

### Core (already in repo, versions verified via `.venv`/`Cargo.lock`)
| Library | Version (verified) | Purpose | Why Standard |
|---------|---------|---------|--------------|
| tauri (Rust crate) | 2.11.5 `[VERIFIED: Cargo.lock]` | Native shell, window lifecycle, macOS bundling | Already the project's locked packaging decision (`docs/EMPACOTAMENTO.md`, DOC-precedence per `.planning/INGEST-CONFLICTS.md`) |
| tauri-cli | 2.11.4 `[VERIFIED: cargo tauri --version]` | Build/bundle command (`cargo tauri build`, `cargo tauri icon`) | Installed and functional in this environment |
| SQLAlchemy | 2.0.36 `[VERIFIED: .venv import]` | ORM + `Index()` declarative construct for LANC-02 | Already the project's fixed stack (CLAUDE.md) |
| alembic | 1.18.5 `[VERIFIED: .venv import]` | Migration for the new indexes | Already the project's fixed stack; 17 prior migrations follow one consistent pattern (see Code Examples) |
| fastapi / uvicorn | 0.115.6 / — | Backend server, unaffected by this phase except for the `_set_sqlite_pragmas` one-line change | Already fixed |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| python-build-standalone (PBS) | latest `install_only` CPython 3.12 arm64 tarball, resolved dynamically by `scripts/empacotar_runtime.sh` from `astral-sh/python-build-standalone` GitHub releases | Embedded Python runtime for the Tauri bundle | Already the locked decision over PyInstaller (fragility of native-lib codesign under sidecar layout — documented rationale in `docs/EMPACOTAMENTO.md`) |

### Alternatives Considered
No alternatives evaluated — CONTEXT.md D-10 marks LANC-02 as "sem área cinzenta — técnico" and LANC-01's stack choice (PBS over PyInstaller) is already an ADR-adjacent DOC-precedence decision (`docs/EMPACOTAMENTO.md`, confirmed in `.planning/INGEST-CONFLICTS.md`). Re-litigating either is out of scope.

**Installation:** No new installs required. `pip install -e ".[xmp,apple]"` (already how the dev `.venv` and `scripts/empacotar_runtime.sh` install the project) and `cargo install tauri-cli --version '^2'` (already present) cover everything this phase touches.

## Package Legitimacy Audit

**Not applicable.** This phase introduces zero new external packages (Python, npm, or Rust crate). All tooling used (SQLAlchemy, Alembic, Tauri, python-build-standalone) is already present and pinned in the repo's `pyproject.toml` / `Cargo.lock`, verified directly from the environment (see Standard Stack table above, all tagged `[VERIFIED]` against live imports/lockfiles, not registry lookups).

## Architecture Patterns

### System Architecture Diagram (LANC-01 — packaging + process lifecycle)

```
┌─────────────────────────────────────────────────────────────┐
│ Tauri shell (Rust, src-tauri/src/main.rs)                    │
│                                                                │
│  setup() ──spawn──▶ Python embedded (PBS)                    │
│                       └─ python -m fotoorganizer web          │
│                          --porta 0 --encerrar-com-pai         │
│                                                                │
│  stdout reader thread ◀── "FOTOORG_READY http://127.0.0.1:N" │
│         │                                                     │
│         ▼                                                     │
│  WebviewWindowBuilder(URL) ──▶ window shows FastAPI-served UI │
│                                                                │
│  RunEvent::ExitRequested ──SIGTERM──▶ backend child process   │
│                                        (uvicorn drains, WAL    │
│                                         checkpoint, exits)     │
└─────────────────────────────────────────────────────────────┘
         ▲ safety net (independent of the SIGTERM path above)
         │
┌────────┴───────────────────────────────────────────────────┐
│ Python backend (fotoorganizer/cli.py cmd_web)                │
│                                                                │
│  if --encerrar-com-pai:                                      │
│    _vigia_pai() thread polls os.getppid() every 2s            │
│    if ppid changed (parent died/reparented) → self SIGTERM    │
└────────────────────────────────────────────────────────────┘
```

This is a two-layer orphan-prevention design (normal-exit SIGTERM from Rust, and a self-watchdog in Python for any exit path that skips the Rust handler) — already implemented, per commit `30ba735` ("watchdog anti-órfão"). LANC-01's job is to *exercise* this against the Marco 1 acceptance criteria, not build it.

### Recommended Project Structure
No new directories. Changes land in:
```
src-tauri/                      # existing scaffold — verify, fix if broken (D-02/D-03)
fotoorganizer/models/*.py       # add Index(...) declarations (LANC-02, both new indexes
                                 # AND the 4 drift-reconciliation ones — see Pitfall 2)
fotoorganizer/database/
  engine.py                     # _set_sqlite_pragmas — add case_sensitive_like=ON (LANC-02)
  migrations/versions/0018_*.py # new Alembic migration (LANC-02, new indexes only —
                                 # the 4 drift ones need no new migration, just model fixes)
docs/PERFORMANCE.md             # new file, AVALIACAO_UX.md-style (LANC-04, D-09)
webapp/src/components/          # ModalCaminho.tsx etc. — no code change expected unless
                                 # LANC-03's uninstructed test finds a real blocker (D-05)
```

### Pattern 1: Alembic migration for a new index — exact repo precedent
**What:** Every prior index addition in this repo follows one shape: `op.batch_alter_table(table, schema=None) as batch_op: batch_op.create_index(name, [col], unique=False)`, paired with a mirrored `Index(...)` declaration added to `__table_args__` in the model file, plus a downgrade that drops it (migrations `0001`, `0005`, `0006`, `0007`, `0008`, `0011`, `0013`, `0017` all create at least one index this way). **In practice, the model-file mirroring step has been skipped four times** (0005, 0006, 0007, 0011 — see Pitfall 2) — the migration itself is a reliable pattern to copy; the "keep the model file in sync" half of the convention has not been reliably followed and needs an explicit verification step this time.
**When to use:** For every new index this phase adds (`pasta`, and the FK columns enumerated below), and retroactively for the 4 drift instances.
**Example:**
```python
# Source: fotoorganizer/database/migrations/versions/0017_indice_trip_id_event_id.py
def upgrade() -> None:
    with op.batch_alter_table('media_files', schema=None) as batch_op:
        batch_op.create_index(
            'ix_media_files_trip_id', ['trip_id'], unique=False
        )

def downgrade() -> None:
    with op.batch_alter_table('media_files', schema=None) as batch_op:
        batch_op.drop_index('ix_media_files_trip_id')
```

### Pattern 2: Timed CLI benchmark against isolated data — existing precedent for LANC-04's scan-rate metric
**What:** `fotoorganizer bench` (`cli.py:566-612`) already measures cold-index and re-scan throughput using `time.monotonic()`, reporting `arq/s`, against synthetic JPEGs in a temp dir/temp DB — explicitly isolated from the real catalog and cache ("nunca para o cache real do usuário").
**When to use:** As the *pattern* for LANC-04's indexing-rate number (D-08), but the actual measurement run must point at real data per D-07 — this command's isolation-from-production design cannot be reused verbatim; a new script or CLI flag path is needed that runs against `catalog.db` directly (the real rescan opportunity D-07 describes), reusing only the `time.monotonic()` + throughput-reporting shape.
**Example:**
```python
# Source: fotoorganizer/cli.py:596-611 (existing pattern to mirror, not the data source to reuse)
inicio = time.monotonic()
_, m1 = scanner.scan_source(fotos)
frio = time.monotonic() - inicio
print(f"Indexação a frio : {m1.indexados} arquivos em {frio:.2f}s "
      f"({m1.indexados / frio:.0f} arq/s)")
```
No equivalent CLI entry point exists yet for `SuggestionEngine.gerar()` or `DuplicateDetector.detectar()` timing — both are currently only reachable via the FastAPI job endpoints (`/api/sugestoes/gerar`, `/api/duplicatas/detectar`, per `.planning/codebase/CONCERNS.md`). LANC-04 needs either a new thin CLI/script wrapper (same `time.monotonic()` pattern, called directly against the engine classes) or timing captured from the existing job/SSE progress records already written to the DB — either is viable; **the model file must be kept honest about which columns are actually indexed** if new instrumentation queries job history.

### Anti-Patterns to Avoid
- **Assuming an `Index()` on a `LIKE`-queried text column is sufficient:** see Pitfall 3 below — this is the single highest-risk assumption in this phase.
- **Trusting `fotoorganizer/models/*.py` as the sole inventory of existing indexes:** see Pitfall 2 — 4 confirmed instances of DB-level indexes with no model-file counterpart.
- **Running `Base.metadata.create_all()` anywhere as a schema shortcut:** the repo already avoids this correctly (`upgrade_to_head()` is the only path used, in both `tests/conftest.py` and `cli.py cmd_web`) — a `create_all()` path would silently produce a schema missing all 4 of the drifted indexes. Do not introduce one.
- **Re-running `SuggestionEngine.gerar()` / `DuplicateDetector.detectar()` against `catalog.db` casually while timing them:** both are documented full-recompute, write-as-a-side-effect operations (`.planning/codebase/CONCERNS.md` § Tech Debt) — every timing run also mutates `Suggestion`/`DuplicateGroup`/`DuplicateMember` rows in the real catalog. Decide up front (this is Claude's Discretion per CONTEXT.md, not pre-decided) whether to measure on a **copy** of the freshly-rescanned `catalog.db` or in place.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Orphan-process prevention for the embedded Python backend | A new watchdog/heartbeat mechanism | The existing two-layer design (`RunEvent::ExitRequested` SIGTERM from Rust + `_vigia_pai` ppid-poll self-SIGTERM in Python, `cli.py:664-679`) | Already implemented and matches Marco 1's acceptance criterion verbatim; this phase verifies it, per D-02, does not replace it |
| Determining whether SQLite will use a new index | Guessing from the `Index()` declaration alone | `EXPLAIN QUERY PLAN <query>` against a real or representative SQLite connection, with the exact PRAGMA state the app uses in production | SQLite's LIKE-optimization rule is a documented, narrow condition (see Pitfall 3) — the only reliable check is running the actual query plan, not reading the schema |
| An inventory of "which FK columns already have an index" | Reading `models/*.py` `__table_args__` alone | Cross-referencing every `create_index`/`drop_index` call across all files in `fotoorganizer/database/migrations/versions/` against the current model files | 4 confirmed drift instances (Pitfall 2) prove the model files alone under-report what's actually indexed |
| A new empty-state / onboarding component | A new "first-time" wizard or welcome screen | `ModalCaminho.tsx` + the 3 existing empty-state buttons (`Panorama.tsx`, `PhotoGrid.tsx`, `Trips.tsx`), all wired by Phase 4 plan `04-06` | D-04/D-05 explicitly forbid new UI construction here — the path exists, only validation is in scope |
| Indexing-throughput measurement scaffolding | A new benchmark harness from scratch | `time.monotonic()` + throughput-reporting pattern already in `cmd_bench` (`cli.py:566-612`) | Established, working pattern in the same file; only the data source (real catalog vs. synthetic) needs to change |

**Key insight:** Every piece of "Don't Hand-Roll" guidance in this phase points at code that already exists in this repo — the risk in Phase 5 is not choosing the wrong library, it's (a) re-building something that was already built in Phase 4 or in the packaging scaffold commits, or (b) trusting a source-of-truth file (the ORM model) that this research proved is not, in fact, the full truth.

## Common Pitfalls

### Pitfall 1: Assuming "unsigned" means "won't launch" (or the reverse) on Apple Silicon
**What goes wrong:** Planning either over-scopes (trying to acquire ad-hoc signing tooling that isn't needed) or under-scopes (assuming `cargo tauri build` with no `signingIdentity` configured produces something Gatekeeper will silently refuse to run at all).
**Why it happens:** macOS on Apple Silicon (arm64 — the project's target, per `scripts/empacotar_runtime.sh`'s `aarch64-apple-darwin`) requires *some* code signature for any executable to launch, even for purely local use. Ad-hoc signing (pseudo-identity `-`) satisfies that requirement without a paid Developer ID, but it does **not** suppress the Gatekeeper "unidentified developer" prompt — the user must still right-click → Open once. `[CITED: v2.tauri.app/distribute/sign/macos/, community sources cross-checked via WebSearch]`
**How to avoid:** Verify empirically, don't assume: after `cargo tauri build`, run `codesign -dv --verbose=4 "Foto Organizer.app"` to see what identity actually got applied (Tauri's bundler behavior when no identity is configured is not fully documented — confirm directly rather than trust the doc's silence on the default case), then confirm the right-click → Open path actually works, exactly as `docs/EMPACOTAMENTO.md` § Marcos already specifies as the Marco 1 acceptance test.
**Warning signs:** The verification task skips actually launching the built `.app` and only checks that the build command exited 0.

### Pitfall 2: Model file and migration chain drifting out of sync — 4 confirmed instances, not one
**What goes wrong:** A full audit of every `create_index`/`drop_index` call across all 17 files in `fotoorganizer/database/migrations/versions/`, cross-referenced against the current `__table_args__` in every `fotoorganizer/models/*.py` file, found **four** indexes that exist in the live database schema but have no corresponding declaration in the ORM model:

| Index (exists in DB) | Column | Migration that created it | Present in current model `__table_args__`? |
|---|---|---|---|
| `ix_media_files_gps_estimado_de_id` | `MediaFile.gps_estimado_de_id` | `0005` | ❌ No |
| `ix_media_files_tipo_imagem` | `MediaFile.tipo_imagem` | `0006` | ❌ No |
| `ix_media_files_tipo_confirmado` | `MediaFile.tipo_confirmado` | `0007` | ❌ No |
| `ix_sources_volume_id` | `Source.volume_id` | `0011` | ❌ No (`Source` has no `__table_args__` at all) |

`[VERIFIED: grep "create_index" across all 17 migration files, cross-checked against fotoorganizer/models/catalog.py's current __table_args__ for both MediaFile and Source]`. This has no functional impact today — schema is always built via `upgrade_to_head()`, never `Base.metadata.create_all()` (verified in `tests/conftest.py` and `cli.py`) — but it means the model files under-report which columns are already indexed by exactly these 4. Enumerating LANC-02's "índices de FK ausentes" list from `catalog.py` alone (as D-10's wording literally suggests: "enumerar a lista completa a partir do modelo") would incorrectly treat these 4 columns as unindexed candidates when they are not.
**Why it happens:** Migrations in this project are hand-written (not `alembic revision --autogenerate`), so nothing mechanically enforces that a `create_index` in a migration is mirrored into the model file — the two are two independently-maintained sources describing the same schema, and drift is a plain human-error mode with no CI check catching it.
**How to avoid:** When LANC-02 enumerates its target list, cross-check against the live migration chain (`grep -n "create_index" fotoorganizer/database/migrations/versions/*.py`), not just against `models/*.py`. This phase should also fix the drift itself as a cheap, in-scope cleanup: add the 4 missing `Index(...)` declarations to their respective model files (no new migration needed for these 4 — the DB-level index already exists, only the model file needs to catch up).
**Warning signs:** A planned migration tries to `create_index` on a column that already has one in the DB, causing an Alembic error at `upgrade_to_head()` time — this is the exact failure mode a model-file-only enumeration would walk into for any of these 4 columns.

### Pitfall 3: A plain `Index()` on `MediaFile.pasta` does not make SQLite use it for the existing `LIKE 'prefix%'` query (LOAD-BEARING — verified empirically)
**What goes wrong:** LANC-02's success criterion is "consultas por prefixo de pasta ... usam índice, não table scan." The obvious implementation — add `Index("ix_media_files_pasta", "pasta")` and stop — silently fails this criterion. `_sob_a_pasta()` (`fotoorganizer/repositories/media.py:171`) calls `MediaFile.pasta.like(f"{prefixo}/%", escape="\\")`, a plain (case-insensitive by SQLite default) `LIKE`. SQLite's query planner only rewrites a `col LIKE 'prefix%'` into an indexable range scan (`col >= 'prefix' AND col < 'prefiy'`) under one of two conditions: (a) the index is built `COLLATE NOCASE` and `case_sensitive_like` is off (the default), or (b) `PRAGMA case_sensitive_like=ON` is set for the connection and the index uses the default `BINARY` collation.
**Why it happens:** This is SQLite-specific, undocumented in most ORM-level tutorials, and easy to miss because the index *is* created successfully and *is* used by other equality queries (e.g. exact-match lookups) — only the prefix-`LIKE` case silently keeps scanning.
**How to avoid — verified fix, two viable options:**
1. **Recommended:** Add one line to the existing `_set_sqlite_pragmas` connect hook in `fotoorganizer/database/engine.py`: `cursor.execute("PRAGMA case_sensitive_like=ON")`. Verified empirically (see Code Examples) that this does **not** break any other LIKE-family usage in the codebase — a full sweep of every `.like(`, `.not_like(`, and `.ilike(` call site (plus a raw-keyword `grep -rn "LIKE"` to catch any hand-written SQL in `text()` blocks — none found) turned up exactly three usage shapes, all confirmed safe:
   - `.ilike()` calls (search text, camera, país/cidade, palavra-chave — `repositories/media.py:238-284`) compile on SQLite to `lower(x) LIKE lower(y)`, a function-wrapped comparison entirely independent of the `case_sensitive_like` pragma — confirmed by direct query-plan inspection.
   - `MediaFile.pasta.like(...)` (`repositories/media.py:171`) — the one this fix targets. Its only caller passes `filters.pasta`/`prefixo` values sourced from `/api/pastas` (which itself reads from `MediaFile.pasta`), never free-typed user text, so a switch from case-insensitive to case-sensitive prefix matching changes no observable behavior.
   - `MediaFile.caminho.not_like(PADRAO_SQL_REFERENCIA_EXTERNA)` (`scanner/reconciliacao.py:86`, `scanner/scanner.py:379`) — the pattern is `"%://%"`, which contains no alphabetic characters, so case sensitivity is a non-issue by construction; it also has a leading wildcard, so it was never index-eligible regardless of this pragma.
2. **Alternative (more invasive, not recommended without cause):** Change `_sob_a_pasta` to use SQLite's `GLOB` operator instead of `LIKE` — GLOB is always case-sensitive and index-eligible regardless of the `case_sensitive_like` pragma — but this requires re-escaping `pasta`'s existing `%`/`_`/`\` LIKE-escaping logic into GLOB's `*`/`?`/`[...]` special-character set, a larger and riskier diff for the same outcome.
**Warning signs:** `EXPLAIN QUERY PLAN SELECT ... WHERE pasta LIKE ?` still reports `SCAN media_files` (not `SEARCH ... USING INDEX`) after the migration lands — this is the actual verification step the plan must include, not just "migration applied successfully."

### Pitfall 4: Suggestion/duplicate-detection timing runs mutate the catalog they're measuring
**What goes wrong:** Both `SuggestionEngine.gerar()` and `DuplicateDetector.detectar()` are documented full-recompute operations that write `Suggestion`/`DuplicateGroup`/`DuplicateMember` rows as a side effect (`.planning/codebase/CONCERNS.md` § Tech Debt). A naive LANC-04 timing script that calls these directly against the freshly-rescanned production `catalog.db` will leave that catalog in a "sugestões geradas" / "duplicatas detectadas" state as a byproduct of a measurement run, not a deliberate product action.
**Why it happens:** No existing CLI entry point isolates these two operations from the real catalog the way `cmd_bench` isolates the scanner (temp DB, temp cache).
**How to avoid:** Decide explicitly (Claude's Discretion, per CONTEXT.md — not pre-decided by the user) whether to (a) copy the freshly-rescanned `catalog.db` to a throwaway file before timing generation/detection, or (b) run in place and treat the resulting suggestions/duplicates as a legitimate first real analysis pass, not just a benchmark artifact. Either is defensible; document the choice in `docs/PERFORMANCE.md` itself so future baseline re-measurements use the same method (methodology reproducibility is D-09's whole point).
**Warning signs:** The plan runs the timing script without first deciding this, and the production catalog ends up with an undocumented, un-reviewed batch of auto-generated suggestions.

## Code Examples

### PRAGMA fix for the `pasta` index (verified via live SQLite EXPLAIN QUERY PLAN)
```python
# Source: empirical verification in this research session (python3 sqlite3 + SQLAlchemy,
# against the project's own .venv SQLAlchemy 2.0.36). Target file:
# fotoorganizer/database/engine.py

def _set_sqlite_pragmas(dbapi_connection, _record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.execute("PRAGMA case_sensitive_like=ON")  # NEW — required for the
    # pasta prefix-LIKE query to use ix_media_files_pasta; verified not to
    # affect any .like()/.not_like()/.ilike() call site in the codebase
    # (see Pitfall 3 for the full sweep).
    cursor.close()
```

Verification query to include in the plan's acceptance check (must show `SEARCH`, not `SCAN`):
```sql
EXPLAIN QUERY PLAN
SELECT * FROM media_files WHERE pasta LIKE '/some/prefix/%' ESCAPE '\';
-- Expected after fix: SEARCH media_files USING INDEX ix_media_files_pasta (pasta>? AND pasta<?)
-- Before fix (index present, pragma absent): SCAN media_files
```

### Enumerated FK-index gap list (LANC-02), derived from direct model + migration + usage-site inspection
`[VERIFIED: grep across fotoorganizer/models/*.py, all 17 files in fotoorganizer/database/migrations/versions/, and fotoorganizer/{repositories,server,operations,duplicates,classification,scanner}` for actual query-site usage of each column]`.

**Already indexed (in the model file, no action needed):** `ix_media_files_hash_rapido`, `ix_media_files_data_capturada`, `ix_media_files_mtime_tamanho`, `ix_media_files_papel`, `ix_media_files_arquivo_offline`, `ix_media_files_trip_id`, `ix_media_files_event_id`, `ix_metadata_entries_media_id`, `ix_evidence_media_id`, `ix_suggestions_status`.

**Already indexed in the DB, missing from the model file (fix the model, no new migration — Pitfall 2):** `ix_media_files_gps_estimado_de_id`, `ix_media_files_tipo_imagem`, `ix_media_files_tipo_confirmado`, `ix_sources_volume_id`.

**Not indexed anywhere — candidates for the new migration:**

| Column | Table | Real consumer found | Already covered by a composite unique index? |
|---|---|---|---|
| `MediaFile.pasta` | `media_files` | `_sob_a_pasta` (repositories/media.py:171) — folder filter + `/api/pastas` tree, clicked at every level | No — needs new index **and** the pragma/GLOB fix (Pitfall 3) |
| `Suggestion.media_id` | `suggestions` | `engine.py:1042,1083,1106`; `server/app.py:724`; `repositories/media.py:118,149`; `repositories/suggestions.py:119,296`; `operations/planner.py:60`; `operations/inventario.py:161` — heavily queried (Inspector's per-media suggestion lookup, "sem_sugestao" filter, planner join) | No |
| `OperationItem.plan_id` | `operation_items` | `repositories/operations.py:71,141`; `operations/executor.py:272` — list items of a plan, the Operations screen's core query | No |
| `OperationItem.media_id` | `operation_items` | `operations/planner.py:68` — check pending ops per media | No |
| `AuditLog.plan_id` | `audit_log` | `repositories/operations.py:95,128`; `operations/executor.py:131,163` — audit trail per plan (dry-run + execution log) | No |
| `DuplicateMember.media_id` | `duplicate_members` | `operations/planner.py:79`; `duplicates/detector.py:302` — "which group is this media in" reverse lookup | No — covered only as the *second* column of `UniqueConstraint(group_id, media_id)`, not usable for a media_id-only filter |
| `MediaFile.location_id` | `media_files` | `repositories/media.py:278,356` — location filter, join to `Location` | No |
| `ScanSession.source_id` | `scan_sessions` | `server/app.py:1324,1328` — join for scan-session listing per source | No |
| `FaceOccurrence.media_id` / `person_id` | `face_occurrences` | `repositories/people.py:42,108,109` | No |
| `FaceEmbedding.person_id` | `face_embeddings` | Relationship traversal only (`people.py` model, cascade delete) — no direct filtered query site found `[grep found no WHERE-clause usage]` | No — **lower priority**, no measured/observed query-site consumer found; per the project's own stated principle ("índice quando o custo de escrita se justifica por um consumidor real e mensurável", `catalog.py` comment), this one may not clear the bar — flag as Open Question for the planner |
| `MediaTag.tag_id` | `media_tags` | No query-site usage found `[grep found zero filters on this column outside the model file]` | Partially — covered as second column of `UniqueConstraint(media_id, tag_id)`, same caveat as `DuplicateMember.media_id` | **Lower priority** — no observed consumer |
| `Trip.location_id` | `trips` | No query-site usage found | No — **lower priority**, no observed consumer |

This gives roughly 8-10 real candidate indexes for the new migration (matching the "8 índices" figure in `docs/PLANO_IA_E_PRODUTO.md` §6, though that document predates the `trip_id`/`event_id` additions already shipped in migration `0017` — treat its number as directional, not authoritative; this table is the current, code-verified count), **plus 4 separate drift-reconciliation fixes to the model files that need no new migration** (Pitfall 2). `MediaFile.pasta` is unambiguously the highest-priority new index (explicit success criterion #2, `LIKE`-queried at every folder-tree click); `Suggestion.media_id`, `OperationItem.plan_id`/`media_id`, and `AuditLog.plan_id` are the next tier (frequently-hit screens: Inspector, Operations). `FaceEmbedding.person_id`, `MediaTag.tag_id`, and `Trip.location_id` have no observed query-site consumer today — flagged as an Open Question rather than auto-included, consistent with the project's own "consumer justifies the write cost" precedent already documented in `catalog.py`.

### Migration template to follow exactly
```python
# Source: fotoorganizer/database/migrations/versions/0017_indice_trip_id_event_id.py
# (the most recent, most directly analogous prior migration)
"""índices de FK ausentes (fase 5, LANC-02)

<justificativa por índice, mesmo padrão das migrações 0005/0017: qual
consulta faz SCAN hoje, qual tela/endpoint aciona, medido ou observado por
grep de uso real>

Revision ID: 0018
Revises: 0017
Create Date: <data>

"""
from typing import Sequence, Union
from alembic import op

revision: str = '0018'
down_revision: Union[str, None] = '0017'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('media_files', schema=None) as batch_op:
        batch_op.create_index('ix_media_files_pasta', ['pasta'], unique=False)
        batch_op.create_index('ix_media_files_location_id', ['location_id'], unique=False)
    with op.batch_alter_table('suggestions', schema=None) as batch_op:
        batch_op.create_index('ix_suggestions_media_id', ['media_id'], unique=False)
    # ... one batch_alter_table block per table touched, mirroring __table_args__
    # additions in the corresponding fotoorganizer/models/*.py file.
    # Separately (same PR, no new migration): add the 4 missing Index(...)
    # declarations for indexes that already exist in the DB (Pitfall 2).


def downgrade() -> None:
    # symmetric drop_index calls, reverse order
    ...
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| PyInstaller sidecar for embedded Python | python-build-standalone (PBS) + venv congelado | Already decided, documented in `docs/EMPACOTAMENTO.md` (references Tauri issue #11992 for PyInstaller `externalBin` notarization fragility) | Not a change introduced by this research — pre-existing project decision, out of scope to revisit |
| PySide6 desktop UI | Web UI (FastAPI + React) served into a Tauri WKWebView | Commit `2e0ef1a`, 2026-07-31 | Already complete; this phase only packages the already-current architecture |

**Deprecated/outdated:** `docs/PLANO_IA_E_PRODUTO.md` §6's "8 índices, migração de 2 linhas" figure predates migration `0017` (which already added 2 of those 8) — treat as historical context, not a current target count; use the Code Examples table above instead.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `cargo tauri build` with no `signingIdentity` configured in `tauri.conf.json` applies ad-hoc signing automatically on macOS arm64 (rather than producing a fully unsigned, non-launchable binary) | Common Pitfalls (Pitfall 1) | If wrong, Marco 1's acceptance test (open the built `.app`) fails immediately and the plan needs an explicit `"signingIdentity": "-"` addition to `tauri.conf.json` before LANC-01 can be verified at all — low risk because the verification step itself (Pitfall 1's `codesign -dv` check) will surface this in the first minute of the LANC-01 task, before any other work depends on it |

**All other claims in this research are `[VERIFIED]` (direct code read, live SQLite/SQLAlchemy experiment, or environment probe) or `[CITED]` (official Tauri docs) — no other assumption requires user confirmation before planning.**

## Open Questions (RESOLVED)

1. **Should `FaceEmbedding.person_id`, `MediaTag.tag_id`, and `Trip.location_id` get indexes in this phase?**
   - What we know: no query-site (`WHERE`/`join` filter) usage of these columns was found via grep across the backend. They exist for relationship traversal (ORM lazy-loads via `relationship()`), not for filtered queries today.
   - What's unclear: whether "no consumer found by grep" truly means "no consumer" or just "not yet exercised" — face recognition (`FaceEmbedding`) is opt-in/disabled by default per invariant 6, so its query patterns may simply not exist in the codebase yet, not because they're unneeded but because the feature isn't built out.
   - Recommendation: exclude these three from LANC-02's migration by default (matches the project's own documented precedent: "índice quando o custo de escrita se justifica por um consumidor real e mensurável," `catalog.py` comment) — planner should confirm this reading of D-10's "enumerar a lista completa a partir do modelo" is about *FK columns with real consumers*, not *every FK column that exists*.
   - **RESOLVED:** fechada pelo plano `05-01`, Task 2 — a recomendação foi adotada: `FaceEmbedding.person_id`, `MediaTag.tag_id` e `Trip.location_id` ficam **fora** da migração `0018`, e a exclusão é registrada com motivo no docstring da própria migração (critério de aceite: `grep -rn "FaceEmbedding" fotoorganizer/models/people.py | grep -c "Index("` retorna 0). A leitura de D-10 confirmada é *FK columns with real consumers*: os 9 índices criados têm consumidor citado com arquivo:linha.

2. **Where should suggestion-generation and duplicate-detection timing be captured — a new CLI entry point, or driven through the existing `/api/sugestoes/gerar` / `/api/duplicatas/detectar` job endpoints?**
   - What we know: `SuggestionEngine.gerar()` and `DuplicateDetector.detectar()` are directly callable Python classes/methods (no CLI wrapper exists yet); the FastAPI job system already tracks job start/end times via SSE progress records (per `.planning/codebase/CONCERNS.md`'s description of the job system).
   - What's unclear: whether the existing job records already have enough timestamp granularity to extract "time to generate suggestions" without new instrumentation, or whether a direct-call timing script (mirroring `cmd_bench`'s `time.monotonic()` pattern) is simpler and more reproducible.
   - Recommendation: a direct-call script is lower-risk and more reproducible for a one-time baseline document (`docs/PERFORMANCE.md`, D-09) — avoids depending on job/SSE internals that could change independently of this measurement. Planner should pick one; this is Claude's Discretion territory per CONTEXT.md, not a locked decision.
   - **RESOLVED:** fechada pelo plano `05-04`, Task 1 — escolhido o **script de chamada direta**, `scripts/medir_baseline_producao.py`, no padrão `time.monotonic()` de `cmd_bench`. O job system / SSE não é instrumentado nesta fase. Registrado também em `05-VALIDATION.md` § Wave 0 Requirements como a segunda dependência de Wave 0.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Rust toolchain (`rustc`, `cargo`) | LANC-01 build | ✓ | rustc 1.97.1 / cargo 1.97.1 | — |
| `tauri-cli` | LANC-01 build/bundle | ✓ | 2.11.4 (matches `tauri` crate 2.11.5 in `Cargo.lock`) | — |
| Node.js / npm | Frontend build (`webapp && npm ci && npm run build`), required before `scripts/empacotar_runtime.sh` embeds `webapp/dist` | ✓ | node v24.14.0 / npm 11.9.0 | — |
| `.venv` (project's Python 3.12 dev env) | Running `scripts/verificar.sh`, pytest, migrations | ✓ | Python 3.12.5 (symlinked `.venv/bin/python -> python3.12`) | — |
| exiftool | Metadata extraction (optional per CLAUDE.md; pure-Python fallback exists) | ✓ | 13.55 (homebrew) | Pure-Python extractor (Pillow + exifread + pillow-heif + rawpy) already the documented fallback |
| Developer ID Application certificate (macOS keychain) | Marco 2 only (signing + notarization) — **not required for this phase per D-01** | ✗ | — (only "Apple Development" and "Apple Distribution" identities present, neither is a Developer ID Application cert usable for outside-App-Store distribution) | N/A — confirms Marco 2 is correctly out of scope; no fallback needed since D-01 already excludes it |
| Disk space for build artifacts (PBS runtime + Cargo target + DMG) | LANC-01 build | ✓ (marginal) | 12Gi free on `/` at research time | If a `cargo tauri build` run fails on disk space, clear `src-tauri/target/` between iterations — no other fallback needed, just noting the margin is not large |

**Missing dependencies with no fallback:** None — LANC-01 through LANC-04 are all executable in this environment as scoped (Marco 1 only).

**Missing dependencies with fallback:** None applicable beyond exiftool's already-documented fallback (pre-existing, not introduced by this phase).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework (Python) | pytest 8.x (`[tool.pytest.ini_options] testpaths = ["tests"]`, `pyproject.toml`) |
| Framework (webapp) | vitest (`webapp/package.json` `"test": "vitest run"`), 17 existing `*.test.tsx` files |
| Config file | `pyproject.toml` (pytest); `webapp/vite.config.ts`/`vitest` defaults (no separate vitest.config found — inline in vite config, not read in this session, existing precedent per `04-06-SUMMARY.md`'s use of `npm test`) |
| Quick run command | `.venv/bin/python -m pytest -q --no-header` (backend); `cd webapp && npm test` (frontend) |
| Full suite command | `scripts/verificar.sh` (pytest + `scripts/avaliar_agrupamento.py` benchmark + vitest + `npm run build`) — **note:** this script does not run `cargo tauri build` or any Rust check; LANC-01 verification is manual/outside `verificar.sh` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LANC-01 | `.app` builds, opens on a fresh catalog, scans fixtures, shows the grid, leaves no orphan Python process on close | manual (native app lifecycle — not automatable in this stack) | `cd src-tauri && cargo tauri build`, then manual launch + `ps aux \| grep fotoorganizer` / `~/.claude/scripts/portas.py` after quitting | N/A — no existing automated test for native app lifecycle; this is inherently manual per D-02's own description of the acceptance criterion |
| LANC-02 | `pasta` and other enumerated FK columns use an index (`SEARCH`, not `SCAN`) after migration | integration (DB-level) | New test recommended: `EXPLAIN QUERY PLAN` assertion against a migrated test DB (see Code Examples verification query) — no existing test covers query-plan shape | ❌ Wave 0 — new test file needed, e.g. `tests/test_indices.py` |
| LANC-03 | First-time user reaches a populated grid without documentation | manual UAT (uninstructed user test, per D-06 — explicitly *not* code inspection) | None automatable — the requirement is specifically about an unguided human, not a scripted click-path | N/A by design (D-06) |
| LANC-04 | Baseline metrics measured and documented in `docs/PERFORMANCE.md` | manual/scripted one-time measurement, not a repeatable pytest assertion | New script (mirroring `cmd_bench`'s pattern) run once against the real, freshly-rescanned catalog | ❌ Wave 0 — new script needed; no existing CLI entry point for suggestion/duplicate timing |

### Sampling Rate
- **Per task commit:** `.venv/bin/python -m pytest -q` for any LANC-02 model/migration change; `npm test` for any (unlikely, per D-05) webapp change.
- **Per wave merge:** `scripts/verificar.sh` (full backend+frontend suite) — does **not** cover LANC-01 (native build) or LANC-03/04 (manual/one-time) by design; those need explicit manual verification steps in the plan itself, not a CI gate.
- **Phase gate:** Full `scripts/verificar.sh` green, plus the three non-automatable verifications (LANC-01 native launch test, LANC-03 uninstructed user test, LANC-04 documented measurement run) each explicitly checked off before `/gsd:verify-work`.

### Wave 0 Gaps
- [ ] `tests/test_indices.py` (or equivalent) — asserts `EXPLAIN QUERY PLAN` uses `SEARCH ... USING INDEX` (not `SCAN`) for the `pasta` prefix query post-migration, covering LANC-02's actual success criterion, not just "migration applied."
- [ ] A timing script for `SuggestionEngine.gerar()` / `DuplicateDetector.detectar()` against real data (see Open Question 2) — covering LANC-04.
- [ ] No gap for LANC-01/LANC-03 — both are inherently manual verifications per the phase's own success criteria (D-02, D-06), not something a Wave 0 automated test should attempt to replace.

## Security Domain

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Single-user local app, no auth surface touched by this phase |
| V3 Session Management | No | N/A |
| V4 Access Control | No | N/A |
| V5 Input Validation | No | LANC-02's index/pragma change does not alter what input reaches the query — `filters.pasta` is already sourced from `/api/pastas` tree values, not free user text (verified in Pitfall 3) |
| V6 Cryptography | No | Not touched by this phase |

### Known Threat Patterns for this stack
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| N/A for this phase | — | This phase's four items (packaging verification, indexing, onboarding UX validation, performance measurement) do not introduce new attack surface. LANC-01's embedded-Python packaging already inherits the project's existing invariants (subprocess never uses `shell=True`, no App Sandbox entitlement requested, local-only listen — none of that changes here). `PRAGMA case_sensitive_like=ON` (Pitfall 3's fix) is a query-planner behavior change, not a security control, and was verified not to weaken any existing `.like()`/`.not_like()`/`.ilike()`-based search path. |

No new ASVS-relevant surface is introduced by this phase; the project's existing 8 invariants (CLAUDE.md) remain the operative security baseline and are unaffected by packaging verification, index additions, onboarding UX validation, or performance measurement.

## Sources

### Primary (HIGH confidence)
- Direct repository reads: `docs/EMPACOTAMENTO.md`, `docs/PLANO_IA_E_PRODUTO.md` §6, `.planning/codebase/CONCERNS.md`, `.planning/codebase/STACK.md`, `.planning/PROJECT.md` § Context/Constraints, `fotoorganizer/models/*.py` (all 9 model files), `fotoorganizer/repositories/media.py`, `fotoorganizer/database/{engine,migrate}.py`, all 17 files in `fotoorganizer/database/migrations/versions/` (full `create_index`/`drop_index` audit), `fotoorganizer/cli.py`, `fotoorganizer/scanner/{elegibilidade,reconciliacao,scanner}.py`, `src-tauri/{main.rs,tauri.conf.json,Entitlements.plist,Cargo.toml,Cargo.lock}`, `scripts/{empacotar_runtime.sh,assinar_runtime.sh,verificar.sh}`, `tests/conftest.py`, `webapp/package.json`, `.planning/phases/04-consist-ncia-visual-secund-ria/04-06-SUMMARY.md`.
- Empirical verification (this session): Python `sqlite3` `EXPLAIN QUERY PLAN` experiments (4 scenarios: default LIKE, `case_sensitive_like=ON` LIKE, GLOB, NOCASE index) confirming the exact conditions under which SQLite uses an index for prefix-`LIKE`; a second SQLAlchemy-level experiment confirming `.ilike()` on SQLite compiles to `lower(x) LIKE lower(y)` (independent of the `case_sensitive_like` pragma) using the project's own `.venv` (SQLAlchemy 2.0.36); a full-codebase sweep of every `.like(`, `.not_like(`, `.ilike(`, and raw `LIKE` keyword usage to confirm the pragma change has no unintended side effect.
- Environment probes (this session): `rustc/cargo/tauri-cli --version`, `security find-identity -v -p codesigning`, `df -h`, `node/npm --version`, `.venv/bin/python --version`, `exiftool -ver`.

### Secondary (MEDIUM confidence)
- [Tauri v2 macOS Code Signing](https://v2.tauri.app/distribute/sign/macos/) — confirms ad-hoc signing via `signingIdentity: "-"` and that Gatekeeper enforcement on macOS is not optional; does not explicitly document the fully-unconfigured default case (flagged as Assumption A1).
- WebSearch cross-referencing (dev.to articles, GitHub issue #8763) on Tauri v2 ad-hoc signing behavior — consistent with the official docs page, used only to corroborate, not as sole source.

### Tertiary (LOW confidence)
None — every claim in this document is either directly verified against this repository's code/environment or cited to an official source.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries, all versions read directly from `.venv`/`Cargo.lock`, zero registry lookups needed.
- Architecture: HIGH — packaging lifecycle, onboarding UI ownership, and migration pattern all read directly from source, not inferred.
- Pitfalls: HIGH for Pitfalls 2-4 (all verified by direct code read, exhaustive grep audit, or live experiment); MEDIUM for Pitfall 1 (macOS default-signing behavior is corroborated but not from a single fully authoritative source — flagged as Assumption A1).

**Research date:** 2026-08-17
**Valid until:** 30 days (stable, internal-codebase-driven research; the one external-doc-dependent claim, Tauri's default signing behavior, should be re-verified if Tauri is upgraded before this phase executes)
