# Phase 6: Escrita EXIF de localização - Research

**Researched:** 2026-08-18
**Domain:** In-place EXIF/IPTC/XMP write (macOS, exiftool CLI) + XMP sidecar fallback, for a
shipped local-first photo cataloger
**Confidence:** HIGH — exiftool write mechanics and tag-name choices below were verified
empirically against a live `exiftool 13.55` binary and this repo's own code in this session
(not just cited from docs). Sync-folder path prefixes were verified against this machine's
actual `~/Library/Mobile Documents` and `~/Library/CloudStorage`. See per-claim tags below.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Dono aprova o plano dry-run inteiro de uma vez (mesmo padrão de `Operations.tsx`
  para cópia), não arquivo por arquivo.
- **D-02:** Dentro do lote aprovado, o dono pode desmarcar itens pontuais antes de confirmar
  (checkbox por linha, mesmo padrão de review de sugestões) — não é tudo-ou-nada.
- **D-03:** Antes de fechar o escopo de formato, roda um teste empírico de escrita contra cópia
  descartável real cobrindo **todo formato RAW/proprietário que aparecer no acervo** (não só
  CR3/HEIC citados na pesquisa) — formato que passa limpo entra no escopo da fase, formato que
  não passa fica de fora, registrado como decisão medida (mesmo padrão de D-026/D-074).
- **D-04:** Critério de "passou limpo": diff completo de tags antes/depois (só as tags de
  localização esperadas mudaram) **e** confirmação de que o arquivo ainda abre normalmente
  depois (ex.: `exiftool -validate` ou equivalente) — diff de tags sozinho não pega corrupção
  estrutural fora das tags.
- **D-05:** Arquivo com formato reprovado no teste (ou já sabidamente sem suporte) aparece no
  plano dry-run como linha explícita "formato não suportado" com o motivo — nunca desaparece
  silenciosamente da lista.
- **D-06:** Arquivo reprovado ganha oferta de sidecar XMP como alternativa no mesmo plano
  (D-075 mantém XMP disponível) — o dono decide se quer esse caminho para os casos que EXIF
  direto não cobre. Isto expande o entregável da Fase 6 para incluir escrita de sidecar XMP
  como fallback, não só EXIF direto.
- **D-07:** Sistema detecta se o arquivo está dentro de uma pasta sincronizada (iCloud Drive,
  Dropbox, etc.) e marca isso explicitamente no plano dry-run com aviso do risco
  (dessincronização silenciosa). Dono decide incluir ou desmarcar via o mesmo checkbox de D-02
  — não é bloqueio automático nem escrita silenciosa sem aviso.
- **D-08:** Cada arquivo tenta os 3 campos (GPS lat/long, cidade, país) juntos, no mesmo
  plano/execução — sem seleção de campo por sessão.

### Claude's Discretion

- Mecanismo exato de detecção de "pasta sincronizada" (checar `.icloud`/atributos de arquivo,
  caminho conhecido do iCloud Drive, presença de `.dropbox` etc.) — resolvido abaixo em
  "Sync-Folder Detection".
- Formato exato do teste empírico de escrita por formato (script standalone vs. parte do plano
  da fase) — resolvido abaixo em "Empirical Format-Write Test Design".

### Deferred Ideas (OUT OF SCOPE)

None — discussão ficou dentro do escopo da fase.

### Abordagem travada (ROADMAP.md, não re-derivar)

- Módulo **novo e próprio** (`fotoorganizer/exif_write/`), **não** estende
  `operations/executor.py`.
- Verificação é diff completo de tags antes/depois, não hash do arquivo inteiro (refinamento de
  D-075: hash vira fato de auditoria, não critério de aprovação).
- Escrita só após plano dry-run aprovado explicitamente.
- Audit log registra falha parcial, não só sucesso/erro binário.
- Pré-condição "campo vazio" é o mecanismo de recuperação de crash (reexecutar é idempotente).

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| EXIF-01 | Dono aprova plano dry-run listando, por arquivo, campos vazios que seriam preenchidos, antes de qualquer escrita | `operations/executor.py`'s `dry_run()`/`DryRunObrigatorio` pattern is the structural template (Architecture Patterns below); the new plan model computes "empty?" via `MetadataExtractor.extract()`, not `exiftool -if` |
| EXIF-02 | Escreve GPS lat/long, cidade e país somente quando vazio; nunca sobrescreve | Verified empirically: exiftool has no way to gate this itself reliably across independent fields (`-if` ANDs across the whole file — see Common Pitfalls); emptiness check must be Python-side using the same `extract()` call already in the codebase |
| EXIF-03 | Cada escrita verificada por diff completo de tags (não hash de arquivo inteiro) antes/depois, registrada em audit log incluindo falha parcial | Verified empirically that exiftool write is atomic **per file** but NOT atomic **per tag within one invocation** — a single malformed tag silently no-ops while sibling tags still write and the process still exits 0 (Common Pitfalls, Pitfall 2). Diff-based detection is the only reliable partial-failure signal. `AuditLog` reuse has a real FK constraint gotcha (Common Pitfalls, Pitfall 5) that must be worked around. |
| EXIF-04 | Nunca escreve campos fora de localização | Explicit tag allowlist in the writer (`GPSLatitude/GPSLatitudeRef/GPSLongitude/GPSLongitudeRef`, `IPTC:City`+`XMP:City`, `IPTC:Country-PrimaryLocationName`+`XMP:Country`) — enforce at code level, not by convention (PITFALLS.md's own "Security Mistakes" table already flags this) |
| EXIF-05 | Formato reprovado no teste empírico aparece como "não suportado" com motivo, ganha oferta de sidecar XMP no mesmo plano | Empirical Format-Write Test Design + Sidecar XMP Writer sections below; **critical scoping finding**: the real, currently-scanned catalog has zero CR3/HEIC files today (Common Pitfalls, Pitfall 8) — this materially affects what D-03's test can actually validate this milestone |

</phase_requirements>

## Summary

No new library, no new pip package, no new binary dependency — `exiftool` (already the sole
metadata-read authority, D-026/D-027) does the entire write job, for both direct EXIF/IPTC/XMP
mutation and the new XMP-sidecar fallback (D-06), via the exact same command shape aimed at a
different target path. The correct architecture is the one the milestone-level research already
locked in: a new, narrow module (`fotoorganizer/exif_write/`) structurally parallel to
`operations/` but not inheriting from it, because in-place mutation has no equivalent to the
copy executor's exclusive-create safety trick.

This phase-level research closes the three things the milestone research left as discretion,
**all verified empirically against a live exiftool binary in this session, not just cited**:

1. **Sync-folder detection** is a pure path-prefix check on the *resolved* (symlink-followed)
   path against two known roots — `~/Library/Mobile Documents/` (iCloud Drive, and confirmed
   locally to also catch the "Desktop & Documents Folders" redirect case) and
   `~/Library/CloudStorage/` (the unified File Provider root that modern OneDrive, Google
   Drive, Box, and current-version Dropbox all use since macOS 12.3) — plus a legacy
   `~/Dropbox`/`~/.dropbox/info.json` fallback for pre-File-Provider Dropbox installs. Zero
   subprocess calls, zero new dependency, O(1) per file.
2. **Empirical format-write test** follows the exact shape of `scripts/calibrar_raio_incerteza.py`
   (standalone, read-mostly script with a clear docstring contract) but must write to disposable
   copies rather than stay read-only. The diff-based "passou limpo" check needs a documented
   **allowlist of scaffolding tags** (`GPS:GPSVersionID`, `IPTC:ApplicationRecordVersion`,
   `File:CurrentIPTCDigest`, `XMP-x:XMPToolkit`, and `Composite:*` derived duplicates) that
   exiftool creates as an unavoidable side effect of establishing a *brand new* GPS/IPTC/XMP
   block on a file that never had one — verified empirically to be the **normal case**, not an
   edge case, for the exact population this phase targets (files with no prior location data).
3. **Sidecar XMP writer** needs no separate Protocol or class: `exiftool <args> photo.xmp`
   (instead of `exiftool <args> photo.jpg`) creates a standalone, spec-conformant XMP sidecar in
   one invocation, verified working with the identical GPS/City/Country argument list used for
   the direct-write path. One `MetadataWriter` method with a `destino: Path` parameter covers
   both cases — a symmetrical `MetadataWriter` Protocol mirroring `MetadataExtractor` is
   over-engineering here; a single free function or single-method class is enough.

**Primary recommendation:** build `fotoorganizer/exif_write/` around one `ExifToolWriter` class
with a single `escrever(origem: Path, campos: dict, destino: Path | None = None) -> ...` method
(destino defaults to origem for direct write, or a `.xmp` sidecar path for D-06's fallback);
gate every write behind a Python-side emptiness check computed from the existing
`MetadataExtractor.extract()`, validate GPS bounds and non-empty strings in Python before ever
shelling out (exiftool does not validate coordinate ranges — verified, see Pitfall 1), and treat
the pre/post full-tag diff (with the scaffolding-tag allowlist) as the *only* trustworthy
success/failure signal — not exiftool's exit code or "N files updated" message, which are
provably insufficient for the partial-failure case EXIF-03 requires.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| EXIF/IPTC/XMP direct write (mutate original) | Backend domain (`fotoorganizer/exif_write/`) | — | New bounded write surface, isolated from `operations/` per locked architecture decision |
| XMP sidecar write (D-06 fallback) | Backend domain (same module, same writer class) | — | Same exiftool invocation shape, different target path — not a separate subsystem |
| Sync-folder detection (D-07) | Backend domain (`exif_write/` or `security/`) | — | Pure filesystem/path logic, no I/O beyond `Path.resolve()` + `os.path` checks; belongs beside path-safety helpers already in `security/paths.py` |
| Dry-run plan computation (emptiness check, GPS/string validation, format-support lookup) | Backend domain | — | Mirrors `operations/executor.py::dry_run()` — must run before any write is possible |
| Plan approval + per-row checkbox + "unsupported format" badge (D-01/D-02/D-05/D-06) | Frontend (`webapp/src/components/`) | Backend Server (new `/api/exif/*` endpoints) | UI surface explicitly required (ROADMAP.md "UI hint: yes"); **no existing checkbox-per-row component exists in this codebase today** — verified by grep, see Common Pitfalls Pitfall 6 |
| Long-running execution + progress | Backend Server (`server/jobs.py::JobManager`) | Frontend (`StatusBar.tsx`-style polling) | Existing `JobManager` pattern already used for scan/copy jobs — reuse, don't reinvent |
| Audit trail (success + partial failure) | Database/Storage (SQLite, `AuditLog`) | Backend domain | Reuse `AuditLog` table, but **not** its `plan_id` FK column for exif-write plans — see Pitfall 5 |
| Empirical per-format write test (D-03) | Standalone script (`scripts/`) | — | Offline, one-time-per-catalog-change measurement tool, same category as `calibrar_raio_incerteza.py` — not runtime app code |

## Standard Stack

### Core

No new packages. Confirmed via direct inspection of `pyproject.toml` and a live install on this
machine:

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `exiftool` CLI (already a runtime dependency, D-026/D-027) | ≥13.00; **13.55 confirmed installed and tested in this session** `[VERIFIED: local binary, exiftool -ver]` | Write GPS/IPTC/XMP to the original AND write standalone `.xmp` sidecars | Same tool the read path already trusts (`ExifToolExtractor`); a second write library would reopen the "two engines disagree" problem D-026 already solved for reads (STACK.md, unchanged from milestone research) |

No `pyproject.toml` change needed for this phase. `Pillow`/`pillow-heif`/`rawpy`/`exifread`
(already dependencies, used by `PurePythonExtractor`) are reusable as the "does it still parse"
structural re-check called for by D-04 (see Code Examples), no new install.

### Supporting patterns (not libraries)

| Pattern | Purpose | When to Use |
|---------|---------|-------------|
| One short-lived `exiftool` process per write (`subprocess.run`, list args, no `shell=True`) | Avoid serializing against the shared `-stay_open` reader process's lock | Every write call — write volume is a reviewed, bounded plan (dozens–low thousands), not a full scan; per-file spawn cost (~200ms) is acceptable here (unchanged from milestone STACK.md) |
| Explicit-group tag names for city/country (`-IPTC:City` **and** `-XMP:City`, `-IPTC:Country-PrimaryLocationName` **and** `-XMP:Country`) | Deterministic, tool-version-independent write target | Always — bare `-City`/`-Country` (no group prefix) resolve to **different, asymmetric default groups** (verified below), which is easy to get wrong if assumed symmetric |
| Explicit `GPSLatitudeRef`/`GPSLongitudeRef` alongside `GPSLatitude`/`GPSLongitude` | Removes ambiguity around auto-derivation from signed decimal | Always — milestone STACK.md already flagged the auto-derivation as unverified; this session did not need to rely on it because explicit refs were used throughout |
| Python-side coordinate/string validation before shelling out | exiftool does **not** validate GPS ranges | Always — verified empirically that `-GPSLatitude=999` is accepted silently (no warning, no error, exit 0); the app is the only validation boundary here |
| Full-tag diff (before/after `extract()`) as the sole pass/fail signal for a write, with a documented scaffolding-tag allowlist | exiftool's exit code / "N files updated" message is provably insufficient for partial-per-tag failure detection | Every write, both in the empirical format test (D-03/D-04) and in production execution (EXIF-03) |

**Installation:** none — verify the already-installed binary meets the floor:
```bash
exiftool -ver   # confirmed 13.55 on this machine, 2026-08-18
```

### Alternatives Considered

Unchanged from milestone STACK.md — `pyexiv2`/`piexif`/hand-rolled binary patching were already
ruled out there for the same "second engine disagrees with the first" reason this phase's
findings reinforce (exiftool's own tag-group resolution is nuanced enough — see the
City/Country asymmetry finding — that a second library would only add a second source of
disagreement, not remove one).

## Package Legitimacy Audit

**Not applicable this phase.** No new external packages are installed — `exiftool` is an
already-vetted (D-026/D-027) runtime dependency, and no new Python package is added to
`pyproject.toml`. `slopcheck`/registry verification is skipped because there is nothing new to
verify.

## Architecture Patterns

### System Architecture Diagram

```
Dono (webapp) ──HTTP, 127.0.0.1──> server/app.py
                                     │  POST /api/exif/plano        (build plan: scan candidates,
                                     │  POST /api/exif/dry-run       compute empty fields, run
                                     │  POST /api/exif/executar      format-support lookup)
                                     ▼
                          fotoorganizer/exif_write/  (NEW module, parallel to operations/)
                          ┌─────────────────────────────────────────────────────────────┐
                          │ 1. Planner: for each media_id, call existing                 │
                          │    MetadataExtractor.extract() (read path, unchanged) →      │
                          │    which of GPS/city/country are empty?                      │
                          │ 2. Sync-folder check: Path.resolve() prefix match against     │
                          │    known cloud-sync roots (pure filesystem, no I/O)           │
                          │ 3. Format-support lookup: extension in a measured allowlist   │
                          │    (from D-03's script output, stored in code or config)      │
                          │    → not supported: mark "formato não suportado", offer       │
                          │    sidecar path (destino = photo.<ext>.xmp)                   │
                          │ 4. Dry-run: persist ExifWritePlan + ExifWriteItem rows,        │
                          │    nothing written to disk yet (EXIF-01)                      │
                          │ 5. Execute (only after explicit approval + per-row checkbox    │
                          │    deselection, D-01/D-02): ExifToolWriter.escrever() per item │
                          │    — re-check emptiness (TOCTOU), validate GPS bounds in       │
                          │    Python, shell out once per file with only the confirmed-    │
                          │    empty tags, then re-extract() and diff full tag dump        │
                          │    against the scaffolding-tag allowlist (EXIF-03)             │
                          └─────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
                          security/paths.py (reused, unchanged) · security/hashing.py (hash_pre
                          as audit fact, NOT the pass/fail criterion — diff of tags is)
                                     │
                                     ▼
                          AuditLog (existing model) — plan_id left NULL for exif-write rows,
                          exif plan/item id carried inside `detalhe` JSON instead (see Pitfall 5)
                                     │
                                     ▼
                          Original file (mutated in place) — or photo.<ext>.xmp (new sidecar,
                          D-06, same writer, different destino)
```

### Recommended Project Structure

```
fotoorganizer/
  exif_write/
    __init__.py
    writer.py        # ExifToolWriter — single class, escrever(origem, campos, destino=None)
    planner.py        # builds ExifWritePlan/ExifWriteItem rows, emptiness + sync + format checks
    executor.py        # dry_run()/executar(), mirrors operations/executor.py's shape, not its class
    sync_detect.py     # is_synced_folder(path) -> str | None  (D-07)
  models/
    exif_write.py       # ExifWritePlan, ExifWriteItem (new tables, new Alembic migration)
scripts/
  testar_escrita_exif.py   # D-03's empirical per-format test (see below)
```

### Pattern 1: Writer method shape (covers both direct write AND sidecar, D-06)

**What:** one method, one exiftool invocation shape, target path is the only variable.
**When to use:** every write in this phase — direct EXIF/IPTC/XMP mutation and XMP sidecar
creation are the *same operation* aimed at a different `destino`.
**Example (verified working in this session, exiftool 13.55):**
```python
# Source: verified locally, this session — subprocess.run, list args, no shell=True (invariant 5)
def escrever(origem: Path, campos: dict, destino: Path | None = None) -> subprocess.CompletedProcess:
    alvo = destino or origem
    args = ["exiftool"]
    if "gps" in campos:
        lat, lon = campos["gps"]
        args += [
            f"-GPSLatitude={abs(lat)}", f"-GPSLatitudeRef={'N' if lat >= 0 else 'S'}",
            f"-GPSLongitude={abs(lon)}", f"-GPSLongitudeRef={'E' if lon >= 0 else 'W'}",
        ]
    if "cidade" in campos:
        args += [f"-IPTC:City={campos['cidade']}", f"-XMP:City={campos['cidade']}"]
    if "pais" in campos:
        args += [
            f"-IPTC:Country-PrimaryLocationName={campos['pais']}",
            f"-XMP:Country={campos['pais']}",
        ]
    args.append(str(alvo))
    # destino == origem: in-place mutation (default backup kept, see Pitfall 4)
    # destino != origem and destino.suffix == ".xmp": creates a standalone sidecar
    return subprocess.run(args, capture_output=True, text=True, check=False)
```
No `-overwrite_original` here — see Pitfall 4 for why, and for the explicit cleanup step that
should follow a *verified* success.

### Pattern 2: Diff-based verification with scaffolding-tag allowlist

**What:** the only reliable pass/fail signal for a write (see Pitfall 2).
**When to use:** every write, both in D-03's format test and in production `executar()`.
```python
# Source: verified locally, this session — full-tag diff via existing extractor
ANTES = extractor.extract(caminho)          # or raw exiftool -j -G1 -a dump, pre-write
# ... write happens ...
DEPOIS = extractor.extract(caminho)          # same call, post-write

TAGS_ESTRUTURAIS_ESPERADAS = {
    "GPS:GPSVersionID",             # exiftool always writes this when creating a new GPS IFD
    "IPTC:ApplicationRecordVersion",  # exiftool always writes this when creating a new IPTC block
    "File:CurrentIPTCDigest",         # IPTC block checksum, auto-managed by exiftool
    "XMP-x:XMPToolkit",               # identifies the writer, always set on new XMP packet
    # Composite:* are derived/read-only re-renderings of GPS tags, not independently written
}
# A tag not in TAGS_DE_LOCALIZACAO ∪ TAGS_ESTRUTURAIS_ESPERADAS that changed → FAIL, corruption
# suspected. File:FileSize / File:FileModifyDate / System:* also change unconditionally — expected.
```

### Pattern 3: Empirical Format-Write Test Design (D-03)

**What:** a standalone script mirroring `scripts/calibrar_raio_incerteza.py`'s shape (argparse,
direct sqlite3 `mode=ro` catalog read, dataclass-based results, a documented decision written to
`docs/DECISOES.md`) — but this one **writes**, so it must operate on disposable copies, never
the catalog or the real files.

**Shape:**
1. Query `catalog.db` (read-only, `sqlite3.connect(f"file:{db}?mode=ro", uri=True)`) grouped by
   file extension, sample N files per extension actually present (today: `.jpg`, `.cr2`, `.dng`,
   `.tif` — see Pitfall 8 for why this list is smaller than the milestone brief assumed).
2. For each sample: `shutil.copy2` to a scratch tmp dir (never touch the original — this script
   is the one place in the whole app that's allowed to write test data, but it still must not
   touch real files).
3. Dump full tags via `extract()` (or raw `exiftool -j -G1 -a`) — this is "antes".
4. Run the exact production `ExifToolWriter.escrever()` code path against the copy with
   synthetic-but-plausible GPS/city/country values.
5. Dump full tags again — "depois". Diff against `TAGS_DE_LOCALIZACAO ∪
   TAGS_ESTRUTURAIS_ESPERADAS` (Pattern 2). Any other change → format fails D-04's criterion.
6. Run `exiftool -validate -warning -error` **both before and after**, and compare the
   **delta** — not "zero warnings after" (verified: a synthetic/edge-case fixture can carry a
   pre-existing warning unrelated to this phase's write; the correct check is "no *new*
   warnings/errors appeared").
7. Optionally, re-parse via the app's own `MetadataExtractor.extract()` and assert
   dimensions/`DateTimeOriginal`/camera model are unchanged (PITFALLS.md's structural-integrity
   recommendation — cheap, already-available extra confidence, no new dependency).
8. Emit a per-extension pass/fail table; write the result as a new `docs/DECISOES.md` entry
   (same rigor as D-026/D-074): which extensions passed, which failed and why, what the write
   allowlist becomes.

**Explicitly not read-only** — unlike `calibrar_raio_incerteza.py`, this script's whole purpose
is to write to disposable copies. Its docstring must say so loudly, and it must never accept a
path inside the real catalog's source roots without copying first.

### Anti-Patterns to Avoid

- **Reusing `operations/executor.py`'s `_copiar_exclusivo` file-handling for the EXIF path** —
  wrong safety model entirely (copy-to-new-path vs. mutate-in-place). Already flagged at
  milestone level (PITFALLS.md Pitfall 1); still true, worth restating because it's the single
  most likely reflexive mistake given how much of this module's *shape* is copied from
  `operations/`.
- **Trusting exiftool's exit code / "N image files updated" stdout line as a success signal** —
  verified this session to be insufficient (see Pitfall 2). Always diff.
- **Writing bare `-City=`/`-Country=` and assuming both land in the same tag group** — verified
  asymmetric (see Code Examples / Pitfall 3).
- **Building a symmetrical `MetadataWriter` Protocol mirroring the multi-format `MetadataExtractor`
  Protocol** — over-engineered for this phase's actual scope (3 fields, one tool, one method).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| GPS/IPTC/XMP binary tag writing | Custom TIFF/IFD or IPTC-IIM byte patcher | `exiftool` CLI (already a dependency) | Same reasoning D-026 already established for reads — a hand-rolled writer would need to reimplement exiftool's own IFD-block-creation logic (which is exactly where the scaffolding-tag behavior comes from) with zero of exiftool's battle-testing |
| XMP sidecar file generation | Manual XML/RDF templating | `exiftool <args> file.xmp` | Verified working in one command this session — produces spec-conformant XMP (`x:xmpmeta`/`rdf:RDF` wrapper) with zero string-templating risk |
| "Does this file still open" structural check | Custom byte-level file validator | `exiftool -validate` **and/or** the app's own `MetadataExtractor.extract()` re-parse (Pillow/rawpy/pillow-heif already dependencies) | Both are already in the toolchain; a hand-rolled validator would need per-format knowledge exiftool/Pillow/rawpy already encode |
| Cloud-sync folder detection | Polling `NSMetadataQuery` via PyObjC, or parsing `.icloud` placeholder filenames | Path-prefix check on `Path.resolve()` against `~/Library/Mobile Documents/` and `~/Library/CloudStorage/` | The per-file "is it currently downloaded" signal is flaky and transient (verified this session — a file's dataless/materialized state changed *during* this research session from background activity); D-07 only needs "is this path inside a sync-managed folder", which is a stable, cheap, path-only fact |

**Key insight:** every piece of this phase that looks like it needs new tooling (writer,
sidecar generator, format validator, sync detector) is actually already covered by
already-installed tools (`exiftool`, Pillow/rawpy stack) or plain `pathlib`. The actual new work
is orchestration (plan/dry-run/audit model) and UI (checkbox-per-row, unsupported-format badge),
not metadata engineering.

## Common Pitfalls

### Pitfall 1: exiftool does not validate GPS coordinate ranges — the app is the only validation boundary

**What goes wrong:** Verified empirically this session: `exiftool -GPSLatitude=999
-GPSLatitudeRef=S <file>` succeeds silently — exit code 0, "1 image files updated", and the
file ends up with `GPS:GPSLatitude = 999 deg 0' 0.00"`. exiftool performs no domain-level
sanity check on the numeric value it's told to write.

**Why it happens:** exiftool's job is byte-level tag writing, not domain validation — it trusts
the caller.

**How to avoid:** Validate `lat ∈ [-90, 90]`, `lon ∈ [-180, 180]`, and non-empty/reasonable-length
city/country strings in Python **before** ever building the exiftool argument list. This is new
code this phase must add — nothing upstream does it.

**Warning signs:** No unit test asserting an out-of-range coordinate is rejected before the
subprocess call.

**Phase to address:** This phase, in the writer/planner, before any `subprocess.run`.

**Confidence:** `[VERIFIED: local exiftool 13.55, this session]`

---

### Pitfall 2: exiftool write is atomic per file, but NOT atomic per tag within one invocation — exit code and stdout are insufficient for partial-failure detection

**What goes wrong:** Verified empirically: `exiftool -GPSLatitude=notanumber -City="X"
-Country="Y" <file>` prints a warning to stderr (`Error converting value for GPS:GPSLatitude
(ValueConvInv)`), **skips only the GPS tag**, **still writes City and Country**, still reports
"1 image files updated", and still exits 0. A design that reads EXIF-03's "falha parcial" as
needing to catch a whole-invocation exception, or that trusts exit code / the "N files updated"
message as the write's outcome, will silently miss exactly the case D-03/D-04/EXIF-03 exist to
catch.

**Why it happens:** exiftool applies each `-TAG=value` argument independently; a per-tag
conversion failure is a warning, not a fatal error, by design (it's meant to be forgiving when
batch-processing large tag lists).

**How to avoid:** Never treat exit code or exiftool's summary line as the source of truth for
"what actually got written." The pre/post full-tag diff (Pattern 2 above) is the only reliable
signal, and it naturally produces exactly the "which tags entered before the error" detail
EXIF-03's audit log requires — diff the intended write set against what's actually different,
per field, not per invocation.

**Warning signs:** Audit log code that branches on `subprocess.CompletedProcess.returncode`
instead of on the tag diff.

**Phase to address:** This phase — this is the central design fact EXIF-03's verification step
must be built around.

**Confidence:** `[VERIFIED: local exiftool 13.55, this session]`

---

### Pitfall 3: bare `-City`/`-Country` resolve to different, asymmetric default tag groups — silently inconsistent unless both are written explicitly

**What goes wrong:** Verified empirically on a real write: `exiftool -City="São Paulo"
-Country="Brasil" <file>` (no group prefix) wrote `City` to the **IPTC** group but `Country` to
the **XMP-photoshop** group — not the same group for both, despite the symmetric-looking
command. A reasonable assumption ("both bare tags land in IPTC, since IPTC is what `-City`
usually means") would be wrong for `Country` specifically, because IPTC's actual tag name is
`Country-PrimaryLocationName`, not literally `Country` — so the bare `-Country` argument
resolves unambiguously to the one group that *does* have a tag literally named `Country`
(XMP-photoshop), while `-City` is ambiguous between IPTC and XMP-photoshop and exiftool's
priority rules pick IPTC.

**Why it happens:** exiftool's tag-name-to-group resolution follows an internal priority table
per tag name, not a single default group applied uniformly.

**How to avoid:** Always write **both** groups explicitly and don't rely on the bare/ambiguous
form: `-IPTC:City=<v>` **and** `-XMP:City=<v>`; `-IPTC:Country-PrimaryLocationName=<v>` **and**
`-XMP:Country=<v>`. Verified this session to land cleanly (all four tags present,
`exiftool -validate` = OK) — this is also the interoperability-maximizing choice D-075's own
rationale calls for (write once, readable by both IPTC-only and XMP-only consumers).

**Warning signs:** Code that writes bare `-City=`/`-Country=` and assumes symmetric group
placement; a test asserting `IPTC:Country-PrimaryLocationName` was written when only
`XMP-photoshop:Country` actually was.

**Phase to address:** This phase, in the writer's tag-name constants.

**Confidence:** `[VERIFIED: local exiftool 13.55, this session]` for the write behavior.
`[CITED: Adobe XMP namespace docs — ns.adobe.com/photoshop/1.0/, ns.adobe.com/exif/1.0/]`
`[MEDIUM]` for the claim that Lightroom/Photos.app/Finder read these specific groups back — this
is the standard, documented namespace (same one Adobe's own products use for City/Country in
Lightroom's metadata panel), but this session did **not** have Lightroom or Photos.app installed
to empirically confirm the read-back; treat as an open item, see Open Questions.

---

### Pitfall 4: creating a brand-new GPS/IPTC/XMP block produces "scaffolding" tags that are not location data — and this is the *normal* case for this phase's target population, not an edge case

**What goes wrong:** Verified empirically, twice, with two different fixtures (a truly minimal
JPEG, and a JPEG with pre-existing `Make`/`Model`/IFD0 but no GPS/IPTC/XMP): writing GPS+city+
country for the *first time* to a file that never had any of those blocks causes exiftool to
also write `GPS:GPSVersionID` (mandatory GPS IFD version tag), `IPTC:ApplicationRecordVersion`
(mandatory IPTC record version) + `File:CurrentIPTCDigest` (IPTC checksum, auto-managed), and
`XMP-x:XMPToolkit` (identifies the writing tool) — none of which are "tags de localização" under
a literal reading of D-04's "só as tags de localização esperadas mudaram." On a file that
*already* has an EXIF IFD0 (any real camera JPEG), pre-existing IFD0 tags like
`XResolution`/`YResolution`/`ResolutionUnit` do **not** get spuriously rewritten — that artifact
was specific to the minimal synthetic fixture that had no EXIF at all. But the IPTC/XMP/GPS
scaffolding tags above appear **whenever those specific blocks are new**, which is true for
essentially every file this phase writes to, since EXIF-02 only ever writes into *currently
empty* location fields.

**Why it happens:** IPTC and XMP are versioned, checksummed container formats; exiftool must
write their mandatory header/version fields to produce a spec-valid block, and the GPS IFD has
its own mandatory version tag for the same reason.

**How to avoid:** Document and code an explicit **scaffolding-tag allowlist** (Pattern 2 above)
that D-04's diff check treats as expected, not a violation — with each entry justified (why
this specific tag, why it's unavoidable), not a broad "ignore anything IPTC/XMP-shaped"
exemption that could mask a real problem.

**Warning signs:** D-03's format test rejecting every format because `IPTC:ApplicationRecordVersion`
"changed" on every single sample.

**Phase to address:** This phase — must be resolved before D-03's test can produce a meaningful
pass/fail table.

**Confidence:** `[VERIFIED: local exiftool 13.55, this session, two independent fixtures]`

---

### Pitfall 5: `AuditLog.plan_id` is a real, enforced foreign key to `operation_plans.id` — reusing `AuditLog` for exif-write plans as milestone ARCHITECTURE.md suggests would violate it

**What goes wrong:** `fotoorganizer/models/operations.py` declares
`plan_id: Mapped[int | None] = mapped_column(ForeignKey("operation_plans.id"))` on `AuditLog`,
and `fotoorganizer/database/engine.py` runs `PRAGMA foreign_keys=ON` — both confirmed by direct
read. The milestone-level ARCHITECTURE.md recommends "reuse `AuditLog`... this is the one place
sharing infrastructure with `operations/` is genuinely low-risk, since `AuditLog` has no
copy-specific assumptions" — that claim is **not fully accurate**: the column has a live,
enforced schema-level assumption that `plan_id` refers to a row in `operation_plans`. If the new
`ExifWritePlan` table has its own independent primary-key sequence (as the "structurally
parallel, not shared" architecture recommends) and code sets `AuditLog.plan_id =
exif_plan.id`, the insert will raise a foreign key constraint violation the moment an
`ExifWritePlan.id` doesn't happen to collide with a real `operation_plans.id`.

**Why it happens:** The milestone-level research read `AuditLog`'s Python shape (nullable int)
correctly but didn't check the FK constraint or confirm `PRAGMA foreign_keys` was enabled at
runtime — an easy gap to miss without directly querying the schema/engine config.

**How to avoid:** `plan_id` is nullable — leave it `NULL` for exif-write audit rows, and carry
the `ExifWritePlan`/`ExifWriteItem` id inside the existing `detalhe` JSON column instead (e.g.
`detalhe={"exif_plan_id": ..., "item_id": ..., ...}`). This requires **no migration** and keeps
`AuditLog` genuinely reusable, just not via the `plan_id` column for this feature. (Alternative:
add a nullable `exif_plan_id` FK column to `AuditLog` pointing at the new table — more explicit,
but is a schema change the JSON-payload approach avoids needing.)

**Warning signs:** A migration adding rows to `operation_plans` just to satisfy the FK for
exif-write audit entries (a real anti-pattern that would silently pollute the copy-operations
plan list with fake entries) — or a test that only exercises `AuditLog` in isolation without
`PRAGMA foreign_keys=ON`, which would hide this failure until it hits the real app.

**Phase to address:** This phase, in the audit-log integration design — before any code writes
to `AuditLog` from the exif-write path.

**Confidence:** `[VERIFIED: fotoorganizer/models/operations.py line ~90, fotoorganizer/database/engine.py line 14, this session]`

---

### Pitfall 6: no existing checkbox-per-row / multi-select-with-per-item-deselect component exists anywhere in this codebase — D-02's UI is new work, not reuse

**What goes wrong:** CONTEXT.md's `<code_context>` section states "Padrão de checkbox por linha
já usado em review de sugestões — reusar para D-02," implying this is a drop-in reuse. A grep
across every `webapp/src/components/*.tsx` file this session found **zero** occurrences of
`type="checkbox"` or a `checked=` prop anywhere in the codebase. `Duplicates.tsx`'s closest
analog is a per-group `<button>` toggle for "mark as primary" (single-select-like, not
multi-select-with-individual-deselect), and every other `selecionado` state in the codebase
(`Mapa.tsx`, `ArvoreDePastas.tsx`) is single-selection, not a batch-with-opt-out list.

**Why it happens:** the review-of-suggestions UI achieves a similar *outcome* (approve/reject
individual items in a batch) through a different mechanism (per-item approve/reject action, not
a persistent checkbox state) — easy to conflate as "the same pattern" at the requirements level
without checking the actual component implementation.

**How to avoid:** Size this as new frontend work in planning — a `Set<number>` (or
`Map<number, boolean>`) of selected item ids in local state, rendered as native
`<input type="checkbox">` elements (Tailwind-styled, no new dependency needed), defaulting to
"all checked" per D-02 ("desmarcar itens pontuais," not opt-in). `Operations.tsx` remains the
right structural precedent for the surrounding plan→dry-run→approve→execute flow (D-01); the
per-row checkbox itself has no existing precedent to copy.

**Warning signs:** A plan/task that estimates the checkbox UI as "reuse existing component" with
no new component file.

**Phase to address:** This phase's frontend slice.

**Confidence:** `[VERIFIED: grep across webapp/src/components/*.tsx, this session — zero matches for checkbox pattern]`

---

### Pitfall 7: the STACK.md and PITFALLS.md milestone documents directly contradict each other on `-overwrite_original` — needs a resolved answer, not two

**What goes wrong:** STACK.md's "What NOT to Use" table says *avoid* `-overwrite_original`
("keeping the default backup gives a second, independent proof that the pristine original
survives... the `_original` file should be treated as a second copy of the original, not a
scratch file to clean up"). PITFALLS.md's Pitfall 1 says the opposite: *explicitly pass*
`-overwrite_original` ("Without it, exiftool leaves an `IMG_1234.CR3_original` backup file
sitting in the user's real photo folder — clutter... could be picked up by iCloud Drive/Dropbox
sync as a 'new file'"). Both concerns are real and verified in this session (default backup
behavior confirmed empirically: without the flag, a same-named `_original` file is created
alongside the target).

**Why it happens:** the two milestone documents were researched independently and each
optimized for a different risk (data-loss safety vs. tree cleanliness) without reconciling with
the other.

**How to avoid — recommended synthesis, not in either source document:** don't pass
`-overwrite_original`. Let exiftool create its `_original` backup as an actual, literal recovery
copy during the highest-risk window (between write and verification). Run the full pre/post tag
diff (Pattern 2). **On verified success**, explicitly delete the `_original` backup as a
deliberate, logged cleanup step (`AuditLog` entry: `acao="limpeza_backup_exiftool"`) — this
satisfies invariant 8's "nothing that could be the real reference is deleted" spirit during the
window where it matters (before the write is proven safe) while avoiding PITFALLS.md's
legitimate concern about permanent tree clutter and sync-client confusion. **On verified
failure**, keep the `_original` file and surface its path in the error — it's the actual
recovery mechanism, not just a hash record.

**Warning signs:** Code that passes `-overwrite_original` unconditionally (loses the literal
recovery copy for the risky window) or that never cleans up `_original` files after verified
success (permanent clutter in a tree the scanner treats as read-only-observed).

**Phase to address:** This phase — needs an explicit decision in the plan, since upstream
research left two contradictory recommendations.

**Confidence:** `[VERIFIED: default backup behavior confirmed locally, this session]` for the
mechanism. The synthesis/recommendation itself is `[ASSUMED]` — a reasonable reconciliation, not
independently validated against a real crash scenario; flag for the dono/planner to confirm the
cleanup-after-verified-success policy explicitly (see Open Questions).

---

### Pitfall 8: the real, currently-scanned catalog has zero CR3 and zero HEIC files — D-03's test can't validate the two formats PITFALLS.md flags as historically riskiest, this milestone

**What goes wrong:** Direct query of the production `catalog.db`
(`~/Library/Application Support/FotoOrganizer/catalog.db`, 1,399 total files) shows the extension
distribution is `.jpg` (1,384), `.cr2` (12), `.dng` (2), `.tif` (1) — **zero** `.cr3`, **zero**
`.heic`/`.heif`. This matches `.planning/STATE.md`'s own documented blocker: the two sources
that would carry the bulk of CR3/HEIC (Apple Fotos iCloud-only library, ~44,661 records; a
Lightroom library on a currently-unmounted volume, ~45,397 records) are not registered in the
catalog — reconnecting them is `ARCH-01`, explicitly deferred out of v2.0 scope. D-03 requires
testing "todo formato RAW/proprietário que aparecer no acervo" — but per the *catalog*, that set
is currently just `{jpg, cr2, dng, tif}`, none of which have documented write-corruption history
(unlike CR3/HEIC, per milestone PITFALLS.md Pitfall 3).

**Why it happens:** the milestone-level research's framing ("CR3/HEIC citados na pesquisa")
implicitly assumed those formats would be reachable for testing; the phase-level catalog reality
check wasn't run until now.

**How to avoid:** the plan must make an explicit choice, not silently narrow scope: (a) source
D-03's sample files from real photos on disk that match RAW extensions the app *can* read
(`RAW_EXTENSIONS` in `purepython.py` already includes `.cr3`, `.nef`, `.arw`, `.raf`, `.orf`,
`.rw2`) even if those files aren't yet catalog-registered — e.g. ask the dono for a small sample
from an accessible volume; or (b) explicitly scope Phase 6's initial write-support allowlist to
`{jpg, cr2, dng, tif}` (what's measurably testable today) and treat CR3/HEIC as "no real data to
test this milestone — default to sidecar-XMP-only (D-06) until ARCH-01 reconnects real samples,"
logged as a measured decision per D-03's own "medição real, não suposição" discipline. Either
way this is a **planning decision**, not a research gap — flag it to the dono explicitly rather
than letting the plan silently assume CR3/HEIC will be tested when the data to test them isn't
there.

**Warning signs:** A plan task that says "test all RAW formats" without naming which files it
will actually use, given the catalog's real content.

**Phase to address:** This phase, at plan-creation time — needs a dono decision before D-03's
script can run meaningfully.

**Confidence:** `[VERIFIED: direct sqlite3 query against production catalog.db, this session]`

## Code Examples

### Confirmed write command shape (direct EXIF/IPTC/XMP write)

```bash
# Source: verified locally, exiftool 13.55, this session — full command, both groups, explicit refs
exiftool \
  -GPSLatitude=-23.55052 -GPSLatitudeRef=S \
  -GPSLongitude=-46.633308 -GPSLongitudeRef=W \
  -IPTC:City="São Paulo" -XMP:City="São Paulo" \
  -IPTC:Country-PrimaryLocationName="Brasil" -XMP:Country="Brasil" \
  photo.jpg
# Result (verified): IPTC:City, XMP-photoshop:City, IPTC:Country-PrimaryLocationName,
# XMP-photoshop:Country, GPS:GPSLatitude/GPSLatitudeRef/GPSLongitude/GPSLongitudeRef all present
# and consistent; `exiftool -validate photo.jpg` → "Validate: OK"
```

### Confirmed sidecar write (D-06) — identical args, different target

```bash
# Source: verified locally, this session — same argument shape, .xmp target instead of the photo
exiftool \
  -GPSLatitude=-23.55052 -GPSLatitudeRef=S \
  -GPSLongitude=-46.633308 -GPSLongitudeRef=W \
  -XMP:City="São Paulo" -XMP:Country="Brasil" \
  photo.jpg.xmp
# Result (verified): creates a new, spec-conformant standalone XMP file (x:xmpmeta/rdf:RDF
# wrapper), readable back via `exiftool photo.jpg.xmp` with XMP-exif:GPSLatitude/Longitude and
# XMP-photoshop:City/Country populated. No IPTC group available for a bare .xmp file (IPTC is a
# binary-segment format specific to image containers) — sidecar-only writes should therefore
# rely on the XMP group alone; this is a real, smaller-surface-area difference from the direct
# write path, not a bug.
```

**Sidecar naming convention:** the existing read path (`exiftool.py::_sidecar_de()`) already
checks `foto.<ext>.xmp` (Adobe convention) before `foto.xmp` (darktable/Lightroom convention)
when reading. For **newly created** sidecars (neither exists yet, by construction — D-06 only
fires when EXIF write itself is unsupported), write to `foto.<ext>.xmp` to match what the
existing reader checks first, so the very next scan picks up the new sidecar automatically with
zero reader-side changes needed.

### Sync-folder detection (D-07) — verified against this machine's real filesystem

```python
# Source: verified locally against real ~/Library/Mobile Documents and ~/Library/CloudStorage
# contents, this session (OneDrive-Personal folder confirmed present under CloudStorage)
from pathlib import Path

_RAIZES_SINCRONIZADAS = {
    "iCloud Drive": Path("~/Library/Mobile Documents").expanduser(),
    # Catches OneDrive, Google Drive, Box, and current-version Dropbox (macOS 12.3+ unified
    # File Provider root) — verified: this machine has ~/Library/CloudStorage/OneDrive-Personal
    "Nuvem (File Provider)": Path("~/Library/CloudStorage").expanduser(),
}
# Legacy fallback for pre-File-Provider Dropbox installs (not verified locally — no legacy
# Dropbox install available on this machine to test against). [CITED, not verified this session]
_DROPBOX_LEGADO = Path("~/Dropbox").expanduser()


def pasta_sincronizada(caminho: Path) -> str | None:
    """Nome do serviço de sync, ou None. Resolve symlinks primeiro — cobre o caso em que
    ~/Desktop ou ~/Documents foram redirecionados pelo 'iCloud Drive Desktop & Documents
    Folders' (verificado: nesse caso o caminho resolvido cai dentro de Mobile Documents mesmo
    que o caminho original pareça um Desktop comum)."""
    try:
        resolvido = caminho.resolve()
    except OSError:
        return None
    for nome, raiz in _RAIZES_SINCRONIZADAS.items():
        if resolvido.is_relative_to(raiz):
            return nome
    if resolvido.is_relative_to(_DROPBOX_LEGADO):
        return "Dropbox (legado)"
    return None
```

No subprocess call, no new dependency, O(1) per file — cheap enough to run on every candidate in
the dry-run pass.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Lightroom/Photos.app read `XMP-photoshop:City`/`Country` and `IPTC:City`/`Country-PrimaryLocationName` back correctly (not empirically tested — no Lightroom/Photos.app import test run this session) | Pitfall 3, Standard Stack | If wrong, the whole premise of D-075 (write EXIF for cross-tool interoperability, vs. sidecar) is weaker than assumed for whichever tool doesn't read it — worth a manual spot-check before full rollout, not before writing the plan |
| A2 | Legacy (pre-File-Provider) Dropbox installs still use `~/Dropbox` or `~/.dropbox/info.json` as documented; not verified against an actual legacy install on this machine | Code Examples, Sync-Folder Detection | Low — this is a fallback tier behind the empirically-verified `~/Library/CloudStorage` check, which already covers current-version Dropbox; only affects users on old Dropbox versions |
| A3 | Deleting the `_original` exiftool backup only after a *verified* successful diff (Pitfall 7's synthesis) is the right policy — reconciles STACK.md vs PITFALLS.md but wasn't itself tested against a real interrupted/crashed write | Pitfall 7 | If the cleanup step itself has a bug, could either leak `_original` files permanently (tree clutter PITFALLS.md warned about) or delete them before a failure is fully confirmed (losing the literal recovery copy STACK.md wanted) — needs explicit dono/planner sign-off as a policy decision, not silently coded either way |
| A4 | `-P`/mtime-preservation behavior after a write wasn't conclusively tested (one quick check didn't show the flag preserving the original modify date) — not a blocking finding, just unresolved | (not in a numbered pitfall — minor) | Low — affects whether "Date Modified" in Finder changes after a location write; cosmetic, not a correctness or safety issue |

## Open Questions (RESOLVED)

1. **(RESOLVED → `06-09-PLAN.md` Task 3, blocking human checkpoint)** Does Lightroom (or
   Photos.app, or plain Finder "Get Info") actually surface `XMP-photoshop:City`/`IPTC:City`
   back to the dono the way D-075's rationale assumes?
   - What we know: the tag groups chosen are the standard, documented Adobe/IPTC-Core
     conventions, and exiftool's own write of them validates cleanly.
   - Resolution: not resolved by measurement (no Lightroom/Photos.app available to script
     against this session) — resolved procedurally instead. `06-09-PLAN.md` Task 3 is a
     blocking human checkpoint: the dono opens one written test file in whichever tool they
     actually use day-to-day and confirms location shows up, before the plan can be
     considered fully verified. This is the premise underlying D-075's choice of EXIF direct
     over sidecar-only, so it gates before rollout, not after.

2. **(RESOLVED → D-09 in `06-CONTEXT.md`)** What should Phase 6's initial format-write
   allowlist be, given the real catalog has no CR3/HEIC to test against right now (Pitfall 8)?
   - What we know: `{jpg, cr2, dng, tif}` are measurably testable today; CR3/HEIC are the
     formats with documented historical write-corruption risk and are exactly the ones not
     reachable without ARCH-01.
   - Resolution: dono chose (via `AskUserQuestion` during discuss-phase, not silently
     narrowed) to test only formats present in the real catalog today. CR3/HEIC are marked
     "não testado" (not "reprovado") and route to the sidecar XMP fallback (EXIF-05) until a
     testable sample exists — recorded as D-09.

3. **(RESOLVED → `06-05-PLAN.md` executor design + `06-09-PLAN.md` Task 2 step 8)** Cleanup
   policy for exiftool's `_original` backup file (Pitfall 7) — delete immediately after
   verified success, or retain until explicit user action?
   - Resolution: delete only after the tag-diff verification passes AND the file still opens
     normally (the synthesis this document recommended). Made observable to the dono, not
     just coded silently: `06-09-PLAN.md` Task 2 step 8 has the dono confirm `_original` is
     absent after a successful write and present after a rejected/failed one, at the same
     blocking checkpoint as Open Question 1. This is the de facto sign-off mechanism — the
     dono can reject the behavior at that checkpoint if it doesn't match expectations.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `exiftool` | Direct EXIF/IPTC/XMP write, XMP sidecar write, format-support test script | ✓ | 13.55 `[VERIFIED: exiftool -ver, this session]` | None needed — this phase has no pure-Python write path; if exiftool is absent, EXIF write must be entirely unavailable (mirrors the existing read path's `ExifToolExtractor.disponivel()` check) |
| Real CR3/HEIC sample files | D-03's empirical format test, for those two extensions specifically | ✗ | — | See Pitfall 8 / Open Question 2 — no fallback within this milestone's registered catalog; needs an explicit dono decision |

**Missing dependencies with no fallback:** CR3/HEIC sample files for D-03 (see Open Question 2)
— not a missing *tool*, a missing *data sample*, blocking only the two riskiest formats'
coverage, not the phase as a whole.

**Missing dependencies with fallback:** none beyond the above.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework (backend) | pytest, configured in `pyproject.toml [tool.pytest.ini_options]`, `testpaths = ["tests"]` `[VERIFIED: pyproject.toml, this session]` |
| Framework (frontend) | vitest, `npm test` → `vitest run`, per `webapp/package.json` `[VERIFIED: webapp/package.json, this session]` |
| Config file | `pyproject.toml` (backend), `webapp/vitest.config.*` (frontend, present per existing `webapp/src/components/*.test.tsx` files) |
| Quick run command (backend) | `.venv/bin/pytest tests/test_exif_write.py -x` |
| Quick run command (frontend) | `cd webapp && npm test -- EscritaExif` |
| Full suite command | `.venv/bin/pytest` and `cd webapp && npm test` |

### Fixture infrastructure already available (reuse, no new dependency)

`tests/fixtures.py::make_jpeg(gps=None, make="TestMake", ...)` already generates synthetic
JPEGs with a realistic EXIF IFD0 (Make/Model) and no GPS by default — exactly the "camera-like,
no location data" baseline this phase's write tests need. `tests/test_operations.py`'s `ambiente`
fixture pattern (temp SQLite + temp source tree) is the direct structural precedent for the new
`ExifWritePlan`/`ExifWriteItem` tests.

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EXIF-01 | Dry-run lists empty fields per file, nothing written before approval | unit | `pytest tests/test_exif_write.py::test_dry_run_nao_escreve -x` | ❌ Wave 0 |
| EXIF-02 | Only empty fields get written; pre-filled fields skip with visible reason | unit | `pytest tests/test_exif_write.py::test_pula_campo_preenchido -x` | ❌ Wave 0 |
| EXIF-03 | Full-tag diff verification incl. scaffolding-tag allowlist; partial failure logged with which tags landed | unit | `pytest tests/test_exif_write.py::test_diff_detecta_falha_parcial -x` | ❌ Wave 0 |
| EXIF-04 | Never writes non-location tags, proven by full tag dump comparison | unit | `pytest tests/test_exif_write.py::test_nunca_escreve_fora_de_localizacao -x` | ❌ Wave 0 |
| EXIF-05 | Unsupported format appears as explicit dry-run line + sidecar XMP offer | unit + integration | `pytest tests/test_exif_write.py::test_formato_nao_suportado_oferece_sidecar -x` | ❌ Wave 0 |
| D-02 (checkbox per row) | Per-item deselect before confirming, batch approval otherwise | frontend unit | `cd webapp && npm test -- EscritaExif` | ❌ Wave 0 (no existing checkbox component to extend, per Pitfall 6) |
| D-07 (sync detection) | Path inside iCloud Drive/CloudStorage flagged with warning | unit | `pytest tests/test_exif_write.py::test_detecta_pasta_sincronizada -x` | ❌ Wave 0 |
| Pitfall 5 fix (AuditLog FK) | Exif-write audit rows never populate `plan_id` with a non-`operation_plans` id | regression | `pytest tests/test_exif_write.py::test_audit_log_nao_viola_fk -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** backend quick-run command above; frontend `npm test -- EscritaExif`.
- **Per wave merge:** full `pytest` + full `npm test`.
- **Phase gate:** full suite green before `/gsd:verify-work`, plus D-03's standalone
  `scripts/testar_escrita_exif.py` run once against real (disposable-copy) samples and its
  result logged to `docs/DECISOES.md` before the format allowlist is considered final.

### Wave 0 Gaps

- [ ] `tests/test_exif_write.py` — covers EXIF-01..05 (new file, no existing equivalent)
- [ ] `tests/fixtures.py` extension — a `make_jpeg_com_gps_preenchido` variant (or reuse
      `make_jpeg(gps=...)`, already supports this) for the "already has GPS, must skip" case
- [ ] `webapp/src/components/EscritaExif.test.tsx` (or equivalent) — new component, new test
      file, no existing checkbox-per-row component to extend (Pitfall 6)
- [ ] `scripts/testar_escrita_exif.py` — D-03's empirical script itself; not a pytest target,
      but its existence and one real run against real (copied) samples is a phase-gate
      precondition per D-03/D-04, same as `calibrar_raio_incerteza.py` was for D-074
- [ ] Migration for `ExifWritePlan`/`ExifWriteItem` tables (Alembic, new revision) — needs a
      test asserting `PRAGMA foreign_keys=ON` doesn't reject legitimate inserts (regression test
      for Pitfall 5)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Local-only app, 127.0.0.1, no auth layer in scope |
| V3 Session Management | No | N/A |
| V4 Access Control | No | Single local user, no multi-tenant concern |
| V5 Input Validation | Yes | GPS bounds (`lat ∈ [-90,90]`, `lon ∈ [-180,180]`) and city/country string sanity validated in Python before shelling out (Pitfall 1) — exiftool itself does not validate |
| V6 Cryptography | No | No new crypto surface this phase |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Argument injection via unsanitized city/country strings passed to `subprocess.run` | Tampering | List-args `subprocess.run`, no `shell=True` (invariant 5, already the codebase's universal pattern — `volumes.py`, `exiftool.py` reader both follow it; the writer must too) |
| Path traversal via a maliciously crafted `origem`/`destino` for the write target | Tampering | Reuse `security/paths.py` unchanged — the file being written already lives inside a known, already-validated source root (unchanged from milestone ARCHITECTURE.md's finding) |
| Out-of-range GPS values silently accepted and persisted as if valid | Tampering (data integrity) | Python-side range validation before write (Pitfall 1) — new code this phase must add, exiftool provides no such check |
| Foreign-key-violating audit writes silently swallowed or crashing the write path | Tampering / Denial of Service | `plan_id` left NULL for exif-write rows, id carried in `detalhe` JSON (Pitfall 5) — verified `PRAGMA foreign_keys=ON` is enforced, so this is a real, not theoretical, failure mode if unaddressed |

## Sources

### Primary (HIGH confidence — verified empirically this session)

- Local `exiftool 13.55` binary (`/opt/homebrew/bin/exiftool`) — GPS write, IPTC/XMP write,
  bare-tag group resolution, scaffolding-tag behavior, `-validate` delta behavior, partial-tag
  failure behavior, `_original` backup default, standalone `.xmp` sidecar creation — all tested
  directly against disposable copies of `/opt/homebrew/Library/Homebrew/test/support/fixtures/test.jpg`
  in the session's scratchpad, never against real catalog photos.
- `~/Library/Application Support/FotoOrganizer/catalog.db` (production catalog, read-only query)
  — real extension distribution (1,399 files: jpg 1384, cr2 12, dng 2, tif 1).
- `~/Library/Mobile Documents/`, `~/Library/CloudStorage/` — confirmed present and populated
  (iCloud Drive `com~apple~CloudDocs`, OneDrive `CloudStorage/OneDrive-Personal`) on this
  machine.
- `fotoorganizer/metadata/exiftool.py`, `fotoorganizer/metadata/purepython.py`,
  `fotoorganizer/operations/executor.py`, `fotoorganizer/security/paths.py`,
  `fotoorganizer/security/hashing.py`, `fotoorganizer/security/volumes.py`,
  `fotoorganizer/models/operations.py`, `fotoorganizer/database/engine.py` — read directly, this
  session.
- `webapp/src/components/*.tsx` — grepped directly for checkbox/multi-select patterns, this
  session (zero matches).
- `scripts/calibrar_raio_incerteza.py` — read directly as the structural precedent for D-03.
- `tests/fixtures.py`, `tests/test_metadata.py`, `tests/test_operations.py` — read directly for
  Wave 0 gap analysis.

### Secondary (MEDIUM confidence)

- `[CITED: Dropbox Help / TidBITS]` — Dropbox's migration to the unified File Provider
  `~/Library/CloudStorage/` root on macOS (WebSearch, cross-referenced against the empirically
  confirmed presence of `~/Library/CloudStorage/OneDrive-Personal` on this machine, though no
  actual Dropbox install was available to verify directly).
- `[CITED: Adobe XMP namespace specs]` — `ns.adobe.com/photoshop/1.0/` as the standard
  City/Country namespace Lightroom/Photoshop use; not independently confirmed against a running
  Lightroom instance this session (see Open Question 1, Assumption A1).

### Tertiary (LOW confidence)

- `[ASSUMED]` — legacy pre-File-Provider Dropbox detection via `~/Dropbox`/`~/.dropbox/info.json`
  (Assumption A2); not verified against an actual legacy Dropbox install.

### Inherited from milestone-level research (unchanged, still authoritative)

- `.planning/research/STACK.md`, `.planning/research/ARCHITECTURE.md`,
  `.planning/research/PITFALLS.md` — read in full; this document explicitly notes where
  phase-level empirical testing **confirmed**, **refined**, or **corrected** specific claims
  from these (scaffolding tags, AuditLog FK, `-overwrite_original` contradiction, format
  distribution, checkbox-pattern claim) rather than re-deriving the architecture decision
  itself, which stands as researched.

---
*Phase research for: Foto Organizer v2.0 — Phase 6, Escrita EXIF de localização*
*Researched: 2026-08-18*
