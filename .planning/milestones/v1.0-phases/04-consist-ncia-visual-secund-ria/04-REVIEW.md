---
phase: 04-consist-ncia-visual-secund-ria
reviewed: 2026-08-17T00:00:00Z
depth: standard
files_reviewed: 28
files_reviewed_list:
  - fotoorganizer/server/app.py
  - tests/test_server_api.py
  - webapp/src/App.test.tsx
  - webapp/src/App.tsx
  - webapp/src/api.ts
  - webapp/src/components/Duplicates.test.tsx
  - webapp/src/components/Duplicates.tsx
  - webapp/src/components/Inspector.tsx
  - webapp/src/components/Loupe.test.tsx
  - webapp/src/components/Loupe.tsx
  - webapp/src/components/Mapa.tsx
  - webapp/src/components/ModalCaminho.tsx
  - webapp/src/components/Operations.test.tsx
  - webapp/src/components/Operations.tsx
  - webapp/src/components/Panorama.tsx
  - webapp/src/components/PhotoGrid.tsx
  - webapp/src/components/RetomarScan.test.tsx
  - webapp/src/components/RetomarScan.tsx
  - webapp/src/components/Review.test.tsx
  - webapp/src/components/Review.tsx
  - webapp/src/components/Sidebar.test.tsx
  - webapp/src/components/Sidebar.tsx
  - webapp/src/components/TemplateEditor.tsx
  - webapp/src/components/Trips.test.tsx
  - webapp/src/components/Trips.tsx
  - webapp/src/design-tokens.test.ts
  - webapp/src/index.css
  - webapp/src/node-builtins.d.ts
findings:
  critical: 0
  warning: 5
  info: 1
  total: 6
status: issues_found
---

# Phase 04: Code Review Report

**Reviewed:** 2026-08-17T00:00:00Z
**Depth:** standard
**Files Reviewed:** 28
**Status:** issues_found

## Summary

Reviewed the FastAPI server (`app.py`), its test suite, and the full set of
webapp components/tests touched by this phase (visual-consistency pass:
`Botao`, typography, error-state styling, badges, etc.).

Most of the phase's stated goal — token/typography/error-state consistency —
is well executed and backed by targeted regression tests (`design-tokens.test.ts`,
the CONS-0x tests scattered through the component tests). No crashes,
security vulnerabilities, or data-loss risks were found in the reviewed
files. Cross-file reading (component ↔ `api.ts` ↔ `app.py` ↔ repository) did
turn up two functional defects that produce incorrect information or
incorrect UI state without ever surfacing an error to the user: a mutation
that silently reports success on server failure (`Duplicates.tsx`), and a
status endpoint whose per-source filter is silently ignored for one of its
response fields (`/api/sugestoes` `contagens`, consumed by `Review.tsx`).
Both are logic/error-handling defects rather than crashes or security gaps,
so they're reported as Warnings.

Three further warnings cover an inconsistent modal-error contract (Sidebar's
Google Takeout import silently discards the shared `ModalCaminho` error
contract that `App.tsx` correctly honors), an unsound TypeScript type
(`DoadoraMapa.lat/lon` declared non-nullable while the backend can send
`null`), and a confusing variable shadow in `Mapa.tsx`'s label-collision
geometry code.

## Warnings

### WR-01: `/api/sugestoes` `contagens` ignores `source_id`, misleading the per-fonte tab counts in Review

**File:** `fotoorganizer/server/app.py:1050` (endpoint `sugestoes`), consumed by `webapp/src/components/Review.tsx:63-73`

**Issue:** The Review screen's status tabs ("Pendentes N", "Aprovadas N",
"Rejeitadas N") are fed by:

```tsx
const { data: contagensData } = useQuery({
  queryKey: ["sugestoes", "contagens", status, fonte],
  queryFn: () => api.sugestoes(status, 0, 1, fonte),
});
...
const contagens = contagensData?.contagens ?? {};
```

The query key and the call both include `fonte` (the source filter selected
in the sidebar), which signals the author's intent that the badge counts be
scoped to the selected source. But on the server:

```python
@app.get("/api/sugestoes")
def sugestoes(status: str = "pendente", source_id: int | None = None, ...):
    filters = SuggestionFilters(status=status_enum, source_id=source_id, destino=destino)
    linhas = suggestion_repo.listar(filters, limit=..., offset=offset)
    contagens = suggestion_repo.contagens_por_status()   # <-- no filters at all
    ...
    return {
        "contagens": {s.value: n for s, n in contagens.items()},
        "total": suggestion_repo.contar(filters),          # <-- correctly filtered
        "itens": [...],
    }
```

`SuggestionRepository.contagens_por_status()` (`fotoorganizer/repositories/suggestions.py:208`)
takes no arguments and always groups over the *entire* catalog:

```python
def contagens_por_status(self) -> dict[SuggestionStatus, int]:
    with self._factory() as session:
        stmt = select(Suggestion.status, func.count()).group_by(Suggestion.status)
        return dict(session.execute(stmt).all())
```

So `total` (the group-list total, correctly filtered by `source_id`) and
`contagens[status]` (the tab badge, never filtered) can legitimately disagree
whenever a source filter is active — e.g. selecting a fonte with 50 pending
suggestions still shows "Pendentes 5048" (the whole-catalog count) on the tab.
No test exercises `source_id` against `contagens` (`tests/test_server_api.py`
only asserts `depois["contagens"]["aprovada"] == 2` in the unfiltered
single-source fixture, so the bug is invisible there).

**Fix:** Either scope `contagens_por_status` by the same `SuggestionFilters`
used for `contar`/`listar` (minus `status`, since it needs to break out by
status) and pass `source_id`/`destino` through, or explicitly document/label
this as a whole-catalog count in the UI (and stop passing `fonte` into the
query key, which currently implies scoping that doesn't happen):

```python
def contagens_por_status(self, *, source_id: int | None = None) -> dict[SuggestionStatus, int]:
    with self._factory() as session:
        stmt = select(Suggestion.status, func.count()).join(MediaFile, ...)
        if source_id is not None:
            stmt = stmt.where(MediaFile.source_id == source_id)
        stmt = stmt.group_by(Suggestion.status)
        return dict(session.execute(stmt).all())
```

### WR-02: `Duplicates.tsx` mutation never checks `response.ok` — failed actions report success

**File:** `webapp/src/components/Duplicates.tsx:29-38`

**Issue:** Every write in the app goes through `api.ts`'s `post`/`patch`/`put`
helpers, which all check `resposta.ok` and throw with the server's `detail`
message on failure (`api.ts:401-410`). `Duplicates.tsx` is the sole exception
in the reviewed file set — it rolls its own `fetch` directly in the
mutation, with no `.ok` check and no `onError` handler:

```tsx
const acao = useMutation({
  mutationFn: ({ url, body }: { url: string; body?: unknown }) =>
    fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : undefined,
    }),
  onSuccess: () =>
    void queryClient.invalidateQueries({ queryKey: ["duplicatas"] }),
});
```

`fetch` only rejects on network failure — it resolves normally for any HTTP
status, including 404/409/500. Because `mutationFn`'s returned promise always
resolves for a server error response, React Query treats it as a *success*:
`onSuccess` fires, `["duplicatas"]` is invalidated, and the UI proceeds as if
"marcar principal" / "ignorar grupo" / "desfazer" succeeded — with no error
ever surfaced to the user. `tests/test_server_api.py` has no coverage of a
failing `/api/duplicatas/*` call, and `Duplicates.test.tsx` has no test for
the failure path either, so this regressed silently.

Root cause: `api.ts` has no `marcarPrincipal`/`ignorarGrupo`/`desfazerGrupo`
helpers, so the component had to hand-roll the request instead of reusing the
shared, error-safe helper.

**Fix:** Add the missing helpers to `api.ts` and use them:

```ts
// api.ts
marcarPrincipal: (grupoId: number, mediaId: number) =>
  post<{ ok: boolean }>(`/api/duplicatas/${grupoId}/principal`, { media_id: mediaId }),
ignorarGrupo: (grupoId: number) =>
  post<{ ok: boolean }>(`/api/duplicatas/${grupoId}/ignorar`),
desfazerGrupo: (grupoId: number) =>
  post<{ ok: boolean }>(`/api/duplicatas/${grupoId}/desfazer`),
```

```tsx
// Duplicates.tsx
const acao = useMutation({
  mutationFn: (chamada: () => Promise<unknown>) => chamada(),
  onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["duplicatas"] }),
  onError: (e: Error) => setErro(e.message), // and render `erro` somewhere in the panel
});
```

### WR-03: Sidebar's Google Takeout modal ignores `ModalCaminho`'s own error contract

**File:** `webapp/src/components/Sidebar.tsx:55-60,163-169`, contract defined in `webapp/src/components/ModalCaminho.tsx:20-23`

**Issue:** `ModalCaminho` documents an explicit contract: when `erro` is
passed, "aparece acima dos botões e o modal permanece aberto — quem chamou
decide, não fechar sozinho, é o que evita engolir a falha." `App.tsx`'s own
usage (`abrirAdicionarPasta` flow) honors this correctly — it awaits
`job.escanear(...)`, only closes the modal `.then()` on success, and passes
`erro={erroPasta}` so a 422 keeps the modal open with the message visible
(covered by the "quando o POST /api/scan responde erro" test in `App.test.tsx`).

`Sidebar.tsx`'s usage for Google Takeout does neither:

```tsx
const executar = (acao: Promise<void>) => {
  setErro(null);
  acao.catch((e: Error) => setErro(e.message));   // fire-and-forget
  setModal(null);                                  // closes unconditionally, before the promise settles
  setMenuAberto(false);
};
...
{modal === "takeout" && (
  <ModalCaminho
    titulo="Pasta do Google Takeout (extraída)"
    onConfirmar={(caminho) => executar(job.importarTakeout(caminho))}
    onCancelar={() => setModal(null)}
    // no `erro` prop passed at all
  />
)}
```

If the Takeout path is invalid (backend 422), the modal has already vanished
by the time the error resolves; the message appears as a stray line at the
bottom of the sidebar's action panel instead of inline in the dialog next to
the field that caused it — the exact anti-pattern the shared component's
docstring was written to prevent. There's no test covering the Sidebar
Takeout failure path (unlike `App.test.tsx`'s equivalent for
`Adicionar pasta…`), so this went unnoticed.

**Fix:** Mirror `App.tsx`'s pattern — keep the modal open until the promise
settles, and pass `erro` through:

```tsx
const [erroModal, setErroModal] = useState<string | null>(null);
...
{modal === "takeout" && (
  <ModalCaminho
    titulo="Pasta do Google Takeout (extraída)"
    erro={erroModal}
    onConfirmar={(caminho) => {
      setErroModal(null);
      job.importarTakeout(caminho)
        .then(() => setModal(null))
        .catch((e: Error) => setErroModal(e.message));
    }}
    onCancelar={() => { setModal(null); setErroModal(null); }}
  />
)}
```

### WR-04: `DoadoraMapa.lat`/`lon` typed as non-nullable, but the backend can send `null`

**File:** `webapp/src/api.ts:228-235` (type), `fotoorganizer/server/app.py:981-994` (source of the data), used defensively in `webapp/src/components/Mapa.tsx:107,181`

**Issue:** The TS interface declares:

```ts
export interface DoadoraMapa {
  id: number;
  nome: string;
  lat: number;
  lon: number;
  camera: string | null;
  no_grupo: boolean;
}
```

but `app.py`'s `mapa()` endpoint builds the `doadoras` list straight from
`MediaFile.gps_lat`/`gps_lon`, which are nullable columns:

```python
"doadoras": [
    {
        "id": d.id,
        "nome": d.nome,
        "lat": d.gps_lat,
        "lon": d.gps_lon,
        ...
    }
    for d in doadoras.values()
],
```

`Mapa.tsx` itself proves the type is unsound — it has to defensively
re-check nullability at both consumption sites despite TS claiming it's
unnecessary:

```ts
// agruparPorLugar
if (doadora.lat == null || doadora.lon == null) continue;

// limitesComDoadoras
d.lat == null || d.lon == null ? acc : { ... }
```

A future call site that trusts the declared type (e.g. `doadora.lat.toFixed(5)`
without a guard) would compile cleanly and crash at runtime on a `null` donor
coordinate.

**Fix:** Make the type match reality:

```ts
export interface DoadoraMapa {
  id: number;
  nome: string;
  lat: number | null;
  lon: number | null;
  camera: string | null;
  no_grupo: boolean;
}
```

### WR-05: `rotulosSemColisao` shadows the module-level `ALTURA` constant with an unrelated value

**File:** `webapp/src/components/Mapa.tsx:35,440`

**Issue:** The module declares the SVG viewBox height at the top:

```ts
const LARGURA = 1000;
const ALTURA = 620;
```

`rotulosSemColisao`, a dense function doing label-collision geometry, then
shadows it with a completely different meaning (label box height in px):

```ts
export function rotulosSemColisao(...): RotuloMapa[] {
  const ALTURA = 12;
  const LARGURA_CARACTERE = 6.5;
  ...
```

Both names are legal JS/TS (the local binding correctly shadows the outer
one, so there's no runtime bug today), but this is exactly the kind of
variable shadowing the review is meant to catch: a maintainer skimming this
620-line geometry file, searching for "ALTURA" to change the SVG viewBox size
would land on the wrong declaration first and could easily edit the label
height by mistake, or vice versa.

**Fix:** Rename the local constant, e.g. `ALTURA_ROTULO = 12`.

## Info

### IN-01: `api.ts` builds query strings by hand in `sugestoes()`/`gruposDeSugestoes()`, inconsistent with the `URLSearchParams` pattern used everywhere else

**File:** `webapp/src/api.ts:507-517,536-540`

**Issue:** Most list endpoints in `api.ts` (`midia`, `linhaDoTempo`, `pastas`)
build the query string via `URLSearchParams`, which handles encoding
uniformly. `sugestoes` and `gruposDeSugestoes` instead concatenate template
strings and manually `encodeURIComponent` only the `destino` param:

```ts
sugestoes: (status, offset = 0, limit = 200, sourceId?, destino?) =>
  json<PaginaSugestoes>(
    `/api/sugestoes?status=${status}&offset=${offset}&limit=${limit}` +
      (sourceId ? `&source_id=${sourceId}` : "") +
      (destino ? `&destino=${encodeURIComponent(destino)}` : ""),
  ),
```

Not currently exploitable (status/offset/limit/sourceId are all
programmatically constrained values, never raw user text), but it's a
maintenance trap: the next person who adds a free-text filter to one of these
two functions is one copy-paste away from an unencoded query param.

**Fix:** Use `URLSearchParams` here too, for consistency with the rest of the
module.

---

_Reviewed: 2026-08-17T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
