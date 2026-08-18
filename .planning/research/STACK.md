# Stack Research

**Domain:** EXIF write (location-only), GenAI folder classification, confidence rollup — additions to an already-shipped stack
**Researched:** 2026-08-18
**Confidence:** MEDIUM-HIGH (exiftool write mechanics: HIGH, documented + matches existing D-026/D-027 tool choice; Anthropic API cost levers: MEDIUM, verified against current docs but pricing/behavior changes fast; confidence rollup: HIGH, no new dependency)

No new core framework is being introduced. This document only covers the **delta** needed for milestone v2.0 features 1, 2, 5 and 6. Everything else in the existing stack (Python 3.12+, SQLAlchemy 2, FastAPI 127.0.0.1, React/Vite/TS/Tailwind) is unchanged and out of scope here.

## Recommended Stack

### Core additions

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `exiftool` CLI (already a runtime dependency) | ≥13.00 (current stable 13.53, Mar 2026) | Write GPS lat/long + IPTC/XMP city/country to the original file | Already the project's sole metadata authority (D-026/D-027, 386 tags read vs 8 from libraw). Writing with the same tool that reads avoids a second parser disagreeing with the first about tag precedence. No new binary dependency — `shutil.which("exiftool")` already gated at read time. |
| `anthropic` Python SDK | ≥0.116 (already pinned in `pyproject.toml[llm]`) | Folder-name → city/event classification call | Same SDK, same credential path, same opt-in gate as `ClassificationAdvisor`. No version bump required — `output_config.format=json_schema` structured outputs already in use in `advisor.py` and already validated at ≥0.116. |

No new Python packages need to be added to `pyproject.toml` for any of the four features. This is the headline finding: **feature 1 is a CLI-invocation pattern change in `metadata/`, not a new library; feature 2 is a new prompt/schema on the existing `llm` extra; features 5 and 6 are SQL + Python, no dependency at all.**

### Supporting patterns (not libraries)

| Pattern | Purpose | When to Use |
|---------|---------|-------------|
| Python-side emptiness check, not `exiftool -if` | Decide per-field, independently, which of GPS/city/country is actually empty, before ever shelling out | The pre-write `extract()` call (already needed for the verification diff, see below) already tells you in Python which fields are empty. Build the exiftool arg list from that — pass `-GPSLatitude=...` only if GPS was empty, `-City=...` only if city was empty, in one invocation with only the confirmed-empty tags. **Do not** chain multiple `-if` conditions in a single exiftool call to gate independent fields: exiftool ANDs all `-if` conditions across the *whole file*, so `-if 'not $GPSLatitude' ... -if 'not $City' ...` in one command means a file with GPS already present but city empty (the catalog's common mixed state — GPS is rare/recent, city from folder is abundant) fails the first condition and the file is skipped entirely, silently dropping the city write it should have made. `-if` is still useful as defense-in-depth against the TOCTOU window between the Python check and the exiftool call, but only ever for a single field per invocation, never combined across fields. |
| exiftool's default backup (`<file>_original`), i.e. **do NOT pass `-overwrite_original`** | Atomicity + built-in rollback artifact | exiftool always writes to a temp file and renames over the target — this is already atomic at the filesystem level. Keeping the default backup gives a second, independent proof that the pristine original survives, on top of the app's own hash discipline. Given invariant 8 ("nothing that could be the real reference is ever deleted"), the `_original` file should be treated as a second copy of the original, not a scratch file to clean up — see Integration Notes. |
| Full-tag diff before/after (reuse `ExifToolExtractor.extract()`), not just a file hash | Verification step comparable to `operations/executor.py`'s hash_pre/hash_pos, adapted for an intentional mutation | A whole-file hash is useless here — the write is *supposed* to change the file. What must be proven is "only the intended fields changed, nothing else". Call `extract()` before and after the write and diff the two `MediaMetadata` (+ raw `extras`) — assert every non-location tag is byte-identical and every location tag went from empty to the written value. This is the write-path equivalent of hash verification and slots into the same `AuditLog` table used by `operations/`. |
| `anthropic.messages.batches.create` (Message Batches API) | Bulk folder→city/event classification at import/catalog scale | The advisor today is called interactively, one cluster at a time. Folder classification for feature 2 is closer to a catalog-wide sweep (hundreds–thousands of folders) — a natural fit for async batch submission with 50% lower cost and a poll-for-completion progress bar, which also matches the "cost visible per session" requirement more literally (one batch = one visible bill, not N interleaved calls). |
| `cache_control: {"type": "ephemeral"}` on the system block | Prompt caching for repeated system prompt across many folder classifications | Only pays off if the cached block is ≥1,024 tokens (Sonnet and Haiku share this floor; Opus needs 2,048–4,096) — see Integration Notes, this is a real gate, not a nicety. |

## Installation

No `pip install` changes. Confirm the exiftool binary meets the version floor:

```bash
exiftool -ver   # want >= 13.00; current stable is 13.53 (2026-03-19)
brew upgrade exiftool   # if below floor
```

`pyproject.toml` is unchanged — `anthropic>=0.116` under `[project.optional-dependencies].llm` already covers feature 2.

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|--------------------------|
| exiftool CLI for EXIF/IPTC/XMP write | `pyexiv2` (libexiv2 bindings) | Never here. It writes EXIF/XMP fine but has weaker IPTC support and, critically, would be a *second* metadata engine disagreeing with the exiftool-derived read path on tag precedence and group mapping. The project already paid the cost of standardizing on exiftool (D-026) — a second library for writes reopens that exact problem for no measured gain. |
| exiftool CLI for EXIF/IPTC/XMP write | `piexif` (pure Python, EXIF-only) | Never here. No IPTC/XMP support at all, so city/country (feature 1's second half) would need a separate library anyway. Also weaker RAW/HEIC coverage than exiftool, which is why the pure-Python fallback already exists as a *fallback*, not the primary. |
| `anthropic` SDK, Sonnet 5, existing `ClassificationAdvisor` pattern | Keep folder→city/event on the same Sonnet 5 tier as the multi-category advisor | Reasonable default: reuses a decision already validated against 104 real clusters (D-059/D-060), same credential/opt-in/audit path, one model to reason about in support. Do **not** silently switch to Haiku 4.5 without measuring — see Integration Notes for why the D-059/D-060 method (not its Sonnet-vs-Haiku *conclusion*) should be reused here. |
| Message Batches API for bulk folder classification | Synchronous per-folder calls (current advisor pattern) | Use synchronous calls only if folder classification stays interactive/on-demand (user clicks "classify this folder now"). If it runs as a catalog sweep at import time (which "custo visível por sessão" implies), batch is strictly better: half the cost, and the async job model matches the existing scanner's checkpoint/pause-resume UX language already used elsewhere in the app. |
| SQL aggregation via SQLAlchemy (existing) | `pandas` for the confidence health index rollup | Never — 400k rows, single `GROUP BY`/`COUNT`/`CASE WHEN` query is sub-second in SQLite; pandas would add a dependency, a memory copy, and zero capability the SQL doesn't already have. Confirmed: **no new dependency for feature 5's rollup.** |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|--------------|
| `-overwrite_original` on exiftool writes | Deletes the only pristine copy exiftool itself would have kept; this is a self-inflicted violation of invariant 8 ("nunca sobrescrever", "nada que possa ser a referência real é apagado") for zero benefit — the app already has disk headroom concerns addressed elsewhere, not here | Default backup behavior (`<file>_original`); decide retention policy explicitly (see Integration Notes), don't disable the safety net to save a few KB |
| A second metadata-writing library (pyexiv2, piexif, or hand-rolled binary TIFF/IPTC patching) | Would reintroduce the exact "two extractors disagree" failure mode D-026/D-027 already solved for reads | exiftool, same tool as the read path |
| Switching the folder-classification model to Haiku 4.5 on cost grounds without a measurement pass | D-059/D-060 exists specifically because "cheaper model" was tried and empirically failed (Haiku asserted categories in 19/31 disagreements where Opus correctly abstained) — the failure mode was hallucinated confidence on sparse metadata, and folder-name-only input is *sparser*, not richer, than the multi-signal cluster the advisor sees | Reuse the D-059/D-060 *method* (small real sample, compare abstention/hallucination rate, not just token cost) before picking a tier for feature 2 |
| Wiring `cache_control` onto a short (<1,024 token) system prompt | Below the token floor the cache write/read overhead isn't recovered — this is a hard gate in the API, not a soft tradeoff (confirmed: Sonnet/Haiku floor is 1,024 tokens, Opus 2,048–4,096) | Either pad the cached block deliberately (e.g. a static gazetteer/few-shot block) past the floor, or skip caching and rely on Batch API's 50% discount instead — don't assume caching "just helps" |

## Stack Patterns by Variant

**If feature 1 (EXIF location write) ships:**
- Extend `metadata/` with a writer counterpart to `ExifToolExtractor` (e.g. `metadata/exiftool_writer.py`), reusing the same `-stay_open` persistent-process infra is *not* necessary — write volume is bounded by a user-reviewed plan (dozens–low thousands per approval), not a full scan, so a plain per-file `subprocess.run([...], shell=False)` call is simpler and easier to audit than threading writes through the shared read-only `_stay_open` process.
- Model this as `operations/`-adjacent: `OperationPlan`/`OperationItem`-style dry-run → approve → execute → audit-log, but the "item" is a (file, field, value) triple instead of a (origem, destino) copy. The dry-run step's job is specifically to re-check "still empty?" at execution time, because the field could have been filled by another path (manual edit, another tool) between plan creation and execution — same TOCTOU concern the existing dry-run already handles for "destination now exists".
- Verification step differs from `operations/executor.py`'s SHA-256 file-hash equality check: use full-tag diff (see Supporting Patterns above), not file-hash equality, since the write is an intentional mutation.

**If feature 2 (GenAI folder→city/event) ships as a catalog sweep:**
- Use Message Batches, poll status, surface progress via the same FastAPI progress-endpoint pattern feature 4 (import gauge) already needs — one polling mechanism serves both features.
- Keep the schema minimal and `additionalProperties: false` like the existing `_SCHEMA` in `advisor.py` — structured outputs constrain tokens directly, so a smaller schema is also a smaller/cheaper response, independent of the caching question.

**If feature 2 ships as on-demand/interactive instead:**
- Reuse `ClaudeAdvisor` almost verbatim: new `ClusterInfo`-equivalent dataclass (folder name + maybe sibling folder names for context), new `_SCHEMA`, new `_SYSTEM`, same `thinking={"type": "disabled"}` reasoning (this is an even more constrained extraction task than the current advisor's 3-way categorization — no case for extended thinking here either).

**If features 5/6 (confidence axis, health index, generalized corroboration) ship:**
- No stack change. Feature 5's rollup is a SQLAlchemy aggregate query against the existing `Evidence`/`evidence` table; feature 6 generalizes `grouping/correlacao.py`'s D-074 two-anchor-confrontation logic to other evidence types — this is an algorithm change inside `classification/`/`grouping/`, not a new dependency. Flag for the architecture/pitfalls researchers: D-074's "confront before AND after, don't just pick nearest" pattern is currently GPS-shaped (spatial interpolation with a radius-of-uncertainty formula); date/time and city/country inheritance don't have the same continuous-interpolation structure, so "generalize" likely means "same *epistemics* (require agreement between independent anchors before granting confidence), different math per evidence type" rather than one shared function — worth flagging as non-trivial for the roadmap, not a mechanical refactor.

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|------------------|-------|
| `exiftool` ≥13.00 | macOS (Homebrew build already assumed by existing read path) | No version-specific write-syntax changes found between 12.x and 13.x for GPS/IPTC/XMP write args used here; floor is conservative, not a hard requirement discovered in research. |
| `anthropic` ≥0.116 | Structured outputs (`output_config.format=json_schema`), Message Batches API | Both already available at the pinned floor per the SDK version already in use for the existing advisor. If batching is adopted, verify `client.messages.batches.create` + `cache_control` combination empirically before relying on stacked discounts — one open upstream SDK issue reported friction between Batch API and `cache_control` on some request shapes; treat the batch 50% discount as the reliable lever and caching as a bonus to verify, not assume. |

## Integration Notes (answers to the specific questions)

**(a) EXIF write pattern for feature 1.**
No new library. The correct guard for "only write empty fields" is **Python-side, not `exiftool -if`**: call `ExifToolExtractor.extract()` (already exists) before the write, inspect which of GPS/city/country are actually empty, and build the exiftool argument list only from the fields confirmed empty. This matters because of a real bug in the naive version of this pattern: chaining `-if 'not $GPSLatitude' ... -if 'not $City' ...` in a single exiftool invocation does **not** gate each field independently — exiftool ANDs all `-if` conditions across the whole file, so a file with GPS already present but city empty (the catalog's documented common case: GPS is rare/recent, folder-derived city is abundant) fails the GPS condition and the *entire command is skipped*, silently dropping the city write that should have happened. The pre-write `extract()` call needed for verification (below) already gives you the emptiness answer in Python before you ever shell out — use it as the primary guard, and keep `-if` only as single-field, single-invocation defense-in-depth against the TOCTOU window between the Python check and the exiftool call.

For the GPS write itself, write `GPSLatitude`/`GPSLongitude` **and** explicitly set `GPSLatitudeRef`/`GPSLongitudeRef` (`N`/`S`, `E`/`W`) rather than relying on exiftool to auto-derive the ref from a signed decimal — research found this auto-derivation referenced in community sources but not confirmed in exiftool's own docs, so treat it as unverified (LOW confidence) and just write both tags explicitly; it costs nothing and removes the ambiguity.

Example shape (values already confirmed empty in Python, only those tags passed): `exiftool -GPSLatitude=<abs decimal> -GPSLatitudeRef=<N|S> -GPSLongitude=<abs decimal> -GPSLongitudeRef=<E|W> -City=... -Country=... <path>`, invoked per-file via `subprocess.run` (list args, no shell — invariant 5), with the default `<file>_original` backup left in place (no `-overwrite_original`). Read the current app code first: `metadata/exiftool.py` already knows how to read `Composite:GPSLatitude`/`Composite:GPSLongitude` and the IPTC/XMP groups it cares about (`_GRUPOS` dict) — the writer should target the *same* tag names it reads, so a value written today is read back identically by the existing extractor tomorrow (round-trip symmetry, verifiable by calling `extract()` before/after, see Supporting Patterns). Verification is a full-tag diff, not a file hash, because this is the one write path in the app where the file is *supposed* to change — reuse `AuditLog` (already imported by `operations/executor.py`) for the record, don't invent a parallel audit mechanism.

**(b) Anthropic API pattern for feature 2.**
Reuse the exact operating model already proven by `ClassificationAdvisor`/`ClaudeAdvisor` (opt-in gate, metadata-only payload, `thinking={"type": "disabled"}`, `output_config.format=json_schema`, `additionalProperties: false`, refusal handling, never raises on failure — returns `None`). Two things are genuinely new to decide, not reuse: model tier and call shape.
- **Model tier:** default to Sonnet 5 for consistency and because D-059/D-060's failure mode (cheap model hallucinating a category from thin evidence) applies at least as strongly here — folder name alone is thinner evidence than the full cluster the existing advisor sees. If Haiku 4.5 is considered for cost (it is ~2x cheaper on input, cheaper still relative to Sonnet through Aug 31, 2026 promotional pricing), re-run the D-059/D-060 measurement method (small real sample, count abstention-vs-hallucination, not raw agreement rate) before switching — don't infer from the old Haiku-vs-Sonnet result on a *different* task.
- **Call shape:** if feature 2 runs as a catalog-wide sweep (all folders at import time), use the Message Batches API (50% discount, async, fits a progress-bar UX). If it stays interactive/on-demand per folder, keep synchronous calls like today. Prompt caching (`cache_control` on the system block) only activates above a 1,024-token floor for Sonnet/Haiku — the current `_SYSTEM` string in `advisor.py` is far below that, so caching is not a free win; it only becomes worth wiring if the new system prompt grows (e.g., a static list of known place names/aliases embedded for grounding) past the floor.

**(c) Health index rollup for feature 5.**
No new dependency. This is a `SELECT` with `GROUP BY`/aggregate functions over the existing `evidence`/confidence columns, run through the existing SQLAlchemy 2 session — same pattern as any other repository query in `repositories/`. At ~400k catalog rows this is sub-second in SQLite (WAL mode, already the project's baseline). Confirmed: **do not add pandas, numpy-for-stats, or any analytics library for this.**

## Sources

- ExifTool official GPS tag reference — https://exiftool.sourceforge.net/TagNames/GPS.html (HIGH — GPSLatitude/GPSLatitudeRef/GPSLongitude/GPSLongitudeRef/GPSAltitude write requirements)
- ExifTool GitHub source (GPS.pm) — https://github.com/exiftool/exiftool/blob/master/lib/Image/ExifTool/GPS.pm (HIGH — confirms tag set)
- ExifTool forum, GPS coordinate writing threads — https://exiftool.org/forum/index.php?topic=12620.0, https://exiftool.org/forum/index.php?topic=9639.0 (MEDIUM — community-verified conditional write and signed-decimal behavior)
- ExifTool `-overwrite_original`/backup behavior — Linux man page (https://linux.die.net/man/1/exiftool) and community summaries (MEDIUM — consistent across sources: atomic rename, default `_original` backup unless disabled)
- Claude Platform Docs, Prompt caching — https://platform.claude.com/docs/en/build-with-claude/prompt-caching (HIGH — official, confirms 1,024-token floor for Sonnet/Haiku, 2,048–4,096 for Opus, 5–10 min TTL up to 1h)
- Claude Platform Docs, Batch processing — https://platform.claude.com/docs/en/build-with-claude/batch-processing (HIGH — official, confirms 50% discount, async model)
- anthropic-sdk-python GitHub issue #689 ("Batch API does not support cache_control") — https://github.com/anthropics/anthropic-sdk-python/issues/689 (LOW-MEDIUM — single GitHub issue, flagged as a risk to verify empirically, not treated as settled)
- Pricing aggregators (finout.io, cloudzero.com, pricepertoken.com) cross-checked for Haiku 4.5 vs Sonnet 5 vs Opus 5 relative pricing (LOW-MEDIUM — third-party aggregators, not Anthropic's own pricing page; directionally consistent across three independent sources, treat exact numbers as approximate and re-verify against `anthropic.com/pricing` before budgeting)
- Existing codebase, read directly: `fotoorganizer/metadata/exiftool.py`, `fotoorganizer/operations/executor.py`, `fotoorganizer/classification/advisor.py` (HIGH — ground truth for integration points, not a research source but the basis for every "reuse X" recommendation above)

---
*Stack research for: Foto Organizer v2.0 — EXIF write, GenAI folder classification, confidence health index*
*Researched: 2026-08-18*
