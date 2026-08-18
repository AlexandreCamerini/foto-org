# Project Research Summary

**Project:** Foto Organizer — v2.0 milestone (6-feature slice on a shipped, local-first macOS photo cataloging app)
**Domain:** Local-first desktop DAM/photo cataloging — integration research (not greenfield), covering EXIF write, GenAI folder classification, sidebar navigation, folder picker/import progress, confidence-as-navigation-axis + catalog health index, and a generalized evidence-corroboration engine
**Researched:** 2026-08-18
**Confidence:** MEDIUM-HIGH

## Executive Summary

This is not a new product being designed from scratch — it is six features being grafted onto an already-shipped, invariant-governed photo catalog (FastAPI/SQLite backend, React/TS + Tauri webapp, exiftool-based metadata pipeline, a weakest-link confidence model, and a measured GPS-corroboration engine, D-074). All four research passes converge on the same posture: **reuse existing infrastructure and decision patterns aggressively, but do not assume any existing pattern transfers by analogy without re-deriving its guarantees for the new write shape or evidence type.** Feature 1 (EXIF write) needs a genuinely new module because the existing copy-executor's safety model (exclusive-create to a new path) has no equivalent for in-place mutation. Feature 2 (GenAI folder→city/event) reuses the `ClassificationAdvisor`/`ClaudeAdvisor` plumbing almost verbatim but needs its own opt-in flag, its own result type, and cost-tracking that doesn't exist yet anywhere in the codebase. Features 3 and 4 are frontend-only or infra-light (a Tauri dialog plugin). Features 5 and 6 are pure backend/aggregation work with no new dependencies, but both carry a sharp philosophical trap: any scalar "health score" or any uncalibrated categorical corroboration threshold directly violates the project's own D-017/CONFIANCA.md weakest-link discipline, which has already been violated and fixed once before (D-071).

The recommended approach, consistent across STACK/ARCHITECTURE/PITFALLS: no new core frameworks or packages beyond `tauri-plugin-dialog`; a new isolated `exif_write/`-style package for feature 1 (never fold into `operations/` or `metadata/`); a sibling result type and new confidence-cascade rung for feature 2 (never overload the existing `AdvisorResult`); a pure `GROUP BY`/`COUNT` distribution (never a blended score) for feature 5's health index; and a "land narrow, extract broad only when a second consumer exists" strategy for feature 6's corroboration generalization, with each new field (date/time, city, country) requiring its own measurement pass before any threshold is trusted — exactly the discipline D-074 already modeled for GPS.

The dominant risk cluster is feature 1 (EXIF write): four of eight critical pitfalls concentrate there — treating in-place mutation like a copy operation, silent desync with Lightroom/Photos.app/cloud-sync clients that also touch the file, format-specific write corruption history for CR3/HEIC that the project's read-side validation (D-026) does not cover, and permission/mount-state checks the read/copy paths never needed. Feature 2's risk is process discipline (cost visibility, opt-in scope, backoff) rather than data safety. Features 5 and 6's risk is conceptual: building something that looks done (a percentage, a threshold) but quietly reintroduces the arbitrary-weighting problem the confidence model exists to prevent.

## Key Findings

### Recommended Stack

No new core framework or Python package is required for any of the six features. `exiftool` (already the sole metadata authority per D-026/D-027) gets a write counterpart via a new short-lived-subprocess invocation, not the shared `-stay_open` reader process. The `anthropic` SDK is already pinned (`>=0.116`) and already supports the structured-output pattern feature 2 needs. Features 5 and 6 are SQL/Python only — explicitly confirmed **no pandas, no analytics library, no new confidence-scoring dependency**. The one genuinely new dependency across the whole milestone is `tauri-plugin-dialog` for feature 4's native folder picker.

**Core technologies:**
- `exiftool` CLI (≥13.00, already a runtime dependency) — writes GPS lat/long + IPTC/XMP city/country in place; same tool as the read path avoids two extractors disagreeing on tag precedence (the exact problem D-026/D-027 already solved once).
- `anthropic` Python SDK (≥0.116, already pinned) — folder-name → city/event classification, reusing `ClassificationAdvisor`'s opt-in/structured-output/never-crash pattern; Message Batches API is the right call shape *if* classification runs as a catalog-wide sweep (50% cost discount, async, fits a progress-bar UX), plain synchronous calls if it stays interactive/on-demand.
- `tauri-plugin-dialog` (new) — native OS folder picker replacing `ModalCaminho.tsx`'s raw text `<input>`; keep the text-input fallback for the non-Tauri dev-server path.
- SQLAlchemy 2 (existing) — health index and confidence-tier filtering are `GROUP BY`/`COUNT` aggregate queries against the existing `Evidence`/`Suggestion` tables, sub-second at ~423K rows in WAL-mode SQLite.

### Expected Features

**Must have (table stakes):**
- Native OS folder picker replacing free-text path entry (single clearest table-stakes gap found — every desktop app expects "Browse…").
- Search-as-you-type filter + keyboard navigation over the existing folder tree (`ArvoreDePastas.tsx`), matching the teclado-first constraint already established in `Review.tsx`.
- Filter the grid by confidence tier (alta/média/baixa) — this is "the missing verb on an existing noun": confidence filtering already exists as a row-level predicate (`_condicao_lacuna`) but isn't a first-class navigation axis yet.
- A per-dimension health rollup (location/date/category percentages, shown in parallel, never blended into one number).
- Date/time corroboration and city/country corroboration (via normalized exact-match, not a fuzzy distance) as direct, lower-risk extensions of D-074's confront-both-sides pattern.

**Should have (differentiators):**
- Confidence tier as a first-class sidebar section + a DSL search token (`confianca:baixa`), tying features 3 and 5 together — no competitor DAM (Immich, PhotoPrism, digiKam) has evidence-confidence as a navigation axis at all.
- Health index broken down by field, with a trend-over-time view once feature 6 exists.
- A single shared `confrontar_evidencias()`-style abstraction — explicitly flagged as a judgment call to defer until a second real consumer exists, not to build speculatively now.

**Defer / anti-features (do not build):**
- A blended single "catalog health score" combining location + date + category into one weighted number — this is the aggregate-level version of the exact anti-pattern D-017 already rejected at the suggestion level.
- A decorative circular/radial progress "gauge" replacing the linear bar without confirming what's actually missing (visibility vs. granularity vs. ETA) — needs one clarifying question to the owner before any build.
- A second, separate "filter" sidebar panel duplicating the top bar — already explicitly killed once in `docs/NAVEGACAO.md`.
- Fuzzy string-distance thresholds for city/country corroboration agreement — an invented, uncalibrated constant, the same category of move D-074 already rejected once ("nenhum fator novo foi adicionado").
- Volume-aware (source→volume→folder) sidebar tree — pre-planned but explicitly gated on a trigger ("lista de fontes passar de uma tela") that hasn't happened yet; do not build ahead of it.

### Architecture Approach

The existing system is a strictly layered desktop app (React/TS+Tauri webapp → FastAPI local server → domain services → repositories → SQLAlchemy/SQLite), with one hard invariant this milestone must not blur: cataloging is read-only, and `operations/` is the *only* module allowed to write outside the catalog. All architectural decisions below follow from either extending that boundary correctly (feature 1) or staying inside it (features 2–6).

**Major components (new or extended):**
1. **`exif_write/` (new package)** — `MetadataWriter` Protocol + `ExifToolWriter` (short-lived per-file subprocess, not the shared `-stay_open` reader), its own `ExifWritePlan`/`ExifWriteItem` dry-run/audit model structurally parallel to but not inheriting from `operations/`, reusing `AuditLog` and `security/` path/hash helpers.
2. **`ClaudeAdvisor` extended with a second method** — new `LocationAdvisorResult` (city/país/justificativa) alongside the existing `AdvisorResult`, plugged into `SuggestionEngine`'s cascade as a new rung with its own `SCORES_REFERENCIA` entry (`llm_pasta` or similar, distinct from the existing `llm` score) — never overload the existing schema.
3. **`repositories/media.py` extended** — health index and confidence-tier filtering both build on the existing `panorama()`/`LACUNAS`/`_condicao_lacuna` precedent (pure aggregation, no new schema); add an index on `Suggestion.nivel` (currently missing) since navigation-axis filtering runs at per-click frequency, not once-per-panorama-load.
4. **`grouping/correlacao.py` extended in place (narrow-first)** — new per-field comparators (`_comparador_data`, `_comparador_pais`) plugged into the same three-way agree/disagree/pass-through shape as `_confrontar_com_outro_lado`; extract a shared primitive into `classification/confidence.py` only once a second consumer outside `grouping/` actually needs it.
5. **Frontend-only** — `Sidebar.tsx`/`ArvoreDePastas.tsx` (feature 3) and `ModalCaminho.tsx`/`StatusBar.tsx` (feature 4) share a file surface; sequence them as adjacent slices to avoid two sessions rebasing the same ~300-line file.

### Critical Pitfalls

1. **In-place EXIF write treated as "just another copy operation"** — the copy-executor's exclusive-create trick has no equivalent for mutation-in-place; rely on exiftool's own temp+rename atomicity, pass `-overwrite_original` explicitly (don't leave stray `_original` backup files in the real photo tree for iCloud/Dropbox to pick up as "new"), and design the empty-field precondition as the crash-recovery mechanism (idempotent retry).
2. **Concurrent access is silent trust-corruption, not a blocked write** — macOS/POSIX locking is advisory; Lightroom/Photos.app/cloud sync can silently overwrite or desync from what was just written. Solve with detection-and-disclosure in dry-run (flag managed-library proximity), not with locking.
3. **CR3/HEIC write reliability does not inherit from D-026's read-side validation** — both formats have real historical write-corruption bugs; verify per format/exiftool-version, add structural (not just 3-field) post-write verification, and scope initial rollout to formats actually present in volume in the real acervo.
4. **Health index degenerates or silently becomes a weighted sum either way** — literal weakest-link at population scale is a useless always-"baixa" metric; any scalar rollup (mean, weighted average) is exactly the arbitrary-summing D-017 forbids, just moved up a level of abstraction. Build a distribution (counts/percentages per tier + an explicit "sem evidência" bucket), never a single score — this bug class has already shipped once (D-071, zero-evidence items rendering as "Alta").
5. **Generalizing D-074's corroboration to categorical fields without separately calibrating each field** — GPS agreement is continuous/measured (40,678 real pairs); a naive exact-match port for city/country swaps a calibrated tolerance for an unmeasured, assumed one, and ignores that "país" agreement happens by chance at a high background rate in a skewed acervo. Each new field needs its own `scripts/calibrar_raio_incerteza.py`-style measurement pass and its own logged decision before any threshold is trusted.

## Implications for Roadmap

Based on research, suggested phase structure (the architecture research's recommended build order, which deviates from the owner's stated priority order 1,2,3,4,5,6 in two places — both deviations are file-conflict/sequencing optimizations, not scope changes, and should be flagged for owner sign-off rather than silently applied):

### Phase 1: EXIF Location Write
**Rationale:** Highest invariant-risk item in the milestone (it's the one that revises invariant 7); isolating it first, before UI churn competes for review attention, matches the project's existing vertical-slice convention for invariant-sensitive work.
**Delivers:** A new `exif_write/` package (writer Protocol + implementation, dry-run/execute/audit plan model) that writes GPS/city/country only to currently-empty fields, with full-tag diff verification and format-scoped rollout.
**Addresses:** Feature 1 table stakes (empty-field-only write, atomic in-place mutation, audit trail parity with `operations/`).
**Avoids:** Pitfalls 1–4 (copy-pattern-clone assumption, managed-library/cloud-sync desync, CR3/HEIC corruption, permission/mount-state blind spot) — all four must be resolved in this phase's design before implementation starts.

### Phase 2: GenAI Folder → City/Event Classification
**Rationale:** Independent of everything else, but landing it before Phase 5 lets the health index's aggregation scope account for the new `llm_pasta`-origin evidence type from the start instead of retrofitting a facet later.
**Delivers:** A second `ClaudeAdvisor` method + `LocationAdvisorResult`, a new cascade rung in `SuggestionEngine`, a dedicated opt-in config key, and first-class cost visibility (token/usage capture, pre-run cost estimate, hard per-run ceiling, backoff on 429).
**Addresses:** Feature 2 table stakes (metadata-only payload, structured output, never-crash-the-pipeline).
**Avoids:** Pitfalls 5–6 (opt-in flag piggybacking on the existing Advisor's consent, cost-visibility assumed-already-built when it isn't).

### Phase 3: Folder Picker + Import Progress
**Rationale:** Swapped ahead of Phase 4's original position (sidebar) relative to the owner's stated order — pure file-conflict avoidance: the picker replaces the modal that the sidebar's "Adicionar pasta…" button triggers, so doing the picker first means sidebar work lands on already-settled wiring instead of two sessions touching the same ~60-line region in parallel. Not a functional dependency; ignorable if both ship in one slice.
**Delivers:** `tauri-plugin-dialog` integration replacing `ModalCaminho.tsx`'s free-text input (with graceful non-Tauri fallback retained), and a clarified answer (from the owner) on what "gauge" actually means before building anything beyond the existing linear bar.
**Addresses:** Feature 4 table stakes (native picker, path validation through existing `security/` layer).
**Avoids:** The "decorative gauge with no functional gap closed" anti-feature; the folder-picker path-validation security gotcha (symlink/network path bypassing invariant 5).

### Phase 4: Sidebar Navigation
**Rationale:** Lands after the picker so it inherits settled button/modal wiring rather than changing the same file region concurrently.
**Delivers:** Search-as-you-type + keyboard navigation over `ArvoreDePastas.tsx`, active-node auto-scroll, expand/collapse-all with persisted state.
**Addresses:** Feature 3 table stakes; explicitly does not build the volume-aware tree ahead of its documented trigger.
**Avoids:** Drift from `docs/NAVEGACAO.md`'s three already-approved decisions (sidebar=place/top=scope, no dropdown-per-field panel, no module-per-tab fragmentation).

### Phase 5: Confidence as Navigation Axis + Catalog Health Index
**Rationale:** Matches the owner's explicit priority (5 before 6); builds on `panorama()`/`LACUNAS`, which already exist — this is "promote an existing filter to first-class" more than new construction. Landing after Phases 1–2 means the health index's field set already includes EXIF-write and GenAI-classification evidence types from day one.
**Delivers:** A `GROUP BY`/`COUNT` distribution endpoint (per-tier percentages, per field, plus an explicit "sem evidência" bucket) and a promoted confidence-tier filter alongside year/camera/extension; an index on `Suggestion.nivel`; a payload shape (named facets, not fixed-arity) that leaves room for Phase 6's corroboration signal without an endpoint-contract break.
**Addresses:** Feature 5 table stakes and its constraint note (this is a rollup across finalized suggestions, not a new scoring formula — does not touch the weakest-link rule).
**Avoids:** Pitfall 7 (scalar health index that degenerates or silently sums) — the single most load-bearing design constraint in this entire milestone; route the design through whoever owns `docs/CONFIANCA.md` before implementation.

### Phase 6: Generalized Corroboration Engine
**Rationale:** Matches the owner's order and its own status as highest-regression-risk backend change (touches D-074's calibrated, measured GPS behavior — 91.1%/93.6% coverage numbers already in the code's own comments).
**Delivers:** New in-module comparators inside `grouping/correlacao.py` (`_comparador_data` for date/time, `_comparador_pais` for country) following the existing three-way agree/disagree/pass-through shape, each backed by its own real-catalog measurement and logged decision (mirroring D-074's own methodology) — extraction of a shared primitive into `classification/confidence.py` explicitly deferred until a second real consumer exists.
**Addresses:** Feature 6 table stakes (date/time corroboration, city/country corroboration via normalized exact-match) and unblocks Feature 7 (active learning), which `PROJECT.md` explicitly defers until both 5 and 6 exist.
**Avoids:** Pitfall 8 (unmeasured generalization of a calibrated GPS threshold to categorical fields; background/chance agreement rate mistaken for real corroboration).

### Phase Ordering Rationale

- Dependency structure is soft, not hard: all six features are technically independent at the schema level (confirmed in ARCHITECTURE.md's dependency table) — the ordering above optimizes for invariant-risk-first sequencing, file-conflict avoidance, and value-compounding (Phase 2 before 5 enriches 5's evidence coverage; Phase 5's payload shape anticipates Phase 6's later facet), not for unblocking.
- The two deviations from the owner's stated order (4 before 3) must be surfaced explicitly for sign-off rather than silently applied — they're justified by shared-file-conflict avoidance, not by new information about priority.
- Phases 5 and 6 both carry a philosophical trap (arbitrary aggregation) that the other four phases don't — this is why both get an explicit "avoids" pitfall tied to `docs/CONFIANCA.md`/D-017 rather than a technical one.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 1 (EXIF write):** format-specific write reliability (CR3/HEIC) and managed-library/cloud-sync desync behavior are both flagged MEDIUM confidence from external sources only — verify against the actual acervo's format distribution and the actual sync clients in use (iCloud Drive/Dropbox) before finalizing scope.
- **Phase 2 (GenAI classification):** the call-shape decision (Batch API sweep vs. synchronous interactive) and the model-tier decision (Sonnet 5 default vs. re-measuring Haiku 4.5 per the D-059/D-060 method) are both open and cost-sensitive — needs a short research/measurement pass before implementation, not just design.
- **Phase 6 (corroboration generalization):** each new field (date/time, city, country) requires its own calibration measurement against real catalog data before any threshold is trusted — this is empirical work, not desk research, but should be scoped as a research-phase-equivalent step before coding.

Phases with standard patterns (skip research-phase):
- **Phase 3 (folder picker):** `tauri-plugin-dialog` is a well-documented, standard v2 plugin install; no open design questions beyond the "what does gauge mean" clarification, which is a product question, not a research one.
- **Phase 4 (sidebar navigation):** the information architecture is already decided (`docs/NAVEGACAO.md`); this phase is filling in a documented shape, not discovering one.
- **Phase 5 (health index/confidence axis, mechanics only):** the aggregation pattern (`panorama()`/`LACUNAS`) is an established, already-shipped precedent — the risk here is conceptual/design discipline (see Pitfall 7), not technical uncertainty.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | MEDIUM-HIGH | exiftool write mechanics HIGH (official docs + matches existing D-026/D-027 tool choice); Anthropic API cost/pricing levers MEDIUM (verified against current docs but pricing changes fast, third-party pricing aggregators used for relative comparisons); confidence-rollup stack choice HIGH (no new dependency, trivially confirmed) |
| Features | MEDIUM-HIGH | Grounded primarily in the project's own prior engineering (D-074/D-025/D-017, docs/NAVEGACAO.md, docs/referencia-immich/, docs/referencia-photoprism/) — high-confidence internal sourcing; external verification (Tauri dialog plugin, record-linkage/sensor-fusion literature) is MEDIUM, WebSearch-sourced but cross-checked |
| Architecture | HIGH | Every claim grounded in a direct read of the named file/line in the actual codebase (executor.py, advisor.py, confidence.py, correlacao.py, media.py, jobs.py, and the relevant webapp components) — not inferred or templated |
| Pitfalls | MEDIUM-HIGH | Grounded in the project's own code and decision log (D-017/D-059/D-060/D-074/D-075) plus verified external sources for exiftool write behavior and POSIX locking semantics; CR3/HEIC corruption history and cloud-sync-conflict behavior are single/thin-source and explicitly flagged for empirical verification |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- **Feature 4's "gauge" ask is not yet scoped** — research found the existing linear progress bar already satisfies every documented principle (honest, non-blocking, persistent). Whether the owner wants more visibility, more granularity, or an ETA (each a different, cheap fix) versus a literal widget-shape change is unresolved — get this answered before Phase 3 implementation, not during it.
- **Feature 2's call shape (batch sweep vs. interactive) is not yet decided** — this materially changes the API pattern (Message Batches vs. synchronous), the cost-visibility UX (one bill vs. N interleaved calls), and whether prompt caching is worth wiring at all (only pays off above a 1,024-token system-prompt floor). Needs an owner decision before Phase 2 design is finalized.
- **Feature 2's model tier (Sonnet 5 vs. Haiku 4.5) is unresolved** — D-059/D-060 already found cheap-model hallucination failure on a richer input than folder-name-only; do not infer the old conclusion transfers, re-run the measurement method on a small real sample before committing to a tier.
- **Feature 6's shared-abstraction question (narrow-in-module vs. broad-shared-primitive) is deliberately left open** — architecture research recommends landing narrow first and extracting only once a second real consumer exists; this is a judgment call for whoever implements Phase 6, not a pre-decided design.
- **Cloud-sync (iCloud Drive/Dropbox) behavior under atomic-rename EXIF writes is unverified against the actual clients touching the real acervo** — treat as a pre-Phase-1 verification step, not an assumption.
- **The volume-aware sidebar tree's trigger condition** (`docs/NAVEGACAO.md`: "lista de fontes passar de uma tela") should be explicitly checked against current catalog state before Phase 4 — if it's been met since the 2026-08-17 snapshot, that changes Phase 4's scope.

## Sources

### Primary (HIGH confidence)
- Direct codebase reads: `fotoorganizer/metadata/base.py`, `metadata/exiftool.py`, `operations/executor.py`, `operations/planner.py`, `security/paths.py`, `classification/advisor.py`, `engine.py`, `confidence.py`, `grouping/correlacao.py`, `models/inference.py`, `models/catalog.py`, `repositories/media.py`, `server/jobs.py`, `webapp/src/components/Sidebar.tsx`, `ArvoreDePastas.tsx`, `ModalCaminho.tsx`, `StatusBar.tsx`, `Confianca.tsx`, `src-tauri/Cargo.toml`
- `docs/DECISOES.md` (D-017, D-018, D-025, D-059, D-060, D-074, D-075), `docs/CONFIANCA.md`, `docs/NAVEGACAO.md`, `.planning/PROJECT.md`, `.planning/codebase/ARCHITECTURE.md`, `.planning/codebase/CONCERNS.md`, `.planning/codebase/STRUCTURE.md`
- ExifTool official GPS tag reference and GitHub source (GPS.pm) — https://exiftool.sourceforge.net/TagNames/GPS.html
- Claude Platform Docs, Prompt caching and Batch processing — https://platform.claude.com/docs/en/build-with-claude/

### Secondary (MEDIUM confidence)
- ExifTool forum threads on GPS write behavior and `-overwrite_original`/backup semantics; ExifTool Version History and GitHub issue #313 (HEIC corruption on write)
- POSIX advisory locking on macOS — Apple Developer Forums
- Tauri v2 dialog plugin docs — https://v2.tauri.app/plugin/dialog/
- `docs/referencia-immich/`, `docs/referencia-photoprism/` (internal competitor-reference docs, treated as primary for IA decisions already made, secondary for external competitor behavior claims)
- Record linkage (Fellegi-Sunter) and sensor/track-fusion literature, used as domain-analogy for Feature 6's generalization, not domain-identical

### Tertiary (LOW confidence)
- anthropic-sdk-python GitHub issue #689 (Batch API + cache_control friction) — single issue, flagged as risk to verify empirically
- Third-party pricing aggregators (finout.io, cloudzero.com, pricepertoken.com) for Haiku vs. Sonnet vs. Opus relative pricing — directionally consistent across sources but not Anthropic's own pricing page
- GPS auto-derivation of ref from signed decimal in exiftool — referenced in community sources, not confirmed in official docs; treat as unverified, write both tags explicitly regardless

---
*Research completed: 2026-08-18*
*Ready for roadmap: yes*
