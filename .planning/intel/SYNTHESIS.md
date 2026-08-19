# Synthesis Summary

Entry point for `gsd-roadmapper`. Source: 25 documents classified under
`.planning/intel/classifications/`, ingest mode `new`.

## Doc counts by type

- ADR: 2 (`docs/DECISOES.md`, `docs/NAVEGACAO.md`)
- SPEC: 5 (`docs/AGRUPAMENTO.md`, `docs/CONFIANCA.md`,
  `docs/DIRECAO_DE_ARTE.md`, `docs/desenho-inventario-por-pasta.md`,
  `docs/ARQUITETURA.md`)
- PRD: 0
- DOC: 18 (all remaining classified files)

## Decisions locked

- 59 of 73 entries in `docs/DECISOES.md` are LOCKED (individual
  `Status:` line resolved as decided). 14 are PENDING (still awaiting
  owner/measurement). See `decisions.md` for the full per-entry table,
  including 3 entries (D-035, D-036, D-037) whose lock status was
  inferred from surrounding prose rather than a clean status string
  (flagged inline for transparency).
- `docs/NAVEGACAO.md`'s 3 decisions are presented as final but not
  formally locked (classifier `locked: false`, medium confidence) — see
  WARNING in `INGEST-CONFLICTS.md`.
- 1 additional firm decision found embedded in a DOC-classified file
  (`docs/EMPACOTAMENTO.md`, packaging approach) — not promoted to ADR
  status in this synthesis; flagged as WARNING.

## Requirements extracted

- 0. No documents classified PRD in this ingest. `requirements.md`
  exists per contract with an explanatory note and pointers to
  requirement-shaped DOC content (`docs/ROADMAP.md`,
  `docs/PLANO_IA_E_PRODUTO.md`, `docs/AVALIACAO_UX.md`) preserved in
  `context.md`.

## Constraints

- 5 entries, one per SPEC document: evidence/confidence aggregation
  model, grouping cascade + correlation + album tie-break, design tokens
  + 3-panel layout + map component, per-folder inventory schema +
  integration point, system architecture (data flow/schema/risks).
- Type breakdown: 2 schema-heavy (evidence model, inventory), 1
  protocol/algorithm (grouping cascade), 1 UI/design-system contract, 1
  combined schema+NFR (architecture).

## Context topics

- 18 DOC-sourced topic entries in `context.md`: roadmap/backlog, phase-5
  AI/product plan, geo-first diagnostic, post-gate-fase5 audit (18
  findings), functionality audit (fase 2), architecture audit (fase 1),
  UX audit (multi-round), AI-reach audit, metadata coverage, metadata
  plan, signal inventory, event-subdivision grouping, estimated-place
  rationale, packaging guide, design-token references, privacy
  commitments, method of work, instructions summary.

## Conflicts

- **0 blockers**, **2 warnings**, **4 info** entries. Full detail in
  `../INGEST-CONFLICTS.md`.
- Warnings need user resolution before the roadmapper treats
  `docs/NAVEGACAO.md`'s decisions as locked, and before
  `docs/EMPACOTAMENTO.md`'s packaging decision competes for ADR-level
  precedence against any future contradicting source.
- One real auto-resolved cross-doc contradiction was found and applied:
  ADR (D-022/D-060, Sonnet 5) beats stale SPEC reference
  (`docs/AGRUPAMENTO.md`, `claude-opus-4-8`).
- One deliberate deviation from a literal instruction is logged as INFO,
  not silently applied: cycle detection found a large citation-graph SCC
  (mutual "see also" links centered on `docs/DECISOES.md`); this was not
  treated as a synthesis blocker because extraction here reads each
  source once, independently, with no recursive reference resolution.
  See the INFO entry in `../INGEST-CONFLICTS.md` for the specific cyclic
  pairs and full rationale.

## Files

- `decisions.md` — ADR intel (73-entry DECISOES.md index +
  NAVEGACAO.md's 3 decisions + 1 unformalized candidate)
- `requirements.md` — PRD intel (empty, explained)
- `constraints.md` — SPEC intel (5 entries)
- `context.md` — DOC intel (18 topic entries)
- `../INGEST-CONFLICTS.md` — full conflict report (0 blockers / 2
  warnings / 4 info)
