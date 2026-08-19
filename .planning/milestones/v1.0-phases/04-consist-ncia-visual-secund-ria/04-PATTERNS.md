# Phase 4: Consistência visual secundária - Pattern Map

**Mapped:** 2026-08-16
**Files analyzed:** 17 (16 frontend + 1 backend)
**Analogs found:** 17 / 17 (all in-repo — this phase is full-codebase reconciliation
against an already-established design system, not new-surface construction; every
"analog" is either the file's own established pattern or a sibling component that
already does the target behavior correctly)

**Reading order for the planner:** `04-UI-SPEC.md` already contains locked, literal
code excerpts for every CONS item (exact classNames, exact copy, exact markup) —
treat it as the primary source of truth for *what to write*. This file's job is
narrower: for each touched file, name the *closest correct precedent already in the
codebase* so the executor copies a working pattern instead of inventing one, and
flag where UI-SPEC's snippet already **is** the pattern (no separate analog needed).

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `webapp/src/index.css` | config (design tokens) | static | itself — `@theme` block, `--text-*` namespace precedent (lines 41-53) | exact (same file, same mechanism) |
| `webapp/src/App.tsx` | component (root layout/controller) | request-response + event-driven (keyboard) | itself — no responsive-breakpoint precedent exists anywhere in `webapp/src/` (confirmed by grep, D-09) | no analog (new pattern, plain Tailwind convention) |
| `webapp/src/components/Review.tsx` | component | CRUD (mutations) + request-response | `webapp/src/components/RetomarScan.tsx` (button hierarchy), itself (badge insertion point) | role-match (button), exact (badge, per UI-SPEC snippet) |
| `webapp/src/components/Trips.tsx` | component | request-response | itself — `Card`'s existing "Mapa" badge (lines 163-169) | exact — same visual family, same file |
| `webapp/src/components/Loupe.tsx` | component | event-driven (image `onError`) | `webapp/src/components/Trips.tsx:106-147` (`Card`'s `capaFalhou` pattern) | role-match (behavior), not literal copy per D-06 |
| `webapp/src/components/Duplicates.tsx` | component | CRUD (mutations) + event-driven | `webapp/src/components/Trips.tsx:106-147` (error state) + `webapp/src/components/Miniatura.tsx` (per-item local state extraction shape) | role-match |
| `webapp/src/components/Operations.tsx` | component | batch/CRUD (plan execution) + event-driven | `webapp/src/components/StatusBar.tsx:100-108` (hover-only cancel), `webapp/src/components/RetomarScan.tsx` (contorno default) | exact (both) |
| `webapp/src/components/RetomarScan.tsx` | component | event-driven | `webapp/src/ui/Botao.tsx` default `contorno` variant | exact — this file is migrating TO the default it already imports |
| `webapp/src/components/Inspector.tsx` | component | request-response | `webapp/src/index.css` `--font-weight-titulo` token (no code precedent, pure class swap) | exact (mechanical) |
| `webapp/src/components/Sidebar.tsx` | component | CRUD (scan/import triggers) + event-driven (modal) | itself — `ModalCaminho` (lines 316-354) is the modal being lifted/exposed | exact (source of truth for the lift) |
| `webapp/src/components/TemplateEditor.tsx` | component | CRUD (template save) | `--font-weight-titulo` token (mechanical) | exact |
| `webapp/src/components/Mapa.tsx` | component | request-response | `--font-weight-titulo` token (mechanical) | exact |
| `webapp/src/components/Panorama.tsx` | component | request-response | `webapp/src/components/Sidebar.tsx:114-118` (the "Adicionar pasta…" button being wired to) | role-match — needs the lifted trigger from Sidebar/App |
| `webapp/src/components/PhotoGrid.tsx` | component | streaming (virtualized + infinite scroll) | same as Panorama — `Sidebar.tsx:114-118` trigger | role-match |
| `webapp/src/api.ts` | service (typed fetch client) | request-response (type definitions) | itself — `SugestaoRow` interface (lines 273-281), `Agrupamento` interface (already has `metodo`, lines 193-201, needs no change) | exact |
| `fotoorganizer/server/app.py` | route/controller (FastAPI) | request-response | itself — `_sugestao_json` serializer (lines 217-238), already reads `linha.source_id` internally at line 236, just not exposed in the returned dict | exact |
| `webapp/src/fontes.ts` | utility (pure functions, not modified) | transform | consumed as-is by CONS-01 — `rotuloDeFonte(fontes, id)` (lines 60-62) | exact, zero changes needed |

---

## Pattern Assignments

### `webapp/src/index.css` (config, static) — CONS-08 token

**Analog:** itself, `--text-*` namespace precedent already in the same `@theme` block.

**Existing convention to follow** (lines 41-53, same block CONS-08 extends):
```css
/* --- Escala tipográfica ------------------------------------------------
   Três degraus, e são os três que a interface já usa... */
--text-micro: 11px;
--text-corpo: 13px;
--text-realce: 15px;
```
`--font-weight-*` follows the identical naming/comment convention — see the exact
addition already locked in `04-UI-SPEC.md` lines 107-112 (`--font-weight-titulo: 500`).
Tailwind 4 auto-generates `font-titulo` from this namespace the same way it already
auto-generates `font-medium`/`font-semibold` from its own built-in scale — no
additional registration needed anywhere else.

---

### CONS-08 — font-weight token migration (9 files, mechanical)

**Pattern:** find-and-replace `font-semibold` → `font-titulo` and `font-medium` →
`font-titulo` at the 17 exact call sites enumerated in `04-UI-SPEC.md` lines 125-143.
No analog search needed beyond the token definition above — this is a class-string
swap, not a structural change. Confirmed call sites read directly from source in this
session (cross-checked against UI-SPEC's line numbers):

- `App.tsx:206` — `<span className="mr-3 font-semibold">Foto Organizer</span>`
- `Trips.tsx:151` — `<div className="mb-0.5 text-realce font-semibold leading-tight">`
- `Loupe.tsx:38` — `<span className="font-semibold text-texto">{media.nome}</span>`
- `Operations.tsx:286` — `<span className="min-w-0 flex-1 truncate font-medium">`
- `Inspector.tsx:38` — `<div className="mb-2 break-all font-semibold">{media.nome}</div>`
- `Inspector.tsx:114` — `<span className="font-medium">{ev.campo}: {ev.valor}</span>`
- `Review.tsx:201` — `<span className="truncate font-medium">{destino}</span>`
- `Review.tsx:306` — `<div className="truncate font-medium">{s.nome}</div>`
- `TemplateEditor.tsx:139` — `<div className="truncate font-medium">{ex.destino || "—"}</div>`
- `Sidebar.tsx:218,294,329` — `<div className="mb-2 font-semibold">...</div>` (3 modal titles)
- `Sidebar.tsx:241` — `<span className="min-w-0 flex-1 truncate font-medium" ...>`
- `Mapa.tsx:249` — `<div className="text-[15px] font-medium">`
- `Mapa.tsx:777` — `<div className="mb-1 text-[15px] font-medium leading-tight">`
- `Duplicates.tsx:134` — `<span className="shrink-0 font-semibold">{grupo.rotulo}</span>`
- `Duplicates.tsx:186` — `<div className="truncate font-medium" title={m.caminho}>`

All 17 become `font-titulo`, no exceptions (D-10 revised).

---

### `webapp/src/components/Review.tsx` (component, CRUD + request-response)

**CONS-01 — selo de fonte.** UI-SPEC's snippet (lines 318-330 of `04-UI-SPEC.md`) is
already the literal target markup — implement it verbatim inside `FotosDoGrupo`'s
`renderizar` callback (the file/name block currently at Review.tsx:306
`<div className="truncate font-medium">{s.nome}</div>`, which becomes the `font-titulo`
wrapped `<span>` inside the new flex row). Needs:
1. A `useQuery({ queryKey: ["fontes"], queryFn: api.fontes })` added to `Review.tsx`
   — same queryKey `Sidebar.tsx:31` and `App.tsx:100` already use, so react-query
   serves it from cache, no duplicate network request. Copy that exact call:
   ```tsx
   const { data: fontes } = useQuery({ queryKey: ["fontes"], queryFn: api.fontes });
   ```
2. `rotuloDeFonte` import from `../fontes` (already used the same way in `App.tsx:5`
   and `Sidebar.tsx:5`):
   ```tsx
   import { rotuloDeFonte } from "../fontes";
   ```
3. Adjacency collision detection (`colide`) computed client-side per D-01's
   implementation note — no existing analog for this exact computation in the
   codebase (new logic), but it operates on the same paginated `itens` array
   `FotosDoGrupo` already fetches (Review.tsx:396-405), comparing each `Item` to its
   immediate neighbor by `nome`+`data_capturada`+`camera`.
4. Requires `source_id` on `Item`/`SugestaoRow` — see `api.ts` and `app.py` sections
   below; this is the one genuine backend dependency in the phase. **Note:** `Item`
   (`Review.tsx:18-30`) is a hand-maintained local type, NOT `extends SugestaoRow` —
   it already duplicates fields (`gps_estimado`, `motivo_indisponivel`) rather than
   importing the shared interface. Adding `source_id` to `api.ts`'s `SugestaoRow`
   does NOT automatically fix `Item` — `source_id?: number` must be added to
   `Review.tsx`'s own `Item` type independently, or the field will be present on the
   wire but untyped/unreadable inside this file.

**CONS-03 — "Gerar/atualizar sugestões" button.** Current code (Review.tsx:151-158):
```tsx
<Botao
  variante="solido"
  onClick={() => job.gerarSugestoes()}
  disabled={job.rodando}>
  {job.rodando && job.estado.tipo === "sugestoes"
    ? "Gerando…"
    : "Gerar/atualizar sugestões"}
</Botao>
```
Drop `variante="solido"` — default `Botao` (`variante="contorno"`, the component's
own default per `webapp/src/ui/Botao.tsx:58`) is the target. No `className` override
needed; this makes it match the plain default already used correctly at
`RetomarScan.tsx` before that file's own D-04 fix (see below).

---

### `webapp/src/components/Trips.tsx` (component, request-response)

**CONS-02 — selo álbum/evento.** Analog is the file's OWN existing "Mapa" badge
(Trips.tsx:163-169):
```tsx
<button
  onClick={onAbrirMapa}
  title="ver onde este grupo aconteceu"
  className="absolute right-2 top-2 z-10 rounded-full border border-borda bg-janela/80 px-2 py-0.5 text-texto-2 backdrop-blur-sm transition-colors hover:border-borda-forte hover:text-texto"
>
  Mapa
</button>
```
The new selo (top-left, per UI-SPEC) reuses the exact same visual family
(`border-borda`, `bg-janela/80`, `backdrop-blur-sm`, `text-texto-2`) — deliberately
NOT the accent-colored `Duplicates.tsx:138` badge style. UI-SPEC's locked markup
(lines 350-354) is the target; `Card`'s existing `capaFalhou`/`semCapa` local-state
pattern (Trips.tsx:106-111) is the precedent for how this component already handles
per-card derived boolean state, which the new `secao`/`colideNome` props extend.

**Structural change required (per UI-SPEC's implementation note):** `Card` gets a
new `secao: "viagens" | "eventos"` prop and `Secao` (Trips.tsx:71-95) computes
`colideNome` (name collisions within `itens`) before passing it down — `Secao`
already owns the full `itens` array, same shape of computation Review.tsx's `colide`
needs for CONS-01 (sibling problem, same technique: compare each item to others in
the same already-fetched list).

---

### `webapp/src/components/Loupe.tsx` (component, event-driven)

**CONS-04 — broken preview image.** Behavioral analog: `Trips.tsx`'s `Card` component
(lines 106-111, 132-148) — `useState` boolean + `onError` handler + conditional
render swapping the `<img>` for a "no image" block using the `⊘` glyph:
```tsx
const [capaFalhou, setCapaFalhou] = useState(false);
...
{grupo.capa_id != null && !capaFalhou && (
  <img ... onError={() => setCapaFalhou(true)} ... />
)}
{semCapa && (
  <div className="absolute inset-0 flex flex-col items-center justify-center gap-1 text-texto-3">
    <span aria-hidden className="text-2xl">⊘</span>
    <span className="text-texto-2">capa fora de alcance</span>
  </div>
)}
```
Per D-06, do NOT replicate this literally — Loupe's target markup is already fully
specified in `04-UI-SPEC.md` lines 247-267 (full-screen two-line variant, larger `⊘`
at `text-5xl`, guards the zoom-toggle `onClick`). The `Miniatura.tsx` component
(lines 37-49, 52-72) is the third precedent for the same `⊘`-glyph-on-failure
vocabulary — confirms `⊘` is this app's established "no image" sign across three
independent call sites (Miniatura, Trips, and now Loupe/Duplicates).

Current file's existing `useEffect` reset point (Loupe.tsx:20-26, already resets
`setZoom100(false)` on index change) is where `setFalhouPreview(false)` gets added,
per UI-SPEC's comment `// reset alongside the existing setZoom100(false)`.

---

### `webapp/src/components/Duplicates.tsx` (component, CRUD + event-driven)

**CONS-04 — broken member image, compact variant.** Same three-way precedent
(`Trips.tsx` Card, `Miniatura.tsx`) as Loupe, but per-member instead of singular —
current code has no per-item local state because `.map()` bodies can't hold hooks;
UI-SPEC (lines 273-296) already flags this and delegates the `MembroFigura`
extraction to the executor. The existing inline `<figure>` block being replaced
(Duplicates.tsx:169-217, specifically the `<img>` at 179-184) is the extraction
target — pull the whole `<figure>` into its own component so `falhouPreview` can be
local `useState` per member, following the same shape `Card` in `Trips.tsx` already
uses (one `useState` per rendered instance, not a keyed map, since React already
keys each `.map()` output by `m.member_id`).

The `bg-black` → `bg-cartao` swap on failure (UI-SPEC line ~299-301) has no direct
in-file precedent but matches `Miniatura.tsx`'s established convention of `bg-cartao`
as this app's "empty/broken surface" color (Miniatura.tsx:43, 62).

---

### `webapp/src/components/Operations.tsx` (component, batch/CRUD + event-driven)

**CONS-07 — Cancelar hover-only red.** Analog: `webapp/src/components/StatusBar.tsx`
lines 101-108, the file's own already-correct pattern for the identical situation
(cancelling an in-progress job):
```tsx
<Botao
  variante="fantasma"
  tamanho="sm"
  onClick={() => void job.cancelar()}
  className="px-1 hover:text-erro"
>
  cancelar
</Botao>
```
Operations.tsx's current violation (lines 213-215):
```tsx
{executando && (
  <Botao tom="erro" onClick={() => job.cancelar()}>
    Cancelar
  </Botao>
)}
```
`tom="erro"` resolves through `Botao.tsx`'s `TONS.erro` (`border-erro/40 bg-erro/10
text-erro hover:bg-erro/20` — colored at rest, the actual bug). Target (per UI-SPEC,
matches StatusBar's pattern exactly):
```tsx
<Botao variante="fantasma" onClick={() => job.cancelar()} className="hover:text-erro">
  Cancelar
</Botao>
```

**CONS-03 — button hierarchy, no change here.** `Operations.tsx:194`'s solid
"Copiar N arquivos" button is already correct per D-04 (physical copy = only
category allowed `variante="solido"`) — do not touch.

---

### `webapp/src/components/RetomarScan.tsx` (component, event-driven)

**This file is both a modification target and the analog other files migrate
toward** — it needs its own CONS-03 fix (drop the override below) at the same time
it establishes the pattern `Review.tsx`'s button lands on.

**CONS-03 — "Retomar" button.** Current code (RetomarScan.tsx:48-60):
```tsx
<Botao
  tamanho="sm"
  onClick={() => void job.escanear(scan.caminho)}
  disabled={job.rodando || !scan.disponivel}
  title={...}
  className="border-acento text-acento hover:bg-cartao"
>
  Retomar
</Botao>
```
Drop the `className="border-acento text-acento hover:bg-cartao"` override entirely
— `Botao`'s own default `contorno` variant (`webapp/src/ui/Botao.tsx:27-28`:
`"border border-borda bg-cartao text-texto hover:border-acento"`) already reads as a
real button without a colored border. This file becomes the reference other files
migrate toward (Review.tsx's "Gerar sugestões" button lands on the exact same
no-override default).

---

### `webapp/src/components/Sidebar.tsx` (component, CRUD + event-driven)

**CONS-05 — lifting `ModalCaminho`.** The modal itself (Sidebar.tsx:316-354) and its
trigger (Sidebar.tsx:114-118, the "Adicionar pasta…" button) are the literal source
of truth being extracted/exposed — UI-SPEC locks the visible contract (same title,
placeholder, confirm action) but leaves the mechanism to the executor. Closest
existing precedent for "state owned by `App.tsx`, passed down as a prop to multiple
sibling components" is `useJob()` (`webapp/src/hooks/useJob.ts`) — `App.tsx:118`
calls it once (`const job = useJob();`) and passes the same `job` object down to
`Sidebar`, `Review`, `Duplicates`, `Operations`, `RetomarScan.tsx` as a prop. Lifting
`ModalCaminho`'s open/close state (or extracting a `useAdicionarPasta()` hook
following the exact same shape as `useJob`) and passing a callback/hook result down
to `Panorama`, `PhotoGrid`, `Trips` (which don't currently receive `job` either) is
structurally the same pattern already proven at `App.tsx:229-247`.

---

### `webapp/src/components/Panorama.tsx` / `webapp/src/components/PhotoGrid.tsx` (component, request-response / streaming)

**CONS-05 — empty state button.** Both files' current empty states are simple
centered text blocks with no button:
```tsx
// Panorama.tsx:147-152
if (data.total === 0) {
  return (
    <div className="flex flex-1 items-center justify-center text-texto-2">
      Catálogo vazio — adicione uma pasta na barra lateral para começar.
    </div>
  );
}
```
```tsx
// PhotoGrid.tsx:71-78
if (total === 0) {
  return (
    <div className="flex h-full items-center justify-center text-texto-2">
      Nenhuma foto no filtro atual — adicione uma pasta ou importe um
      catálogo na barra lateral.
    </div>
  );
}
```
Analog for the button itself: `Sidebar.tsx:114-118`
```tsx
<Botao tamanho="sm" cheio
  onClick={() => setModal("pasta")}
  disabled={job.rodando}>
  Adicionar pasta…
</Botao>
```
Per D-07/copy contract: keep existing text verbatim (both files), append the same
"Adicionar pasta…" button below it, wired to whatever mechanism CONS-05's Sidebar
lift produces. Note: whether the button uses `cheio` (full-width, matching
`Sidebar.tsx`'s own usage) or default sizing is NOT covered by `04-CONTEXT.md`'s
"Claude's Discretion" list (which only names breakpoint structure, the CSS
class/prop name for the font token, and the 404 layout) — this is planner's/
executor's call to make explicitly, not a decision this pattern map should
preempt. These are centered empty states, not a sidebar column, so default sizing
is the more likely fit, but flag it rather than assert it. `Trips.tsx`'s empty state
(Trips.tsx:48-52, `"Nenhuma viagem ou evento ainda…"`) is the third site getting the
identical button — Trips.tsx is already read above for its CONS-02 changes; this is
an independent, additive change to its `vazio` branch.

---

### `webapp/src/api.ts` (service, request-response type definitions)

**CONS-01 — `source_id` on `SugestaoRow`.** Current interface (api.ts:273-281):
```typescript
export interface SugestaoRow {
  id: number;
  media_id: number;
  nome: string;
  pasta: string;
  destino: string;
  nivel: "alta" | "media" | "baixa";
  status: string;
}
```
Add `source_id: number;` — raw id only, no formatted name (name resolution stays
client-side via `rotuloDeFonte`, already imported the same way in `App.tsx`/
`Sidebar.tsx`). `Agrupamento` (api.ts:193-201) already has `metodo: string` — CONS-02
needs zero changes here, it's `Trips.tsx` that's never read the field.

---

### `fotoorganizer/server/app.py` (route/controller, request-response)

**CONS-01 backend dependency.** `_sugestao_json` (app.py:217-238) is the serializer
used by the sugestões endpoints. It already reads `linha.source_id` internally
(line 236, to compute `motivo_indisponivel`) but never puts it in the returned dict:
```python
def _sugestao_json(linha: SuggestionRow, fora: frozenset[int] = frozenset()) -> dict:
    return {
        "id": linha.id,
        "media_id": linha.media_id,
        "nome": linha.nome,
        "pasta": linha.pasta,
        "destino": linha.destino,
        "nivel": linha.nivel.value,
        "status": linha.status.value,
        "data_capturada": (...),
        "camera": linha.camera,
        "gps_estimado": linha.gps_estimado,
        "motivo_indisponivel": (...),
    }
```
Minimal fix: add `"source_id": linha.source_id,` to this dict — one line, no new
query, no new endpoint. This is the single backend touch point for the whole phase;
`grupos_de_sugestoes` (app.py:1118-1139) and `_agrupamentos` (app.py:843-883, used
by `/api/viagens` and `/api/eventos`) need no changes — CONS-02's `metodo` field is
already serialized (confirmed by grep showing `"nivel": g.nivel.value` sibling keys
in the same dict at app.py:1134-1139, and `metodo` already typed in `api.ts:198`).

---

## Shared Patterns

### Button hierarchy (`Botao` variant system)
**Source:** `webapp/src/ui/Botao.tsx:18-45`
**Apply to:** `Review.tsx`, `Operations.tsx`, `RetomarScan.tsx`
```tsx
const VARIANTES: Record<Variante, string> = {
  solido: "bg-acento text-texto-invertido hover:opacity-90",
  contorno: "border border-borda bg-cartao text-texto hover:border-acento",
  fantasma: "text-texto-2 hover:bg-cartao hover:text-texto",
};
const TONS: Record<Tom, string> = {
  erro: "border-erro/40 bg-erro/10 text-erro hover:bg-erro/20",
  ...
};
```
CONS-03/07's entire scope is choosing the right combination of `variante`/`tom`/
`className` from this existing table — no new variant or tom is introduced this
phase, only reclassification of which call sites use which existing option.

### "No image" glyph vocabulary
**Source:** `webapp/src/components/Miniatura.tsx:37-72`, `webapp/src/components/Trips.tsx:141-148`
**Apply to:** `Loupe.tsx`, `Duplicates.tsx` (CONS-04)
```tsx
<span aria-hidden>⊘</span>
```
Always paired with `text-texto-3`/`text-texto-2` text explaining why, never the raw
browser broken-image icon, never bare — this is the established, cross-file
convention CONS-04 extends to two new call sites.

### Source-name resolution
**Source:** `webapp/src/fontes.ts:59-62`
**Apply to:** `Review.tsx` (CONS-01)
```typescript
export function rotuloDeFonte(fontes: Fonte[] | undefined, id: number): string {
  return rotulosDeFontes(fontes ?? []).get(id) ?? "fonte";
}
```
Already consumed identically by `App.tsx:5,263` and `Sidebar.tsx:5,46`.

### `["fontes"]` query cache
**Source:** `webapp/src/App.tsx:100`, `webapp/src/components/Sidebar.tsx:31`
**Apply to:** `Review.tsx` (CONS-01, new consumer)
```tsx
const { data: fontes } = useQuery({ queryKey: ["fontes"], queryFn: api.fontes });
```
Cache-shared across the app — adding this to `Review.tsx` does not trigger a
duplicate network request in practice, per UI-SPEC's explicit note.

### Prop-drilled shared job/mutation state
**Source:** `webapp/src/hooks/useJob.ts` + `webapp/src/App.tsx:118,229-293`
**Apply to:** `Sidebar.tsx`/`App.tsx`/`Panorama.tsx`/`PhotoGrid.tsx`/`Trips.tsx` (CONS-05 lift)
`App.tsx` owns one `useJob()` instance and passes the resulting `job` object as a
prop to five different sibling components. This is the structural precedent for
lifting `ModalCaminho`'s state out of `Sidebar.tsx` so `Panorama`/`PhotoGrid`
(currently not even receiving `job`) can trigger it too.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `webapp/src/App.tsx` (CONS-06 two-row stacking) | component | request-response | No responsive breakpoint class exists anywhere in `webapp/src/` today (confirmed by grep per D-09) — UI-SPEC's `flex-col gap-2 ... lg:flex-row lg:items-center lg:gap-2` (lines 374-381) is a fresh application of a stock Tailwind convention, not a codebase pattern to copy. Treat UI-SPEC's snippet as the implementation directly. |
| Adjacency/collision computation (CONS-01 `colide`, CONS-02 `colideNome`) | logic, not a file | transform | No existing "compare item to neighbors in an already-fetched list" helper exists in `webapp/src/` — both CONS-01 (`Review.tsx`) and CONS-02 (`Trips.tsx`) need this written fresh, though they're mutually consistent (same technique, same phase, could plausibly share a tiny utility if the planner wants one — not required by any decision). |

---

## Metadata

**Analog search scope:** `webapp/src/components/`, `webapp/src/ui/`, `webapp/src/hooks/`,
`webapp/src/`, `fotoorganizer/server/app.py`
**Files scanned:** 17 target files read in full (all ≤ 472 lines, single-pass reads),
plus `webapp/src/ui/Botao.tsx`, `webapp/src/components/Miniatura.tsx`,
`webapp/src/components/StatusBar.tsx` (targeted range), `webapp/src/hooks/useJob.ts`
(targeted range), `fotoorganizer/server/app.py` (targeted range around
`_sugestao_json`) as shared-pattern sources.
**Pattern extraction date:** 2026-08-16
