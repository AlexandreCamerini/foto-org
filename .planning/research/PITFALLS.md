# Pitfalls Research

**Domain:** Adding 7 features to an existing, shipped, local-first macOS photo cataloging app (Foto Organizer v2.0)
**Researched:** 2026-08-18
**Confidence:** MEDIUM-HIGH — grounded in the project's own code (`operations/executor.py`, `classification/advisor.py`, `docs/CONFIANCA.md`, `docs/DECISOES.md` D-017/D-059/D-060/D-074/D-075) plus verified external sources for exiftool write behavior and POSIX locking semantics. LOW confidence flagged individually where only training data or a single web source supports a claim.

## Critical Pitfalls

### Pitfall 1: In-place EXIF write treated as "just another copy operation"

**What goes wrong:**
The existing `operations/executor.py` pattern (dry-run → `hash_pre` → exclusive create `'xb'` → `hash_pos` → verify → audit log) is airtight for **copy-to-new-path**, but it doesn't transfer directly to **in-place mutation of the original**. The exclusive-create trick (`destino.open("xb")`) that makes "never overwrite" true *by construction* has no equivalent for an in-place write — there is no second path to refuse-if-exists against. A naive port of the pattern would call `hash_pre`, invoke exiftool, call `hash_pos`, and assume the same guarantees apply, when the actual guarantee (atomicity, no partial write) now depends entirely on exiftool's own write strategy, not on filesystem semantics the app controls.

**Why it happens:**
The team has one working mental model for "safe write" (verified copy) and D-075 explicitly frames this as reusing "the same rigor as `operations/`" — which invites literally reusing the code path rather than re-deriving what "rigor" means for a fundamentally different write shape (mutate-in-place vs. create-new).

**How to avoid:**
- Confirm and rely on exiftool's actual safe-write mechanism: by default it writes a full temporary copy and does an atomic `rename()` over the original (verified via exiftool docs/changelog) — this already gives crash-safety equivalent to the copy executor's exclusive-create, but through a different mechanism (temp+rename, not refuse-if-exists). Do not reimplement your own temp-file dance in Python around exiftool's subprocess call; that would double the risk surface.
- Never invoke exiftool with default backup behavior left implicit. Without `-overwrite_original`, exiftool leaves an `IMG_1234.CR3_original` backup file sitting in the user's real photo folder — clutter in a supposedly read-only-observed tree, and a file the read-only scanner has never had to reason about before (could be picked up by iCloud Drive/Dropbox sync as a "new file," or by the app's own next scan pass). Explicitly pass `-overwrite_original` (temp+rename, no backup left) and let the app's own `hash_pre`/`hash_post` + audit log be the safety net that replaces exiftool's discarded backup.
- The invariant "only write when currently empty" is not just a scope limiter — treat it as the crash-recovery mechanism. Because the write is a no-op precondition check (field must be empty), a crash between exiftool's write and the app's own commit is naturally recoverable: on retry, re-read the field first; if already populated, mark the item done without re-invoking exiftool (idempotent retry). Design the executor around this from the start rather than bolting on a reconciliation pass later.
- Extend (don't bypass) the existing "stuck in EXECUTANDO after crash" gap. `.planning/codebase/CONCERNS.md` already documents that `OperationPlan.status == EXECUTANDO` has no boot-time reconciliation for copy plans, where it's low-severity because a stuck copy plan is trivially safe to resume (destino missing or hash mismatch = redo). For in-place EXIF writes this gap is higher severity: a plan stuck in EXECUTANDO after a mid-write crash leaves ambiguous state (was the original mutated or not?) with no boot check to even flag it. This feature is the forcing function to finally fix that debt — do not ship EXIF write with a still-open reconciliation gap.

**Warning signs:**
- Code review that copies `_copiar_exclusivo`'s file-handling pattern for the EXIF path instead of shelling out to exiftool's own write.
- No test that kills the process (or mocks a crash) mid-exiftool-call and asserts the retry path is safe.
- `_original` backup files appearing in test fixtures after a write test runs — sign `-overwrite_original` wasn't passed.

**Phase to address:**
Feature 1 (EXIF location write) — must be resolved in that phase's design, before implementation starts.

---

### Pitfall 2: Concurrent access is silent corruption of *trust*, not a blocked write

**What goes wrong:**
The natural framing — "what if Lightroom or Finder has the file open when we write?" — imports a Windows mandatory-locking mental model. macOS/POSIX file locking is **advisory**: exiftool's write (temp file + atomic rename) will very likely *succeed* even while Lightroom holds an open file descriptor to the original, because nothing enforces cooperation. The real risk isn't a blocked write, it's a **silent desync**: Lightroom's in-memory catalog and its own XMP sidecar continue to describe the pre-write state, while the file on disk now has GPS/city/country burned into EXIF that Lightroom doesn't know about until the user manually does "Read Metadata from File." If Lightroom later writes its own metadata back (auto-write XMP is a common Lightroom setting), it can overwrite the fields Foto Organizer just wrote, or produce a merge the user never asked for and never reviewed — invisibly defeating the entire dry-run/audit-log guarantee from the user's point of view, even though the app's own log is accurate.

**Why it happens:**
The team's existing safety model (invariant 3, the copy executor) was built entirely around files the app itself fully owns during the operation (fresh copies at new paths). EXIF write is the first feature where a *second, uncoordinated* piece of software (Lightroom, Photos.app, Finder tags, iCloud sync) has an ongoing relationship with the exact file being mutated.

**How to avoid:**
- Do not try to solve this with locking (POSIX advisory locks won't stop an uncooperative process like Lightroom or `fseventsd`/Spotlight). Solve it with **detection and disclosure** instead: before writing, check if the file is inside a known managed library structure (Lightroom catalog folder, Photos.app library bundle) and if so, surface a one-time warning in the dry-run review ("este arquivo é gerenciado por [X]; a escrita pode ser sobrescrita pelo próprio [X] depois") rather than silently proceeding as if the app is the only writer.
- Verify hash-after only proves *this process's* write landed correctly — it does not prove no other process touched the file afterward. Don't let "hash_pos matched" be read by the UI/audit log as a permanent guarantee; it's a guarantee about the moment of the write only.
- Treat iCloud Drive / Dropbox-synced folders specially: an atomic rename over a file inside a cloud-sync watch folder can trigger the sync client to treat it as a new version, sometimes producing a "conflicted copy" duplicate rather than a clean update — verify actual behavior with the specific sync client(s) the real acervo touches before assuming rename-based writes behave the same as on a plain local volume.

**Warning signs:**
- No mention of managed-library detection (Lightroom `.lrcat` proximity, Photos.app `.photoslibrary` bundle) anywhere in the EXIF-write plan.
- Test fixtures for this feature use only plain loose files, never files inside a simulated Photos.app/Lightroom-managed folder structure.

**Phase to address:**
Feature 1 (EXIF location write).

---

### Pitfall 3: Format-specific write reliability is not universal — CR3/HEIC have a real corruption history

**What goes wrong:**
D-026 already validated exiftool as *read* extractor (0/40 → 40/40 CR3 cameras identified). That validation does not transfer to *write*. GPS/EXIF write support for CR3 and HEIC was added to exiftool comparatively late (v11.43) and has had real corruption bugs on write for both formats historically (HEIC image corruption on tag write; CR3 QuickTime-atom padding truncation when the rewritten atom is smaller than the original). Assuming "we already validated exiftool for this acervo" covers write as well as read is exactly the kind of untested assumption the project's own discipline (measure before deciding, D-059/D-060/D-074) argues against.

**Why it happens:**
Read and write share a tool and a vendor but are different code paths with different maturity; a team that already trusts exiftool from the read side has no natural trigger to re-verify write support per format.

**How to avoid:**
- Before enabling EXIF write for a given file extension, verify write support and known-issue status for that specific format/exiftool-version combination actually in use — don't assume RAW format parity with JPEG.
- Add a hash-based corruption check that's stronger than "hash before ≠ hash after" (that's expected — the point is to change the file). Add a **structural** check post-write: re-open the file with the same extractor used elsewhere in the app (exiftool or the pure-Python fallback) and confirm it still parses and that non-location fields (dimensions, DateTimeOriginal, camera model) are byte-identical to pre-write values. A write that "succeeds" but silently truncates a MakerNotes block or corrupts the image data stream would pass a naive before/after diff on the 3 written fields while destroying the photo.
- Scope the initial rollout to the formats actually present in the real acervo in meaningful volume (check the catalog's format distribution) rather than "all formats exiftool claims to support," and gate less-common/riskier formats behind an explicit second opt-in or defer them.

**Warning signs:**
- No format-distribution check against the real catalog before deciding which extensions get write support.
- Verification step only re-checks the 3 written fields, not overall file structural integrity.

**Phase to address:**
Feature 1 (EXIF location write).

---

### Pitfall 4: Permissions and mount-state assumed same as read path

**What goes wrong:**
The scanner and copy executor both already handle "origin unavailable" (unmounted volume) as an expected, non-fatal condition — but that's read-time or copy-source availability. Write availability is a stricter and different check: a file can be fully readable and copyable while being on a read-only-mounted volume (many archival/backup workflows mount external drives read-only), inside a Photos.app library that macOS protects with stricter permissions, or simply `chmod`-read-only after import (a common practice to prevent accidental edits). None of the existing read/copy code paths ever needed to check `os.access(path, os.W_OK)` or the containing directory's write permission (exiftool needs to write its temp file in the same directory as the original by default) — this is a genuinely new failure class for the codebase.

**How to avoid:**
- Add an explicit writability pre-check in the dry-run step, separate from and in addition to the existing "origem indisponível" check: file write permission AND containing-directory write permission (for the temp file exiftool creates alongside the original), surfaced in the same dry-run "problemas" list the copy executor already produces (`dry_run()` → `problemas.append(...)`, same UX pattern already in place).
- Treat a read-only-mounted volume as equivalent to "unmounted" for this feature specifically — reuse `sources/disponibilidade.py`'s volume-detection machinery but add a write-capability check, don't assume "mounted = writable."

**Warning signs:**
- Dry-run for EXIF write only checks file existence, not write permission.
- No test with a `chmod 0444` fixture file or a read-only bind mount.

**Phase to address:**
Feature 1 (EXIF location write).

---

### Pitfall 5: Reusing the Advisor's single opt-in flag lets GenAI folder classification piggyback on consent it was never separately given

**What goes wrong:**
The existing Advisor gates external calls behind one global boolean, `[privacidade] servicos_externos = true`. The milestone explicitly frames GenAI folder→city/event classification as "same operating model as the existing Advisor" — which is right for the *mechanism* (metadata-only, opt-in, cost visible) but wrong if read as "same flag." If the new feature is wired to the same boolean, a user who opted into the Advisor's cluster-classification months ago silently also opts into a *different* feature (folder→city/event) with a different data shape and different cost profile, without ever seeing a distinct consent moment for it — a direct tension with invariant 4's requirement that the user gets "indicação visual prévia de quais dados serão enviados, finalidade, destino e forma de revogação" **per use**, not per app-wide toggle.

**Why it happens:**
Reusing an existing, already-tested boolean is the path of least resistance, and "same operating model" in the milestone framing is easy to over-read as "same config key."

**How to avoid:**
- Give the new feature its own opt-in key (e.g. `[privacidade] servicos_externos_classificacao_pasta = true`), gated behind the existing `servicos_externos` master switch but requiring its own explicit enable — mirrors how invariant 6 (face recognition) is already "off by default" as a distinct switch from the general cloud toggle.
- Add a regression test asserting a fresh config has BOTH flags false, and that flipping only the Advisor's flag does not enable folder classification (and vice versa).
- Surface, in the UI, which distinct purpose each toggle unlocks — not a single unlabeled "allow cloud" switch.

**Warning signs:**
- New feature's code checks `config.privacidade.servicos_externos` directly instead of a feature-specific flag.
- No test distinguishing the two flags' independence.

**Phase to address:**
Feature 2 (GenAI folder classification).

---

### Pitfall 6: "Cost visible per session" is a stated requirement with no existing implementation to extend

**What goes wrong:**
`fotoorganizer/classification/advisor.py` (read in full) has no cost tracking, no token accounting, no per-run spend cap, and no retry/backoff logic at all — a single `try/except Exception` around one API call that returns `None` on any failure (network, auth, rate limit, malformed response all collapse to the same "no opinion" outcome, logged only). D-059/D-060's cost measurement was a one-off script (`scripts/medir_qualidade_advisor.py`) the *owner* ran manually with his own API key, outside the app — not a runtime cost-visibility feature. The milestone context's "custo visível por sessão" for feature 2 is therefore new work, not an extension of something already built — treating it as already-solved-just-reuse-it will under-scope the phase.

**Why it happens:**
D-059/D-060 make it easy to believe cost measurement is a solved, integrated concern for this codebase, when in fact it was a manual, external, one-time measurement exercise.

**How to avoid:**
- Design cost visibility as a first-class part of the feature: capture `usage` (input/output tokens) from each `messages.create()` response (the Anthropic SDK returns this on `response.usage`), accumulate per run, and surface an estimate to the user **before** the run executes (dry-run-style: "isto vai classificar N pastas, custo estimado ~$X") — mirroring the `operations/executor.py` dry-run pattern the app already trusts, rather than inventing a new UX shape.
- Add a hard per-run cost/count ceiling with explicit confirmation to exceed it, not just a running total the user can ignore.
- Because folder classification likely runs over many more folders than the Advisor's narrow "neutral sessions only" trigger, do not assume the Advisor's current lack of retry/rate-limit handling scales safely — a batch of N folder-classification calls fired without concurrency limiting or backoff risks 429s cascading into a naive retry-everything loop (thundering herd) and real, fast cost overrun. Add explicit concurrency cap + exponential backoff, and make retry-on-429 distinct from retry-on-other-errors (don't retry auth/schema errors).

**Warning signs:**
- PR for feature 2 has no UI element showing estimated or actual spend before/after a run.
- No test asserting a hard ceiling stops further calls once exceeded.
- Feature reuses `ClaudeAdvisor.classificar()` unmodified at higher volume without adding backoff.

**Phase to address:**
Feature 2 (GenAI folder classification).

---

### Pitfall 7: Aggregate "health index" degenerates or silently becomes a weighted sum — both violate D-017/CONFIANCA.md by construction

**What goes wrong:**
`docs/CONFIANCA.md`'s weakest-link rule ("a confiança da sugestão é a do campo mais fraco... sem médias nem somas") is explicitly defined **within one item** — across the handful of fields (`categoria/ano/pais/cidade`) that make up one destination path. A catalog-wide health index aggregates **across the whole population** (hundreds of thousands of `MediaFile` rows), which is a different axis entirely, and neither of the two obvious ways to port the rule works:
- **Literal weakest-link at population scale** ("catalog health = confidence of the single weakest item in the whole catalog") degenerates to a near-constant "baixa," because in a catalog this size there is always at least one item with weak/no evidence — a useless, always-red metric.
- **Any scalar rollup that isn't literal min** (mean, weighted average, "% high + 0.5×% medium," etc.) is, by definition, exactly the "somar pontos arbitrários" the confidence model was built to reject — just moved up one level of abstraction where it's easier to miss in review because it's labeled "index," not "score."

There is direct historical evidence this class of bug already happened once: D-071/REV finding — items with *zero* evidence were rendering as "Alta" confidence in the "Sem categoria" bucket before being fixed to show "Sem categoria" explicitly. An aggregate index that includes unclassified items without a deliberate rule for how they count (excluded? counted as lowest tier? counted as "no data," distinct from "low confidence"?) risks reintroducing that exact class of survivorship-bias bug at the aggregate level — an index that looks healthier than reality because it silently drops or mis-weights the un-evidenced mass.

**Why it happens:**
"Health index" as a product concept pulls toward a single number almost by definition (that's what stakeholders expect from a "health score"), which is in direct tension with a confidence model deliberately designed to resist collapsing into a single number.

**How to avoid:**
- Do not build a scalar index. Build a **distribution**: counts/percentages of items at each confidence tier (alta/média/baixa) plus a distinct "sem evidência" bucket, and show it as a breakdown (this is the population-scale version of D-017's original move — quantity/segments, not a semaphore or a single percentage). This is directly analogous to what D-017 already decided for a single item's badge; extend the same "quantity over compression" philosophy upward instead of building a competing metric.
- Explicitly define, in the design doc for this feature, how items with *zero* evidence are counted — never let them be silently excluded from the denominator (that inflates the apparent health) or silently blended into "baixa" without being distinguishable from "an item that has weak evidence" (those are different problems requiring different user action).
- If a single "headline number" is required for the UI (e.g., a progress-bar-style summary), derive it transparently as "% of catalog at alta or média confidence, excluding sem-evidência items shown separately" and label it as exactly that — not as an opaque "health score" — so the computation is auditable the same way a single suggestion's confidence is auditable today ("por quê?").
- Route this feature's design through the same reviewer/discipline that owns `docs/CONFIANCA.md` before implementation — this is a change to how confidence is *represented*, not just a new screen.

**Warning signs:**
- Any code that does `sum(scores) / len(scores)` or applies numeric weights (e.g. `0.9*alta + 0.5*media + 0.1*baixa`) to produce the index.
- UI mockups showing a single percentage or 0–100 gauge for "saúde do acervo" with no drill-down into the underlying distribution.
- No explicit handling for items with zero evidence in the aggregation logic.

**Phase to address:**
Feature 5 (Confidence as navigation axis + aggregate health index).

---

### Pitfall 8: Generalizing D-074's corroboration pattern to categorical fields without separately calibrating each field

**What goes wrong:**
D-074's mechanism is inherently continuous and geometric: two GPS donors "agree" when the distance between their coordinates fits inside the sum of two calibrated uncertainty radii (`raio_incerteza(Δt)`), a threshold measured against 40,678 real GPS photos. Generalizing this to categorical fields (city, country) has no natural equivalent to "distance" or "radius" — a naive port (e.g., "agree if the two donor cities/countries are the exact same string") silently swaps a *calibrated, continuous, measured* tolerance for an *unmeasured, binary, assumed* one, exactly the shortcut D-074 itself rejected once already (the decision explicitly tested and discarded an unmeasured "encolhimento extra" bonus for concordant pairs, keeping only what the coverage measurement actually supported).

A second, more subtle version of the same mistake: even a binary exact-match test has an unmeasured base rate. For a field like "país," where the real acervo is likely dominated by one or two countries, two independent donors will *agree by pure chance* at a high background rate regardless of whether they're actually corroborating anything meaningful about the photo in between — treating that agreement as strong evidence manufactures confidence from noise, which is precisely what the weakest-link/no-arbitrary-sum discipline exists to prevent. "Cidade" agreement, by contrast, is much rarer by chance and carries real information — the two fields are not interchangeable and a single generalized rule applied uniformly to both will be wrong for at least one of them.

**Why it happens:**
"Generalize the corroboration engine" as a phase name invites reusing the *code shape* (confront both sides, mark concordância/discordância, use existing score, no new constant) without re-running the *measurement step* that gave D-074 its legitimacy in the first place — the temptation is to treat D-074 as "the corroboration algorithm" when it's actually "the GPS-specific calibration of a corroboration *pattern*."

**How to avoid:**
- Treat each new evidence type the corroboration engine extends to as requiring its own measurement pass, mirroring `scripts/calibrar_raio_incerteza.py --concordancia`'s methodology (same discipline: measure real coverage/agreement rate against the real catalog, band by the relevant confound — e.g. Δt for GPS; for categorical fields, band by the field's own base-rate skew) before deciding how agreement should affect confidence, if at all.
- For each categorical field, measure the **background agreement rate** first (how often do two independent, unrelated donors already agree by chance, e.g. because most of the acervo is one country) — if that rate is high, agreement on that field is weak evidence and the engine should say so explicitly (or exclude that field from corroboration bonuses entirely) rather than applying a uniform "concordância" treatment across all fields.
- Preserve D-074's "no new constant unless measured" discipline explicitly as an acceptance criterion for this phase: any new threshold, bonus, or matching rule introduced for a non-GPS field must cite a measurement against real catalog data in the decision log, the same way D-074 does — not be justified by analogy to GPS alone.
- Do not assume "discordância" for categorical fields carries the same signal as GPS discordância. D-074's GPS discordância case specifically flags "foto em trânsito" / one donor's coordinate being wrong — a meaningful physical interpretation. Two donors disagreeing on "cidade" could mean the same (photo taken while traveling between two donor-adjacent locations) or could mean one donor's city was itself weak/derived evidence (e.g. from folder name) rather than GPS-grade — conflating those requires checking the *evidence origin*, not just the value, of each donor before generalizing the "confront both sides" logic.

**Warning signs:**
- Corroboration logic for city/country ships without a corresponding measurement script or logged decision citing real-catalog numbers, unlike every other confidence-affecting change in `docs/DECISOES.md`.
- The same tolerance/bonus code path is applied to city and country without separate base-rate analysis for each.
- No handling for "one donor's evidence for this field is itself weak" (e.g., a folder-name-derived city) before treating it as a corroboration input on par with GPS-grade evidence.

**Phase to address:**
Feature 6 (Generalized corroboration engine).

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|-----------------|------------------|
| Reuse `operations/executor.py`'s copy pattern verbatim for EXIF write instead of designing for in-place mutation | Faster to ship, familiar code | Misses exiftool-specific atomicity/backup semantics; false sense of parity with copy safety guarantees | Never — the write shape is fundamentally different, must be re-derived |
| Wire GenAI folder classification to the existing `servicos_externos` flag instead of a dedicated opt-in | Less config plumbing | Silent consent scope creep across two distinct data-sharing purposes | Never, per invariant 4's per-purpose disclosure requirement |
| Ship a single scalar "health index" now, refine the breakdown UI later | Faster demo-able metric | Locks in a number that already violates the weakest-link philosophy; hard to walk back once users anchor on it | Never — build the distribution view first, add a headline number derived transparently from it if still wanted |
| Port D-074's GPS threshold to categorical fields by analogy, measure later "if it looks wrong" | Faster to ship feature 6 | Invents unmeasured confidence exactly like the discarded "encolhimento extra" bonus D-074 already rejected once | Never, per the project's own established discipline |
| Skip a boot-time reconciliation check for `OperationPlan.EXECUTANDO` for the EXIF-write path (defer the existing tech debt) | Ships feature 1 faster | For copy operations this gap is low-severity (self-evidently resumable); for in-place mutation it leaves genuinely ambiguous state after a crash | Never for feature 1 — acceptable to leave unfixed *only* for the pre-existing copy path if truly out of scope, but not for the new mutation path |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|--------------|-----------------|-------------------|
| exiftool (write path) | Calling it without `-overwrite_original`, leaving `_original` backup files in the user's real photo tree | Always pass `-overwrite_original`; rely on the app's own hash-before/after + audit log as the safety net instead of exiftool's backup |
| exiftool (CR3/HEIC write) | Assuming read-side validation (D-026) implies write-side reliability | Verify write support and known-corruption issues per format/exiftool-version actually in use; add post-write structural verification beyond the 3 written fields |
| Anthropic SDK (folder classification, extending `ClaudeAdvisor`) | Reusing the single-call try/except-everything pattern at higher volume with no backoff/concurrency cap | Add exponential backoff on 429, a concurrency cap, and distinguish retryable (rate limit) from non-retryable (auth, schema) errors |
| iCloud Drive / Dropbox-synced folders | Assuming atomic rename behaves identically inside a cloud-sync watch folder as on a plain local volume | Detect sync-managed folders and verify behavior (conflicted-copy risk) before enabling write there, or warn explicitly in dry-run |
| Lightroom/Photos.app-managed files | Assuming POSIX file access = safe concurrent access | Detect managed-library proximity and disclose the desync risk in the dry-run review; don't attempt to "lock" against an uncooperative process |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|-----------------|
| Folder classification run without a per-run cap, triggered on a full catalog re-scan | Cost/time balloons unexpectedly after a large incremental import | Cap classification runs by count and cost estimate, shown before execution (dry-run style) | Any run over the acervo's full ~422K-record scale, not just the 104-cluster measurement sample |
| Health index computed as a live aggregate query over the whole catalog on every navigation | UI stalls when opening the confidence-axis view at catalog scale | Precompute/cache the distribution incrementally (same incremental discipline already required elsewhere: CLAUDE.md "processar incrementalmente... evitar N+1, reprocessamento") | At current measured scale (~422,738 registros) if the index is a naive full-table scan per view |
| Generalized corroboration engine re-scanning full neighbor windows per new evidence type | Same class of slowdown D-074's own `procurar` function had to address (27,117 candidatos barrados comment) before optimization | Reuse the already-optimized neighbor-search machinery from the GPS case rather than re-implementing a naive scan per new field | At acervo scale, for any field with a large candidate-donor pool |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Folder picker (feature 4) returns a symlinked or network path without validation | Bypasses invariant 5 (no symlink traversal, validated paths) at the exact entry point meant to prevent it | Route every path returned by the native picker through the existing `security/` path-validation code before registering it as a source, same as any other path input |
| GenAI folder classification payload scope creep | "Metadata only" silently grows to include more than folder/file names, dates, counts, geocoded places (e.g. someone adds EXIF comment fields, or full file lists instead of samples) as the feature evolves | Define and test the payload schema explicitly (mirror `ClusterInfo`'s frozen dataclass shape) and add a test asserting the API payload never contains image bytes or fields outside the documented set |
| EXIF write payload scope creep | Feature ships writing only lat/long/city/country per D-075, but a later "small addition" (e.g. also writing date, since it's "right there") reintroduces a full EXIF-write-anywhere precedent without a new decision | Enforce field allowlist at the code level (not just by convention), require a new logged decision (like D-075) before any additional field is ever added |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|--------------|-------------------|
| Health index shown as a bare percentage/gauge with no drill-down | User can't tell *why* the catalog is "62% healthy" or what to do about it — same problem D-017 already solved once for single items | Distribution view (counts per tier + sem-evidência bucket) with click-through to the underlying items, consistent with the "por quê?" answerability the confidence model already promises |
| Import progress gauge (feature 4) reports a naive linear percentage during incremental/resumed scans | Gauge appears to "jump backward" or lie when a paused/resumed scan reports fewer new items than a fresh scan would | Gauge must reflect the scanner's existing checkpoint state (already tracks incremental progress) rather than assuming every run starts at 0% |
| Sidebar changes (feature 3) drift from the 3 already-approved navigation decisions in `docs/NAVEGACAO.md` | Reintroduces inconsistency the team already resolved once (sidebar=lugar, top=recorte com chips, rolagem contínua com âncora temporal) | Treat `docs/NAVEGACAO.md` as binding for this phase; any deviation needs its own logged decision, not an incidental UI tweak |

## "Looks Done But Isn't" Checklist

- [ ] **EXIF write feature:** Often missing structural post-write verification beyond the 3 written fields — verify a re-parse of the whole file (dimensions, DateTimeOriginal, camera model) matches pre-write values, not just that `hash_pre != hash_pos`.
- [ ] **EXIF write feature:** Often missing a boot-time reconciliation check for plans stuck in `EXECUTANDO` — verify this is fixed for the mutation path even if left as debt for the copy path.
- [ ] **GenAI folder classification:** Often missing actual token/cost accounting — verify `response.usage` is captured and surfaced to the user before/after each run, not just logged.
- [ ] **GenAI folder classification:** Often missing a distinct opt-in flag from the existing Advisor — verify the two features can be enabled/disabled independently, with a test proving it.
- [ ] **Health index:** Often missing explicit handling of zero-evidence items — verify the design doc states how they're counted (never silently excluded or blended into "baixa" without distinction).
- [ ] **Corroboration engine generalization:** Often missing a calibration measurement per new field — verify a `docs/DECISOES.md` entry exists citing real-catalog numbers for each field the engine is extended to, not just the GPS case.
- [ ] **Folder picker:** Often missing path validation on the picker's return value — verify it passes through the same `security/` validation as any other source-registration path.

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|-----------------|------------------|
| EXIF write corrupts a file (format-specific bug) | HIGH | Because writes only touch previously-empty fields and hash_pre is recorded pre-write, a corrupted file can be identified from the audit log; recovery requires either a pre-write backup copy (consider making one mandatory for at-risk formats, e.g. CR3/HEIC, until write reliability is proven) or accepting data loss on that item — cheapest prevention is format allowlisting per Pitfall 3, not recovery after the fact |
| Health index ships as a scalar sum, gets called out later | MEDIUM | Reversible: replace the scalar with the distribution view; the underlying per-item confidence data was never touched, only the aggregate presentation — no data migration needed |
| GenAI classification cost overrun | LOW–MEDIUM | Add the cap retroactively; because the Advisor pattern already treats all LLM output as revisable evidence never auto-applied, no catalog corruption results — only wasted spend, recoverable by adding the missing cap |
| Corroboration engine ships with an unmeasured categorical threshold, later found wrong | MEDIUM | Same recovery pattern as any evidence-logic change: bump `versao_logica` and regenerate suggestions — the architecture already supports this (docs/CONFIANCA.md), but real user review time already spent on wrong suggestions is not recoverable |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|-------------------|----------------|
| In-place write treated as copy-executor clone | Feature 1 (EXIF write) | Design doc explicitly re-derives atomicity guarantees from exiftool's own temp+rename mechanism, not the copy executor's exclusive-create trick |
| Concurrent access / managed-library desync | Feature 1 (EXIF write) | Dry-run flags files inside detected Lightroom/Photos.app structures; test fixture includes a simulated managed library |
| Format-specific write corruption (CR3/HEIC) | Feature 1 (EXIF write) | Post-write structural verification beyond the 3 fields; format allowlist checked against real catalog distribution |
| Permissions/read-only-mount blind spot | Feature 1 (EXIF write) | Dry-run adds explicit write-permission check (file + containing dir), test with read-only fixture |
| Single opt-in flag scope creep | Feature 2 (GenAI folder classification) | Dedicated config key; test proving independent enable/disable from the Advisor's flag |
| Cost visibility assumed already built | Feature 2 (GenAI folder classification) | UI shows estimated cost pre-run and actual cost post-run, backed by `response.usage` capture; hard cap enforced with test |
| Retry storm / rate limiting absent | Feature 2 (GenAI folder classification) | Backoff + concurrency cap implemented and tested against simulated 429 responses |
| Scalar health index violating weakest-link philosophy | Feature 5 (confidence axis + health index) | Design doc shows a distribution/breakdown, not a single formula combining tiers; reviewed against `docs/CONFIANCA.md` |
| Zero-evidence items mishandled in aggregation | Feature 5 (confidence axis + health index) | Explicit test asserting zero-evidence items are counted in a distinct bucket, never defaulting into "alta" or silently excluded (regression test mirroring the D-071 bug class) |
| Unmeasured generalization of D-074 to categorical fields | Feature 6 (corroboration engine) | Each new field has a logged decision citing real-catalog measurement, mirroring `scripts/calibrar_raio_incerteza.py --concordancia` methodology |
| Categorical base-rate agreement mistaken for corroboration | Feature 6 (corroboration engine) | Measurement includes background/chance agreement rate per field before any bonus/threshold is applied |
| Sidebar drift from approved navigation decisions | Feature 3 (sidebar navigation) | Changes reviewed against `docs/NAVEGACAO.md`'s 3 decisions; regression tests for text-search-doesn't-leak-between-groups (REV-03) still pass |
| Folder picker bypasses path validation | Feature 4 (folder picker + import gauge) | Picker's returned path routed through existing `security/` validation before source registration; test with a symlink fixture |
| Import gauge misreports during incremental/resumed scans | Feature 4 (folder picker + import gauge) | Gauge driven by scanner's existing checkpoint state; test covers pause/resume scenario, not just fresh-scan-from-zero |

## Sources

- `.planning/PROJECT.md` — v2.0 milestone scope, active features, constraints (read in full)
- `docs/DECISOES.md` D-017, D-018, D-059, D-060, D-074, D-075 (read in full, direct quotes above)
- `docs/CONFIANCA.md` (read in full) — weakest-link aggregation rule, evidence level table
- `fotoorganizer/operations/executor.py` (read in full) — existing copy-execution safety pattern (hash pre/post, exclusive create, audit log, cancellation/resume)
- `fotoorganizer/classification/advisor.py` (read in full) — existing Advisor implementation: no retry/backoff, no cost tracking, single global opt-in check
- `.planning/codebase/CONCERNS.md` — existing tech debt: no boot-time reconciliation for `OperationPlan.EXECUTANDO`
- exiftool write mechanics (safe temp-file + rename, `-overwrite_original` vs. default backup behavior) — MEDIUM confidence, WebSearch verified against exiftool documentation/changelog and man page. [ExifTool man page](https://linux.die.net/man/1/exiftool), [Writing and Modifying Metadata (DeepWiki)](https://deepwiki.com/exiftool/exiftool/4.2-writing-and-modifying-metadata)
- CR3/HEIC write support history and known corruption issues — MEDIUM confidence, single-source WebSearch (ExifTool version history) plus a GitHub issue citation. [ExifTool Version History](https://exiftool.sourceforge.net/history.html), [HEIC images corrupted when writing tags — exiftool/exiftool#313](https://github.com/exiftool/exiftool/issues/313)
- POSIX advisory locking on macOS (no mandatory locking; atomic rename as the standard safe-write pattern) — MEDIUM confidence, WebSearch verified against Apple Developer Forums discussion. [File exclusive access on macOS — Apple Developer Forums](https://developer.apple.com/forums/thread/709905)

---
*Pitfalls research for: Foto Organizer v2.0 (7-feature milestone on an existing local-first macOS photo cataloging app)*
*Researched: 2026-08-18*
