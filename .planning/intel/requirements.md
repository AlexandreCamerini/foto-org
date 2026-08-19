# Requirements (PRD intel)

**No documents in this ingest were classified `PRD`.** Of the 25 classified
documents, the type breakdown was: 2 ADR, 5 SPEC, 0 PRD, 18 DOC. This file
is written per the standard synthesis contract even though there is no PRD
content to extract in this batch.

This is not a failure state — it reflects the actual shape of the Foto
Organizer doc corpus at ingest time: product requirements live implicitly
inside `docs/ROADMAP.md` (milestone acceptance criteria + backlog
cost/value items), `docs/PLANO_IA_E_PRODUTO.md` (launch prerequisites),
and `docs/AVALIACAO_UX.md` (prioritized fix backlog) — all three
classified `DOC`, not `PRD`, because they read as narrative/rationale
reports rather than formal requirement-with-acceptance-criteria documents.
Their content is preserved in `context.md` under the relevant topics, with
source attribution, for the roadmapper to mine directly.

**If `gsd-roadmapper` needs formal requirements**, it should either:
1. Derive them from `docs/ROADMAP.md`'s milestone "Aceite" sections and
   backlog items (see `context.md` → Roadmap / backlog), or
2. Flag to the user that no PRD-classified source exists and ask whether
   one should be authored, or whether `docs/ROADMAP.md` should be
   reclassified/promoted on a future ingest pass via `--manifest`.

No `REQ-*` IDs are minted in this file since there is no PRD source to
derive them from.
