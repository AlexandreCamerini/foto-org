# Phase 3: Revisão acessível e consistente - Pattern Map

**Mapped:** 2026-08-16
**Files analyzed:** 4 (all modified, none new)
**Analogs found:** 4 / 4 (all in-file self-analogs — this phase extends an already-established pattern in the same files, not a new one)

**Verification note:** Every line number cited in `03-CONTEXT.md` D-02/D-03 was
re-checked against the current file content (`git status` shows these 4 files
unmodified since CONTEXT.md was written). No drift found — all 19 texto-3 line
numbers in Review.tsx/Inspector.tsx/Operations.tsx and all 3 App.tsx call-site
line ranges match exactly. Line numbers below are safe to use as-is in PLAN.md.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|----------------|
| `webapp/src/App.tsx` | component (root/router) | event-driven (state setters on user nav) | itself — 2 already-fixed `setBusca("")` call sites in the same file (lines 267, 277) | exact (same file, same pattern, same author intent) |
| `webapp/src/components/Review.tsx` | component | transform (className-only edits) | itself — lines already fixed by commit `ae60319` (e.g. former line ~309) | exact |
| `webapp/src/components/Inspector.tsx` | component | transform (className-only edits) | itself — line already fixed by commit `ae60319` (`Linha` component, dt) | exact |
| `webapp/src/components/Operations.tsx` | component | transform (className-only edits) | itself — 2 lines already fixed by commit `ae60319` (origem/destino header, audit log line) | exact |

This phase is unusual: the analog is not a *different* file playing the same
role, it's the **same file, an earlier commit**, extending an established
pattern to remaining instances. There is no cross-file pattern search needed
— `ae60319` already set the diff shape for REV-02, and the two working
`setBusca("")` sites in `App.tsx` already set the shape for REV-03.

---

## Pattern Assignments

### REV-03 — `webapp/src/App.tsx` (component, event-driven)

**Analog:** the 2 already-fixed call sites in the same file.

**Pattern source 1 — `Panorama.aoRecortar`** (lines 260-272, confirmed current):
```tsx
{aba === "Panorama" && (
  <Panorama
    aoRecortar={(novo) => {
      // Uma busca de texto deixada de outra visita à Biblioteca
      // fazia um recorte de 4.812 fotos aparecer como "vazio" —
      // a tela mostrava a mensagem genérica de biblioteca vazia
      // em vez de dizer que era a busca antiga filtrando tudo.
      setBusca("");
      setRecorte(novo);
      setAba("Biblioteca");
    }}
  />
)}
```

**Pattern source 2 — `Trips.onAbrir`** (lines 273-283, confirmed current):
```tsx
{aba === "Viagens" && (
  <Trips
    fonte={fonte ?? undefined}
    onAbrir={(filtro, nome, vista) => {
      setBusca("");
      vistaPendente.current = vista ?? null;
      setRecorte({ ...filtro, nome });
      setAba("Biblioteca");
    }}
  />
)}
```

**Pattern to apply:** a single `setBusca("");` line inserted at the start (or
alongside the other state resets) of each handler body — no new imports, no
new state, `setBusca` already destructured at line 73 (`const [busca,
setBusca] = useState("")`).

**Testing pattern — analog test exists for ONE of the two sites:**
`webapp/src/App.test.tsx:116-143`, `it("abrir uma viagem limpa a busca
deixada de outra visita à Biblioteca", ...)` exercises `Trips.onAbrir`
(pattern source 2) end-to-end: types into the busca input, switches to
Viagens, opens a trip, asserts the input `toHaveValue("")`. There is no
equivalent test for `Panorama.aoRecortar` (pattern source 1) — confirmed via
grep, no "Panorama" + "busca" test co-occurs. Grep across
`Review.test.tsx`/`Inspector.test.tsx`/`Operations.test.tsx` found no
className-based assertions (`texto-2`/`texto-3`) anywhere — this suite tests
user-visible text/behavior, not Tailwind classes, so REV-02 has no test
analog and needs none; a passing existing test suite plus manual/visual
contrast check is the verification path for REV-02.

For REV-03, the existing test is the shape to copy for new coverage of the
3 target call sites:
```tsx
it("abrir uma viagem limpa a busca deixada de outra visita à Biblioteca", async () => {
  servirApi({ ...ROTAS_BASE, "/api/viagens": [{ /* fixture */ }] });
  const usuario = userEvent.setup();
  montar(<App />);

  await usuario.click(await screen.findByText("Biblioteca"));
  const busca = await screen.findByPlaceholderText("Buscar por nome ou caminho…");
  await usuario.type(busca, "IMG");

  await usuario.click(screen.getByText("Viagens"));
  await usuario.click(await screen.findByText("Dubai, Thai & Viet"));

  expect(
    await screen.findByPlaceholderText("Buscar por nome ou caminho…"),
  ).toHaveValue("");
});
```
Same shape applies to: type into busca → trigger tab-switch button /
`onSelecionarPasta` / `aoIrPara` → assert the busca input's value is `""`.

**Target 1 — tab-switch button** (lines 207-217, confirmed current):
```tsx
{ABAS.map((nome) => (
  <button
    key={nome}
    onClick={() => setAba(nome)}
    className={`rounded-full px-3.5 py-1 transition-colors duration-[var(--dur-micro)] hover:bg-cartao ${
      aba === nome ? "bg-cartao text-texto" : "text-texto-2"
    }`}
  >
    {nome}
  </button>
))}
```
Unlike the two analogs, this is an inline arrow (`() => setAba(nome)`), not a
named callback — the fix needs the handler expanded to a block body (or a
short helper) to add `setBusca("")`. CONTEXT.md D-Claude's-Discretion leaves
open whether to clear unconditionally or only when `nome !== aba`; the
mechanical part (call `setBusca("")` before `setAba(nome)`) is locked.

**Target 2 — `onSelecionarPasta`** (lines 226-241, confirmed current):
```tsx
{sidebarVisivel && ABAS_COM_FONTE.includes(aba) && (
  <Sidebar
    fonteAtual={fonte}
    onSelecionar={setFonte}
    pastaAtual={pasta}
    onSelecionarPasta={(p) => {
      setPasta(p);
      // Escolher pasta é escolher um conjunto: manter a seleção de
      // uma foto que pode não estar mais na grade deixaria o inspetor
      // descrevendo algo que sumiu da tela.
      setSelIndex(null);
      if (p) setAba("Biblioteca");
    }}
    job={job}
  />
)}
```
Insert `setBusca("");` alongside `setSelIndex(null);` — same shape as the two
analogs (a state reset added to an existing multi-statement callback body).

**Target 3 — `aoIrPara`** (lines 438-443, confirmed current):
```tsx
<StatusBar
  job={job}
  dica={noMapa ? (mapaVazio ? DICA_MAPA_VAZIO : DICA_MAPA) : DICAS[aba]}
  noFiltro={aba === "Biblioteca" ? total : undefined}
  aoIrPara={(novo) => {
    setAba("Biblioteca");
    setAlcance(novo);
    setRecorte(null);
    setFonte(null);
  }}
/>
```
Insert `setBusca("");` into this callback — same shape as analog 2
(`Trips.onAbrir`), which also resets multiple pieces of state together.

**Error handling / validation:** none applicable — these are synchronous
local state setters, no async, no try/catch in any of the 5 call sites
(2 existing + 3 target).

---

### REV-02 — `webapp/src/components/Review.tsx` (component, transform)

**Analog:** commit `ae60319`, `Review.tsx` diff (className-only, no structural change):
```diff
-                            <div className="truncate text-[11px] text-texto-3">
+                            <div className="truncate text-[11px] text-texto-2">
```
Pattern: swap `text-texto-3` → `text-texto-2` on the exact className string;
no other change to the JSX, no new props, no new imports.

**Lines to change to `texto-2`** (all confirmed current against CONTEXT.md D-02):
- `Review.tsx:145` — `<span className="text-texto-3">` wrapping the queue
  total (`{totalNaFila...} em {lista.length} grupos`).
- `Review.tsx:253` — `<div className="mb-1 truncate text-[11px] text-texto-3">`
  wrapping `{s.nome}` in the inline-edit thumbnail subtitle.
- `Review.tsx:447` — `<div className="px-3 pb-2 pl-[68px] text-texto-3">`
  wrapping "Sem evidência registrada para esta sugestão."

**Lines that stay `texto-3`** (confirmed current, do not touch):
- `Review.tsx:141` — badge count next to already-legible tab label.
- `Review.tsx:190` — disclosure caret `▾`/`▸`.
- `Review.tsx:198` — `aria-hidden` arrow `→`.
- `Review.tsx:316` — `✎` icon inside a button with an accessible `title`.
- `Review.tsx:403`, `Review.tsx:443` — "carregando…" transient state.

---

### REV-02 — `webapp/src/components/Inspector.tsx` (component, transform)

**Analog:** commit `ae60319`, `Inspector.tsx` diff:
```diff
-      <dt className="w-20 shrink-0 text-texto-3">{rotulo}</dt>
+      <dt className="w-20 shrink-0 text-texto-2">{rotulo}</dt>
```
Same swap pattern, applied to a `<dt>` element — directly analogous to the
two `<dt>`/namespace lines this phase touches (250, 246).

**Lines to change to `texto-2`** (confirmed current):
- `Inspector.tsx:202` — "desfazer" button label (`className="px-1 text-texto-3"`
  on the `Botao variante="fantasma"` — note this sits alongside `title=` on
  the button, but D-02 classifies the label text itself as content the user
  must read to know what the click does, unlike the icon-button case at
  Review.tsx:316 which has no visible text, only a title).
- `Inspector.tsx:239` — `<div className="mt-1 text-texto-3">` "Este arquivo
  não trouxe metadado nenhum."
- `Inspector.tsx:246` — `<div className="mb-1 text-[11px] text-texto-3">{ns.rotulo}</div>`
  namespace label.
- `Inspector.tsx:250` — `<dt className="w-24 shrink-0 break-all text-texto-3">`
  metadata key (`item.chave`) — same element type as the `ae60319` analog above.

**Lines that stay `texto-3`** (confirmed current, do not touch):
- `Inspector.tsx:196` — "classificado por você" annotation next to `{rotulo}`
  (already `texto-2`).
- `Inspector.tsx:232` — parenthesized count next to "Metadados do arquivo" header.
- `Inspector.tsx:236` — "lendo…" transient state.

---

### REV-02 — `webapp/src/components/Operations.tsx` (component, transform)

**Analog:** commit `ae60319`, `Operations.tsx` diff:
```diff
-              <div className="flex gap-6 border-b border-borda px-3 py-1 text-texto-3">
+              <div className="flex gap-6 border-b border-borda px-3 py-1 text-texto-2">
```
and
```diff
-                      <div key={linha.id} className="text-texto-3">
+                      <div key={linha.id} className="text-texto-2">
```
Same swap pattern on wrapping `<div>` elements carrying multi-child content.

**Lines to change to `texto-2`** (confirmed current):
- `Operations.tsx:152` — `<div className="text-texto-3">` wrapping the plan
  status line (`{p.status} · N/M copiados` — note the `<span>` for the status
  word itself already has its own color via `CORES_STATUS[p.status]`; only
  the wrapping div's base color changes).
- `Operations.tsx:223` — ternary fallback branch:
  ```tsx
  <span
    className={
      plano.dry_run_em && !plano.executavel
        ? "text-erro"
        : "text-texto-3"    // ← this branch becomes text-texto-2
    }
  >
    {veredito(plano)}
  </span>
  ```
  Only the `"text-texto-3"` literal at line 223 changes; the `"text-erro"`
  branch (line 222) is untouched.

**Lines that stay `texto-3`** (confirmed current, do not touch):
- `Operations.tsx:122` — `placeholder:text-texto-3` on an `<input>` (universal
  placeholder convention, explicitly out of REV-02 scope per D-02).
- `Operations.tsx:291` — `CORES_STATUS[item.status] ?? "text-texto-3"` fallback
  inside a template literal, same REV-07 "color by state" family, not a
  contrast issue — do not touch.

---

## Shared Patterns

### texto-3 → texto-2 swap (REV-02)
**Source:** commit `ae60319` (already applied 6 times across these 3 files).
**Apply to:** the 9 lines listed above across Review.tsx/Inspector.tsx/Operations.tsx.
**Shape:** literal string replace of `text-texto-3` with `text-texto-2` inside
an existing `className`. No JSX structure change, no new props, no logic
change. Where `text-texto-3` appears inside a template literal or ternary
(Operations.tsx:223), only the specific branch identified changes — sibling
branches (e.g. `text-erro`) are untouched.
**Tokens:** both `texto-2` and `texto-3` are already defined in
`webapp/src/index.css` under `@theme` — no new token needed (see CONTEXT.md
`<code_context>`).

### setBusca("") on navigation (REV-03)
**Source:** `webapp/src/App.tsx` — 2 existing call sites, lines 267 (`Panorama.aoRecortar`)
and 277 (`Trips.onAbrir`).
**Apply to:** 3 target call sites in the same file — tab-switch button
(~line 210), `onSelecionarPasta` (~lines 231-237), `aoIrPara` (~lines 438-443).
**Shape:** insert a bare `setBusca("");` statement into an existing (or
newly-expanded, for the tab button) callback body, alongside other state
resets already present there (`setSelIndex(null)`, `setRecorte(null)`, etc.).
No new state, no new imports — `busca`/`setBusca` already declared at
App.tsx:73.

### Test coverage for REV-03 (vitest, `webapp/src/App.test.tsx`)
**Source:** `webapp/src/App.test.tsx:116-143`, the single existing test that
covers this pattern (`Trips.onAbrir` only — `Panorama.aoRecortar` has no
matching test despite being fixed). See excerpt and shape under the
`webapp/src/App.tsx` pattern assignment above.
**Apply to:** add 3 new `it(...)` blocks (or extend the existing one) in
`App.test.tsx` covering the tab-switch button, `onSelecionarPasta`, and
`aoIrPara` — each: type into busca, trigger the navigation action, assert
the busca input `toHaveValue("")`.
**Note:** no test analog exists for REV-02 (className swaps) — grep across
`Review.test.tsx`/`Inspector.test.tsx`/`Operations.test.tsx` found zero
assertions on `texto-2`/`texto-3` classNames; this suite tests rendered
text/behavior, not Tailwind classes. REV-02 verification is "existing tests
still pass" + visual/contrast check, not new test code.

---

## No Analog Found

None for the code changes themselves — all 4 files in scope have a direct,
exact in-file (or same-repo, earlier-commit) analog for both REV-02 and
REV-03. No cross-file pattern search was needed.

**Test coverage gap (not a blocker, but planner should know):** REV-03's
`Panorama.aoRecortar` fix (one of the two "already corrected" reference
sites) has no corresponding test in `App.test.tsx` — only `Trips.onAbrir` is
covered by `it("abrir uma viagem limpa a busca...")`. REV-02 has zero
className-based test coverage in any of the 3 target files (the suite
doesn't assert on Tailwind classes). Neither gap blocks this phase, but the
planner should decide whether to backfill the missing `Panorama` test
alongside the 3 new REV-03 sites, since all 3 new sites share the same
"clear busca on navigation" contract that only half the existing pattern
currently has a regression test for.

## Metadata

**Analog search scope:** `webapp/src/App.tsx`, `webapp/src/components/Review.tsx`,
`webapp/src/components/Inspector.tsx`, `webapp/src/components/Operations.tsx`,
plus `git show ae60319` and `git log -p -S 'setBusca("")' -- webapp/src/App.tsx`
for historical diff shape.
**Files scanned:** 4 (all 4 files in phase scope; no broader codebase search
required since CONTEXT.md's D-02/D-03 audit already pinpointed exact lines
and the analog is the files' own history).
**Pattern extraction date:** 2026-08-16
