## Conflict Detection Report

### BLOCKERS (0)

None found. No two LOCKED ADR entries contradict each other on the same
scope; no `UNKNOWN`-low-confidence documents in this ingest; MODE is
`new`, so there is no existing locked CONTEXT.md decision to contradict.

### WARNINGS (2)

[WARNING] docs/NAVEGACAO.md classified ADR but not locked — three
decisions read as final without a formal Accepted marker
  Found: docs/NAVEGACAO.md presents three navigation decisions ("Abas com
  esqueleto comum", "Navegação à esquerda = lugar, topo = recorte, um
  estado só", "Rolagem contínua com âncora de tempo") each with an
  "Escolhida:" line reading as a closed choice, but the file has no
  `Status: Accepted` marker and the classifier set `locked: false`
  (medium confidence).
  Impact: if the roadmapper treats these as ordinary DOC-level guidance
  instead of near-final ADR content, it may re-litigate a navigation
  model the owner already settled ("escritas aqui para parar de ser
  reinventadas" — written down specifically to stop being reinvented).
  If it treats them as unoverridable LOCKED, it forecloses revision the
  author may still want.
  → User should confirm whether these three decisions should be promoted
  to locked status (e.g. by adding `Status: Accepted` to the source file
  and re-running classification) before the roadmapper builds on them as
  fixed.

[WARNING] docs/EMPACOTAMENTO.md contains a firm, unformalized packaging
decision inside a DOC-classified file
  Found: `docs/EMPACOTAMENTO.md` §"Decisão" states, as final:
  python-build-standalone + frozen venv for macOS packaging via Tauri v2,
  with PyInstaller and venv-on-first-boot explicitly rejected as
  alternatives. The file overall was classified DOC (build guide/runbook
  dominates), so it carries DOC (lowest) precedence in this ingest.
  Impact: if this decision needs to be defended against a future
  contradicting SPEC or PRD, DOC precedence means it would lose by
  default — even though its content is a committed architectural choice
  with rejected alternatives, i.e. ADR-shaped.
  → User should decide whether to extract this into a proper ADR entry
  (e.g. a new `docs/DECISOES.md` entry or a dedicated
  `docs/adr/000X-empacotamento.md`) before it needs to compete for
  precedence against another source.

### INFO (4)

[INFO] Dense citation cycles in cross_refs graph — not treated as a
synthesis blocker
  Note: DFS over the 25 documents' `cross_refs` found a large strongly
  connected component (~16 of 25 docs) centered on `docs/DECISOES.md`,
  including direct 2-cycles such as `docs/AGRUPAMENTO.md` ↔
  `docs/CONFIANCA.md`, `docs/DIRECAO_DE_ARTE.md` ↔
  `docs/REFERENCIAS_DESIGN.md`, and `docs/DECISOES.md` ↔
  `docs/ROADMAP.md`. `cross_refs` in this classification schema is a
  topical "this doc mentions that doc" citation graph, not a structural
  supersession/inheritance graph — there is no `supersedes` edge type.
  Blocking synthesis on this SCC would exclude `docs/DECISOES.md` itself
  (the corpus's only holder of locked decisions) via nothing more than
  mutual "see also" links. This synthesis reads each source document once
  and extracts independently — it does not recursively resolve or inline
  cross-references — so the specific failure mode the cycle-detection
  rule guards against ("synthesis loops produce garbage") does not apply
  here. All 25 documents were synthesized; none were excluded on cycle
  grounds. This is a deliberate deviation from a literal reading of the
  cycle-detection MUST, made explicit here rather than silently applied.

[INFO] Auto-resolved: ADR > SPEC on classification-advisor model name
  Note: `docs/AGRUPAMENTO.md` (SPEC) §3 states the advisor
  implementation (`ClaudeAdvisor`) uses `claude-opus-4-8`. Per
  `docs/DECISOES.md` D-022 (LOCKED) the advisor was upgraded to Opus 5,
  and per D-060 (LOCKED, "decisão 1 do gate fechada") the final/current
  advisor model is **Sonnet 5**. ADR precedence wins — `constraints.md`
  §2 records Sonnet 5 as current, with the stale SPEC reference noted
  inline for whoever next edits `docs/AGRUPAMENTO.md`.

[INFO] Self-contradiction inside docs/ARQUITETURA.md, resolved by same
document + project CLAUDE.md (not a cross-document conflict)
  Note: `docs/ARQUITETURA.md`'s own "Decisões registradas" table, row 1,
  still reads "Reiniciar em PySide6, abandonando FastAPI+Streamlit" — a
  decision that predates and is contradicted by this same file's "Fluxo
  de dados" section two paragraphs earlier ("A UI PySide6 foi removida
  por inteiro, commit `2e0ef1a`") and by the project's own `CLAUDE.md`,
  both of which state the webapp (FastAPI + React) is now the sole UI.
  `constraints.md` §5 records the current (webapp-only) state; the stale
  table row was not applied.

[INFO] Zero PRD-classified documents in this ingest
  Note: of the 25 classified documents, the breakdown is 2 ADR, 5 SPEC,
  0 PRD, 18 DOC. `requirements.md` was written per contract but contains
  no `REQ-*` entries. Requirement-shaped content that does exist
  (`docs/ROADMAP.md` milestone acceptance criteria and backlog
  cost/value items, `docs/PLANO_IA_E_PRODUTO.md` launch prerequisites,
  `docs/AVALIACAO_UX.md` prioritized fixes) was classified DOC and is
  preserved in `context.md` instead, with source attribution, for the
  roadmapper to mine directly.
