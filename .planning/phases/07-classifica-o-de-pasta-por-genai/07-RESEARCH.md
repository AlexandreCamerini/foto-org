# Phase 7: Classificação de pasta por GenAI - Research

**Researched:** 2026-08-18
**Domain:** Anthropic API batch-classification call shape, pre-flight cost estimation, `SuggestionEngine` cascade integration, opt-in config storage
**Confidence:** HIGH — every recommendation below is grounded either in code already in this repo (`advisor.py`, `lexico.py`, `engine.py`, `confidence.py`, `settings.py`, `repositories/lexico.py`, `cli.py`) or in official Anthropic docs fetched directly in this session. No new library, no unverified package.

## Summary

Phase 7 has almost no genuinely new technical risk — it is a second instance of a pattern the codebase already runs twice (`ClaudeAdvisor` for cluster categorization, `LexicoClaude` for name lookup). The batching shape D-03 requires ("one call covers every confirmed folder in a session, one structured output item per folder") is **not new** — `LexicoClaude._lote()` in `fotoorganizer/classification/lexico.py:149-196` already does exactly this: N names in, `output_config.format=json_schema` with an array-of-objects schema, one object per input name, filtered by "only accept a name I actually asked about." The GENAI-02/03 call should copy this shape almost verbatim, with folders instead of names and `{cidade, pais, evento, categoria, justificativa}` instead of `{categoria}`.

**One recommendation in this document is research-derived, not something CONTEXT.md/ROADMAP.md asked for or locked, and the planner should treat it as a proposal to validate, not a closed decision:** persisting the GenAI folder→city/event result in a **new dedicated table** (Pattern 3/4 below), rather than writing straight into `Evidence`. CONTEXT.md and ROADMAP.md never mention a new table — they describe the call shape (D-03) and the cascade slot (`llm_pasta` in `SCORES_REFERENCIA`), but say nothing about durability between the interactive session and the next `SuggestionEngine.gerar()` run. This research derived the need for a persistence layer by reading `engine.py`'s regeneration logic directly: `gerar()` deletes and rebuilds `Evidence` per-media on every run for undecided media (`engine.py:1127`), so anything written only into `Evidence` from outside that loop is silently lost on the next regeneration (see Pitfall 1). The recommended shape — a small table keyed by `pasta`, structurally identical to the already-shipped `NomeClassificado`/`LexicoRepository` (`fotoorganizer/models/lexico.py`, `fotoorganizer/repositories/lexico.py`) — is the same solution this codebase already chose for an analogous problem (léxico of folder/album names). **This should be surfaced explicitly to the user/discuss-phase before the planner locks a migration and model around it**, since it is new schema the user hasn't seen proposed, not a research confirmation of an existing decision.

The other substantive judgment call in this document — the exact `SCORES_REFERENCIA["llm_pasta"]` numeric value — is **explicitly not resolved** here; see Open Question 1 and Pitfall 2, which are deliberately consistent with each other: this research does not recommend locking a number silently, because this project's own convention (D-074, D-059/D-060) is to measure confidence scores against real data before locking them, not to assign them by analogy.

**Primary recommendation:** Copy `LexicoClaude`'s batched-array call shape (not `ClaudeAdvisor`'s single-cluster shape) for the Anthropic call; use `client.messages.count_tokens` (already in the pinned SDK, confirmed free and exact) for the pre-session cost estimate instead of a hand-rolled token-per-folder heuristic; treat the new-persistence-table design and the `llm_pasta` score value as two open items for the planner to route back to the user rather than silently lock.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Candidate folder pre-filter (D-01) | API/Backend (`repositories/`) | — | Pure SQL query over `MediaFile.pasta`/`Suggestion`/`Evidence` — same tier as existing repository queries, no new pattern |
| Cost estimation (token count + price) | API/Backend | — | Needs the exact same payload/schema that will be sent — must be server-side, not re-derived in the browser |
| Anthropic API call (classification) | API/Backend (`classification/`) | — | Same tier as `ClaudeAdvisor`/`LexicoClaude` today — opt-in gated, credential never touches the browser |
| Classification result persistence | Database/Storage (new table — proposal, see Summary) | — | Must survive independently of `Evidence`, which `SuggestionEngine.gerar()` deletes/rebuilds every run — same reasoning as `nomes_classificados` |
| Antes/depois review UI (approve per folder) | Frontend Server (React) | API/Backend (endpoint to fetch/approve) | Same tier split as `EscritaExif.tsx` + `/api/exif/*` — UI renders, backend owns the checkbox-confirm→commit transition |
| Evidence cascade rung (`llm_pasta`) | API/Backend (`classification/engine.py`) | Database/Storage (`SCORES_REFERENCIA`) | Cascade logic lives in `engine.py`; the score constant lives in `confidence.py` — same split as every other origin today |
| Cost confirmation UI (D-04/D-05) | Frontend Server (React) | — | Narrow, single-purpose modal — "UI hint: yes, escopo estreito" per ROADMAP.md |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `anthropic` Python SDK | 0.116.0 (confirmed installed in `.venv`, matches `pyproject.toml` floor `>=0.116`) | Structured-output classification call + pre-flight token count | Already the sole LLM client in the codebase (`advisor.py`, `lexico.py`). `client.messages.count_tokens` confirmed present on this exact installed version via `inspect.signature` in this session — no SDK bump needed. |

No new package. `pyproject.toml`'s `[project.optional-dependencies].llm` extra already covers everything this phase needs.

### Supporting patterns (not libraries)

| Pattern | Purpose | When to Use |
|---------|---------|-------------|
| Batched array-schema call (`LexicoClaude._lote`, `lexico.py:155-196`) | One call, N folders in, N structured results out | This is D-03's call shape — reuse the pattern directly, don't design a new one |
| Persisted lookup table keyed by the classified string (`NomeClassificado`, `models/lexico.py`) | Survive `SuggestionEngine.gerar()`'s per-run `Evidence` rebuild; never silently overwrite a human correction | **Proposal, not a locked decision** — see Summary. GENAI-03's result needs some durability mechanism; this is the closest in-repo precedent, but the shape itself should be confirmed with the user before the planner commits a migration to it. |
| `client.messages.count_tokens` (confirmed present, official endpoint `POST /v1/messages/count_tokens`) | Exact, free, pre-flight input-token count for the *actual* payload about to be sent | Use for D-04's cost estimate — see Common Pitfalls for why a hand-rolled estimate is worse here |

**Installation:** none — `anthropic>=0.116` is already pinned and installed.

**Version verification:**
```bash
.venv/bin/python -c "import anthropic; print(anthropic.__version__)"   # → 0.116.0, confirmed in this session
.venv/bin/python -c "import anthropic; c=anthropic.Anthropic(api_key='x'); print(hasattr(c.messages,'count_tokens'))"  # → True, confirmed in this session
```

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Sonnet 5 (locked, D-059/D-060 a fortiori per CONTEXT.md/ROADMAP.md) | Haiku 4.5 | Explicitly out of scope per ROADMAP.md "Explicitly out of scope: reabrir a escolha de modelo sem medição". Not re-researched here — D-059/D-060 already closed this with real measurement against 104 clusters, and folder-name-only input is *sparser* evidence than the cluster payload that was measured, so the failure mode (cheap model asserts where a stronger model abstains) applies at least as strongly. |
| `client.messages.count_tokens` for cost preview | Local tiktoken-style estimate (chars/4) | Anthropic's own docs (fetched this session) explicitly warn against `tiktoken` for Claude token counts ("undercounts by ~15–20% on typical text, more on code/non-English"). Portuguese folder names + JSON schema overhead make a generic heuristic materially wrong; the real endpoint is free and exact. |
| One call for all folders (D-03, locked) | Message Batches API (50% discount, async) | Explicitly closed by D-03/ROADMAP.md: "síncrono, porque a UX é interativa e o custo precisa ser visível por sessão" — Batch API's 24h async model doesn't fit "sessão interativa". `.planning/research/STACK.md` had flagged Batch API as a candidate for a catalog-wide sweep; the discuss-phase session explicitly rejected that framing in favor of interactive single-call-per-session. Do not resurrect the Batch API question — it's closed. |

## Package Legitimacy Audit

No new external package is being installed in this phase — `anthropic>=0.116` is already a dependency, already installed, already used in production code (`advisor.py`, `lexico.py`). The Package Legitimacy Gate does not apply; there is nothing new to run `slopcheck`/`npm view`/`pip index versions` against.

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. Dono abre sessão de classificação (UI: novo botão/tela)        │
└───────────────────────────┬─────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. Backend: pré-filtro de candidatas (D-01)                       │
│    Query: pastas com Evidence.categoria OU Evidence.cidade/pais   │
│    ausentes, agregadas por MediaFile.pasta                        │
└───────────────────────────┬─────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. UI mostra lista, dono desmarca linhas pontuais (D-01)          │
└───────────────────────────┬─────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. Backend: monta payload (nome pasta + metadado já catalogado,   │
│    NUNCA imagem) para as pastas confirmadas                       │
│    → client.messages.count_tokens(mesmo system/schema/payload)    │
│    → tokens × preço Sonnet 5 = custo estimado (R$/US$)            │
└───────────────────────────┬─────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. UI mostra custo estimado; dono confirma (D-04/D-05, sem teto)  │
└───────────────────────────┬─────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ 6. Backend: UMA chamada messages.create (D-03), output_config     │
│    json_schema, array de N itens, thinking disabled               │
│    → falha/timeout/429: never-crash, log + resultado vazio         │
└───────────────────────────┬─────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ 7. Backend: grava em persistência própria (PROPOSTA — ver Summary,│
│    ex. tabela nova PastaClassificada), chave = pasta,             │
│    origem='llm', nunca sobrescreve origem='manual'/já confirmada  │
│    (D-02: só completa campo vazio)                                │
│    Item ambíguo/"não sei" (D-06): não grava nada                  │
└───────────────────────────┬─────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ 8. UI: tela antes/depois por pasta (reuso do padrão de checkbox    │
│    de Revisão), dono aprova/rejeita por linha                     │
└───────────────────────────┬─────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ 9. Próximo SuggestionEngine.gerar(): cascata lê a persistência     │
│    nova (bulk, uma consulta — mesmo padrão de _carregar_curadoria)│
│    novo degrau "llm_pasta" alimenta _categoria/_evidencias_geo    │
│    quando pasta E sessão E advisor de cluster não decidiram        │
└─────────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure

```
fotoorganizer/
  classification/
    advisor.py          # existente — ClaudeAdvisor (cluster), não tocar o schema/tipo
    lexico.py            # existente — padrão de call em lote a copiar
    location_advisor.py  # NOVO — LocationAdvisorResult, ClassificacaoDePastaClaude
    confidence.py         # existente — adicionar "llm_pasta" a SCORES_REFERENCIA
                           # (valor NÃO travado por esta pesquisa — ver Open Question 1)
    engine.py             # existente — novo degrau na cascata (_categoria/_evidencias_geo)
  models/
    lexico.py             # existente — modelo de referência (NomeClassificado)
    pasta_classificacao.py  # PROPOSTO (não locked) — PastaClassificada(pasta PK, cidade,
                              #   pais, evento, categoria, justificativa, origem,
                              #   classificado_em) — confirmar com o dono antes de migrar
  repositories/
    lexico.py              # existente — modelo de referência (LexicoRepository)
    pasta_classificacao.py  # PROPOSTO — ClassificacaoPastaRepository (conhecidas/salvar)
  database/migrations/versions/
    0020_pasta_classificacoes_genai.py  # PROPOSTO — próximo número livre (0019 é o último hoje)
  server/
    app.py                 # existente — novos endpoints /api/genai-pasta/* (padrão /api/exif/*)
webapp/src/
  components/
    ClassificacaoPasta.tsx  # NOVO — modal de custo + tela antes/depois (padrão EscritaExif.tsx)
```

### Pattern 1: Batched array-schema call (reuse `LexicoClaude`, not `ClaudeAdvisor`)

**What:** One `messages.create` call, `output_config.format=json_schema` with a top-level array, one object per input item, `thinking={"type": "disabled"}`, response filtered to only accept items that were actually asked about.

**When to use:** Exactly D-03's requirement — this is the call shape, already proven in this codebase, that answers "N folders in, one proposal per folder out, one call."

**Example (adapted from `fotoorganizer/classification/lexico.py:52-196`, confirmed in this session against the installed SDK):**
```python
# Source: fotoorganizer/classification/lexico.py (existing, in-repo pattern)
# — GENAI-02/03 should follow this shape, not advisor.py's single-object shape.

_SCHEMA = {
    "type": "object",
    "properties": {
        "pastas": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "pasta": {"type": "string"},
                    "cidade": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                    "pais": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                    "categoria": {
                        "anyOf": [
                            {"type": "string", "enum": ["Viagens", "Eventos", "Família"]},
                            {"type": "null"},
                        ],
                    },
                    "justificativa": {"type": "string"},
                },
                "required": ["pasta", "cidade", "pais", "categoria", "justificativa"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["pastas"],
    "additionalProperties": False,
}

response = client.messages.create(
    model="claude-sonnet-5",
    max_tokens=16000,          # cobre raciocínio+resposta; lexico.py usa o mesmo teto
    thinking={"type": "disabled"},
    system=_SYSTEM,
    output_config={"format": {"type": "json_schema", "schema": _SCHEMA}},
    messages=[{"role": "user", "content": json.dumps({"pastas": payload}, ensure_ascii=False)}],
)
# Filter response the same way lexico.py:189-196 does: only accept items whose
# "pasta" matches what was actually sent — never let the model introduce a folder
# the catalog doesn't have.
```

**Prompt caching — no caching in this phase, and Pattern 2's cost formula below is written consistently with that:** `STACK.md` already established (HIGH confidence, official docs) that Sonnet/Haiku need a **≥1,024-token cached block** to break even. The existing `_SYSTEM` strings in both `advisor.py` and `lexico.py` are well under that floor. D-03's payload varies per session (different folder lists every time) — only the **system prompt** is a caching candidate, and it's short. **Recommendation: do not wire `cache_control` for this phase.** It would not pay off at the current system-prompt length, and artificially padding the prompt to clear the floor just to enable caching is not a real cost win — the caching-write premium (1.25x on a 5-minute write) would exceed the eventual read discount unless the same exact system block is reused across many calls in a tight window, which a once-per-session, user-confirmed call is not. Because caching is not recommended, Pattern 2's cost formula intentionally uses only base input/output pricing, no cache-write/cache-read multipliers — the two sections are consistent by design, not by omission.

### Pattern 2: Precise pre-flight cost estimate via `count_tokens`, not a heuristic

**What:** Call `client.messages.count_tokens` with the **exact same** `model`, `system`, `output_config`, and `messages` payload that will be sent to `messages.create` — this is a free, no-generation API call that returns the true input token count for that exact request (confirmed via official docs, fetched this session: `POST /v1/messages/count_tokens`, `MessageTokensCount{input_tokens}`).

**When to use:** D-04's cost-estimate-before-confirm step. This is strictly better than counting characters or estimating tokens-per-folder, because:
1. The exact payload (N folders × metadata fields) is already fully known at estimate time — there's no reason to approximate what can be counted exactly, for free.
2. The JSON schema itself (`output_config`) consumes input tokens too — a hand-rolled estimate that only counts the folder-name text would systematically undercount.
3. Anthropic's own docs explicitly warn against generic tokenizers (tiktoken) for Claude — Portuguese text and JSON structure make heuristics worse, not just imprecise.

**Example:**
```python
# Source: verified against installed anthropic==0.116.0 SDK signature (this session)
# and https://platform.claude.com/docs/en/api/messages/count_tokens (official docs)
count = client.messages.count_tokens(
    model="claude-sonnet-5",
    system=_SYSTEM,
    output_config={"format": {"type": "json_schema", "schema": _SCHEMA}},
    messages=[{"role": "user", "content": json.dumps({"pastas": payload}, ensure_ascii=False)}],
)
input_tokens = count.input_tokens   # exact, confirmed by the API itself

# Output tokens cannot be counted pre-flight (nothing has been generated yet).
# Estimate conservatively: N folders × (schema field count × ~15-25 tokens/field
# for short PT-BR strings) is a reasonable upper bound — or simply price against
# max_tokens as a worst-case ceiling, since Sonnet 5 output is $10/MTok and a
# folder-classification response is small (tens of folders × a few short fields).
#
# No prompt-caching multiplier applied here — consistent with Pattern 1's
# recommendation not to wire cache_control for this phase's system-prompt size.
custo_usd = (input_tokens / 1_000_000) * 2.0 + (max_tokens_estimado / 1_000_000) * 10.0
```

**Output-token estimation caveat (be honest about this in the UI):** unlike input tokens, output tokens genuinely cannot be known before generation. The safest approach for D-04 is to show a **range** (best case: minimal per-folder JSON; worst case: `max_tokens` ceiling) or to price the worst case only, since Sonnet 5 output pricing ($10/MTok) applied to a bounded, small `max_tokens` value for a folder-count in the tens is already a small absolute number — the existing precedent (`lexico.py` uses `max_tokens=16000` for up to 200 names/batch) suggests output cost is not the dominant term here; input tokens (folder names + metadata + schema) dominate. Confirm this assumption empirically once real session sizes are known — flag as `[ASSUMED]`, see Assumptions Log A2.

### Pattern 3: Persisted cache table, not a live cascade call (`NomeClassificado`/`LexicoRepository`) — PROPOSAL, confirm before locking

**What:** A new SQLAlchemy model + repository keyed by the classified string (`pasta`), following `fotoorganizer/models/lexico.py:10-31` and `fotoorganizer/repositories/lexico.py:1-56` structurally.

**Status: this is this research's own inference, not a requirement from CONTEXT.md/ROADMAP.md.** Neither document mentions a new table. This pattern exists in this document because Pitfall 1 (below) is real and demonstrable by reading `engine.py` directly — but the *specific* shape (new table vs. some other durability mechanism) is a design choice the planner should confirm, ideally with the user, before committing a schema migration to it. Treat this section as "here is a proven-safe answer if you need one," not "here is what to build."

**When to use:** GENAI-03's persistence, if the planner confirms a durability mechanism is needed (this research believes it is — see Pitfall 1 — but flags this as a proposal, not a lock).

**Why not write directly into `Evidence`:** `SuggestionEngine._persistir_sugestao` (`engine.py:1114-1128`) deletes and rebuilds `Evidence` rows for every *undecided* media on every `gerar()` call. Anything written straight into `Evidence` outside of a `gerar()` run would be silently wiped on the next regeneration unless `gerar()` itself is taught to re-derive it — which is exactly what the cascade rung (Pattern 4) does, reading from the new persisted table, the same way `_carregar_curadoria` (`engine.py:115-132`) reads `MetadataEntry` fresh on every call instead of writing directly into `Evidence` from outside the generation loop.

**Example shape (proposed, not existing code — sketch for the planner to validate):**
```python
# Source: structural precedent = fotoorganizer/models/lexico.py:10-31 (NomeClassificado)
class PastaClassificada(Base):
    __tablename__ = "pasta_classificacoes_genai"

    pasta: Mapped[str] = mapped_column(primary_key=True)
    cidade: Mapped[str | None]
    pais: Mapped[str | None]
    categoria: Mapped[str | None]     # "Viagens" | "Eventos" | "Família" | None
    evento: Mapped[str | None]
    justificativa: Mapped[str]
    # 'llm' | 'manual' — dono aprovando/editando na tela antes/depois grava
    # 'manual' aqui, e uma futura sessão nunca sobrescreve isso (mesma
    # disciplina de NomeClassificado.origem).
    origem: Mapped[str] = mapped_column(default="llm")
    classificado_em: Mapped[datetime] = mapped_column(default=utcnow)
```
D-02 ("evidência parcial nunca é sobrescrita — só complementa o campo que falta") maps directly onto this table's write path: the session's `salvar()` (mirroring `LexicoRepository.salvar`, `repositories/lexico.py:32-56`) must check per-field whether `cidade`/`categoria` is already non-null before overwriting, not just check row existence.

### Pattern 4: New cascade rung in `SuggestionEngine`

**What:** `classification/confidence.py`'s `SCORES_REFERENCIA` gets one new key (value TBD — see Open Question 1, do not lock silently); `classification/engine.py`'s `_categoria` (line 974) and `_evidencias_geo` (line 872) get a new fallback step that queries the bulk-loaded classification lookup (loaded once per `gerar()` call, same pattern as `_carregar_curadoria` at `engine.py:115`) — the lookup source is whatever persistence mechanism Pattern 3 resolves to.

**Where exactly (file:line, read directly from `engine.py` in this session):**
- `_categoria` (`engine.py:974-1015`) is a 3-step cascade: (1) `pasta` segment match (`_CATEGORIAS_PASTA`, line 978), (2) session type from the deterministic GPS/geocoding cascade (line 990), (2b) human XMP/IPTC keyword (line 1003), (3) `sessao.categoria` from the existing cluster advisor (line 1011, `origem="llm"`, score 0.55). **`llm_pasta` slots in as a new step 2c/3b** — after the pasta-word match and the deterministic session cascade have both failed to name a category, before falling through to `None`. Concretely: add a lookup against the bulk-loaded `pasta_classificacoes` dict keyed by `media.pasta`, checked either just before or just after step 3 (existing cluster advisor) — **not replacing it**, since D-03/ROADMAP.md require `llm_pasta` to remain a sibling evidence type, never merged into `AdvisorResult`/the existing `"llm"` origin.
- `_evidencias_geo` (`engine.py:872-972`) is a 3-step cascade: (1) own GPS + offline geocoding (line 877), (1b) inherited GPS via cross-source correlation (line 895), (2) folder-name hierarchy (`extrair_hierarquia_da_pasta`, line 952), (3) session-neighborhood country (line 965). **`llm_pasta`'s city/country slots in after step 2 (folder-name hierarchy) fails** — this is precisely the condition D-01 already filters on ("pasta com cidade/país vazio"), so the two conditions align structurally: `llm_pasta` only ever fires where the deterministic folder-hierarchy parser already came up empty.

**Confidence-enum mapping — reuses the existing scale, needs one new score constant only:**
`ConfidenceLevel` (`fotoorganizer/models/inference.py:18-21`, `ALTA`/`MEDIA`/`BAIXA`) is **not** extended — `nivel_para_score()` (`confidence.py:66-71`) already maps any float score to one of the three existing levels via the same 0.8/0.5 thresholds used everywhere else. Only `SCORES_REFERENCIA` needs a new entry:
```python
# Source: fotoorganizer/classification/confidence.py:13-60 (existing table, add one key)
"llm_pasta": <VALOR NÃO DETERMINADO POR ESTA PESQUISA>,
```
**This research deliberately does not recommend a specific number as a finding.** Placement logic (cross-checked against `.planning/research/ARCHITECTURE.md:203-213`, which already analyzed this exact question during milestone research): a location guess derived from folder name alone is evidentially weaker than `"pasta"` (0.60, a *deterministic* parse of an explicit country/city segment) because it requires the model to infer a place from an ambiguous string, but it should stay distinguishable from `"llm"` (0.55, the cluster advisor's category guess) since the two are different kinds of claims per `docs/CONFIANCA.md`'s no-summing rule. Both this research and the milestone-level `ARCHITECTURE.md` converge on "somewhere close to 0.55" as a plausible **starting point**, not a verified value — and this project's own established norm (D-074, D-059/D-060: scores are *measured* against real clusters/photos, never assigned by analogy alone) argues against silently locking any number here. **Recommendation for the planner: route this specific number through discuss-phase or a `checkpoint:human-verify` step before it ships in a migration/constant** — see Open Question 1 and Pitfall 2, which are intentionally aligned on this point.

### Anti-Patterns to Avoid

- **Extending `AdvisorResult`/`ClassificationAdvisor.classificar()` with a city field.** Explicitly forbidden by CONTEXT.md D-canonical-refs and ROADMAP.md ("nunca sobrecarregar o `AdvisorResult`"). The two questions ("which of 3 categories" vs. "which city/event string") have different confidence semantics and different failure modes; mixing them in one schema risks the model conflating the two when only one was needed (this exact risk is called out in `.planning/research/ARCHITECTURE.md:191-197`, already researched at milestone level).
- **Writing LLM results directly into `Evidence` from the session endpoint.** They will be silently deleted on the next `SuggestionEngine.gerar()` call for any media whose suggestion is still pending (`engine.py:1127`). Always go through a persisted table read back by the cascade — see Pattern 3's proposal status, though.
- **Reusing `servicos_externos` alone as "the" opt-in for this feature** without a second, feature-specific flag — CONTEXT.md/ROADMAP.md are explicit ("Flag de opt-in própria, não carona no consentimento já dado ao Advisor de cluster"). See Runtime State Inventory / opt-in storage section below for the concrete mechanism.
- **Estimating cost from folder-name character count alone.** Ignores JSON schema overhead and metadata fields, and Anthropic explicitly warns generic-tokenizer heuristics undercount Claude tokens by double digits of percent. Use `count_tokens`.
- **Silently locking `SCORES_REFERENCIA["llm_pasta"]` to a specific number during planning without a visible confirmation step.** See Pattern 4 and Pitfall 2 — this project's convention is to measure, not assign by analogy.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|--------------|-----|
| Token counting for cost estimate | A char-count or generic-tokenizer heuristic | `client.messages.count_tokens` (already in the pinned SDK) | Free, exact, model-specific, already accounts for schema/system overhead — confirmed present on the installed 0.116.0 SDK in this session |
| Batched multi-item structured output | A hand-designed schema/loop | `LexicoClaude._lote`'s exact shape (`lexico.py:149-196`) | Already proven in this codebase against real API responses, already handles refusal/JSON-parse-failure/never-crash |
| Confidence level bucketing for the new evidence origin | A new enum value or new threshold logic | `nivel_para_score()` (`confidence.py:66-71`) unchanged, only add a `SCORES_REFERENCIA` entry | The 3-level enum + 0.8/0.5 threshold model already covers any float score; no new enum is needed for GENAI-03 |
| Cross-session result durability | A JSON blob on disk, or writing straight to `Evidence` | A new small table + repository, structurally identical to `NomeClassificado`/`LexicoRepository` (proposal — confirm before locking, see Pattern 3) | This exact problem (persist a name→classification mapping that survives `gerar()` regeneration and never overwrites a manual correction) was already solved once in this codebase for the léxico feature — same shape applies here with `pasta` as the key instead of `nome` |

**Key insight:** every piece of this phase has a same-codebase precedent already built and tested. The planning risk is not "what Anthropic API pattern to use" (answered) — it's (a) making sure the plan explicitly routes through a durable persistence layer instead of trying to shortcut through `Evidence` directly, because the shortcut looks like it works in a single manual test and then silently breaks on the next full regeneration, and (b) not letting the specific shape of that persistence layer or the `llm_pasta` score value get locked without a visible confirmation step, since neither was actually decided upstream of this research.

## Common Pitfalls

### Pitfall 1: Writing GenAI results straight into `Evidence`, skipping a durable lookup table
**What goes wrong:** A folder gets a city/event proposal, the dono approves it in the antes/depois screen, everything looks correct — until the next `gerar()` run (triggered by a rescan, or by any other media in the catalog getting a fresh suggestion), at which point `_persistir_sugestao` deletes and rebuilds `Evidence` for that media and the LLM-derived evidence vanishes because nothing re-derives it.
**Why it happens:** `Evidence`/`Suggestion` regeneration is per-run, not incremental, for any media without a decided (`APROVADA`/`REJEITADA`/`EDITADA`) `Suggestion` (`engine.py:1053-1057`, `_midias_com_decisao`).
**How to avoid:** Persist the raw LLM answer in its own durable store (Pattern 3 proposes a table, but the exact shape should be confirmed — see Summary), and make the cascade (Pattern 4) re-read it every `gerar()` call, exactly like `_carregar_curadoria` does for XMP/IPTC keywords.
**Warning signs:** A manual QA pass shows the right destino right after approval, but a second `gerar()` (e.g. after importing more photos) shows the folder reverted to "sem cidade/categoria."

### Pitfall 2: Assigning `llm_pasta`'s `SCORES_REFERENCIA` value by pure analogy instead of flagging it for confirmation
**What goes wrong:** `docs/CONFIANCA.md`'s scores in this codebase were historically **measured**, not guessed — see D-074 (GPS inheritance calibration against 40,678 real photos) and D-059/D-060 (Sonnet-vs-Haiku measured against 104 real clusters). Silently hardcoding `llm_pasta = 0.55` (or any number) without flagging it risks baking an unverified confidence level into the confidence model that other invariants (weakest-link rollup, health index in Phase 10) will treat as ground truth.
**Why it happens:** The number is easy to *guess plausibly* (between "pasta" 0.60 and "vizinhanca" 0.55) but there's no measurement behind it in this research — this session found the *placement logic* in `.planning/research/ARCHITECTURE.md:203-213` (milestone-level), not a *measured* value.
**How to avoid:** Plan should surface this as an explicit decision point (discuss-phase or a `checkpoint:human-verify`-style plan step), not silently lock a number. This research intentionally stops short of recommending a specific value for this exact reason — see Pattern 4.
**Warning signs:** Nobody asked "why 0.55 and not 0.50 or 0.58" before shipping.

### Pitfall 3: Output-token cost estimate treated as exact when it can't be
**What goes wrong:** D-04 requires a cost estimate shown before the dono confirms. `count_tokens` gives an **exact** input-token count, but output tokens are fundamentally unknowable before generation — a UI that presents a single precise-looking number (e.g. "R$ 0,14") for the *total* cost is presenting false precision for the output half.
**Why it happens:** It's tempting to multiply `count_tokens`'s exact input number by the input price and call the result "the cost," silently using a rough guess (or `max_tokens`) for the output side without saying so.
**How to avoid:** Either show a range (input is exact, output is bounded by `max_tokens`) or clearly label the output-token component as an estimate in the UI copy. This matters given the project's general "nunca invente confiança sem base" discipline (D-06 in this same CONTEXT.md) — the same honesty standard should apply to a cost number shown to the dono.
**Warning signs:** QA compares the shown estimate to the actual post-call cost and finds a persistent, unexplained gap on the output side.

### Pitfall 4: Treating `servicos_externos` as sufficient gating for the new feature
**What goes wrong:** Both existing LLM features (`ClaudeAdvisor`, `LexicoClaude`) are gated by the single flag `[privacidade] servicos_externos` (confirmed: `fotoorganizer/server/jobs.py:324`, `fotoorganizer/classification/lexico.py:18`). CONTEXT.md/ROADMAP.md explicitly require GENAI-01 to have its **own** flag, distinct from the Advisor's. If the plan reuses `servicos_externos` alone, it technically satisfies "opt-in, off by default" but violates the explicit "não reusa o consentimento do Advisor de cluster" requirement.
**Why it happens:** `servicos_externos` already does the invariant-4 job (nothing leaves the machine by default) — it's tempting to treat that as "the" opt-in and skip adding a second flag, since functionally a single flag would still gate the feature correctly.
**How to avoid:** Add a second field to `PrivacySettings` (`fotoorganizer/config/settings.py:58-63`), e.g. `classificacao_pasta_genai: bool = False`, following the exact same dataclass/TOML/`_apply_section` pattern already used for `servicos_externos`/`reconhecimento_facial`. Gate the feature on **both** flags being true (`servicos_externos` — the master "any external call" switch — AND the feature-specific flag), mirroring how `reconhecimento_facial` already coexists as a second, independent flag in the same section without replacing `servicos_externos`.
**Warning signs:** The plan's opt-in gate check is a single `if not settings.privacidade.servicos_externos: return` identical to `jobs.py:324`, with no second condition.

## Code Examples

### Opt-in flag storage — exact pattern to mirror (add, don't replace)
```python
# Source: fotoorganizer/config/settings.py:58-64 (existing, read in this session)
@dataclass(frozen=True)
class PrivacySettings:
    # Nenhum dado sai da máquina enquanto isto for False (invariante 4).
    servicos_externos: bool = False
    # Reconhecimento facial: opcional e desativado por padrão (invariante 6).
    reconhecimento_facial: bool = False
    # NOVO (GENAI-01): opt-in próprio, distinto do Advisor de cluster —
    # exige servicos_externos=true E este flag para a sessão rodar.
    classificacao_pasta_genai: bool = False
```
`_SECOES`/`_apply_section` (`settings.py:101,135-143`) already generalize over `PrivacySettings`' fields via `fields(instance)` — no change needed there, the new field is picked up automatically by both TOML loading and CLI/env override paths.

**CLI/env override — read `fotoorganizer/cli.py` directly this session (lines 111-157):** `_overrides_de_cli_e_env` builds the `privacidade` override dict via an `escolhido(campo, env_nome, tipo)` helper (line 111-115) that checks an `argparse` attribute first, then an env var. Today **only `servicos_externos`** gets this treatment (line 146-148: `escolhido("servicos_externos", "SERVICOS_EXTERNOS", bool)` → `privacidade["servicos_externos"] = ...`) — `reconhecimento_facial`, the closer structural analog (a second, independent opt-in flag in the same `[privacidade]` section), has **no CLI/env override today**, only a TOML-and-default path. This weakens the case for assuming every new `PrivacySettings` field needs a CLI flag: the actual precedent is mixed (one flag has CLI/env, the other doesn't), so this is a planner judgment call, not a "just copy `servicos_externos`'s treatment" default — see Open Question 2.

### Gate check — exact pattern to mirror
```python
# Source: fotoorganizer/server/jobs.py:322-332 (existing _advisor() method, read in this session)
def _classificador_de_pasta(self):
    """GenAI de pasta só com opt-in explícito E próprio — nunca carona no
    consentimento do Advisor de cluster."""
    if not (self._settings.privacidade.servicos_externos
            and self._settings.privacidade.classificacao_pasta_genai):
        return None
    try:
        from fotoorganizer.classification.location_advisor import ClassificacaoDePastaClaude
        return ClassificacaoDePastaClaude()
    except Exception as exc:
        log.warning("classificador de pasta indisponível (%s)", exc)
        return None
```

### Endpoint shape — exact pattern to mirror (`/api/exif/*` → `/api/genai-pasta/*`)
```python
# Source: fotoorganizer/server/app.py:1348-1400 (existing exif endpoints, read in this session)
# GET  /api/genai-pasta/candidatas         → lista pré-filtrada (D-01)
# POST /api/genai-pasta/estimar-custo      → { pastas_confirmadas: [...] } → { tokens, custo_usd, custo_brl }
# POST /api/genai-pasta/rodar              → dispara a chamada única (D-03), grava a proposta
# GET  /api/genai-pasta/{sessao_id}        → antes/depois por pasta, para a tela de revisão
# POST /api/genai-pasta/{sessao_id}/aprovar → { pastas: [...] } → grava origem='manual' nas aprovadas
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| Manual token-per-char cost estimates | `POST /v1/messages/count_tokens` (free, exact, model-specific) | Available on the SDK version already pinned in this project (0.116.0, confirmed) | D-04's cost estimate can be exact for the input side instead of approximate |
| Anthropic Messages API without native structured output | `output_config.format=json_schema` (already in use in this codebase since `advisor.py`/`lexico.py`) | Already adopted, no change needed | No action — this phase inherits the pattern for free |

**Deprecated/outdated:** none identified specific to this phase — the existing codebase's Anthropic integration is already current (confirmed structured-output param names, `thinking` param shape, and `count_tokens` signature all match the installed 0.116.0 SDK and current official docs fetched this session).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|----------------|
| A1 | `llm_pasta`'s `SCORES_REFERENCIA` value is left undetermined by this research and should be resolved via discuss-phase/checkpoint, not assigned silently during planning | Pattern 4 / Pitfall 2 | Low — this is deliberately a non-finding, flagged as needing a human decision; the risk is only that a planner ignores the flag and locks a number anyway without measurement, matching this project's own established anti-pattern |
| A2 | Output-token cost is a small fraction of total cost for typical session sizes (tens of folders) | Pattern 2 | Low — if wrong, the "show input cost precisely, output as a bounded estimate" UI framing still holds; only the relative sizing intuition would be off, not the estimation method |
| A3 | A new dedicated table (`PastaClassificada`) is preferable to reusing `MetadataEntry` with a new namespace, IF a persistence layer is confirmed as needed | Pattern 3 | Low — `MetadataEntry` is per-`media_id` (FK), not per-folder-string; reusing it would require either duplicating rows across every media in a folder or inventing a pasta-keyed pseudo-entity inside a media-keyed table, both worse than a dedicated table. This entire pattern (not just the table-vs-namespace choice) is flagged in the Summary as research-derived and not yet confirmed with the user. |
| A4 | Session-scoped folder pre-filter (D-01) can be expressed as a single SQL aggregate query over `MediaFile.pasta` grouped against `Evidence`/`Suggestion` state, without a new index | Architecture Patterns | Low-medium — not measured against the production catalog size in this research; if the query is slow at the ~423k-row scale referenced elsewhere in STATE.md, an index analogous to `ix_media_files_pasta` may be needed, but this phase's target catalog is explicitly the small one (~1,400 files, per STATE.md Blockers/Concerns) so this is unlikely to matter for Phase 7's own measurement |
| A5 | Every `PrivacySettings` field needs a matching CLI/env override, following `servicos_externos`'s treatment | Code Examples / Open Question 2 | Low — actually contradicted by the codebase itself: `reconhecimento_facial`, the closer structural analog, has no CLI/env override today (confirmed by reading `cli.py:111-157` directly). The new flag can ship TOML/UI-only without breaking precedent. |

**If this table is empty:** N/A — see entries above; all are medium-or-lower risk and none touches privacy/security invariants (which are all `[CITED]`/`[VERIFIED]`, not assumed).

## Open Questions (RESOLVED)

1. **(RESOLVED → plano 07-05 + 07-09)** Exact `SCORES_REFERENCIA["llm_pasta"]` value — deliberately left open by this research
   - What we know: placement should be below `"pasta"` (0.60, deterministic) and distinguishable from `"llm"` (0.55, different kind of claim per `docs/CONFIANCA.md`'s no-summing rule); `.planning/research/ARCHITECTURE.md` already flagged this exact question at milestone level with the same "close to 0.55, not measured" conclusion.
   - What's unclear: no measurement (à la D-074/D-059/D-060) has been run for this specific evidence type, and this project's convention is to measure before locking a score.
   - Recommendation: do not have the plan silently hardcode a number. Route this through discuss-phase as a numbered decision, or gate it behind a `checkpoint:human-verify` step in the plan, matching this project's established practice of measuring scores rather than assigning them by analogy. If a placeholder is needed to keep planning moving, mark it unmistakably provisional (e.g. a `# TODO(D-0XX): confirmar score medido` comment plus a plan task to revisit) rather than presenting it as settled.
   - Resolution: 07-05 lands `SCORES_REFERENCIA["llm_pasta"]` as an explicit `# PROVISÓRIO` constant with a pointer to 07-09; 07-09 measures against the acervo real (mesmo método D-059/D-060) and its acceptance criteria require `grep -c "PROVISÓRIO"` == 0 after the dono decide o número medido. Provisional-to-measured lifecycle enforced, not just documented.

2. **(RESOLVED → nenhum plano adiciona override)** CLI/env override for the new opt-in flag
   - What we know: `fotoorganizer/cli.py:111-157` (read in full this session) shows `servicos_externos` has a CLI/env override (`escolhido("servicos_externos", "SERVICOS_EXTERNOS", bool)`, line 146-148) but `reconhecimento_facial` — the closer structural analog, a second independent privacy opt-in — does **not**. The codebase's own precedent is mixed, not uniform.
   - What's unclear: CONTEXT.md doesn't specify whether GENAI-01's flag needs CLI/env control or should be UI/TOML-only, and the existing code doesn't establish a single clear convention to default to.
   - Recommendation: default to TOML + UI-only (matching `reconhecimento_facial`, the more similar precedent — a feature-specific privacy toggle, not a general operational flag like `servicos_externos`), unless the planner has a specific reason (e.g. scripted/headless sessions) to need a CLI override. Either choice is defensible; just don't assume `servicos_externos`'s treatment is "the" pattern to copy, since it isn't uniformly applied even within `PrivacySettings` today.
   - Resolution: nenhum plano adiciona override de CLI/env para `classificacao_pasta_genai` — bate com a recomendação (TOML/UI-only). O flag em si migrou de `PrivacySettings`/TOML para `application_settings` via `SettingsRepository` (decisão de 07-04, já que o servidor não escreve TOML e o UI-SPEC exige ligar/desligar pela tela), mas a ausência de override continua a mesma conclusão desta pesquisa.

3. **(RESOLVED → plano 07-02, `PastaPayload`)** Exact wording/scope of "metadados já catalogados" sent per folder (GENAI-02)
   - What we know: `ClusterInfo` (`advisor.py:33-41`) already defines a reasonable metadata payload shape (folder names, sample filenames, period, photo count, known places) that `.planning/research/ARCHITECTURE.md:169-173` already identified as reusable for this feature's payload too.
   - What's unclear: whether Phase 7's payload should be `ClusterInfo` reused as-is, or a narrower folder-scoped variant (a single folder's own already-catalogued fields — e.g. any partial `Evidence.pais`/`Evidence.categoria` already present — rather than a full session/cluster shape). D-02 ("só complementa o campo que falta") implies the payload should communicate *which field is already known* so the model doesn't waste effort re-guessing a field D-02 says must never be overwritten anyway.
   - Recommendation: design a folder-scoped payload dataclass (not `ClusterInfo` verbatim) that includes existing partial evidence explicitly, so the schema/prompt can instruct "only propose the field(s) marked missing" — this is a planning-level schema design decision, not fully closed by this research.
   - Resolution: 07-02 define `PastaPayload` como dataclass própria (não `ClusterInfo` reaproveitado), exatamente como recomendado, com o campo já conhecido marcado explicitamente para o prompt instruir "só proponha o que falta".

4. **(RESOLVED → CONTEXT.md D-07, confirmado via AskUserQuestion)** Where the new-table proposal (Pattern 3) should be confirmed before it's built
   - What we know: this research derived the need for durable persistence from reading `engine.py`'s regeneration logic directly (Pitfall 1) — it's a real problem, not speculative — but the specific solution shape (a new table mirroring `NomeClassificado`) is this research's own design, not a decision the user or ROADMAP.md made.
   - What's unclear: whether the planner should treat this as settled-enough-to-plan (the precedent is strong and low-risk) or should explicitly loop the user in before a migration lands.
   - Recommendation: given this project's pattern of the dono reviewing and approving architectural proposals during discuss-phase/plan-review (see D-062's "desenho pronto para implementar, mas não implementado" precedent for the folder-inventory feature), treat this the same way — present the table design as a ready-to-approve proposal in the plan, not as an already-locked implementation detail.
   - Resolution: dono confirmou explicitamente (não assumido) via `AskUserQuestion` após esta pesquisa — ver D-07 em `07-CONTEXT.md`, registrado 2026-08-18.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework (backend) | pytest 8.x (`pyproject.toml` `[tool.pytest.ini_options]`, `testpaths = ["tests"]`) |
| Framework (frontend) | vitest (`webapp/package.json` `"test:watch": "vitest"`, config in `webapp/vite.config.ts`) |
| Config file | `pyproject.toml` (backend), `webapp/vite.config.ts` (frontend) |
| Quick run command | `pytest tests/test_classification_pasta_genai.py -x` (new file, mirrors `tests/test_lexico.py` naming) |
| Full suite command | `scripts/verificar.sh` (referenced repeatedly in STATE.md as the project's canonical gate — runs pytest + vitest together) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|---------------------|--------------|
| GENAI-01 | Classification off by default; no external call happens; engine output identical to today | unit | `pytest tests/test_classification_pasta_genai.py::test_desligado_por_padrao -x` | ❌ Wave 0 |
| GENAI-01 | Cost estimate shown before any call; nothing sent before confirm | unit (mocked client) | `pytest tests/test_classification_pasta_genai.py::test_custo_antes_de_confirmar -x` | ❌ Wave 0 |
| GENAI-02 | Payload sent contains only folder name + already-catalogued metadata, never image bytes/paths to image content | unit (payload assertion, mirrors `test_lexico.py`'s privacy-payload pattern) | `pytest tests/test_classification_pasta_genai.py::test_payload_nunca_envia_imagem -x` | ❌ Wave 0 |
| GENAI-02 | Sonnet 5 is the model used, `thinking` disabled | unit | `pytest tests/test_classification_pasta_genai.py::test_modelo_e_thinking -x` | ❌ Wave 0 |
| GENAI-03 | Result becomes `Evidence` with distinct origin (`llm_pasta`), never overloads existing `"llm"`/cluster-advisor result | unit + integration (`SuggestionEngine.gerar()`) | `pytest tests/test_classification_pasta_genai.py::test_evidence_origem_propria -x` | ❌ Wave 0 |
| GENAI-03 | API failure/timeout/429 never crashes generation; media proceeds without the LLM evidence | unit (exception-raising mock client, mirrors `advisor.py`'s `except Exception` contract) | `pytest tests/test_classification_pasta_genai.py::test_falha_api_nunca_derruba -x` | ❌ Wave 0 |
| D-02 | Existing non-empty field (categoria OR cidade/país) is never overwritten by the LLM result | unit | `pytest tests/test_classification_pasta_genai.py::test_nunca_sobrescreve_campo_preenchido -x` | ❌ Wave 0 |
| D-06 | Ambiguous/"unknown" LLM response produces no evidence at all | unit | `pytest tests/test_classification_pasta_genai.py::test_resposta_incerta_nao_gera_evidencia -x` | ❌ Wave 0 |
| Pitfall 1 (durability) | Evidence survives a second `gerar()` run without the session re-running | integration | `pytest tests/test_classification_pasta_genai.py::test_sobrevive_a_segunda_geracao -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_classification_pasta_genai.py -x` (backend), `npx vitest run ClassificacaoPasta` (frontend, once the component exists)
- **Per wave merge:** `scripts/verificar.sh`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_classification_pasta_genai.py` — covers GENAI-01/02/03 + D-02/D-06 + durability, mirrors `tests/test_lexico.py`'s structure (mock `client` injected into the new `ClassificacaoDePastaClaude`, same as `LexicoClaude(client=...)` today)
- [ ] `webapp/src/components/ClassificacaoPasta.test.tsx` — mirrors `webapp/src/components/EscritaExif.test.tsx`'s checkbox-row-review test pattern
- No new framework install needed — pytest and vitest are both already configured and used by directly analogous existing tests

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|----------------|---------|--------------------|
| V2 Authentication | no | Local-only app, no auth layer in scope for this phase |
| V3 Session Management | no | N/A — "sessão" here means a classification run, not a web session |
| V4 Access Control | no | Single-user local app |
| V5 Input Validation | yes | Structured-output JSON schema (`additionalProperties: false`) already constrains the model's response shape at the API boundary — mirror `lexico.py`'s "only accept items that were actually asked about" filter (line 191-196) so a hallucinated/injected folder name in the response can never be trusted |
| V6 Cryptography | no | No new crypto surface — credential handling reuses the existing `ANTHROPIC_API_KEY`/`ant auth` path (`advisor.py:108-116`), never touched or logged by this phase |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|------------------------|
| Data exfiltration via overly broad metadata payload (invariant 4) | Information Disclosure | Explicit allow-list of fields in the payload dataclass (folder name + already-catalogued fields only) — never serialize the full `MediaFile` row or file paths beyond the folder name; test asserts payload shape (see Validation Architecture GENAI-02 row) |
| Prompt injection via a maliciously-named folder (e.g. a folder literally named to manipulate the system prompt) | Tampering | Structured output with `additionalProperties: false` already bounds what the model can *return*; on the *input* side, folder names are user-controlled strings from the dono's own filesystem (not attacker-controlled in this local-first, single-user context) — low real risk here, but the existing "only accept pastas that were actually asked about" filter (Pattern 1) is cheap, already-proven defense-in-depth regardless |
| Silent data loss (LLM result overwritten/lost on regeneration) | (not STRIDE, but a documented project invariant — "nada que possa ser a referência real é apagado") | Persisted store with `origem` provenance (proposal, see Pattern 3), never a live-only in-memory result |

## Sources

### Primary (HIGH confidence)
- `platform.claude.com/docs/en/about-claude/pricing` — official Anthropic pricing page, fetched directly this session; confirmed Claude Sonnet 5 = $2/MTok input, $10/MTok output (standard, permanent as of the $2/$10 note), Batch API = $1/$5 (50% off), prompt caching 5m-write=1.25x/1h-write=2x/read=0.1x, ≥1,024-token floor for Sonnet/Haiku caching
- `platform.claude.com/docs/en/api/messages/count_tokens` — official Anthropic API reference, fetched directly this session; confirmed `POST /v1/messages/count_tokens` accepts `system`, `messages`, `output_config` (including `format: json_schema`), `tools`, `thinking`; returns `{input_tokens: number}`; free, no generation
- Local `.venv` inspection (this session): `anthropic==0.116.0` installed, `client.messages.count_tokens` confirmed present via `inspect.signature`, matching `pyproject.toml`'s `anthropic>=0.116` floor
- Existing codebase, read directly this session: `fotoorganizer/classification/advisor.py`, `fotoorganizer/classification/lexico.py`, `fotoorganizer/classification/engine.py`, `fotoorganizer/classification/confidence.py`, `fotoorganizer/config/settings.py`, `fotoorganizer/cli.py` (lines 100-169, read in full), `fotoorganizer/server/jobs.py`, `fotoorganizer/server/app.py`, `fotoorganizer/models/lexico.py`, `fotoorganizer/models/inference.py`, `fotoorganizer/models/catalog.py`, `fotoorganizer/repositories/lexico.py`, `webapp/src/components/EscritaExif.tsx`, `tests/test_lexico.py`, `fotoorganizer/database/migrations/versions/` (listing) — ground truth for every "reuse X" recommendation above
- `docs/DECISOES.md` D-059/D-060 (read in full this session) — Sonnet-5-over-Haiku precedent this phase extends a fortiori
- `.planning/research/STACK.md` and `.planning/research/ARCHITECTURE.md` (milestone-level research, read in full this session) — prior analysis of the batch-vs-sync question (closed by D-03) and the cascade integration point (Pattern 4 above extends this directly, with exact file:line confirmation added in this session)

### Secondary (MEDIUM confidence)
- WebSearch cross-check on Sonnet 5 pricing (finout.io, openrouter.ai, others) — directionally consistent with the official pricing page fetched above; official page treated as authoritative, search results used only as a sanity cross-check

### Tertiary (LOW confidence)
- None used as a basis for any recommendation in this document — every substantive claim traces to either the official docs fetched directly, the installed SDK inspected directly, or code read directly in this repo.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new package; SDK method presence confirmed by direct inspection, not inferred
- Architecture: HIGH for the call-shape/cascade-slot recommendations (exact file:line from code read this session); MEDIUM for the new-persistence-table proposal specifically, since it is this research's own inference rather than a locked upstream decision — explicitly flagged as such throughout (Summary, Pattern 3, Open Question 4)
- Pitfalls: HIGH — all four pitfalls are either already-documented project invariants (D-02, D-06, invariant 4) or directly observable from reading `engine.py`'s regeneration logic, not speculative

**Research date:** 2026-08-18
**Valid until:** 30 days (stable domain — no fast-moving dependency; re-verify Sonnet 5 pricing if this research is reused after any pricing-page update, since the $2/$10 rate was itself a recent lock-in per the page's own note about a cancelled Sept 1 2026 increase)

---
*Research for: Foto Organizer v2.0 — Phase 7, Classificação de pasta por GenAI*
*Researched: 2026-08-18*
