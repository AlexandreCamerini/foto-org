# Feature Research

**Domain:** Local-first photo cataloging/DAM (desktop, single-user) — v2.0 slice: sidebar navigation, folder picker + import gauge, confidence-as-navigation-axis + catalog health index, generalized corroboration engine
**Researched:** 2026-08-18
**Confidence:** MEDIUM-HIGH (grounded primarily in the project's own prior engineering — D-074/D-025/D-017, `docs/NAVEGACAO.md`, `docs/referencia-immich/`, `docs/referencia-photoprism/` — plus targeted external verification for the two areas with no internal precedent: Tauri's dialog plugin and record-linkage/sensor-fusion corroboration patterns)

Features 1 (EXIF write) and 2 (GenAI folder→city/event classification) and 7 (active learning) are out of scope for this file per the milestone brief — this covers only 3, 4, 5, 6.

---

## Feature 3 — Sidebar Navigation ("mais navegável")

### Current state (verified in code)

`webapp/src/components/Sidebar.tsx` already has more than the brief implies:
a source list (`Todas as fotos` + per-source rows with counts and an
"unavailable/remounted" badge) and `ArvoreDePastas.tsx`, a folder tree
(146 lines, single expanded path in state, no search). `docs/NAVEGACAO.md`
(Decision 2, already implemented) has already settled the *information
architecture*: **sidebar = "where" (place: source, and in the future
volume/folder), top bar = "what" (scope: search, sort, chips)**. That
document explicitly names the trigger for the sidebar to become a real tree:
*"quando [NAS e HDs externos] entrarem, 'fonte' deixa de ser suficiente como
eixo de lugar — vai ser preciso volume acima de fonte, e a lateral vira
árvore. O momento de rever é quando a lista de fontes passar de uma tela."*
So "navigable sidebar" is not a new IA decision — it is filling in a tree
whose shape was already decided, with the interaction affordances trees need
at scale.

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---|---|---|---|
| Search-as-you-type filter over the folder tree | Universal in DAM sidebars once a tree exists (digiKam: tag/album tree dynamically narrows as you type) — without it a tree with hundreds of folders is a scroll, not navigation | LOW | Client-side filter over the already-fetched tree payload; no new endpoint. Highlight matches, auto-expand ancestors of matches |
| Expand/collapse all, and persist expanded state | Table stakes for any tree once acervo has real depth (2026-08-17 snapshot: only 1 source loaded; production catalog has measured ~422,738 records historically) | LOW | Persist in `sessionStorage` or component state; no backend change |
| Active-node auto-scroll-into-view + visible highlight | Selecting a folder from elsewhere (e.g. clicking a photo's folder badge in Inspector) must land the sidebar on it, not leave it invisible below the fold | LOW-MED | Needs a ref-based scroll-into-view on `pastaAtual` change; already have `pastaAtual`/`onSelecionarPasta` prop pair wired through `App.tsx` |
| Per-node counts | Already present for sources (`fonte.fotos`); folder tree currently shows structure but the codebase should be checked for count parity — DAM users read count-per-node as confirmation the click did something | LOW | Likely already partially there; verify parity between `ArvoreDePastas` and `Sidebar` count rendering |
| Keyboard navigation (arrow up/down between nodes, → expand, ← collapse, Enter select) | Project is teclado-first by explicit constraint (`docs/DIRECAO_DE_ARTE.md`); Review.tsx and StatusBar already model this pattern (REV-01, keyboard-navigable group headers) | MEDIUM | Reuse the `role`/`tabIndex`/`onKeyDown` pattern already established in `Review.tsx` (REV-01) instead of inventing a new one |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---|---|---|---|
| Confidence-tier as a first-class sidebar section (ties to Feature 5) | No competitor DAM (Immich, PhotoPrism, digiKam, Lightroom) has "browse by evidence confidence" as a navigation axis — this is the product's actual differentiator surfaced in the sidebar, not bolted onto a filter dropdown | MEDIUM | Depends on Feature 5's confidence-tier query existing server-side first; sidebar section is UI-only once that exists |
| DSL search bar feeding both sidebar and top filter (round-trip via URL) | PhotoPrism's pattern: one text field is the whole filter language (`camera:iPhone confianca:baixa before:2023-06`), state lives in the URL, sidebar tree and top chips are two views of the same state, not two competing ones | MEDIUM-HIGH | `docs/referencia-photoprism/03-ux-e-organizacao.md` §1.1/1.2 already documents the exact contract to port (not the char-by-char parser — a tokenizing regex/lib is safer per that doc's own recommendation). This is the natural carrier for Feature 5's `confianca:` filter and later a `city:`/`country:` filter once Features 1/6 land |
| Volume-aware tree (source → volume → folder), pre-planned in `docs/NAVEGACAO.md` | Once NAS/external HDs reconnect (candidate noted in `.planning/PROJECT.md` Context, still pending owner decision), a flat source list stops answering "where am I looking" | MEDIUM | **Do not build ahead of the trigger.** `docs/NAVEGACAO.md` names the exact condition ("lista de fontes passar de uma tela") — building this now, with 1-2 sources loaded, is premature |

### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---|---|---|---|
| A second, separate "filter" sidebar/panel duplicating the top bar's scope controls | Feels natural to put "more filters" wherever there's free space | `docs/NAVEGACAO.md` Decision 2 explicitly named and killed this exact defect: two filters for the same grid (fonte in sidebar, recorte at top) competing for the same mental space. Reintroducing it would undo a decision already paid for | Keep the sidebar = place / top = scope split; anything filter-like that isn't "where" belongs at the top, as a chip |
| Faceted dropdown-per-field panel (PhotoPrism's structured filter form) | Looks more discoverable than a text DSL | PhotoPrism's own reference doc (`docs/referencia-photoprism/03-ux-e-organizacao.md` §4.3) flags this as NOT worth porting: "12 dropdowns redundantes com a DSL textual" — duplicated maintenance for the same state, no UX gain given the DSL already exists as the differentiator play | Ship the DSL search bar (see differentiator above); the sidebar tree already covers the structured "pick a place" case |
| Module-per-tab sidebar (Lightroom-style, different capabilities per screen) | Looks powerful, "each screen gets exactly the controls it needs" | `docs/NAVEGACAO.md` Decision 1 already rejected this with sourced evidence — Lightroom users complain about inconsistent capabilities/shortcuts across modules; this app has one user and six tabs, module fragmentation buys inconsistency for nothing | Keep the shared skeleton (already decided, do not reopen without new evidence per the doc's own rule) |

---

## Feature 4 — Folder Picker + Import Progress Gauge

### Current state (verified in code)

`ModalCaminho.tsx` is a **raw text input** for a filesystem path
(`placeholder="/Users/voce/Pictures/Viagens"`) — there is no native "Browse…"
today; the user must know/type the absolute path. This is the actual gap
behind "picker de pasta" in the milestone brief, not a cosmetic ask.

Import/scan progress today (`StatusBar.tsx`) is a **linear determinate bar**
(`data-testid="barra-progresso"`, width = `processados/vistos`), falling back
to an indeterminate pulsing bar when `vistos` is unknown — plus text counters
(`processados / vistos · erros · arq/s`). This is already good: it follows
the project's own documented rule ("nunca fingir um progresso que não temos
como medir") and Immich's own reference doc independently confirms linear
bars + text counts is the correct pattern for background job progress
(`UploadPanel.svelte`: counters `success/errors/duplicates`, no gauge).
So "gauge" in the brief most likely means *more visually prominent*, not a
literal circular/radial gauge — flag this as an open question for the owner
(see Anti-Features) rather than assume a redesign.

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---|---|---|---|
| Native OS folder picker (Finder-style dialog), replacing free-text path entry | Every desktop app expects "Browse…" not "type the absolute path from memory" — this is the single clearest table-stakes gap found in this research | LOW-MED | **Dependency: `tauri-plugin-dialog`**, not yet in `src-tauri/Cargo.toml` (checked — only `tauri`/`tauri-build` present, no plugins). v2 install is `npm run tauri add dialog` + `tauri_plugin_dialog::init()` + `"dialog:default"` capability. JS side calls `open({ directory: true })` and gets a path back — drop-in replacement for `ModalCaminho`'s text `<input>` |
| Determinate progress with real numbers when countable (files scanned/processed, ETA optional) | Already implemented (`StatusBar.tsx`) — verify it stays true after adding the picker, don't regress | LOW | No new work — the linear bar + `processados/vistos/erros/arq/s` line already satisfies this |
| Indeterminate state when total is unknown | Already implemented (pulsing bar fallback) | LOW | No new work |
| Cancel-in-progress remains available during import (not just scan) | `StatusBar.tsx` already wires `cancelar()` for any active job; verify import specifically (not just scan) surfaces it | LOW | Check `job.rodando` covers the `import` job type, not just `scan` |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---|---|---|---|
| Recent/pinned folders in the picker flow | Cuts repeat friction for a single user re-scanning the same 2-3 root folders | LOW | Store last N picked paths client-side (or a small `Source`-adjacent table); optional polish, not core to the ask |
| A literal visual gauge (radial/segmented) for import specifically, distinct from the linear scan bar | If the owner's actual complaint is "I can't tell how big this import is going to be at a glance from across the room" — a big number/percentage readout would do more than a shape change | LOW-MED | **Needs owner clarification before building** — see Anti-Features. If pursued, prefer a large percentage/count readout over a decorative radial gauge (no evidence gauges communicate faster than bars+numbers; Immich/PhotoPrism/digiKam all use bars+counters, no radial gauge found in any reference) |

### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---|---|---|---|
| A decorative circular/radial "gauge" widget replacing the linear bar, built without confirming what's actually missing | "Gauge" reads as a specific widget shape | The current linear bar already satisfies every principle the project has documented for progress (honest, non-blocking, persistent in `StatusBar`, no spinner-modal). A shape change with no functional gap closed is cosmetic churn against `docs/NAVEGACAO.md`'s own warning about "acúmulo não é desenho" (adding widgets to solve unstated problems is exactly the failure mode that document was written to stop) | Before building: ask the owner what's actually missing today — visibility (progress not prominent enough), granularity (no per-source or per-phase breakdown), or ETA (no time estimate). Each has a different, cheap fix that isn't "add a gauge" |
| A modal/blocking progress dialog during import | Feels more "complete" than a status-bar sliver | Directly contradicts the documented decision that progress "é persistente e honesto, nunca um spinner modal" and stays visible across tab switches because work continues in the background | Keep progress in `StatusBar`; if visibility is the real complaint, make the existing bar bigger/more prominent, not modal |

### Feature Dependencies (3 + 4)

```
Feature 4 (native folder picker)
    └──requires──> tauri-plugin-dialog (new Rust + JS dependency, "dialog:default" capability)
    └──replaces──> ModalCaminho.tsx free-text <input> (used by 4 entry points: Sidebar
                    "Adicionar pasta…", 3 empty states, Google Takeout import — CONS-05/D-07)

Feature 3 (sidebar search-as-you-type)
    └──builds on──> ArvoreDePastas.tsx (existing tree, no search today)
    └──enhances──> Feature 5's confidence-tier navigation (shared sidebar section, see below)
```

---

## Feature 5 — Confidence as a Navigation Axis + Catalog Health Index

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---|---|---|---|
| Filter grid by confidence tier (alta/média/baixa) | The confidence model (`docs/CONFIANCA.md`) and its 3-segment badge (D-017) already exist and are shown per-photo; "browse by confidence" is the missing verb on an existing noun, not a new concept | LOW-MED | Confidence today lives on the *suggestion* (destination), computed as elo-mais-fraco across fields (`classification/confidence.py`). Filtering means a new query predicate on the already-computed aggregate confidence, not a new computation |
| A single rollup metric ("% of catalog with high-confidence location") visible somewhere persistent (StatusBar/Panorama) | Every data-quality tool surveyed (Microsoft Purview Unified Catalog, Elementary, OvalEdge, DQOps) leads with exactly this shape: one headline score + drill-down by dimension | LOW-MED | This is an **aggregation across many already-scored suggestions** (count/percentage by tier), not a new scoring formula — see the constraint note below, this is why it's safe |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---|---|---|---|
| Confidence as a DSL token (`confianca:baixa`), not just a dropdown | Ties directly into Feature 3's differentiator (PhotoPrism-style single-field DSL); `docs/referencia-photoprism/03-ux-e-organizacao.md` §4.1-b names this exact combination as the natural next step for this project's evidence model, calling it "já mais rico que o do PhotoPrism" | MEDIUM | Depends on Feature 3's DSL parser existing; can ship as a plain dropdown/chip first, DSL token later |
| Health index broken down by *field* (location vs. date vs. category), not one blended number | A single blended "catalog health %" would itself require deciding how to combine per-field completeness into one number — exactly the kind of arbitrary-weighting decision D-017/CONFIANCA.md forbids at the suggestion level. Reporting per-field percentages side by side (not summed) avoids inventing that weighting while still answering "how healthy is my catalog" | LOW-MED | E.g. "62% high-confidence location · 81% high-confidence date · 34% high-confidence category" as parallel numbers, never averaged into one score |
| Health index trend over time (does it improve after each processing run) | Turns the index from a snapshot into a feedback loop for the corroboration engine (Feature 6) and future EXIF writes (Feature 1) — "did writing GPS to 400 files move the location number" | MEDIUM | Needs a stored snapshot per `versao_logica` run or per day; not needed for v1 of this feature, defer |

### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---|---|---|---|
| A single blended "catalog health score" (0-100%) combining location + date + category + duplicates into one weighted number | Every commercial data-quality dashboard surveyed does exactly this (weighted average of quality pillars, configurable weight) | This is the aggregate-level version of the exact anti-pattern D-017 already rejected at the suggestion level ("nada de somar pontos arbitrários") — a single number forces an arbitrary weight between "location coverage" and "date coverage" with no principled way to set it, and the project's own confidence model explicitly refuses that move | Report per-dimension percentages in parallel (see differentiator above); let the user read three numbers instead of manufacturing a fourth, fake one |
| Using confidence *score* (the 0.0-1.0 float) as a sortable/rankable axis instead of the 3-tier level | Numbers feel more precise than 3 buckets | D-017 already decided this exact question for the badge and the reasoning transfers directly: "percentual numérico... sugere precisão que o modelo... não tem: o score é elo mais fraco, não medida contínua." A rankable float implies the catalog can be sorted "best to worst" with sub-percent precision it doesn't have | Filter/browse/navigate by the 3-tier level (alta/média/baixa), same as the badge; the underlying float stays an internal reference number, never surfaced as a sort key |

### Constraint note (load-bearing for the roadmap)

**This feature does NOT touch the weakest-link rule and should not be framed as if it might.** D-017/CONFIANCA.md forbid summing/averaging scores *within a single suggestion* (combining different evidence fields into one number). The health index is a *rollup across many already-finalized suggestions* (counting how many landed in each tier) — a `GROUP BY` and `COUNT`, not a new scoring formula. The only way this feature could violate the constraint is the blended single-score anti-feature above; the per-dimension-percentage design does not.

### Feature Dependencies (5)

```
Feature 5 (confidence filter + health index)
    └──requires──> existing ConfidenceLevel enum + elo_mais_fraco() (classification/confidence.py) — already built
    └──requires──> a query surface (new API endpoint) that counts MediaFile/suggestion rows by tier, per field
    └──enhances──> Feature 3 (sidebar section + DSL token)
    └──enables──> Feature 7 (active learning, explicitly deferred until 5+6 exist per PROJECT.md)
    └──feeds from──> Feature 6 (corroboration outcomes change which tier a field lands in)
```

---

## Feature 6 — Generalized Corroboration Engine (D-074 pattern beyond GPS)

### What D-074 actually does (verified by reading `_confrontar_com_outro_lado` in `fotoorganizer/grouping/correlacao.py`)

This is the load-bearing detail for the whole feature, so it is stated precisely rather than paraphrased:

1. For a field being inherited (city, region — **country is explicitly excluded**), if the *opposite-side* donor's Δt also fits that field's window (`_JANELA_DO_CAMPO`, per D-025: city 10 min, region 2h, country 12h), the field is **confronted**, not just accepted from the nearest donor.
2. Confrontation is a **binary geometric gate**: `distancia(doador_perto, doador_longe) <= raio_incerteza(Δt_perto) + raio_incerteza(Δt_longe)`. No new constant — it reuses the already-calibrated `raio_incerteza` function from D-032, summed across both sides (analogous to a **combined-uncertainty / tolerance-interval overlap test**).
3. **On agreement**: the field is kept, with the *exact same* confidence factor it already had (Δt of the nearest side, no bonus) — only a marker (`Heranca.concordancia`) and a justification sentence are added ("confirmada por outra foto do lado oposto no tempo"). Confidence numerically **does not move**.
4. **On disagreement**: the field is dropped entirely — not downgraded, not kept from the nearest donor either. Nobody gets to claim it.
5. Guard clause: if any of the three timestamps involved (heir, chosen donor, opposite donor) is filesystem-mtime-derived (`hora_incerta`), the field is **not tested at all** — treated as if there were only one side, because a distance test built on an untrustworthy Δt proves nothing.

This is **not a Bayesian/weighted combiner**. It is a **consensus gate**: independent evidence either falls within each other's stated uncertainty or it doesn't; agreement earns a footnote, disagreement earns silence. That is exactly why it is compatible with the weakest-link model — it never produces a number that isn't already in the reference table.

### External validation of the pattern class

Web research confirms this maps to a known family, and also confirms which adjacent family to avoid:

- **Record linkage (Fellegi-Sunter, 1969)** is the closest-sounding but wrong model to imitate: it assigns a weight per matching field and **sums** them into a total match score, explicitly assuming conditional independence across fields — precisely the "soma arbitrária" the project's confidence model was designed to refuse. Do not use this as the generalization template, even though "compare two independent sources" sounds the same.
- **Sensor/track-to-track fusion (Mahalanobis gating)** is the closer analog: two independent estimates (each with its own uncertainty) are tested via a distance-vs-combined-uncertainty threshold to decide *consistent or not*, before any fusion happens — accept/reject, not blend. `raio_incerteza(Δt1) + raio_incerteza(Δt2)` is a simplified (additive, not covariance-based) version of exactly this gating idea. This is the right mental model to hand to whoever implements Feature 6.

### The generalization is NOT uniform across the three target field types — this is the key finding

The brief asks to generalize D-074 to "date/time inheritance, city/country inheritance from folder/album context." The three don't generalize the same way, because D-074's gate is fundamentally **metric** (a distance in meters, compared to a combined radius in meters). Two of the three targets are metric; one is not:

| Field type | Has a natural "distance" + "combined tolerance"? | Generalization path |
|---|---|---|
| **Date/time** (e.g., EXIF DateTimeOriginal vs. filename-embedded date vs. folder-context date) | **Yes — directly analogous.** "Distance" = `\|t1 - t2\|`, "combined tolerance" = a per-source uncertainty window (already exists in spirit: EXIF is exact, `nome_arquivo` dates are WhatsApp-receipt-time not capture-time per `confidence.py`'s own comment, `fs`/mtime is explicitly untrustworthy). This is the field D-074's mechanism ports to almost unchanged: define a per-source time-uncertainty analogous to `raio_incerteza`, gate on interval overlap, mark-don't-boost on agreement, drop-don't-downgrade on disagreement. | LOW-MEDIUM complexity — mechanically closest to D-074 |
| **City** (string label from folder name vs. album name vs. reverse-geocoded GPS) | **No natural metric distance between two strings that means "close enough."** "São Paulo" vs. "Sao Paulo" is the same city with a typo; "São Paulo" vs. "Santo André" is a 25 km neighbor, arguably "close" in a way GPS's radius test would catch but string comparison won't; "São Paulo" vs. "Campinas" is unambiguously different. A naive Levenshtein/string-similarity threshold would be exactly the kind of **invented, uncalibrated constant** D-074's own writeup was careful to avoid ("nenhum fator novo foi adicionado"). | The honest generalization is **exact-match-as-gate**, not distance-as-gate: two independent sources for city either name the *same* place (after normalization: casefold, NFD accent-strip — already a solved problem in this codebase per D-066/D-067) or they don't. Agreement is boolean, not graded. This preserves the "no new invented constant" discipline but is a materially different test than GPS's, and should be documented as such, not silently presented as "the same algorithm" |
| **Country** | **D-074 already answered this — explicitly excluded, on the record.** The writeup states the geometric test's 50km cap makes it fail for donors 300km apart who are obviously the same country. This is not a gap Feature 6 needs to solve from scratch; the same reasoning (country needs geocoding-aware comparison, not distance) applies to city+country jointly whenever the source is GPS-derived, and to plain string-equality whenever the source is folder/album text | Country corroboration from folder/album text is the **string-equality case** (same as city, one level up); country corroboration from GPS-derived sources should stay excluded, following D-074's own precedent, until real geocoding is deliberately added to `grouping/correlacao.py` (currently deliberately absent) |

No other project document (`docs/AGRUPAMENTO.md`, `docs/PLANO_IA_E_PRODUTO.md`) addresses extending correlation beyond GPS — this table-stakes/differentiator split for city/country vs. date is new analysis for this milestone, not a restatement of an existing decision.

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---|---|---|---|
| Date/time corroboration (two independent date sources confronted before either is trusted over the other) | Directly extends the existing pattern with the least new design risk; the project already has 3+ independent date evidence tiers ranked (`exif` 0.95, `nome_arquivo` 0.65, `fs` 0.40) that today are picked by rank alone, never cross-checked | MEDIUM | Port `_confrontar_com_outro_lado`'s shape: per-source time-tolerance, interval-overlap gate, mark-not-boost on agreement, drop-not-downgrade on disagreement |
| City/country corroboration via normalized exact-match, not distance | Table stakes once the pattern is named "generalized corroboration" — the folder-name/album-name path (already the majority of the catalog per PROJECT.md: "Pixel local é raro... Intenção declarada... é abundante") is exactly where two independent human-written labels (folder vs. album) most often exist for the same photo | MEDIUM | Reuse existing NFD/casefold normalization (D-066/D-067) as the equality function; do not invent a fuzzy-distance threshold |
| Justification text updated to say *why* a field survived or was dropped, per the D-074 precedent | Every existing suggestion already answers "por quê?" (CONFIANCA.md's core promise) — a corroborated/rejected field must keep that promise, not silently change confidence with no explanation | LOW | Same UI surface as D-074's "confirmada por outra foto do lado oposto no tempo" sentence, generalized per field type |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---|---|---|---|
| A single shared `confrontar_evidencias()`-style abstraction parameterized by (distance_fn, tolerance_fn, equality-vs-metric mode) instead of 3 copy-pasted GPS/date/city functions | Keeps the "no arbitrary constant" discipline enforceable in one place instead of 3, and makes the metric-vs-categorical split (above) an explicit parameter instead of an implicit difference between near-identical functions | MEDIUM-HIGH | Real engineering judgment call for whoever implements this — worth a design pass before coding, given GPS/date are metric and city/country are categorical; forcing them through one function signature could be premature abstraction. Flag as a phase-planning decision, not a given |
| Corroboration outcome feeds Feature 5's health index (e.g., "34% of location fields are corroborated by two independent sources, not just one") | Makes corroboration visible as a *dimension* of catalog health, not just an invisible internal upgrade | LOW once both exist | Straightforward once the `concordancia` marker exists per field type — it's another `COUNT`, same rollup discipline as Feature 5 |

### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---|---|---|---|
| Boosting confidence score when 2 sources agree (e.g., "two agreeing médias become alta") | Intuitively "more evidence = more confident" | This is precisely what D-074 tested and rejected for GPS on the record ("MESMO fator de sempre... sem bônus de score") and precisely what CONFIANCA.md forbids project-wide ("nada de somar pontos arbitrários"). Generalizing to date/city must inherit this refusal, not quietly reintroduce it because a different field type feels like it "deserves" a bump | Agreement adds a marker + justification sentence, never moves the score — exactly the D-074 precedent |
| Fuzzy string-distance threshold for city/country agreement (e.g., Levenshtein <= 2, or a geocoding-API similarity score) | Feels like the "obvious" extension of GPS's radius-overlap test to text | This is an invented, uncalibrated constant with no measurement behind it — the same category of move D-074's writeup explicitly avoided ("nenhum fator novo foi adicionado"). It would also silently conflate "same city, misspelled" with "different but nearby city," which are not the same claim | Exact match after existing normalization (NFD/casefold, D-066/D-067); if geocoding-aware distance is ever wanted, that requires the same kind of measured calibration D-032 did for GPS radii — a future decision, not a shortcut taken now |
| A generic "corroboration confidence multiplier" config value, applied to any evidence type | Looks like a clean, reusable knob | Any numeric multiplier not backed by a measurement (like D-032's calibration against 40,678 real GPS pairs) is exactly what D-024/D-017/D-074 have consistently refused across 3 separate decisions — this would be the first time the project invents an unmeasured confidence constant | If/when a new field type's corroboration needs calibration, run the same measurement discipline D-074 used (`scripts/calibrar_raio_incerteza.py --concordancia` is the existing template for that kind of study) before picking any constant |

### Feature Dependencies (6)

```
Feature 6 (generalized corroboration)
    └──extends──> fotoorganizer/grouping/correlacao.py::_confrontar_com_outro_lado (D-074, GPS-only today)
    └──reuses──> D-025's JANELAS_POR_CAMPO (per-field time windows) for the date-corroboration case
    └──reuses──> D-066/D-067 NFD/casefold normalization for the city/country exact-match case
    └──requires──> a phase-planning decision on shared-abstraction-vs-parallel-functions (see Differentiators)
    └──feeds──> Feature 5 (health index gains a "corroborated" dimension)
    └──blocks──> Feature 7 (active learning — explicitly deferred until 5 AND 6 exist, per PROJECT.md)
    └──does NOT extend to──> country-from-GPS (D-074 already excluded this on measured grounds; out of scope
                              until real geocoding is added to correlacao.py, which is deliberately absent today)
```

---

## Combined Feature Dependency Graph (3, 4, 5, 6)

```
Feature 4 (folder picker)
    └──independent──> ships alone, no dependency on 3/5/6

Feature 3 (sidebar)
    ├──independent baseline──> search-as-you-type + keyboard nav ship alone
    └──enhances with──> Feature 5's confidence-tier section + DSL token (optional follow-up, not a blocker)

Feature 5 (confidence axis + health index)
    ├──independent baseline──> filter + per-dimension rollup ship alone
    └──enhanced by──> Feature 6 (adds a "corroborated" dimension to the health index)

Feature 6 (generalized corroboration)
    ├──independent──> date-corroboration and city/country-corroboration can ship as 2 separate slices
    └──feeds──> Feature 5 (optional enhancement, not required for 5's v1)

Feature 7 (deferred, not in this file's scope)
    └──requires──> Feature 5 AND Feature 6 both shipped
```

**Ordering implication for the roadmap:** 3 and 4 have no dependency on each
other or on 5/6 — either can go first purely on owner priority (which
already ranks 3 before 4). 5 and 6 are best sequenced with 5's *baseline*
(filter + per-dimension rollup, no corroboration data yet) shippable
independently, then 6's date-corroboration slice (lower complexity, direct
D-074 port), then 6's city/country slice (new design: exact-match gate, not
distance gate), then optionally wiring 6's output back into 5's health index
as a follow-up slice — matching the milestone's own stated order (5 before
6) and the explicit reason Feature 7 waits for both.

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---|---|---|---|
| 4 — Native folder picker | MEDIUM (removes a real daily-use friction point) | LOW | P1 |
| 4 — Progress "gauge" (as currently understood: bar is likely already sufficient) | LOW until owner clarifies the actual gap | LOW-MED (unknown until scoped) | P3 until clarified |
| 3 — Search-as-you-type + keyboard nav over existing tree | MEDIUM-HIGH (acervo will grow past "one screen" of sources per NAVEGACAO.md's own trigger) | LOW-MED | P1 |
| 3 — DSL search bar | HIGH long-term (differentiator, carries Feature 5's filter too) | MEDIUM-HIGH | P2 |
| 5 — Filter by confidence tier | HIGH (core value prop made navigable) | LOW-MED | P1 |
| 5 — Per-dimension health rollup | HIGH (answers "is this catalog usable" at a glance) | LOW-MED | P1 |
| 5 — Blended single health score | — | — | **Anti-feature, do not build** |
| 6 — Date/time corroboration | HIGH (direct D-074 port, lowest-risk extension) | MEDIUM | P1 |
| 6 — City/country corroboration (exact-match) | MEDIUM-HIGH (majority of catalog per PROJECT.md's own composition data) | MEDIUM | P2 |
| 6 — Shared abstraction across all 3 field types | Engineering-quality value, not user-visible | MEDIUM-HIGH | P3 (defer to implementation-time judgment call) |

**Priority key:** P1 must-have for this v2.0 slice; P2 should-have, sequence after P1s; P3 nice-to-have or blocked on clarification.

---

## Competitor Feature Analysis

| Feature | Immich | PhotoPrism | digiKam | Our Approach |
|---|---|---|---|---|
| Sidebar tree | Not a tree — flat album list + explore views | Left sidebar view-switcher (Albums/Tags/Dates/Map/People), no unified tree | Left sidebar with 9 switchable "Views" including Albums (tree) and Dates (calendar tree), search-as-you-type over tag tree | Single unified place-tree (source→volume→folder), per `docs/NAVEGACAO.md`'s already-made decision, with search-as-you-type added this milestone |
| Folder/import picker | Server-side upload via web/mobile client, not a folder picker | Server config path, not an interactive picker | Native OS dialogs (desktop app) | Native OS dialog via `tauri-plugin-dialog` — closest to digiKam's model since we're also a native desktop shell |
| Progress display | Floating panel, counters (`success/errors/duplicates`), no gauge | Job queue view, no gauge found | Progress bar + log pane, no gauge found | Keep existing linear bar + counters; do not add a decorative gauge without a confirmed functional gap |
| Confidence/quality as navigation axis | Not present — no evidence-confidence concept | Has a numeric "quality" score (photo technical quality, not source-confidence) usable in DSL (`quality:3`) but it's about image quality, not evidence provenance | Not present | Genuinely novel: filter/browse by *evidence* confidence tier, not image quality — no direct competitor precedent found |
| Aggregate quality/health metric | Not present | Not present as a dashboard | Not present as a dashboard | Per-dimension percentage rollup (location/date/category), never blended — matches enterprise data-catalog pattern (Purview, Elementary) adapted to avoid their single-blended-score anti-pattern |
| Corroboration between independent evidence sources | Not present | Not present | Not present | D-074 already shipped for GPS; this milestone's Feature 6 is the generalization — no competitor precedent, closest analog is sensor-fusion/track-fusion gating (different domain entirely) |

## Sources

- Internal (primary, highest confidence — read directly this session):
  - `.planning/PROJECT.md` — milestone scope, catalog composition, constraints
  - `docs/DECISOES.md` D-074 (full text) — GPS corroboration decision and measurement
  - `docs/DECISOES.md` D-025 — per-field temporal inheritance windows
  - `docs/DECISOES.md` D-017 — confidence-as-quantity, no arbitrary summing
  - `docs/DECISOES.md` D-075 — EXIF write scope (context for Feature 6's future field, not itself researched here)
  - `docs/CONFIANCA.md` — full confidence model, weakest-link rule, score reference table
  - `fotoorganizer/grouping/correlacao.py` — `_confrontar_com_outro_lado`, `herdar_gps`, `Heranca` (read directly, not summarized secondhand)
  - `fotoorganizer/classification/confidence.py` — `SCORES_REFERENCIA`, `elo_mais_fraco`
  - `docs/NAVEGACAO.md` — sidebar=place/top=scope decision, tree-ification trigger, sourced competitor critique of Lightroom/Peakto/Apple Photos
  - `docs/referencia-immich/05-ui-web.md` — progress/gauge patterns (`UploadPanel`, `queue-manager`), confirms no gauge widget in a comparable product
  - `docs/referencia-photoprism/03-ux-e-organizacao.md` — DSL search pattern, explicit recommendation to pair it with this project's confidence model, explicit anti-recommendation against dropdown-per-field panels
  - `webapp/src/components/Sidebar.tsx`, `ArvoreDePastas.tsx`, `StatusBar.tsx`, `ModalCaminho.tsx` — current implementation state
  - `src-tauri/Cargo.toml` — confirms no dialog plugin installed yet
- External (MEDIUM confidence, WebSearch, cross-checked against project's own prior sourcing habits):
  - [Dialog | Tauri (v2 docs)](https://v2.tauri.app/plugin/dialog/) — folder-picker plugin install/permissions
  - [tauri-plugins-dialog — Stuffbucket Skills](https://stuffbucket.github.io/skills/catalog/tauri-plugins-dialog/)
  - [Probabilistic record linkage — PMC/NIH](https://pmc.ncbi.nlm.nih.gov/articles/PMC5005943/) — Fellegi-Sunter summed-weight model, used here as the explicit anti-pattern to avoid
  - [Analysis of a Probabilistic Record Linkage Technique — PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC1479910/)
  - Sensor/track-to-track fusion, Mahalanobis gating — general aerospace/tracking literature confirming "distance vs. combined uncertainty, accept/reject" as a named, established pattern class distinct from weighted-score fusion (used as the correct mental model for generalizing D-074, no single canonical citation — treat as MEDIUM confidence, domain-analogy not domain-identical)
  - [Data Health Dashboard — Elementary docs](https://docs.elementary-data.com/cloud/features/collaboration-and-communication/data-health) and [Data quality health report — Microsoft Purview](https://learn.microsoft.com/en-us/purview/unified-catalog-reports-data-quality-health) — confirm the industry-standard shape (single weighted score) that this project should explicitly deviate from, per the constraint note in Feature 5
  - Interface Layout / Search View — Digikam Manual 9.2.0 (docs.digikam.org) — sidebar tree, search-as-you-type over tag tree, calendar/date tree navigation

---
*Feature research for: local-first photo cataloging DAM, v2.0 sidebar/import/confidence/corroboration slice*
*Researched: 2026-08-18*
