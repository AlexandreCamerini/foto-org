# Context (DOC intel)

Running notes from the 18 documents classified `DOC` in this ingest,
grouped by topic. Each note carries its source path. These are audits,
plans, reports, and reference material — informational/rationale, lowest
default precedence (`DOC`), never override ADR/SPEC/PRD content.

---

## Roadmap & backlog

- **source:** `docs/ROADMAP.md`

Status: **M0–M7 complete (MVP done)**. Definition of done per milestone:
`pytest` green, no CLAUDE.md invariant violations, app opens, slice is
demonstrable end-to-end. M0 foundation → M1 scanner/catalog → M2 catalog
UI → M3 evidence/grouping/suggestions → M4 duplicates (3 levels, no
automatic action) → M5 operation plan (dry-run mandatory, verified-copy
executor, overwrite-proof) → M6 vision/face stubs behind `Protocol`,
off by default → M7 legacy removal + packaging docs.

**v2+ backlog, reordered 2026-08-01 with measured data (D-024..D-030),
ruled by value-per-cost-for-this-actual-archive, not abstract feature
value.** Three facts drove the reorder: local pixel is rare (~5% of ~99k
known records are locally readable — most of Apple Photos is iCloud-only,
most of Lightroom is on an unmounted volume); GPS is rare and recent
(only 4 of 25 archive-years have any camera GPS); declared intent (25k+
album tags, notes, flags) is abundant and free to read.

Current order: (1) map with uncertainty radius — *in progress, fase 9*;
(2) document `docs/EVENTOS.md` (already implemented, undocumented debt);
(3) events named from existing album/folder data — *implemented
2026-08-01, D-034*, measured zero new names today, 20,515 photos blocked
pending file access; (4) configurable destination templates — *implemented
2026-08-02*; (5) estimated timezone (reformulated: infer from inherited
country window, not GPS); (6) local face detection (**dropped from 1st to
6th** — 90% of known records lack local pixel); (7) local vision analysis
— *demoted 2026-08-02, D-035*, its founding premise (thumbnails covering
2001-2018) no longer exists (thumbnails already purged from catalog); (8)
people UI (blocked by 6); (9) XMP sidecar write (blocked — no writable
destination for ~90k records); (10) signed packaging (US$99/yr recurring
cost, Apple Developer Program); (11) opt-in external provider (per-photo
recurring cost, ~US$100 for a single pass over known records today, no
ceiling on a still-unknown full archive size).

**Item the list doesn't have yet:** reconnecting the two unmounted/cloud
volumes (45,397 Lightroom + 44,661 Apple Photos records) — flagged as the
single highest-leverage candidate, unlocks items 6/7/8/9 at once, form
proposed 2026-08-08 (`docs/prompts/fase-12-alcance-e-tempo.md`), not yet
a formal decision.

## Plan of AI & product (fase 5)

- **source:** `docs/PLANO_IA_E_PRODUTO.md`

Argues most catalog decisions are already deterministic; analyzes
Opus/Sonnet/Haiku cost trade-offs for the classification advisor; proposes
the folder-inventory feature (implemented since, see constraints.md §4);
lists launch prerequisites and a v2 roadmap. Three decisions were pending
owner approval at time of writing — all three are now closed per
`docs/DECISOES.md` D-059/D-060 (model = Sonnet 5), D-061/D-063/D-064
(inventory shipped), see decisions.md.

## Diagnostic: "Gerar sugestões" vs. geo-first goal

- **source:** `docs/diagnostico-gerar-sugestoes-geo-first.md`

Investigative diagnostic: `SuggestionEngine`'s actual cascade prioritizes
folder/time over geo, geocoding is lazy per-session rather than geo-first
by design. Phased remediation plan proposed (Fases A/B'/C/D). Embeds
references to D-051 through D-055, which are the actual decision records
(see decisions.md) — this document is the rationale/investigation behind
them, already resolved: D-054 refuted the "neutra = disguised
screenshot" hypothesis, D-055 confirmed the Item B gate had no real
basis, D-056 approved Fases A/B', D-057/D-058 mark them implemented.

## Audit: post-gate-fase5 (18 measured findings)

- **source:** `docs/auditoria-pos-gate-fase5.md`

18 measured, prioritized UX/data findings across classification,
duplicates, trips, and operations, cross-referenced against
PhotoPrism/Immich as competitive reference. No changes implemented by the
audit itself — corresponds to `docs/DECISOES.md` D-069 (18 candidates,
owner picks). Findings 1, 2, 3, and 5 are already closed via
D-070/D-071/D-072/D-073 (see decisions.md); remaining findings are open
candidates pending owner triage.

## Audit: functionality (fase 2)

- **source:** `docs/AUDITORIA_FUNCIONALIDADES.md`

End-to-end exercise of the catalog engine, API, and screens. Scope:
evidence/suggestion linking, GPS/location inheritance between devices,
metadata namespaces, CLI commands, server API endpoints, all six webapp
screens, temporal grouping defects. Feeds decisions D-007/D-008 (schema
gaps triaged as non-blocking) and D-016 (four short corrections approved
by owner).

## Audit: architecture (fase 1)

- **source:** `docs/AVALIACAO_ARQUITETURA.md`

Architecture audit: layers, `Protocol` substitutability, background job
handling, path security, PySide6-vs-webapp dual-UI question (resolved
since — webapp only, see constraints.md §5 note), DAM data-model gaps
(derivatives/lineage, tag hierarchy, rights, curated collections),
N+1/missing-index findings, scale/reliability/observability, market
comparison (digiKam, Lightroom, DAM). Feeds D-006 through D-009.

## Audit: UX (multi-round, through fase 6)

- **source:** `docs/AVALIACAO_UX.md`

UX/visual-consistency audit of Review, PhotoGrid, design tokens,
Inspector, Operations, Panorama, and the scanner's SINAL-vs-ACERVO role
split. Two rounds concatenated (2026-08-06 + fase 6). Prioritized fix
tables and effort estimates with owner feedback and design-rationale
prototypes (`docs/prototipos/`). References locked decisions D-017,
D-018, D-024, D-028, D-030, D-034 by ID rather than restating them.

## Audit: AI reach vs. deterministic rules

- **source:** `docs/AUDITORIA_IA.md`

Compares deterministic rules vs. local vision models for
grouping/geolocation/date inference. Ends with an explicitly **open**
recommendation ("downloading a local vision model") left for the owner —
not a closed decision, hence DOC not ADR. Relevant to D-004 (AI-embedded
constraints) and the vision-provider backlog item (#7 in ROADMAP.md).

## Metadata coverage measurement

- **source:** `docs/COBERTURA_METADADOS.md`

Measures actual EXIF/metadata field coverage across a sampled real photo
set; informs extraction and geolocation strategy. Feeds the
exiftool-vs-pure-Python decisions (D-019, D-020, D-026, D-027) and the
confidence-model scoring in `docs/CONFIANCA.md`.

## Metadata plan (fase 3)

- **source:** `docs/PLANO_METADADOS.md`

Progress report on pure-Python EXIF/IPTC/XMP reading, exiftool
evaluation, and pending data-model decisions. Contains a proposed
precedence rule (§7) that was later formally locked as D-021 (XMP → IPTC
→ EXIF) — this document is superseded-by-reference, not authoritative;
see decisions.md D-021.

## Signal inventory

- **source:** `docs/INVENTARIO_DE_SINAIS.md`

Measures which metadata signals (EXIF, XMP sidecar/embedded, IPTC,
filename, folder name, Apple Photos, derivatives) the real archive
actually offers, captures, and uses in classification. No cross-refs to
other docs in this set — standalone measurement reference.

## Grouping — event subdivision

- **source:** `docs/EVENTOS.md`

Explains how `eventos_temporais.py` splits a session into multiple
events via relative firing-rate rules, GPS displacement, and
floor/ceiling thresholds (`FATOR`, `JANELA`, `PISO`, `TETO`,
`DESLOCAMENTO_KM`, `MIN_FOTOS_EVENTO`, `DURACAO_MAX_ACONTECIMENTO`).
Per ROADMAP.md, this document itself is "phase-8 debt" — describing
already-implemented, already-measured behavior that had not yet been
written down.

## Estimated place / uncertainty radius rationale

- **source:** `docs/LOCAL_ESTIMADO.md`

Explains and calibrates the uncertainty-radius formula for GPS
coordinates inherited by photos without their own GPS, with measurement
methodology and results. Narrates the rationale behind D-025 and D-031
(the actual decision records) rather than being the decision record
itself; formula and thresholds are formally specified in D-032 (see
decisions.md).

## Packaging guide (Tauri + embedded Python)

- **source:** `docs/EMPACOTAMENTO.md`

Step-by-step macOS `.app` packaging guide via Tauri v2 with embedded
Python (python-build-standalone). Contains a firm embedded decision
(python-build-standalone over PyInstaller) — see decisions.md
"Candidate decision not yet formalized as ADR" section. Build steps,
milestones with technical acceptance criteria, documented contingencies.

## Design references (tokens comparison)

- **source:** `docs/REFERENCIAS_DESIGN.md`

Comparative study of design tokens from Linear, Peakto (cyme.io), and
macOS HIG informing the fase-6 webapp redesign. Feeds directly into
`docs/DIRECAO_DE_ARTE.md`'s token values (see constraints.md §3) and
`docs/DECISOES.md` D-015 (Peakto rejected as visual reference).

## Privacy commitments

- **source:** `docs/PRIVACIDADE.md`

Local-first by default: catalog/thumbs/logs/config live under
`~/Library/Application Support/FotoOrganizer` and
`~/Library/Caches/FotoOrganizer`; nothing leaves the machine without
explicit opt-in (`[privacidade] servicos_externos`, off by default), and
when on, the UI shows what will be sent and allows cancellation. Advisor
LLM sends **metadata only** (folder/file names, dates, counts, already-
resolved place names) — **never the image**; credential from environment
(Keychain/`ANTHROPIC_API_KEY`), never in code. External catalogs (Apple
Photos via osxphotos read-only, requires Full Disk Access; Google Photos
via local Takeout folder) — no network calls to Apple/Google APIs. No
telemetry, no phone-home, no account. Logs never contain image content,
GPS coordinates, or person names. Face recognition: off by default,
100% local when enabled, encrypted embeddings (Keychain key), deleting a
profile cascades (person + embeddings + occurrences), results are always
suggestions requiring confirmation. **Honest limitation documented**:
local encryption only protects against out-of-session access (stolen
backup, different OS account) — not against malware running as the
logged-in user; FileVault + session password are the real complementary
protections, and the doc says so explicitly rather than overclaiming.

## Method of work (cross-project, reusable)

- **source:** `docs/METODO_DE_TRABALHO.md`

Reusable engineering/UX/data/performance/cost principles + Definition of
Done checklist, referenced as governing document by the project's
`CLAUDE.md`. No project-specific content of its own beyond being the
methodology this project's engineering decisions are checked against.

## Instructions summary

- **source:** `docs/RESUMO_INSTRUCOES.md`

Consolidated quick-reference of global work preferences + Foto Organizer
project rules (invariants, stack, module architecture, evidence/
confidence model, method of work). A derived summary of `CLAUDE.md` (both
global and project) plus pointers to `docs/ROADMAP.md`,
`docs/CONFIANCA.md`, `docs/DIRECAO_DE_ARTE.md` — no independent content
beyond what's already captured above.
