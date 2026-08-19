# Architecture Research — v2.0 Integration

**Domain:** Integration of 6 new features into an existing, shipped layered
desktop app (FastAPI/SQLite backend + React/TS webapp, Tauri shell)
**Researched:** 2026-08-18
**Confidence:** HIGH (every claim below is grounded in a direct read of the
named file/line; sources listed per section)

This is not greenfield domain research — it maps 6 target features onto the
**real, already-existing** module boundaries read directly from the
codebase (`fotoorganizer/operations/executor.py`, `planner.py`,
`classification/advisor.py`, `classification/confidence.py`,
`grouping/correlacao.py`, `models/inference.py`, `repositories/media.py`,
`server/jobs.py`, and the relevant `webapp/src/components/*.tsx`), not
invented ones. Where the milestone brief's phrasing turned out to be
imprecise against the actual code, that's called out explicitly.

## System Overview (existing, unchanged by this milestone)

```
webapp/src/ (React/TS) ──HTTP/SSE, 127.0.0.1──> fotoorganizer/server/
  Sidebar.tsx, ArvoreDePastas.tsx,                app.py (handlers, 1422 lines,
  ModalCaminho.tsx, StatusBar.tsx,                no router-splitting yet)
  Confianca.tsx, Review.tsx, Inspector.tsx        jobs.py (JobManager, 1 job at a time)
                                                          │
                                                          ▼
                              domain services (fotoorganizer/*)
    scanner/ · sources/ · metadata/ (Protocol: MetadataExtractor,
    read-only) · classification/ (engine.py + advisor.py + confidence.py)
    · grouping/ (correlacao.py, temporal.py, eventos.py) · geolocation/
    · duplicates/ · operations/ (planner.py, executor.py — ONLY module
    that writes outside the catalog) · faces/, vision/ (stubs)
                                                          │
                              ┌───────────────────────────┴──────────┐
                              ▼                                      ▼
                       repositories/ (one class per aggregate)  security/
                              │                            (paths, subprocess,
                              ▼                             hashing, crypto)
                       models/ + database/ (SQLAlchemy 2, Alembic,
                       SQLite WAL, single catalog.db)
```

Hard invariant this milestone must not blur: **cataloging is read-only,
`operations/` is the only module allowed to write outside the catalog**
(`.planning/codebase/ARCHITECTURE.md` — "Strict read-only/write-only
separation"). Feature 1 (EXIF write) is a deliberate, narrow exception
carved by D-075 — it needs its **own** write surface, not a folding into
`operations/`. See (a) below.

---

## (a) Feature 1 — EXIF location write

### What's actually there today

- `fotoorganizer/metadata/base.py`: `MetadataExtractor` is a `Protocol`
  with exactly one method, `extract(path) -> MediaMetadata` — **read-only
  by construction**, no write method exists anywhere in `metadata/`.
- `fotoorganizer/metadata/exiftool.py`: `ExifToolExtractor` keeps one live
  `exiftool -stay_open` subprocess (`_garantir()`), talked to via a
  request/response protocol (`_conversar`) guarded by `self._lock`. Its own
  docstring states the reason for the lock: *"não é thread-safe por
  desenho; um lock serializa o acesso porque o protocolo do `-stay_open` é
  uma conversa única por stdin/stdout."* The scanner already holds this
  process busy across a `ThreadPoolExecutor` during extraction.
- `fotoorganizer/operations/executor.py` is the only writer today, and its
  entire safety model is **copy-to-a-new-path**: `hash_pre` on the source,
  exclusive-create (`open('xb')`) to a destination that must not exist,
  `hash_pos` on the destination, mismatch → delete the copy. Every one of
  these steps assumes `item.origem != item.destino` (`OperationItem` has
  separate `origem`/`destino` columns). None of it maps to "mutate this
  exact file in place."

### Decision: new module, not an extension of `metadata/` or `operations/`

**Why not `metadata/`:** the `MetadataExtractor` Protocol's entire contract
is "never raises, always returns a best-effort read" — bolting a write
method onto it either breaks that contract (writes CAN legitimately fail
and must be reported precisely, not swallowed) or forces a second,
incompatible Protocol into the same file. Cleaner: a **new, narrower
Protocol** (e.g. `MetadataWriter` with a single `escrever_localizacao`
method) in a new module.

**Why not the same live exiftool process as the reader:** the existing
concurrency contract (`_lock` serializing `-stay_open` conversations,
shared across scanner threads) means a writer sharing that instance would
have to serialize against in-flight scans too — a correctness risk for no
benefit. exiftool's `-stay_open` protocol accepts arbitrary argument sets
per `-execute` block (write args instead of `-j` read args are just a
different argument list over the same wire protocol), so technically naming
one class is possible — but the existing class's own documented
concurrency discipline argues against reusing the live instance. **Use a
separate, short-lived `exiftool` invocation per write** (spawn, write,
exit) via `security/subprocess_seguro.py`'s existing safe-subprocess
pattern (list args, no `shell=True` — invariant 5), not the persistent
`-stay_open` process.

**Why not `operations/`:** `operations/executor.py`'s entire verification
model is asymmetric to what feature 1 needs. A copy is *origin → new file,
verify both, never touch origin*. An EXIF write is *origin file, verify
before, mutate in place, verify after* — there is no second path, no
`OperationItem.destino`, no collision-avoidance-by-suffix. Folding this
into `OperationExecutor`/`OperationItem` would force nullable
"destino-equals-origem-when-mutating" special cases throughout a class
whose entire design assumes copy semantics. It would also blur the literal
meaning of invariant 2 ("operação física só existe como plano até
aprovação; execução é copiar, nunca mover") — EXIF write is neither copy
nor move, it's a third category the model doesn't have room for today.

**Recommendation:** a new package, `fotoorganizer/exif_write/` (or
`fotoorganizer/metadata/escrita.py` if the team prefers a flatter layout —
either is consistent with "new package if genuinely new bounded concern"
from `.planning/codebase/STRUCTURE.md`), containing:

- `MetadataWriter` Protocol + `ExifToolWriter` implementation (spawns
  exiftool per file, one `-execute` block, no persistent process).
- Its own plan/dry-run/audit model, **structurally parallel to
  `operations/` but not sharing its classes**:
  - `ExifWritePlan`/`ExifWriteItem` (new ORM models, new migration) — one
    row per (media, campo) pending write, mirroring `OperationPlan`/
    `OperationItem`'s shape (plan → items → status) so the UI/audit
    patterns feel familiar, but with `campo`/`valor_novo` instead of
    `origem`/`destino`.
  - Dry-run step: reads current EXIF via the existing `MetadataExtractor`
    read path, confirms field is empty (D-075's scope gate — refuse to
    write over anything non-empty), computes `hash_pre` of the whole file.
  - Execute step: invoke `ExifToolWriter`, then `hash_pos` — but note the
    hash **will legitimately differ** after a metadata write (the file
    bytes changed on purpose), so the verification target is different
    from `operations/`: verify the write took effect (re-read the field)
    and that no *other* bytes/fields were touched (exiftool writes are
    scoped to the tags given — trust but log the full before/after EXIF
    diff in `AuditLog.detalhe`, not just a hash).
  - Reuse `AuditLog` (existing model, already generic: `plan_id`, `acao`,
    `detalhe` JSON, `resultado`) by adding a new `acao` vocabulary
    (`"exif_write"`) rather than a new audit table — this is the one place
    sharing infrastructure with `operations/` is genuinely low-risk, since
    `AuditLog` has no copy-specific assumptions.
- A `server/app.py` endpoint set mirroring the `operations/` ones
  (`POST /api/exif/dry-run`, `POST /api/exif/executar`) routed through
  `JobManager` (long-running, needs progress) exactly like
  `iniciar_execucao` does for copy plans.

**Reuse, explicitly:** `security/paths.py`'s path-safety helpers apply
unchanged (the file being written already lives inside a known source
root — no new path-traversal surface). `security/hashing.py::sha256_full`
applies unchanged for pre/post integrity checks. The double-gate pattern
(`DryRunObrigatorio`-style exception + caller-level `confirmar` flag) from
`executor.py` should be copied as a pattern, not imported as a shared base
class — the two executors diverge too much structurally to share
inheritance without the copy-specific assumptions leaking through.

---

## (b) Feature 2 — GenAI folder → city/event classifier

### What's actually there today

- `fotoorganizer/classification/advisor.py` defines the exact pattern to
  reuse: a `ClassificationAdvisor` Protocol (`local: bool` property +
  `classificar(cluster) -> AdvisorResult | None`), a `NullAdvisor` default
  (opt-out is the default), and `ClaudeAdvisor` (Sonnet 5,
  `thinking={"type":"disabled"}`, structured JSON output, `except
  Exception` never crashes the pipeline, gated behind
  `settings.privacidade.servicos_externos`).
- **Discriminating fact:** `AdvisorResult` today is
  `(categoria: str|None, evento: str|None, justificativa: str)` — there is
  **no city field**. `ClusterInfo` (the advisor's input) carries
  `pastas`, `exemplos_arquivos`, `inicio`/`fim`, `n_fotos`, `lugares`
  (already-geocoded place names) — this is a reasonable payload for "what
  city/event is this folder" too, since it's already folder-name +
  file-sample + period + known-places, exactly what a city/event guess
  needs.
- `SuggestionEngine._categoria` (`classification/engine.py:974`) is a
  4-step cascade: **(1) pasta → known category word, (2) session type
  (GPS/geocoding-derived, deterministic), (2b) human keyword (XMP/IPTC),
  (3) advisor's `categoria` when session left it unset.** The advisor is
  consulted only for `sessao.tipo == "neutra"` sessions
  (`_montar_sessoes:524`) — i.e. only when the deterministic cascade
  couldn't decide. This is the correct integration point for "city/event
  from folder," but it currently answers a **different question**
  (Viagens/Eventos/Família category) than feature 2 asks (city name /
  event name as a value, not a category label).

### Decision: sibling result type, same advisor instance and gate, new cascade slot

Reuse `ClusterInfo` as-is for the payload — no new dataclass needed there.
Add a second method to the `ClassificationAdvisor` Protocol (or a second
Protocol, `LocationAdvisor`, if keeping the two concerns separate is
preferred) returning a new `LocationAdvisorResult` (`cidade: str|None`,
`pais: str|None`, `justificativa: str`) — **do not overload the existing
`AdvisorResult`/`classificar()`**, because the two questions have
different confidence semantics (`docs/CONFIANCA.md`'s "llm" score 0.55
already exists for category advisor output; a location-from-folder guess
is evidentially a different kind of claim — lower-anchored, closer to
`"pasta"` (0.60) than to `"gps"` (0.95) — and mixing them in one JSON
schema risks the model answering one when only the other was needed).
`ClaudeAdvisor` becomes a single class with two structured-output methods
sharing the same `client`/`model`/opt-in gate, not two separate classes —
the cost-per-session accounting the milestone calls out is naturally one
counter either way, since both calls share the same billing surface.

**Plug-in point:** a new evidence source inside `SuggestionEngine`'s
`_evidencias_geo`/`_categoria` cascade area, specifically for media whose
folder has no `pasta`-word match (step 1 failed) and no GPS-derived
country/city (step in `_evidencias_geo`, `engine.py:872`, failed too) —
i.e. it slots in as a **new rung below "pasta" and above/alongside the
existing advisor category call**, gated the same way (`sessao.tipo ==
"neutra"` or equivalent "nothing else answered" condition), with its own
`SCORES_REFERENCIA` entry in `classification/confidence.py` (new key,
e.g. `"llm_local"` or `"llm_pasta"`, distinct from `"llm"` at 0.55, to
keep the two claims separately auditable per docs/CONFIANCA.md's
no-summing rule).

**Explicitly not reusing `_categoria`'s call site verbatim:** that method
answers "which of 3 fixed categories," feature 2 answers "which city/event
string" — different shape of question, same infrastructure. The
integration is "same advisor plumbing, new cascade rung," not "extend the
existing method."

---

## (c) Feature 5 — Confidence as navigation axis + health index

### What's actually there today

- `MediaRepository.panorama()` (`repositories/media.py:510`) is the
  existing precedent: pure aggregation (`GROUP BY`/`COUNT`) over
  `MediaFile`/`Suggestion`, no new schema, computed live per request —
  already ships facets (`por_ano`, `por_camera`, `lacunas`,
  `cruzamento_ano_fonte`).
- `LACUNAS`/`_condicao_lacuna` (`repositories/media.py:96-152`) already
  include `confianca_baixa`/`confianca_media` as **row-level filter
  predicates** (`MediaFile.id.in_(select(Suggestion.media_id).where(
  Suggestion.nivel == nivel))`) — confidence is **already a filterable
  axis today**, just not surfaced as a first-class UI dimension the way
  year/camera/extension are. Feature 5 is closer to "promote an existing
  filter to a first-class view + add an aggregate score" than "build
  confidence filtering from scratch."
- `Suggestion.nivel` (the weakest-link-aggregated confidence, already
  computed and persisted at generation time by `SuggestionEngine`, not
  recomputed live) has **no index** — only `ix_suggestions_status` and
  `ix_suggestions_media_id` exist on that table.

### Decision: pure aggregation for the health index; one optional index, no new columns

**Health index** (a single acervo-wide score/summary): same shape as
`panorama()` — `GROUP BY Suggestion.nivel` / `Evidence.nivel`, counts and
percentages, computed on request, no persisted per-media score needed.
`Suggestion.nivel` is already the materialized aggregate confidence per
suggestion (computed once at `gerar()` time, not per read) — there is
**no live weakest-link recomputation cost** to worry about here, only a
`GROUP BY` over an already-small table (`suggestions`, not the ~423k-row
`media_files`).

**Confidence-as-navigation-axis** (browsing/filtering the grid by
confidence, not just seeing a summary number): this reuses
`_condicao_lacuna`'s existing subquery shape almost verbatim, extended
from two discrete lacuna flags to a full three-way (or acervo-wide)
filter axis alongside year/camera/extension in the existing
`MediaFilters` dataclass. The one real technical gap: `Suggestion.nivel`
has no index, so a `WHERE Suggestion.nivel = X` subquery run at
navigation-axis frequency (every filter change, not just a one-time
panorama load) is a scan of the `suggestions` table on every request.
`.planning/codebase/CONCERNS.md` didn't flag this — but its audit didn't
specifically exercise this path at the ~423k-row scale either, so absence
of a flag there is not confirmation it's fine, just that nobody measured
it. **Recommendation:** add an index on `Suggestion.nivel` (and consider a
composite `(nivel, media_id)` if the grid filter always joins through
media) as part of this feature's migration — small, additive, same
justification pattern the codebase already used for `pasta`
(`ix_media_files_pasta`, added in LANC-02 precisely because folder
navigation became a real per-click consumer) and for
`trip_id`/`event_id` (migration 0017). This is an index, not a new column
— no schema redesign, consistent with "pure aggregation" for the
computation itself.

**Endpoint shape:** either extend `GET /api/panorama` with a
`confianca`/`saude` block (simplest, one more facet next to the existing
ones) or add a sibling `GET /api/saude` if the payload grows large enough
to want independent caching/polling — no strong reason to split it now
given `panorama()`'s existing size; start as an extension, split later if
the endpoint gets unwieldy (same "add a router when `app.py` actually
hurts" posture the codebase already takes toward its 1422-line `app.py`).

**Coupling to feature 6 (soft, not hard):** the health index becomes more
informative once feature 6 exists (a "corroborated by two independent
witnesses" flag is a natural, higher-trust bucket beyond the existing
alta/média/baixa three levels) — but it does not require feature 6 to
ship first. Design the aggregation payload so a corroboration count/flag
can be added as one more facet later without breaking the endpoint
contract (e.g. return a dict of named facets, not a fixed-arity tuple).

---

## (d) Feature 6 — Generalized corroboration engine

### What's actually there today (more precise than the milestone's own framing)

Reading `grouping/correlacao.py` directly surfaces something the milestone
brief gets slightly wrong: `_confrontar_com_outro_lado` (`correlacao.py:346`)
is **not GPS-only today** in the sense of "only tests GPS." It loops over
`campos_base`, which already includes `cidade` and `regiao` (both derived
from the *same* donor-GPS distance test via `raio_incerteza`/haversine) —
so city/region confrontation, as a byproduct of GPS-donor confrontation,
**already exists**. Two things are genuinely missing, more narrowly than
"extend to date/time, city/country":

1. **`pais` is deliberately excluded** from the confrontation test
   (`correlacao.py:380`, `if campo == "pais" ... resultado.append(...);
   continue` — passthrough, never tested) because `raio_incerteza` is
   calibrated for person-scale movement (metres to ~50km), not
   country-scale geography (hundreds/thousands of km) — the docstring
   says so explicitly, and says it needs geocoding this module
   deliberately doesn't have. Generalizing `pais` means giving it a
   **different comparator** (containment/equality of geocoded country
   names, not a distance-radius test), not reusing `raio_incerteza`.
2. **There is no inheritance/confrontation concept for date/time at all.**
   `correlacao.py` corrects clock drift (`estimar_offsets`) and uses
   `Δt` as the *tolerance window* for GPS inheritance — but a photo's own
   *date* is never itself something inherited-and-confronted the way GPS
   is. Building this means designing a genuinely new "two independent
   date witnesses, do they agree" concept (e.g. EXIF date vs.
   filename-embedded date vs. cross-source date), which has no existing
   analog in this file to extend — it's new, not a generalization of
   existing code.

`_distancia_m` (haversine) and `raio_incerteza` (velocity-calibrated,
metres) are geometrically specific to GPS and **cannot** represent either
of the two gaps above — a date/time comparator needs a `timedelta`
tolerance, a country comparator needs categorical/hierarchical equality,
neither is "distance in metres."

### Decision: shared three-way control-flow shape, per-evidence-type comparators — two candidate homes, one recommendation

What generalizes across GPS/date/country is the **shape** of
`_confrontar_com_outro_lado`'s logic, not its math: given a candidate
witness and (optionally) a second witness on the other side, (1) no
second witness → pass the candidate through unchanged; (2) second witness
present and comparator says "agree" → keep the field, record agreement,
**never invent a confidence bonus** (docs/CONFIANCA.md's core rule); (3)
comparator says "disagree" → drop the field for **everyone**, not just
the losing side (the existing GPS logic's "in transit" reasoning, which is
domain-agnostic — two disagreeing witnesses are a reason to distrust the
middle value regardless of what kind of value it is).

I read `classification/confidence.py` directly before deciding where this
belongs (not inferred): it is currently a **pure scoring table +
weakest-link reducer** — `SCORES_REFERENCIA` (origin → score) and
`elo_mais_fraco(scores: list[float])`. It has no concept today of
comparing two witnesses before a score exists; it only combines scores
that already exist. That's a materially different function shape from
"decide agree/disagree between two candidate values." Lifting the
three-way branch there would add a new responsibility (pairwise
comparison) to a module that is currently just "given known scores, pick
the worst" — not a natural fit without also redefining what the module is
for.

**Two candidate designs, both viable:**

- **Narrow (extend in place):** add per-evidence-type comparator
  functions directly beside `_confrontar_com_outro_lado` in
  `grouping/correlacao.py` — a `_comparador_data(delta_tolerance)` and a
  `_comparador_pais(geocoder)`, each plugged into the same three-way
  branch, still inside the module that already owns cross-source
  temporal/geographic correlation. Closest to the milestone's own
  wording ("extends `grouping/correlacao.py`'s
  `_confrontar_com_outro_lado`"). Lowest risk to the calibrated,
  D-074-measured GPS behavior (no file boundary crossed, existing tests
  in place stay adjacent to what they test).
- **Broad (lift the shape):** extract only the **generic three-way
  control flow** (not the GPS math) into `classification/confidence.py`
  as a small primitive, e.g. `confrontar(candidato, outro, comparador) ->
  (mantem: bool, concordou: bool)`, and have `correlacao.py`'s GPS case
  become its first caller, passing a haversine-based comparator. A future
  `pais` comparator (needs geocoding) or a date/time comparator (needs a
  `timedelta` tolerance) can then live wherever the evidence is produced
  — `correlacao.py` for anything cross-source/temporal,
  `classification/engine.py` or the new `exif_write`/GenAI modules for
  anything evidence-type-specific to those features — all calling the
  same shared primitive. This reading treats "never invent a bonus, drop
  on disagreement" as a **confidence-model rule** (which is what
  `docs/CONFIANCA.md` already governs, and where `confidence.py` already
  lives), not a grouping-specific rule that happens to be reusable.

**Recommendation: broad, but land it narrow first.** Ship the `pais`
comparator and the new date/time confrontation logic inside
`grouping/correlacao.py` initially (lowest risk, keeps the
D-074-calibrated test suite next to the code it protects, no cross-module
refactor blocking the feature). Once a **second** consumer outside
`grouping/` actually needs the same three-way shape (e.g. feature 2's
GenAI city guess wanting to be confronted against a `pais`/`cidade`
already known from GPS-inheritance, or a future extension confronting
category guesses from folder vs. advisor), extract the shared shape into
`classification/confidence.py` at that point — informed by a real second
caller instead of a speculative one. This avoids over-abstracting a
25-line branch into a "primitive" before there's a second consumer to
validate the abstraction boundary is right.

---

## Features 3 and 4 — frontend-only / infra-light

### Feature 3 — Sidebar navigation

`webapp/src/components/Sidebar.tsx` (311 lines) and `ArvoreDePastas.tsx`
(146 lines) are the only files touched — no backend change. `/api/pastas`
already exists (`server/app.py:609`) and is index-backed
(`ix_media_files_pasta`, added in LANC-02 — **note:** `.planning/codebase/
CONCERNS.md`, dated 2026-08-16, still lists the missing `pasta` index as
open tech debt; `.planning/PROJECT.md`'s validated section confirms LANC-02
shipped the index on 2026-08-18. Treat `CONCERNS.md` as stale on this
specific point — verified directly against `models/catalog.py:147`, which
has `Index("ix_media_files_pasta", "pasta")`). "Navigable sidebar" is a
pure UI/UX slice: keyboard navigation, tree expansion state, possibly a
richer `/api/pastas` response (e.g. counts already returned; check whether
"navigable" needs anything the endpoint doesn't already return before
assuming a backend change is needed).

### Feature 4 — Folder picker + import progress gauge

`ModalCaminho.tsx` (55 lines) is a raw text `<input>` — replacing it with a
native folder picker means a **Tauri capability addition**
(`src-tauri/capabilities/`, likely the `dialog` plugin) plus a
`webapp/src/api.ts`-level call into the Tauri JS bridge when running
inside the shell (with a graceful fallback to the existing text input when
running as a plain browser dev server, per `webapp/vite.config.ts`'s
existing dev-server-without-Tauri path — `ModalCaminho.tsx`'s current form
IS that fallback and should probably stay as the non-Tauri code path, not
be deleted).

Import progress gauge: `StatusBar.tsx` and `server/jobs.py` **already
have** everything the milestone asks for at the mechanism level —
`JobManager._atualizar` already tracks `vistos`/`processados`/`pulados`/
`erros`/`arquivos_por_segundo`, and `StatusBar.tsx` already renders a
determinate progress bar from `estado.vistos`/`estado.processados`
(`StatusBar.tsx:44-51`). "Extending" this is very likely UI polish (bigger
gauge, per-source breakdown, ETA) rather than new plumbing — verify with
the dono what's actually missing from the current bar before assuming new
backend fields are needed.

**Shared file surface with feature 3:** both touch `Sidebar.tsx`
(feature 4 replaces the "Adicionar pasta…" button's modal; feature 3
changes the tree/fonte list beside it in the same file). No functional
dependency, but doing them as adjacent slices (not necessarily one slice)
avoids two people/sessions rebasing the same ~300-line file.

---

## Build Order

All 6 features are **technically independent at the data/schema level** —
none of them blocks another from being built. The dependency graph below
is about risk, file-conflict, and value-compounding, not hard blocking;
stated explicitly because the quality gate asked for real dependencies,
not narrative convenience.

| # | Feature | Hard dependency on others? | Real coupling |
|---|---------|----------------------------|----------------|
| 1 | EXIF write | None | New module, isolated from everything else |
| 2 | GenAI folder classifier | None | Shares `ClaudeAdvisor`/opt-in gate infra with existing advisor; could become an evidence source feature 6 confronts later (soft) |
| 3 | Sidebar navigation | None | Shares `Sidebar.tsx` file with feature 4 |
| 4 | Folder picker + gauge | None | Shares `Sidebar.tsx`/`ModalCaminho.tsx` with feature 3; needs a Tauri capability, not a backend change |
| 5 | Confidence axis + health index | None (builds on existing `panorama()`/`LACUNAS`) | Richer after 1, 2, 6 exist (more evidence density, corroboration signal) — not blocked by any |
| 6 | Corroboration generalization | None | Pure backend, touches the D-074-calibrated `correlacao.py` — highest regression risk of the six |

**Recommended order:** `1 → 2 → 4 → 3 → 5 → 6`, with two deviations from
the dono's stated priority order (`1,2,3,4,5,6`), both justified below —
flag both explicitly for the dono's sign-off rather than silently
reordering:

1. **1 (EXIF write) first**, as declared. Highest invariant-risk item
   (it's the one that revises invariant 7) — isolating it first, before
   any UI churn competes for review attention, matches how the codebase
   already treats invariant-sensitive work (dedicated slices, per
   `docs/METODO_DE_TRABALHO.md`'s vertical-slice convention).
2. **2 (GenAI classifier) second**, as declared — independent, but
   landing it before 5 means the health index's aggregation scope can
   account for the new `llm_pasta`-origin evidence from the start
   instead of retrofitting a facet later.
3. **Swap 4 before 3** (dono declared 3 then 4). Reasoning is
   file-conflict avoidance, not a functional dependency: feature 4
   replaces the modal that feature 3's sidebar triggers
   (`onAdicionarPasta` → `ModalCaminho`); doing the picker replacement
   first means feature 3's navigation work lands on the already-settled
   button/modal wiring instead of both changing the same ~60-line region
   in parallel. If both are done in a single slice/session this
   distinction doesn't matter — flag it only if they're split across
   separate sessions.
4. **5 before 6**, as declared, but design the health-index payload
   (dict of named facets, not fixed-arity) so a corroboration signal from
   6 slots in later without an endpoint-contract break — see (c) above.
   This honors the dono's explicit priority (5 ranked above 6) while
   keeping the door open for 6 to enrich 5 without rework.
5. **6 last** among the six, matching the dono's order and its status as
   the highest-regression-risk backend change (touches calibrated,
   measured behavior — 91.1%/93.6% coverage numbers in `correlacao.py`'s
   own comments that a change must not silently regress). Its own
   internal build order (see (d)): land the narrow in-module comparators
   first (`pais`, date/time) before considering the broader
   `classification/confidence.py` extraction — do not extract the shared
   primitive speculatively.

**Feature 7 (out of the 6, but informs sequencing):** `PROJECT.md`
explicitly defers "Modo ativo de aprendizado" until **both** 5 and 6
exist. That's consistent with everything found here — 7 is the first
feature that actually needs the *combination* of a confidence axis and a
generalized corroboration signal; nothing in 1-6 needs 7, so it correctly
sits outside this milestone's scope.

---

## Sources

All findings are grounded in direct reads of the current repository
(2026-08-18 checkout), no external documentation needed for this
integration-mode research:

- `fotoorganizer/metadata/base.py`, `fotoorganizer/metadata/exiftool.py`
- `fotoorganizer/operations/executor.py`, `fotoorganizer/operations/planner.py`
- `fotoorganizer/security/paths.py`
- `fotoorganizer/classification/advisor.py`, `engine.py`, `confidence.py`
- `fotoorganizer/grouping/correlacao.py`
- `fotoorganizer/models/inference.py`, `fotoorganizer/models/catalog.py`
- `fotoorganizer/repositories/media.py`
- `fotoorganizer/server/jobs.py`
- `webapp/src/components/Sidebar.tsx`, `ModalCaminho.tsx`, `StatusBar.tsx`,
  `Confianca.tsx`
- `.planning/PROJECT.md`, `.planning/codebase/ARCHITECTURE.md`,
  `.planning/codebase/CONCERNS.md`, `.planning/codebase/STRUCTURE.md`
- WebSearch (LOW confidence, not load-bearing — superseded by the
  primary-source read of `ExifToolExtractor`'s own concurrency docstring):
  general exiftool `-stay_open` protocol documentation, used only to
  confirm the protocol accepts arbitrary argument sets per `-execute`
  block, not to determine the write-integration design.

---
*Architecture research for: Foto Organizer v2.0 feature integration*
*Researched: 2026-08-18*
