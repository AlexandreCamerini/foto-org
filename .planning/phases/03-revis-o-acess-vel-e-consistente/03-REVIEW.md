---
phase: 03-revis-o-acess-vel-e-consistente
reviewed: 2026-08-16T21:55:45Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - webapp/src/App.tsx
  - webapp/src/App.test.tsx
  - webapp/src/components/Inspector.tsx
  - webapp/src/components/Operations.tsx
  - webapp/src/components/Review.tsx
findings:
  critical: 0
  warning: 4
  info: 3
  total: 7
status: issues_found
---

# Phase 3: Code Review Report

**Reviewed:** 2026-08-16T21:55:45Z
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found

## Summary

Diff scope for this phase (`174d2c5..HEAD`) is small and precise: it (1) extends
`setBusca("")` to the three remaining navigation entry points into Biblioteca
(tab button, `onSelecionarPasta`, `aoIrPara`) per D-03, and (2) bumps exactly
the nine `text-texto-3 → text-texto-2` instances locked in `03-CONTEXT.md`
D-02, no more, no less. I cross-checked every changed line against the
committed decision record and the diff matches D-02's audit table exactly —
**no incomplete-contrast finding survives that check** (an earlier draft of
this review flagged several "leftover texto-3" instances as an inconsistent
fix; that was wrong — those exact lines are explicitly and individually
justified as intentionally-left in `03-CONTEXT.md`, and I retract it). REV-03
is likewise complete and covered by four new tests in `App.test.tsx`, all of
which correctly isolate the four independent code paths that clear `busca`.

Reviewing the full files (as instructed) surfaces one finding that undermines
a specific factual premise stated in the locked decision record itself — not
a re-litigation of the decision, but a checkable claim inside its rationale
that turns out to be false when measured. It also surfaces several
pre-existing defects in the same files, out of this phase's diff but in
scope of the full-file review. All are marked pre-existing below so they
aren't mistaken for regressions introduced by this change.

No security issues, no dead debug artifacts, no hardcoded secrets in these
five files.

## Warnings

### WR-01: `title` is not the accessible name for these two buttons — verified empirically, contradicts D-02's own stated rationale

**File:** `webapp/src/components/Review.tsx:313-327`
**Issue:** Two icon-content buttons rely on `title` to explain what they do,
but neither button's *content* is empty, so per the WAI-ARIA Accessible Name
computation algorithm the `title` is never consulted — the accessible name
comes from content instead. I verified this directly (not from memory) using
`dom-accessibility-api`, the same AccName-spec implementation
`@testing-library` itself uses to resolve `getByRole`/`findByRole` queries in
this project's own test suite:

```
button[edit "✎", title="Editar destino de foto.jpg"]      → accessible name: "✎"
button["porquê" wrapping <Confianca rotulo={false}/>,
        title="Por que este destino para foto.jpg?"]       → accessible name: "Confiança Alta"
```

Neither screen-reader announcement matches the intended, informative title.
The edit button announces an unreliable glyph; the "porquê" toggle announces
the confidence level it already shows visually via colored bars, not the
fact that activating it opens an evidence explanation.

This is directly relevant to `03-CONTEXT.md` D-02, which justifies leaving
`Review.tsx:316` (the edit icon) at low-contrast `texto-3` on the premise
that it sits "dentro de botão com title acessível já explicando a ação." That
premise is checkable and is false: the title is not accessible to assistive
technology here. This does not reopen the texto-3/texto-2 classification
(that's a recorded product decision, out of scope to re-litigate) — it flags
that the specific factual claim backing it doesn't hold, independent of
contrast.

**Fix:**
```tsx
<Botao variante="fantasma" tamanho="sm"
  onClick={() => iniciarEdicao(s)}
  aria-label={`Editar destino de ${s.nome}`}
  className="px-1 text-texto-3">
  ✎
</Botao>

<Botao variante="fantasma" tamanho="sm"
  onClick={() => setPorque((p) => (p === s.media_id ? null : s.media_id))}
  aria-expanded={porque === s.media_id}
  aria-label={`Por que este destino para ${s.nome}?`}
  className="px-1">
  <Confianca nivel={s.nivel} naoClassificado={naoClassificado(s.destino)} />
</Botao>
```
`aria-label` outranks content in the AccName algorithm, so this fixes both
cases without touching the visual glyph/badge.

### WR-02: Interactive control nested inside another interactive control

**File:** `webapp/src/components/Review.tsx:172-233` (pre-existing, not introduced by this diff)
**Issue:** The group-row `<header role="button" tabIndex={0} aria-expanded={aberto} onClick={...} onKeyDown={...}>` (line 173) wraps a real `<Botao>` — "Aprovar {total}" (lines 223-232). This is the `nested-interactive` anti-pattern flagged by axe-core: a widget-role element (`role="button"`) must not contain another focusable/interactive descendant. Consequences: the header's computed accessible name pulls in all descendant text — including the nested button's own label — producing a verbose, ambiguous announcement; and the header (`tabIndex={0}`) plus the nested `<button>` both land in the natural Tab order for what a sighted user perceives as one control region with one clickable sub-action, which is disorienting via keyboard/screen-reader navigation even though the `e.target !== e.currentTarget` guard in `onKeyDown` correctly prevents the double-activation bug.
**Fix:** Don't nest interactivity. Make the row a non-interactive `<div>`; give only the caret+label region a dedicated `<button aria-expanded>` for the disclosure toggle, and keep "Aprovar N" as an ordinary sibling `<button>`, not a descendant of another button-role element.

### WR-03: `MetadadosDoArquivo`'s open state isn't scoped to the selected photo

**File:** `webapp/src/components/Inspector.tsx:215-233` (pre-existing, not introduced by this diff)
**Issue:** The component's own docstring states the design intent: "Fechado por padrão e buscado só ao abrir: um JPEG editado traz dezenas de chaves XMP, e o inspetor é recarregado a cada seleção na grade." But `aberto` is local `useState(false)` with no dependency on `mediaId`, and `Inspector` renders `<MetadadosDoArquivo mediaId={media.id} />` without a `key`, so React reuses the same component instance across photo selections. Once a user opens the panel for one photo and then arrow-key-navigates the grid, the panel stays open and the (potentially large) metadata query re-fires for every subsequently selected photo — exactly the "reloaded on every grid selection" cost the docstring says this design avoids.
**Fix:**
```tsx
useEffect(() => setAberto(false), [mediaId]);
```
or have the caller pass `key={media.id}` so the component remounts per photo.

### WR-04: No keyboard submit for "Criar plano"

**File:** `webapp/src/components/Operations.tsx:117-131` (pre-existing, not introduced by this diff)
**Issue:** The destino `<input>` has no `onKeyDown` handler and isn't wrapped in a `<form onSubmit>`, so pressing Enter after typing a destination path does nothing — the user must click "Criar plano" with the mouse. This is inconsistent with the equivalent destino-edit `<input>` in `Review.tsx:256-265`, which explicitly handles `Enter` (save) and `Escape` (cancel) in the same app, and with the project's "teclado-first" UI requirement (`CLAUDE.md`).
**Fix:**
```tsx
<form
  onSubmit={(e) => { e.preventDefault(); if (destino.trim()) criar.mutate(); }}
  className="flex items-center gap-2 border-b border-borda px-3 py-2"
>
  <input ... />
  <Botao type="submit" disabled={!destino.trim() || criar.isPending}>
    Criar plano
  </Botao>
  ...
</form>
```

## Info

### IN-01: `Botao`'s `tom` prop is bypassed with duplicated hand-rolled classes

**File:** `webapp/src/components/Review.tsx:229, 276, 281, 334, 341, 350` (pre-existing, not introduced by this diff)
**Issue:** `Botao.tsx` documents exactly why `tom="ok" | "erro" | "atencao"` exists — a single formula ("fundo a 10%, texto e borda na cor cheia") so state-colored buttons don't drift into one-off variants — and explicitly frames itself as the fix for "59 `<button>` crus repetindo a mesma classe com pequenas divergências." Review.tsx re-introduces exactly that pattern six times, e.g. `className="bg-transparent text-texto-2 hover:border-ok hover:text-ok"` (line 334) instead of `tom="ok"`.
**Fix:** Replace the six `bg-transparent ... hover:border-{ok|erro}` overrides with `tom="ok"` / `tom="erro"` on the affected `Botao` calls; drop the duplicated hover classes.

### IN-02: Font-size inconsistency for the same action label "Aprovar"

**File:** `webapp/src/components/Review.tsx:224-232` vs `330-336` (pre-existing, not introduced by this diff)
**Issue:** The group-level bulk action button forces `text-micro` (11px, line 229) while the per-item "Aprovar" button (line 330) uses the default Botao size — same label, same screen, two different sizes for what a user reads as the same action.
**Fix:** Pick one size; drop `text-micro` from the bulk button or apply it to both.

### IN-03: Unsound `as Media` type assertion

**File:** `webapp/src/components/Review.tsx:294` (pre-existing, not introduced by this diff)
**Issue:** `<Miniatura media={{ id, nome, data_capturada, motivo_indisponivel } as Media} .../>` casts an object literal that supplies only 4 of `Media`'s ~19 required fields. `Miniatura.tsx` already exports the correct, minimal type for this exact use — `AlvoMiniatura` — which structurally matches the literal without any cast. `tsc --noEmit` currently passes only because TypeScript's "sufficient overlap" rule tolerates the assertion; it would not catch a future rename/removal of a field `AlvoMiniatura` depends on.
**Fix:**
```tsx
import type { AlvoMiniatura } from "./Miniatura";
// ...
const alvo: AlvoMiniatura = {
  id: s.media_id,
  nome: s.nome,
  data_capturada: s.data_capturada ?? null,
  motivo_indisponivel: s.motivo_indisponivel ?? null,
};
<Miniatura media={alvo} ... />
```

---

_Reviewed: 2026-08-16T21:55:45Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
