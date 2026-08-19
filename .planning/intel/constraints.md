# Constraints (SPEC intel)

Synthesized from the 5 documents classified `SPEC` in this ingest. Each
entry: title, source, type, content block.

---

## 1. Evidence & confidence model

- **source:** `docs/CONFIANCA.md`
- **type:** schema + nfr (aggregation rule)

Every inference is a row in `evidence`: target field, origin, value,
level (alta/média/baixa), reference score, human-readable justification,
`versao_logica`. No arbitrary point-summing (the v1 prototype's additive
score was explicitly discarded for this reason).

Origin → level → reference score table (highest to lowest):
EXIF date/GPS valid (alta, 0.95) → offline reverse geocoding (alta, 0.85)
→ external geocoding service (média, 0.75) → GPS inherited from another
source within minutes, decaying with Δt (média, 0.75×fator) → country/city
from folder name (média, 0.60) → external-catalog album name covering the
period (média, 0.55) → place inferred from temporal neighbors (média,
0.55) → LLM-suggested category from metadata, opt-in (média, 0.55) →
filesystem date without EXIF (baixa, 0.40) → visual-analysis-only scene
(baixa, 0.30) → face recognition (always requires human confirmation,
level derived from similarity). Manual user correction = alta (1.0),
overrides everything.

Album name intentionally ranks **below** folder name (0.55 vs 0.60) even
though both are dono-authored words — the photo *is* in the folder, it
only *coincides in time* with the album. Tie-break lives in
`docs/AGRUPAMENTO.md` §2c.

**Aggregation rule (weakest link):** a destination suggestion is composed
of template fields (e.g. `{categoria}/{ano}/{pais}/{cidade}`). Each field
uses its best available evidence (highest score, ties broken by table
order); the field's confidence is that evidence's level; the suggestion's
overall confidence is that of its **weakest** field. No averaging, no
summing.

Additional rules: conflicting evidence for the same field is all kept,
the chosen one is flagged, conflict surfaces in UI as "needs
confirmation"; insufficient evidence leaves the field empty — **never
invent** a value, especially location; `versao_logica` allows
regeneration + audit of which rule produced which suggestion; level
thresholds (alta ≥0.8, média ≥0.5, baixa <0.5) are the stable UI-badge
interface, reference scores are configurable in the future.

---

## 2. Grouping cascade (viagem/evento/neutra classification)

- **source:** `docs/AGRUPAMENTO.md`
- **type:** protocol / algorithm contract

Deterministic-first cascade with opt-in LLM advisor as last resort.
Sessions = photos clustered by >3-day temporal gap (unchanged), further
cut when the timeline crosses the 50km home radius (`raio_casa_km`),
confirmed by the next GPS-bearing photo in the same state to avoid
false splits from a single bad-GPS frame.

Cascade order (per session): (1) folder path contains "Viagens" category
segment → VIAGEM (pasta 0.60); (2) folder has event keyword (birthday,
"N anos", wedding, etc.) → EVENTO named by folder (pasta 0.60); (3)
country recognized in folder names → VIAGEM (pasta 0.60); (4) GPS median
distance from home >100km → VIAGEM (gps 0.85); (5) GPS geocoded country
known AND duration ≥3 days AND home unknown → VIAGEM (geocoding 0.85);
(6) folder has non-technical album-like name AND duration ≤2 days →
EVENTO named by folder (pasta 0.60); (7) nothing above → NEUTRA → opt-in
LLM advisor or unlabeled (llm 0.55). A cluster of hours is never a trip
(the original defect this cascade fixes). Home = modal ~11km GPS cell,
requires ≥20 GPS photos and ≥30% in-cell, else "home unknown."

**Cross-source correlation** (`grouping/correlacao.py`, pre-cascade):
clock-drift correction via same-photo anchor pairs (hash or phash match)
across sources, median offset per camera, discarded if MAD >3min or <2
anchors; GPS inheritance from the nearest cross-source/cross-camera
GPS-bearing photo within a corrected ±10min window, evidence
`vizinhanca_temporal` (0.75×fator, decaying 1.0→0.6 across the window).
"Home" itself only uses real (non-inherited) GPS.

**Album-name tie-break (2c, formalizes D-030/D-034):** album names, nunca
divide/create sessions. Neutral sessions stay unnamed. Folder-derived
labels (rules 2/3/6) win over album. Derived labels (country/date-range,
rules 1/4/5) let album substitute if a candidate exists. Album selection
among nesting albums: shelf-albums ("Férias", "Family") demoted last,
then most-photos-first, then shortest-name/alphabetical as pure
tiebreak. `MIN_FOTOS_ALBUM=3`, device/app album names filtered out.

**Advisor** (`ClassificationAdvisor`, opt-in): only consulted for NEUTRA
sessions, only when `[privacidade] servicos_externos=true` AND
`anthropic` package installed AND credential present. Only metadata
leaves the machine, never the image. Result = evidence origin `llm`,
level média-baixa (0.55). `NullAdvisor` is the default (no-op).

**NOTE — stale model reference (auto-resolved, see INGEST-CONFLICTS.md):**
this document's Implementação line names `ClaudeAdvisor` as using
`claude-opus-4-8`. Per `docs/DECISOES.md` D-022 (locked) the advisor was
upgraded to Opus 5, and per D-060 (locked, "gate fechado") the advisor's
final/current model is **Sonnet 5**. ADR precedence wins: treat the
advisor's model as Sonnet 5, not `claude-opus-4-8`.

---

## 3. Design tokens & 3-panel layout (webapp UI spec)

- **source:** `docs/DIRECAO_DE_ARTE.md`
- **type:** api-contract-equivalent (UI/design-system contract)

Layout: 3 panels (sidebar/fontes+filtros, biblioteca grid+controls,
inspetor) + a status bar spanning the full width across all 6 tabs.
Sidebar/inspector collapsible (`[`/`]`, ⌘1/⌘3 only in packaged Tauri app
— browser reserves ⌘1–⌘8). Duplicates use side-by-side compare instead of
grid.

Tokens (source of truth: `webapp/src/index.css` `@theme` block — this doc
mirrors it, not the reverse): window bg `#08090a` (near-black, not gray);
surfaces are white-opacity layers over that bg (`.02`/`.05`/`.08`,
borders `.1`/`.18`), no heavy shadows; text `#fbfbfc` / `#9499a2` /
`#686c73`; single desaturated accent `#e8eaee` (never a chromatic accent)
reserved strictly for state (selection/focus/progress), with
`--color-texto-invertido` = `#08090a` for text-on-accent contrast (~AAA);
pill structure (`rounded-full`) for tab nav, segmented controls, filter
chips, single-line search — decided 2026-08-11 ("o híbrido"), borrows
Immich's structure without its chroma; non-pill controls stay 6px
(`--radius-controle`); confidence renders as filled segments, not
semaphore color, per D-017 (alta/média have no color of their own; only
baixa/atenção uses amber `#c2833a`, always with a text label, never color
alone); system font stack, 13px body/11px secondary; 8pt spacing grid,
6px corners, 10px thumbnail gap, 2px accent-outline selection (never
overlay/shadow).

Map component (`components/Mapa.tsx`, ties to D-031/D-033): no real
cartography — geometry over a schematic mesh. Solid point (raio 5) = GPS
read from file; dashed ring (7% fill, floor 10px) = inherited place, ring
radius = uncertainty; selection ring offset 8px from the shape; "×N"
count label anchored to the owning point only, omitted if closer to a
neighbor's point than its own (never mis-attributed); panel fills full
height; no per-screen-proximity aggregation of counts (rejected, same
reasoning as D-031 rejecting external-tile aggregation).

---

## 4. Per-destination-folder inventory (audit + catalog reconstruction)

- **source:** `docs/desenho-inventario-por-pasta.md`
- **type:** schema + integration-point contract

Implements D-061/D-063 (locked, gate decision 3). Every destination
folder gets a sibling `inventario.json` + `INVENTARIO.md`, written
**additively** (multiple plans/executions targeting the same folder over
time append to the same pair of files, never overwrite).

Integration point: `fotoorganizer/operations/executor.py::_executar_item`
writes the inventory entry immediately after
`_audit_item(..., "copia_verificada", "ok")` — i.e. only once the copy's
hash has already been verified, never before. New module
`fotoorganizer/operations/inventario.py` keeps `executor.py` focused
(mirrors the existing `planner.py`/`executor.py` split).

`inventario.json` schema (per photo): `arquivo`, `origem`, `tamanho`,
`hash_sha256` (= `item.hash_pos`, no recompute), `copiado_em`,
`data_capturada`, `camera`, `lugar` (pais/regiao/cidade), `evidencias[]`
(campo/origem/valor/nivel/score/justificativa), and a **per-entry**
`versao_logica` (not a single file-level header — entries written in
different execution passes may carry different classification-logic
versions). `INVENTARIO.md` is a full-regeneration human rendering of the
same JSON — never incrementally hand-edited, JSON is the source of truth.

Idempotency: before appending, check whether `arquivo` (final destination
name) already exists in the loaded JSON's `fotos` array — skip if so
(second barrier, cheaper than relying solely on `planner.py`'s existing
"already copied" filter).

**Non-blocking failure contract:** a failed inventory write (permission,
full disk) does NOT undo or invalidate the already-hash-verified copy —
the photo stays `CONCLUIDA`. Failure is recorded via `AuditLog`
(`acao="inventario"`, `resultado="erro: ..."`) and surfaced via a
`stats["inventario_falhou"]` counter — visible, non-silent, non-blocking.
Explicit non-goals: no Alembic migration (filesystem-only), no changes to
`planner.py` or destination/collision resolution, no changes to
`classification/**` (reads existing `Evidence`, generates none).

---

## 5. System architecture (data flow, schema, risks)

- **source:** `docs/ARQUITETURA.md`
- **type:** schema + nfr

Data flow: scan (read-only) → SQLite catalog → metadata extraction →
evidence → suggestions (confidence + `versao_logica`) → human review →
operation plan → dry-run → verified-copy execution → audit log. UI ⇄
Repositories/Services ⇄ Workers; all I/O and heavy CPU off the handler
path. Current (sole) UI: `webapp/` (React/Vite/TS/Tailwind) talking to
`fotoorganizer/server/` (FastAPI, 127.0.0.1-only), reusing the same
repositories/services — handlers never touch filesystem/DB directly.
Heavy jobs (scan, import, suggestions, duplicates) run one-at-a-time in a
`JobManager` thread with SSE progress. `webapp/dist` is served by the
same FastAPI process — one process, zero external network.

Schema highlights (Alembic migration 0001+): `sources` (pasta |
apple_photos | google_takeout, migration 0003), `scan_sessions`
(checkpointed), `media_files` (dual time columns per D-038:
`data_capturada` wall-clock + `data_capturada_utc` absolute, equal means
"timezone unknown"; `tz_estimado`, hashes, GPS), `metadata_entries`
(namespaces `exif`/`gps`/`iptc`/`xmp`/`libraw`/`apple`/`google`, repeated
fields become one row with `;`-joined values, not an indexed key),
`locations`, `trips`/`events`, `people`/`face_embeddings`(encrypted
blob)/`face_occurrences`, `tags`/`media_tags`, `evidence`, `suggestions`,
`duplicate_groups`/`duplicate_members`, `operation_plans`/
`operation_items`, `audit_log`, `application_settings`.

Risks called out: photo integrity (mitigated — `operations/` is the only
module with write permission outside the catalog, always
hash-verified); scale to 100k+ (incremental indexing, batched
transactions, WAL, disk thumb cache, UI virtualization, benchmarking from
M1); disconnected external volumes (source marked unavailable, scan/ops
pause with checkpoint, never partial-fail silently); bad/missing
metadata (every field carries origin+confidence, location is never
invented, corrupted files are logged and skipped); scope creep (vision,
faces, external services frozen behind `Protocol` stubs until M0–M5 are
stable).

**NOTE — stale internal row, not applied (informational only):** this
document's own "Decisões registradas" table, row 1, still reads
"Reiniciar em PySide6, abandonando FastAPI+Streamlit" — contradicted by
this same file's "Fluxo de dados" section two paragraphs above ("A UI
PySide6 foi removida por inteiro, commit `2e0ef1a`") and by the project's
own `CLAUDE.md`, both of which state the webapp (FastAPI + React) is the
sole current UI. Synthesized intel above reflects the current
(webapp-only) state, not the stale table row. This is an internal
self-contradiction within one SPEC file, not a cross-document precedence
conflict, so it is not listed as a BLOCKER/WARNING.
