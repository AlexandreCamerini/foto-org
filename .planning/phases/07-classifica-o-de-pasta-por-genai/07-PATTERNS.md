# Phase 7: Classificação de pasta por GenAI - Pattern Map

**Mapped:** 2026-08-18
**Files analyzed:** 14 (9 backend, 5 frontend)
**Analogs found:** 14 / 14

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `fotoorganizer/classification/location_advisor.py` | service | request-response (batched external API call) | `fotoorganizer/classification/lexico.py` (`LexicoClaude._lote`) | exact |
| `fotoorganizer/models/pasta_classificacao.py` | model | CRUD | `fotoorganizer/models/lexico.py` (`NomeClassificado`) | exact |
| `fotoorganizer/repositories/pasta_classificacao.py` | service (repository) | CRUD | `fotoorganizer/repositories/lexico.py` (`LexicoRepository`) | exact |
| `fotoorganizer/database/migrations/versions/0020_pasta_classificacoes_genai.py` | migration | batch (schema) | `fotoorganizer/database/migrations/versions/0019_tabelas_de_escrita_exif.py` | exact |
| `fotoorganizer/classification/confidence.py` (MOD) | config | transform | itself, existing `SCORES_REFERENCIA` table | exact (same file, additive) |
| `fotoorganizer/classification/engine.py` (MOD, `_categoria`/`_evidencias_geo`) | service | transform (cascade) | itself, existing cascade steps at lines 974-1015 / 872-972 | exact (same file, additive) |
| `fotoorganizer/config/settings.py` (MOD, `PrivacySettings`) | config | CRUD (settings load/apply) | itself, existing `servicos_externos`/`reconhecimento_facial` fields | exact (same file, additive) |
| `fotoorganizer/server/jobs.py` (MOD, gate method) | service | request-response (opt-in gate) | itself, `_advisor()` at lines 322-332 | exact (same file, additive) |
| `fotoorganizer/server/app.py` (MOD, `/api/genai-pasta/*`) | controller/route | request-response | itself, `/api/exif/*` endpoints at lines 1348-1413 | exact (same file, additive) |
| `tests/test_classification_pasta_genai.py` | test | request-response + CRUD | `tests/test_lexico.py` | exact |
| `webapp/src/api.ts` (MOD, `genaiPasta*` client functions + types) | service (typed HTTP client) | request-response | itself, `planosExif`/`criarPlanoExif`/`dryRunExif`/`auditoriaExif` + `PlanoExif`/`ItemPlanoExif`/`RelatorioDryRunExif` types (lines 356-419, 626-634) | exact (same file, additive) |
| `webapp/src/components/ClassificacaoPasta.tsx` | component | request-response (wizard/modal) | `webapp/src/components/EscritaExif.tsx` (plan→dry-run→execute wizard) + `webapp/src/components/ModalCaminho.tsx` (modal shell) | role-match (two analogs combined, per UI-SPEC) |
| `webapp/src/components/ClassificacaoPasta.test.tsx` | test | request-response | `webapp/src/components/EscritaExif.test.tsx` | exact (not read this session — mirror by name per RESEARCH.md; structure follows `EscritaExif.tsx`'s own patterns) |
| `webapp/src/components/Review.tsx` (MOD, trigger button + `PorQue` origin pill) | component | CRUD (extends existing review UI) | itself, header bar (lines 156-163) and `PorQue` (lines 463-493) | exact (same file, additive) |

## Pattern Assignments

### `fotoorganizer/classification/location_advisor.py` (service, request-response)

**Analog:** `fotoorganizer/classification/lexico.py` (196 lines, read in full)

**Module docstring / privacy contract pattern** (lexico.py lines 1-25): every LLM-calling module in this codebase opens with a docstring stating exactly what data leaves the machine, what the opt-in gate is, and what the module does when the gate is off. Copy this shape — GENAI-02/03's module docstring should state: "sai da máquina apenas o NOME da pasta e metadado já catalogado — nunca a imagem, o caminho completo além do nome de pasta"; must reference `[privacidade] servicos_externos` AND the phase's own flag (`classificacao_pasta_genai`).

**Imports pattern** (lexico.py lines 27-33):
```python
from __future__ import annotations

import json
import logging
from typing import Protocol

log = logging.getLogger(__name__)
```

**Protocol + Null-object pair** (lexico.py lines 110-127) — every LLM-backed capability in this codebase ships as `Protocol` + a "null" implementation that is the *default*, not the LLM one:
```python
class ClassificadorDeNomes(Protocol):
    @property
    def local(self) -> bool: ...

    def classificar(self, nomes: list[str]) -> dict[str, str]:
        """{nome: categoria}. Nome ausente do retorno = sem opinião."""
        ...


class LexicoNulo:
    """Padrão: nenhuma palavra sai da máquina, nenhuma opinião."""

    @property
    def local(self) -> bool:
        return True

    def classificar(self, nomes: list[str]) -> dict[str, str]:
        return {}
```
GENAI-02/03 needs `ClassificadorDePasta` (Protocol) + `ClassificacaoDePastaNula` (default, `local=True`, returns `{}`/`[]`) + `ClassificacaoDePastaClaude` (the real one, `local=False`).

**Batched array-schema call — core pattern to copy almost verbatim** (lexico.py lines 130-196):
```python
class LexicoClaude:
    def __init__(self, model: str = MODELO_PADRAO, client=None) -> None:
        if client is None:
            import anthropic
            client = anthropic.Anthropic()
        self._client = client
        self._model = model

    @property
    def local(self) -> bool:
        return False  # a UI usa isto para indicar envio externo

    def classificar(self, nomes: list[str]) -> dict[str, str]:
        resultado: dict[str, str] = {}
        for i in range(0, len(nomes), TAMANHO_DO_LOTE):
            resultado.update(self._lote(nomes[i : i + TAMANHO_DO_LOTE]))
        return resultado

    def _lote(self, nomes: list[str]) -> dict[str, str]:
        try:
            resposta = self._client.messages.create(
                model=self._model,
                max_tokens=16000,
                thinking={"type": "disabled"},
                system=_SYSTEM,
                output_config={
                    "format": {"type": "json_schema", "schema": _SCHEMA}
                },
                messages=[{
                    "role": "user",
                    "content": json.dumps({"nomes": nomes}, ensure_ascii=False),
                }],
            )
        except Exception as exc:  # rede/auth/limite: nunca derruba a geração
            log.warning("léxico indisponível: %s", exc)
            return {}

        if resposta.stop_reason == "refusal":
            log.info("léxico recusou a consulta")
            return {}
        texto = next((b.text for b in resposta.content if b.type == "text"), None)
        if not texto:
            return {}
        try:
            dados = json.loads(texto)
        except json.JSONDecodeError:
            log.warning("léxico devolveu JSON inválido")
            return {}

        pedidos = set(nomes)
        return {
            item["nome"]: item["categoria"]
            for item in dados.get("nomes", [])
            if item.get("nome") in pedidos and item.get("categoria") in CATEGORIAS
        }
```
Substitute: `nomes: list[str]` → `pastas: list[PastaPayload]` (dataclass, see Open Question 3 in RESEARCH.md — narrower than `ClusterInfo`), `_SCHEMA`'s `nomes` array → `pastas` array with `{pasta, cidade, pais, categoria, justificativa}` fields (see RESEARCH.md Pattern 1's exact schema), and the final filter must check `item.get("pasta") in pedidos` — never trust a folder name the model introduces (D-06/security V5, same defense as lexico.py line 191-196).

**Error handling pattern:** identical shape at every failure point — network/auth/rate-limit exception, `stop_reason == "refusal"`, missing text block, `JSONDecodeError` — every branch logs and returns an empty/falsy result, never raises. This is the "never-crash contract" CONTEXT.md's canonical refs point to (`ClaudeAdvisor`); `lexico.py` is the batched-shape sibling of it.

**Model choice — copy `advisor.py`'s comment, not `lexico.py`'s:** `lexico.py` uses `MODELO_PADRAO = "claude-opus-5"` (a *different* decision, for name-only classification). GENAI-02/03 must use `claude-sonnet-5` per D-059/D-060 (see `advisor.py` lines 22-29 below) — do not copy `lexico.py`'s model constant, only its call/batching shape.

**Model-choice precedent to cite in the new module's docstring** (`fotoorganizer/classification/advisor.py` lines 22-29):
```python
# Decisão 1 do gate da fase 5 (docs/DECISOES.md D-047 a D-060). Descer
# para Haiku 4.5 foi medido e descartado: em 104 clusters reais, Haiku
# afirmava categoria onde Opus recusava por falta de evidência em pelo
# menos 19/31 discordâncias (D-049) — violava a instrução "nunca invente"
# do próprio `_SYSTEM` abaixo. Sonnet 5, medido depois (D-060) nos mesmos
# 104 clusters, cai nesse padrão só 7 vezes (contra o piso de 19 do
# Haiku) — motivo da escolha.
MODELO_PADRAO = "claude-sonnet-5"
```

**Credential pattern** (advisor.py lines 112-118, identical in lexico.py): credential never touches code/repo, comes from env or `ant auth` profile via bare `anthropic.Anthropic()`. `client` is injectable for tests (mirrors `LexicoClaude(client=...)` in `test_lexico.py`).

---

### `fotoorganizer/models/pasta_classificacao.py` (model, CRUD)

**Analog:** `fotoorganizer/models/lexico.py` (31 lines, read in full — this is the exact precedent RESEARCH.md Pattern 3 names)

**Full pattern to mirror** (lexico.py lines 1-31):
```python
from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column

from fotoorganizer.models.base import Base, utcnow


class NomeClassificado(Base):
    """[docstring: why this table exists, why key=nome not media/session,
    why justificativa+origem is what makes it revisable]"""

    __tablename__ = "nomes_classificados"

    nome: Mapped[str] = mapped_column(primary_key=True)
    categoria: Mapped[str]
    justificativa: Mapped[str | None]
    # 'llm' | 'manual'. A correção do dono nunca é sobrescrita pela máquina.
    origem: Mapped[str] = mapped_column(default="llm")
    classificado_em: Mapped[datetime] = mapped_column(default=utcnow)
```
For `PastaClassificada`: `__tablename__ = "pasta_classificacoes_genai"`, PK `pasta: Mapped[str]`, plus `cidade: Mapped[str | None]`, `pais: Mapped[str | None]`, `categoria: Mapped[str | None]`, `evento: Mapped[str | None]`, `justificativa: Mapped[str]`, `origem: Mapped[str] = mapped_column(default="llm")`, `classificado_em: Mapped[datetime] = mapped_column(default=utcnow)` — exact shape proposed in RESEARCH.md Pattern 3 (flagged there as proposal, not locked; planner should confirm before implementing).

**Registration** — must add to `fotoorganizer/models/__init__.py` the same way `NomeClassificado` is registered (`fotoorganizer/models/__init__.py:46` import + `:64` `__all__` entry).

---

### `fotoorganizer/repositories/pasta_classificacao.py` (service/repository, CRUD)

**Analog:** `fotoorganizer/repositories/lexico.py` (59 lines, read in full)

**Full pattern to mirror** (lexico.py lines 1-59):
```python
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from fotoorganizer.models import NomeClassificado


class LexicoRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._factory = session_factory

    def conhecidos(self) -> dict[str, str]:
        """{nome: categoria} de tudo que já foi classificado."""
        with self._factory() as session:
            return {
                n.nome: n.categoria
                for n in session.scalars(select(NomeClassificado))
            }

    def faltantes(self, nomes: set[str]) -> list[str]:
        """O que ainda não tem classificação — é isto, e só isto, que sai
        da máquina."""
        return sorted(nomes - set(self.conhecidos()))

    def salvar(self, categorias: dict[str, str],
               justificativas: dict[str, str] | None = None,
               origem: str = "llm") -> int:
        """Grava, sem sobrescrever correção manual do dono."""
        justificativas = justificativas or {}
        gravadas = 0
        with self._factory() as session:
            for nome, categoria in categorias.items():
                atual = session.get(NomeClassificado, nome)
                if atual is not None:
                    if atual.origem == "manual" and origem != "manual":
                        continue
                    atual.categoria = categoria
                    atual.justificativa = justificativas.get(nome)
                    atual.origem = origem
                else:
                    session.add(NomeClassificado(
                        nome=nome, categoria=categoria,
                        justificativa=justificativas.get(nome), origem=origem,
                    ))
                gravadas += 1
            session.commit()
        return gravadas
```
`ClassificacaoPastaRepository.salvar()` needs D-02's field-level discipline, which is *stricter* than `LexicoRepository.salvar()`'s row-level `origem == "manual"` check above: D-02 says "never overwrite a field that's already non-null," not just "never overwrite a manual row." Per-field check on `cidade`/`categoria` individually (RESEARCH.md Pattern 3, final paragraph) — this is new logic beyond what `LexicoRepository` does, not a verbatim copy for the `salvar()` method body.

---

### `fotoorganizer/database/migrations/versions/0020_pasta_classificacoes_genai.py` (migration, batch)

**Analog:** `fotoorganizer/database/migrations/versions/0019_tabelas_de_escrita_exif.py` (131 lines, read in full — most recent migration, `0019` is current head)

**Structure to mirror** (0019 lines 32-59, table-creation shape):
```python
revision: str = '0020'
down_revision: Union[str, None] = '0019'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'pasta_classificacoes_genai',
        sa.Column('pasta', sa.String(), nullable=False),
        sa.Column('cidade', sa.String(), nullable=True),
        sa.Column('pais', sa.String(), nullable=True),
        sa.Column('categoria', sa.String(), nullable=True),
        sa.Column('evento', sa.String(), nullable=True),
        sa.Column('justificativa', sa.Text(), nullable=False),
        sa.Column('origem', sa.String(), nullable=False),
        sa.Column('classificado_em', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('pasta', name=op.f('pk_pasta_classificacoes_genai')),
    )


def downgrade() -> None:
    op.drop_table('pasta_classificacoes_genai')
```
Note: `0019`'s docstring header explains *why* each design decision was made (e.g. why no FK, why status split by field) — follow that convention: state why the PK is `pasta` (string), and reference D-02's per-field-never-overwrite rule as the reason `origem` exists per row, same framing as `NomeClassificado`.

---

### `fotoorganizer/classification/confidence.py` (config, transform — MODIFIED, additive)

**Analog:** itself — `SCORES_REFERENCIA` dict, lines 13-60 (79-line file, read in full)

**Exact insertion pattern** — every entry in this table has an inline comment justifying its placement relative to neighbors (see `lexico` entry lines 41-47 as the most directly comparable precedent: it explains why `lexico` (0.58) sits between `pasta` (0.60) and `llm` (0.55)):
```python
    "lexico": 0.58,
    # ... existing entries ...
    "usuario": 1.00,       # correção manual prevalece sobre tudo
```
New key `"llm_pasta"`: **RESEARCH.md Pitfall 2/Open Question 1 explicitly says do not lock this number silently** — insert with a `# TODO(D-0XX): valor não medido — ver RESEARCH.md Open Question 1` comment and route through discuss-phase or a `checkpoint:human-verify` plan step, not a bare constant. `nivel_para_score()` (lines 66-71) needs no change — it already buckets any float via the existing 0.8/0.5 thresholds.

---

### `fotoorganizer/classification/engine.py` (service, transform — MODIFIED, additive cascade rung)

**Analog:** itself — `_categoria` (lines 974-1015) and `_evidencias_geo` (lines 872-972), read in full this session (1222-line file; read via targeted, non-overlapping ranges: 100-140, 860-1140)

**`_categoria` cascade — exact insertion point** (lines 1010-1015, the existing step 3 that GENAI's `llm_pasta` sits beside, never replaces):
```python
        # 3) Advisor deu categoria sem evento.
        if sessao is not None and sessao.categoria:
            return _Draft("categoria", "llm", sessao.categoria,
                          sessao.justificativa or
                          "sugerido por LLM a partir de metadados")
        return None
```
Add a new step (3b or before/after this one, per RESEARCH.md Pattern 4) that looks up the bulk-loaded `pasta_classificacoes` dict by `media.pasta` and returns `_Draft("categoria", "llm_pasta", proposta.categoria, proposta.justificativa)` — **never** merge into the existing `"llm"` step's `_Draft`, since that would violate CONTEXT.md's "nunca overload de `AdvisorResult`" instruction.

**`_evidencias_geo` cascade — exact insertion point** (lines 951-963, step 2, folder-hierarchy parse that must fail first):
```python
        # 2) Nome das pastas.
        hierarquia = extrair_hierarquia_da_pasta(media.pasta)
        if hierarquia.pais:
            just = f"reconhecido no caminho da pasta ('{hierarquia.segmento_pais}')"
            return [
                _Draft(campo, "pasta", valor, just)
                for campo, valor in [
                    ("pais", hierarquia.pais), ("regiao", hierarquia.regiao),
                    ("cidade", hierarquia.cidade),
                ]
                if valor
            ]

        # 3) Vizinhança: a sessão tem país dominante pelo GPS das outras.
        if sessao is not None and sessao.pais_dominante:
            return [_Draft(
                "pais", "vizinhanca", sessao.pais_dominante,
                f"outras fotos da mesma sessão têm GPS em "
                f"{sessao.pais_dominante}",
            )]

        return []  # sem evidência: não inventa localização
```
`llm_pasta`'s city/country fields slot in after step 2 fails (this is the exact condition D-01 pre-filters on) and either before or after step 3 — RESEARCH.md recommends after step 2, before the final `return []`.

**Bulk-load pattern to copy** (`_carregar_curadoria`, lines 115-132) — this is the "one query for the whole catalog, not N+1" precedent every cascade lookup in this engine follows:
```python
def _carregar_curadoria(session: Session) -> dict[int, tuple[str, ...]]:
    """[why: one query for the whole catalog, not one per photo]"""
    stmt = select(MetadataEntry.media_id, MetadataEntry.valor).where(
        MetadataEntry.namespace == NAMESPACE_CURADORIA,
        MetadataEntry.chave == "palavra_chave",
    )
    por_media: dict[int, list[str]] = {}
    for media_id, valor in session.execute(stmt):
        if valor:
            por_media.setdefault(media_id, []).append(valor)
    return {media_id: tuple(valores) for media_id, valores in por_media.items()}
```
`_carregar_classificacoes_de_pasta(session) -> dict[str, PastaClassificada]` should follow this exact shape — one `select` over the new repository/table, called once per `gerar()` run, result passed down into `_categoria`/`_evidencias_geo` the same way `palavras_chave` is threaded through today (see call site at line 867).

**Persistence/regeneration contract (critical, not optional)** — `_persistir_sugestao` (lines 1114-1139) deletes and rebuilds `Evidence` for a media's *pending* suggestion on every `gerar()` call:
```python
    def _persistir_sugestao(self, session: Session, media: MediaFile,
                            drafts: list[_Draft]) -> None:
        antigas = list(
            session.scalars(select(Suggestion).where(
                Suggestion.media_id == media.id,
                Suggestion.status == SuggestionStatus.PENDENTE,
            ))
        )
        for sugestao in antigas:
            session.execute(delete(suggestion_evidence).where(
                suggestion_evidence.c.suggestion_id == sugestao.id
            ))
            session.delete(sugestao)
        session.execute(delete(Evidence).where(Evidence.media_id == media.id))
        session.flush()

        evidencias: dict[str, Evidence] = {}
        for draft in drafts:
            evidencia = Evidence(
                media_id=media.id, campo=draft.campo, origem=draft.origem,
                valor=draft.valor, nivel=nivel_para_score(draft.score),
                score=draft.score, justificativa=draft.justificativa,
                versao_logica=VERSAO_LOGICA,
            )
            session.add(evidencia)
            evidencias[draft.campo] = evidencia
```
This is why GENAI-03's result **must** flow through the cascade rung above (re-derived every `gerar()` call from the persisted table), never written directly into `Evidence` from the approval endpoint — see RESEARCH.md Pitfall 1, and Validation Architecture's `test_sobrevive_a_segunda_geracao`.

---

### `fotoorganizer/config/settings.py` (config, CRUD — MODIFIED, additive flag)

**Analog:** itself — `PrivacySettings` dataclass, lines 58-64 (243-line file; targeted read 40-140)

**Exact pattern** (lines 58-64):
```python
@dataclass(frozen=True)
class PrivacySettings:
    # Nenhum dado sai da máquina enquanto isto for False (invariante 4).
    servicos_externos: bool = False
    # Reconhecimento facial: opcional e desativado por padrão (invariante 6).
    reconhecimento_facial: bool = False
```
Add: `classificacao_pasta_genai: bool = False`, with a comment stating it is a second, independent opt-in (never inferred from `servicos_externos` alone) — mirrors `reconhecimento_facial`'s own comment style exactly.

**No other change needed**: `_apply_section()` (line 135, generalizes over `fields(instance)`) and `_SECOES = ("geral", "scanner", "privacidade")` (line 101) already pick up any new `PrivacySettings` field automatically for both TOML load and `aplicar_overrides()` — confirmed by reading the loop at line 136-143.

**CLI/env override — do NOT copy `servicos_externos`'s treatment automatically.** `fotoorganizer/cli.py` lines 111-148 (`_overrides_de_cli_e_env`, read in full):
```python
    def escolhido(campo: str, env_nome: str, tipo):
        do_cli = getattr(args, campo, UNSET)
        if do_cli is not UNSET:
            return do_cli
        return _bool_env(env_nome) if tipo is bool else _valor_env(env_nome, tipo)
    ...
    servicos_externos = escolhido("servicos_externos", "SERVICOS_EXTERNOS", bool)
    if servicos_externos is not UNSET:
        privacidade["servicos_externos"] = servicos_externos
```
`reconhecimento_facial` — the closer structural analog (a second, independent privacy toggle) — has **no** entry here, TOML/UI-only. RESEARCH.md Open Question 2 recommends defaulting `classificacao_pasta_genai` to TOML+UI-only (matching `reconhecimento_facial`), not adding a CLI/env override, unless the planner has a specific reason.

---

### `fotoorganizer/server/jobs.py` (service, request-response — MODIFIED, additive gate method)

**Analog:** itself — `_advisor()`, lines 322-332 (388-line file, targeted read 300-340)

**Exact pattern to mirror**:
```python
    def _advisor(self):
        """Advisor LLM só com opt-in explícito — sem ele, 100% local."""
        if not self._settings.privacidade.servicos_externos:
            return None
        try:
            from fotoorganizer.classification.advisor import ClaudeAdvisor

            return ClaudeAdvisor()
        except Exception as exc:
            log.warning("advisor indisponível (%s); seguindo local", exc)
            return None
```
New `_classificador_de_pasta()` must gate on **both** flags (RESEARCH.md Pitfall 4 — this is the one place the pattern must NOT be copied verbatim, since verbatim copy only checks `servicos_externos`):
```python
    def _classificador_de_pasta(self):
        """GenAI de pasta só com opt-in explícito E próprio — nunca carona
        no consentimento do Advisor de cluster."""
        if not (self._settings.privacidade.servicos_externos
                and self._settings.privacidade.classificacao_pasta_genai):
            return None
        try:
            from fotoorganizer.classification.location_advisor import (
                ClassificacaoDePastaClaude,
            )

            return ClassificacaoDePastaClaude()
        except Exception as exc:
            log.warning("classificador de pasta indisponível (%s)", exc)
            return None
```

---

### `fotoorganizer/server/app.py` (controller/route, request-response — MODIFIED, additive endpoints)

**Analog:** itself — `/api/exif/*` block, lines 1298-1413 (1557-line file, targeted read 1290-1420 + 109-165 for `BaseModel` bodies)

**Endpoint shape to mirror** — plan → dry-run(cost-preview)-equivalent → confirm/execute → review/approve, same lifecycle as EXIF write plans:
```python
    @app.get("/api/exif")
    def listar_planos_exif() -> list[dict]:
        return [_plano_exif_json(p) for p in exif_repo.listar_planos()]

    @app.post("/api/exif/plano")
    def criar_plano_exif() -> dict:
        plan_id = exif_planner.criar_plano_exif()
        if plan_id is None:
            raise HTTPException(409, "nada a gravar — ...")
        return _plano_exif_json(exif_repo.plano(plan_id))

    @app.get("/api/exif/{plan_id}")
    def detalhe_plano_exif(plan_id: int) -> dict:
        plano = exif_repo.plano(plan_id)
        if plano is None:
            raise HTTPException(404, "plano não encontrado")
        return {**_plano_exif_json(plano), "itens": [...]}

    @app.post("/api/exif/{plan_id}/dry-run")
    def dry_run_plano_exif(plan_id: int) -> dict:
        if exif_repo.plano(plan_id) is None:
            raise HTTPException(404, "plano não encontrado")
        return exif_executor.dry_run(plan_id)

    @app.post("/api/exif/{plan_id}/executar")
    def executar_plano_exif(plan_id: int, body: ExecutarExifBody) -> dict:
        plano = exif_repo.plano(plan_id)
        if plano is None:
            raise HTTPException(404, "plano não encontrado")
        if plano.dry_run_em is None:
            raise HTTPException(409, "rode o dry-run antes de gravar")
        incluidos = exif_executor.aplicar_selecao(plan_id, body.itens)
        if incluidos == 0:
            raise HTTPException(409, "nenhum item selecionado para gravar")
        if not jobs.iniciar_escrita_exif(plan_id):
            raise HTTPException(409, "já existe um trabalho em andamento")
        return jobs.estado()
```
Suggested `/api/genai-pasta/*` shape (RESEARCH.md's "Endpoint shape" section, cross-checked against this analog's exact HTTPException/404/409 conventions):
```
GET  /api/genai-pasta/candidatas          -> lista pré-filtrada (D-01), same shape as GET /api/exif
POST /api/genai-pasta/estimar-custo       -> body: {pastas: [...]} -> {tokens_entrada, custo_usd, custo_brl, teto_saida_tokens}
POST /api/genai-pasta/rodar               -> body: {pastas: [...]} -> dispara a chamada única (D-03), grava a proposta; 404/409 mirror exif pattern
GET  /api/genai-pasta/{sessao_id}         -> antes/depois por pasta
POST /api/genai-pasta/{sessao_id}/aprovar -> body: {pastas: [...]} -> grava origem='manual' nas aprovadas
```

**Pydantic body pattern** (app.py lines 151-160, `EditarDestinoBody`/`ExecutarExifBody`, immediately adjacent to the exif endpoints):
```python
class EditarDestinoBody(BaseModel):
    destino: str


class ExecutarExifBody(BaseModel):
    # `None` preserva a seleção já persistida (D-02); lista vazia zera a
    # seleção — o endpoint distingue os dois casos.
    itens: list[int] | None = None
```
New bodies (`AprovarGenaiPastaBody`, etc.) should follow this exact minimal-dataclass-with-comment style, placed near the other `*Body` classes (lines 109-163).

---

### `tests/test_classification_pasta_genai.py` (test, request-response + CRUD)

**Analog:** `tests/test_lexico.py` (210 lines, read in full)

**Fake-client test double pattern** (lines 126-145) — every LLM-calling module in this codebase is tested against a hand-rolled fake client, never a real network call or a mocking framework:
```python
class _RespostaFalsa:
    def __init__(self, texto: str, stop_reason: str = "end_turn") -> None:
        self.content = [type("B", (), {"type": "text", "text": texto})()]
        self.stop_reason = stop_reason


class _ClienteFalso:
    def __init__(self, resposta) -> None:
        self._resposta = resposta
        self.chamadas: list[dict] = []

    @property
    def messages(self):
        return self

    def create(self, **kw):
        self.chamadas.append(kw)
        if isinstance(self._resposta, Exception):
            raise self._resposta
        return self._resposta
```

**Privacy-payload assertion pattern** (lines 148-159) — GENAI-02's "payload never contains images" test should follow this exact shape (assert on the literal JSON body sent, not on a mock call count):
```python
def test_manda_so_as_palavras(monkeypatch):
    """O contrato de privacidade: sai a lista de nomes, nada mais."""
    import json

    cliente = _ClienteFalso(_RespostaFalsa(json.dumps({"nomes": [
        {"nome": "Pantanal", "categoria": LUGAR, "justificativa": "bioma"},
    ]})))
    resultado = LexicoClaude(client=cliente).classificar(["Pantanal"])

    assert resultado == {"Pantanal": LUGAR}
    corpo = json.loads(cliente.chamadas[0]["messages"][0]["content"])
    assert corpo == {"nomes": ["Pantanal"]}
```

**Never-crash parametrized test** (lines 176-183) — copy this exact `@pytest.mark.parametrize` shape for GENAI-03's failure-never-crashes requirement:
```python
@pytest.mark.parametrize("falha", [
    RuntimeError("sem rede"),
    _RespostaFalsa("", stop_reason="refusal"),
    _RespostaFalsa("isto não é json"),
])
def test_falha_nunca_derruba_a_geracao(falha):
    """Rede, recusa ou JSON quebrado: devolve vazio e a cascata segue."""
    assert LexicoClaude(client=_ClienteFalso(falha)).classificar(["x"]) == {}
```

**Repository/manual-correction-survives test** (lines 113-121) — mirror for `ClassificacaoPastaRepository`'s D-02 field-level discipline:
```python
def test_correcao_do_dono_sobrevive_a_reclassificacao(migrated_engine):
    """A máquina propõe; o dono decide. Sem isto, a próxima consulta
    desfaria a correção em silêncio."""
    repo = LexicoRepository(create_session_factory(migrated_engine))
    repo.salvar({"TERG": "ocasiao"}, origem="llm")
    repo.salvar({"TERG": LUGAR}, origem="manual")

    repo.salvar({"TERG": "ocasiao"}, origem="llm")   # a máquina insiste
    assert repo.conhecidos()["TERG"] == LUGAR        # e não vence
```
(GENAI-03's field-level version needs one more test than this: verify that saving a *different field* on an already-`manual`-origin row still writes the missing field, since D-02 is per-field, not per-row — `migrated_engine` fixture already exists in `conftest.py`, reuse it.)

---

### `webapp/src/api.ts` (service/typed client, request-response — MODIFIED, additive functions + types)

**Analog:** itself — `PlanoExif`/`ItemPlanoExif`/`CampoExif`/`RelatorioDryRunExif` types (lines 356-419) and `planosExif`/`planoExif`/`criarPlanoExif`/`dryRunExif`/`auditoriaExif` client functions (lines 626-634), read directly this session (672-line file; targeted ranges 1-60, 340-420, 460-508, 600-672). **This is the layer every other backend-endpoint pattern in this document assumes exists** — `EscritaExif.tsx`'s `api.criarPlanoExif()`/`api.dryRunExif()` calls (used throughout the `ClassificacaoPasta.tsx` section below) resolve to functions defined here; without this file's `genaiPasta*` counterparts, the component has nothing to call.

**Fetch-wrapper helpers — reuse verbatim, do not reinvent** (lines 464-507, three near-identical wrappers already used by every endpoint in this file):
```typescript
async function json<T>(url: string): Promise<T> {
  const resposta = await fetch(url);
  if (!resposta.ok) throw new Error(`${resposta.status} em ${url}`);
  return resposta.json() as Promise<T>;
}

/** POST com a mensagem do servidor preservada — o usuário precisa ler
 * "rode o dry-run antes de executar", não "erro 409". */
async function post<T>(url: string, body?: unknown): Promise<T> {
  const resposta = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body ?? {}),
  });
  const dados = await resposta.json();
  if (!resposta.ok) throw new Error(dados.detail ?? `erro ${resposta.status}`);
  return dados as T;
}
```
`post<T>` already surfaces `HTTPException(status, "mensagem")`'s `detail` string as the thrown `Error.message` — this is what feeds `EscritaExif.tsx`'s `onError: (e: Error) => setErro(e.message)` pattern and must be reused as-is for every `genaiPasta*` mutation function, not re-implemented.

**Type definitions — mirror shape and doc-comment convention** (lines 356-411, `StatusCampoExif`/`CampoExif`/`ItemPlanoExif`/`PlanoExif`):
```typescript
/** Um dos três campos de localização (gps/cidade/pais) de um item do plano
 *  de escrita EXIF. `StatusCampoExif` é uma união literal, não `string`
 *  solto: a UI mapeia status → cor/copy num `switch`, e um `string` deixaria
 *  esse `switch` sem exaustividade — o TypeScript não acusaria quando um
 *  status novo passasse a existir sem tratamento na tela. */
export type StatusCampoExif =
  | "pendente"
  | "pronto"
  | "pulado"
  | "sem_valor"
  | "gravado"
  | "falha";

export interface CampoExif {
  valor: string | [number, number] | null;
  status: StatusCampoExif;
  motivo: string | null;
}

export interface ItemPlanoExif {
  id: number;
  media_id: number;
  origem: string;
  nome: string;
  incluido: boolean;
  formato_suportado: boolean;
  motivo_nao_suportado: string | null;
  sidecar_destino: string | null;
  pasta_sincronizada: string | null;
  erro: string | null;
  backup_original: string | null;
  campos: { gps: CampoExif; cidade: CampoExif; pais: CampoExif };
}

export interface PlanoExif {
  id: number;
  nome: string;
  status: string;
  dry_run_em: string | null;
  criado_em: string;
  total_itens: number;
  prontos: number | null;
  problemas: number | null;
  campos_a_gravar: number | null;
  sidecars: number | null;
  nao_suportados: number;
  sincronizados: number;
  gravados: number;
  com_erro: number;
  executavel: boolean;
}

export type PlanoExifDetalhe = PlanoExif & { itens: ItemPlanoExif[] };
```
New types to add, following this exact shape (union literal for status fields, doc-comment explaining *why* the shape is what it is, `Detalhe` type composed via `&` for the list-vs-detail split — same convention as `PlanoExif`/`PlanoExifDetalhe`):
```typescript
export interface CandidataGenaiPasta {
  pasta: string;
  campos_ausentes: ("categoria" | "cidade_pais")[];
  n_fotos: number;
}

export interface CustoEstimadoGenaiPasta {
  tokens_entrada: number;
  custo_entrada_usd: number;
  teto_tokens_saida: number;
  teto_custo_saida_usd: number;
  teto_custo_total_usd: number;
}

export interface PropostaGenaiPasta {
  pasta: string;
  campo: "categoria" | "cidade" | "pais";
  valor_antes: string | null;
  valor_proposto: string;
  nivel: string;
  justificativa: string;
}

export interface RevisaoGenaiPasta {
  sessao_id: number;
  propostas: PropostaGenaiPasta[];
  pastas_sem_resposta: string[];
}
```

**Client function pattern — mirror exactly** (lines 626-634):
```typescript
  planosExif: () => json<PlanoExif[]>("/api/exif"),
  planoExif: (id: number) => json<PlanoExifDetalhe>(`/api/exif/${id}`),
  /** Sem parâmetro: escopo global, escrita in-place — não há raiz para
   *  escolher, ao contrário de `criarPlano`. */
  criarPlanoExif: () => post<PlanoExif>("/api/exif/plano"),
  dryRunExif: (id: number) =>
    post<RelatorioDryRunExif>(`/api/exif/${id}/dry-run`),
  auditoriaExif: (id: number) =>
    json<LinhaAuditoria[]>(`/api/exif/${id}/auditoria`),
```
New entries in the `api` object (added inside the same object literal, lines 509-635 — do not create a second `api` export):
```typescript
  candidatasGenaiPasta: () =>
    json<CandidataGenaiPasta[]>("/api/genai-pasta/candidatas"),
  estimarCustoGenaiPasta: (pastas: string[]) =>
    post<CustoEstimadoGenaiPasta>("/api/genai-pasta/estimar-custo", { pastas }),
  rodarGenaiPasta: (pastas: string[]) =>
    post<RevisaoGenaiPasta>("/api/genai-pasta/rodar", { pastas }),
  revisaoGenaiPasta: (sessaoId: number) =>
    json<RevisaoGenaiPasta>(`/api/genai-pasta/${sessaoId}`),
  aprovarGenaiPasta: (sessaoId: number, pastas: string[]) =>
    post<{ aprovadas: number }>(`/api/genai-pasta/${sessaoId}/aprovar`, { pastas }),
```
Field/endpoint names here are illustrative, matching the `/api/genai-pasta/*` shape sketched in the `app.py` Pattern Assignment above — planner must keep the two in sync (frontend type ↔ backend response `dict`/Pydantic model), same discipline already visible between `_plano_exif_json`'s return dict (app.py) and `PlanoExif`'s interface (api.ts) today.

---

### `webapp/src/components/ClassificacaoPasta.tsx` (component, request-response wizard)

**Analogs:** `webapp/src/components/EscritaExif.tsx` (594 lines, read in full — plan/dry-run/execute lifecycle) + `webapp/src/components/ModalCaminho.tsx` (55 lines, read in full — modal shell)

**Modal shell to copy verbatim** (ModalCaminho.tsx lines 26-28, per UI-SPEC's own instruction):
```tsx
<div className="fixed inset-0 z-50 flex items-center justify-center bg-black/95">
  <div className="w-96 rounded-md border border-borda bg-painel p-4">
```
UI-SPEC specifies a wider panel for this phase: `"w-[720px] max-w-[92vw] max-h-[85vh] overflow-y-auto rounded-md border border-borda bg-painel p-4"` — same shell family, different width/height/scroll since this is a multi-row wizard, not a single text field.

**React Query mutation + local error state pattern** (EscritaExif.tsx lines 297-320):
```tsx
const criar = useMutation({
  mutationFn: () => api.criarPlanoExif(),
  onSuccess: (novo) => {
    setErro(null);
    setSelecionado(novo.id);
    void queryClient.invalidateQueries({ queryKey: ["planosExif"] });
  },
  onError: (e: Error) => setErro(e.message),
});

const dryRun = useMutation({
  mutationFn: () => api.dryRunExif(selecionado as number),
  onSuccess: (r) => {
    setErro(null);
    setRelatorio(r);
    void queryClient.invalidateQueries({ queryKey: ["planoExif", selecionado] });
    void queryClient.invalidateQueries({ queryKey: ["auditoriaExif", selecionado] });
  },
  onError: (e: Error) => setErro(e.message),
});
```
`ClassificacaoPasta.tsx`'s wizard needs one `useMutation` per step-transition (`estimarCusto`, `rodar`, `aprovar`), calling the new `api.estimarCustoGenaiPasta`/`api.rodarGenaiPasta`/`api.aprovarGenaiPasta` functions from `api.ts` above, following this exact shape — `onError` always sets a local `erro` string, never throws unhandled into the UI (matches UI-SPEC's Error state row copy).

**Checkbox-row-with-default-state pattern** (EscritaExif.tsx lines 261-266, 480-494) — this is the "checkbox per row, seeded from server, toggle updates a local `Set`" pattern CONTEXT.md/UI-SPEC both point to for step 1 (candidatos) and step 4 (revisão):
```tsx
const [marcados, setMarcados] = useState<Set<number>>(new Set());
...
useEffect(() => {
  if (plano) {
    setMarcados(new Set(plano.itens.filter((i) => i.incluido).map((i) => i.id)));
  }
}, [plano]);
...
<input
  type="checkbox"
  className="h-3.5 w-3.5 shrink-0 rounded-sm border-borda-forte accent-acento"
  checked={marcados.has(item.id)}
  onChange={() =>
    setMarcados((atual) => {
      const novo = new Set(atual);
      if (novo.has(item.id)) novo.delete(item.id);
      else novo.add(item.id);
      return novo;
    })
  }
  aria-label={rotuloCheckbox}
/>
```
UI-SPEC's step 1/step 4 rows are **default-checked** (opt-out phrasing, D-01/D-03) — seed the `Set` with *all* row ids on initial query success, not from an `incluido` server flag (there is no such flag pre-session; this differs from EscritaExif's seed-from-server-state, since candidatos/revisão are fresh each session). Since candidates/proposals are keyed by `pasta: string` here, not `id: number`, use `Set<string>` instead of `Set<number>`.

**Disabled-button-with-reason pattern** (EscritaExif.tsx lines 385-404) — UI-SPEC explicitly requires this for step 1's "Avançar" (disabled at 0 selected) and step 2's cost-confirm:
```tsx
<Botao
  variante="solido"
  onClick={...}
  disabled={!podeGravar}
  title={
    plano.dry_run_em === null
      ? "Rode o dry-run antes de gravar"
      : !plano.executavel
        ? "O dry-run não encontrou nenhum campo gravável"
        : marcados.size === 0
          ? "Nenhum arquivo marcado para gravar"
          : "Grava os campos vazios no arquivo original"
  }
>
  Gravar {marcados.size} arquivos
</Botao>
```

**Error surface pattern** (EscritaExif.tsx line 334): `{erro && <span className="text-erro">{erro}</span>}` — plain inline text, no toast/modal-within-modal; matches UI-SPEC's Error state copy convention (name the failure, offer next step).

---

### `webapp/src/components/ClassificacaoPasta.test.tsx` (test, request-response)

**Analog:** `webapp/src/components/EscritaExif.test.tsx` (referenced in RESEARCH.md Validation Architecture; not read directly this session — file was not opened, follow `EscritaExif.tsx`'s own component structure above as the ground truth for what the test needs to cover: checkbox-row default state, mutation onSuccess/onError branches, disabled-button title text). Confirm the actual test file's structure directly before writing, since this analog was inferred from the source component, not independently verified.

---

### `webapp/src/components/Review.tsx` (component, CRUD — MODIFIED, additive trigger + pill)

**Analog:** itself — header bar (lines 140-163) and `PorQue` (lines 463-493), read in full via targeted ranges (140-380, 460-500)

**Trigger button insertion point** (line 156-162, `"Gerar/atualizar sugestões"` button — new button goes to its left per UI-SPEC):
```tsx
<Botao
  onClick={() => job.gerarSugestoes()}
  disabled={job.rodando}>
  {job.rodando && job.estado.tipo === "sugestoes"
    ? "Gerando…"
    : "Gerar/atualizar sugestões"}
</Botao>
```
Insert `<Botao variante="contorno" tamanho="md" onClick={() => setClassificacaoAberta(true)}>Classificar pastas por IA…</Botao>` immediately before this, per UI-SPEC's exact placement instruction.

**Modal open/close wiring — not independently read in `ModalCaminho.tsx`'s parent (its mount site was outside this session's targeted ranges), but the shape follows directly from `ModalCaminho.tsx`'s own props contract** (`onConfirmar`/`onCancelar` callbacks, read in full above): `Review.tsx` needs a `const [classificacaoAberta, setClassificacaoAberta] = useState(false)` alongside the existing `porque`/`abertos` local state, and a conditional mount `{classificacaoAberta && <ClassificacaoPasta onFechar={() => setClassificacaoAberta(false)} />}` near the component's return statement — same "boolean flag gates a conditionally-rendered modal" shape every modal in this codebase uses, confirm exact mount point against `Review.tsx`'s full render tree before implementing (this session read the header/list/`PorQue` sections but not the outermost return wrapper).

**Existing origin-pill precedent to extend** (lines 310-319, `rotuloDeFonte` CONS-01 pill, imported from `../fontes` at line 8):
```tsx
<div className="flex min-w-0 items-center gap-1.5">
  <span className="truncate font-titulo">{s.nome}</span>
  {colide && s.source_id != null && (
    <span
      title="Mesmo nome, data e câmera de outra sugestão nesta lista — fontes diferentes"
      className="inline-flex shrink-0 items-center rounded-full border border-borda bg-cartao px-1.5 py-0.5 text-[11px] text-texto-2"
    >
      {rotuloDeFonte(fontes, s.source_id)}
    </span>
  )}
</div>
```
UI-SPEC's new pill uses a **different** color family (`herdado`, not the neutral `border-borda bg-cartao text-texto-2` shown above) specifically so a GenAI-origin proposal is never visually confused with this existing source-collision pill — same pill *shell* (`rounded-full ... px-1.5 py-0.5 text-[11px]`), different palette, deliberately.

**`PorQue` extension point — exact insertion, confirmed no `ev.origem` rendering exists today** (lines 480-493):
```tsx
  return (
    <ul className="space-y-1 px-3 pb-2 pl-[68px]">
      {sugestao.evidencias.map((ev, i) => (
        <li key={i} className="flex gap-2 text-[11px]">
          <Confianca nivel={ev.nivel} rotulo={false} />
          <span className="text-texto-2">
            <span className="text-texto">{ev.campo}</span>: {ev.valor} —{" "}
            {ev.justificativa}
          </span>
        </li>
      ))}
    </ul>
  );
```
UI-SPEC's exact addition (already specified verbatim in `07-UI-SPEC.md`):
```tsx
<Confianca nivel={ev.nivel} rotulo={false} />
{ev.origem === "llm_pasta" && (
  <span className="rounded-full border border-herdado/40 bg-herdado/10 px-1.5 py-0.5 text-[11px] text-herdado">
    IA · pasta
  </span>
)}
```

**`Confianca` component — reuse verbatim, no changes** (`webapp/src/components/Confianca.tsx`, 88 lines, read in full): renders 3-segment quantity indicator from `nivel: string` (`"alta"|"media"|"baixa"`); the `llm_pasta` evidence just needs `ev.nivel` populated correctly server-side (via `nivel_para_score()`), nothing new to build on the frontend for confidence rendering.

**`Botao` primitive — reuse verbatim** (`webapp/src/ui/Botao.tsx`, 95 lines, read in full): `variante` (`solido`/`contorno`/`fantasma`), `tamanho` (`sm`/`md`/`lg`), `tom` (state-only color, never decorative) — every button in `ClassificacaoPasta.tsx` and the `Review.tsx` trigger must use this component, never a raw `<button>`.

---

## Shared Patterns

### LLM call never-crash contract
**Source:** `fotoorganizer/classification/lexico.py:155-196` and `fotoorganizer/classification/advisor.py:135-176` (identical shape in both)
**Apply to:** `location_advisor.py`'s `_lote()`/`classificar()`
Every failure point (network/auth exception, `stop_reason == "refusal"`, missing text, invalid JSON) logs at `warning`/`info` and returns an empty/falsy result — never raises past the module boundary. `SuggestionEngine.gerar()` must keep working with zero LLM evidence when this happens.

### Opt-in gate, additive not replacing
**Source:** `fotoorganizer/server/jobs.py:322-332` (`_advisor`) + `fotoorganizer/config/settings.py:58-64` (`PrivacySettings`) + `fotoorganizer/cli.py:146-148`
**Apply to:** `jobs.py`'s new `_classificador_de_pasta()`, `settings.py`'s new `classificacao_pasta_genai` field
Gate on `servicos_externos AND classificacao_pasta_genai` both true (Pitfall 4) — copying only the `servicos_externos` check is the most likely regression here since it's the pattern every existing gate uses today.

### Bulk-load-once-per-run, never N+1
**Source:** `fotoorganizer/classification/engine.py:115-132` (`_carregar_curadoria`) and the `_IndiceDeAlbuns` class immediately following it
**Apply to:** the cascade's new lookup of the persisted `pasta_classificacoes` table — one `select` per `gerar()` call, threaded into `_categoria`/`_evidencias_geo` as a parameter, same as `palavras_chave` today (call site `engine.py:867`).

### Manual correction never overwritten by machine
**Source:** `fotoorganizer/repositories/lexico.py:32-59` (`LexicoRepository.salvar`)
**Apply to:** `ClassificacaoPastaRepository.salvar()` — but note the *stricter, field-level* version required by D-02 (never overwrite a non-null `cidade`/`categoria` individually), not just the row-level `origem == "manual"` check `LexicoRepository` uses.

### Checkbox-row review UI, default-checked, opt-out phrasing
**Source:** `webapp/src/components/EscritaExif.tsx:261-266,480-494` (checkbox `Set` state, seeded via `useEffect`)
**Apply to:** `ClassificacaoPasta.tsx` steps 1 and 4 — both UI-SPEC steps use "desmarque o que não quer" phrasing, matching this component's existing D-01/D-02 convention, not a build-up-from-empty selection model.

### Structured-output schema with "never trust an unrequested item" filter
**Source:** `fotoorganizer/classification/lexico.py:189-196`
**Apply to:** `location_advisor.py`'s response parsing — `additionalProperties: false` in the JSON schema plus an explicit `item.get("pasta") in pedidos` filter is the security control (ASVS V5) that prevents a hallucinated/injected folder name from ever being trusted, per RESEARCH.md's Security Domain section.

### Typed HTTP client function per endpoint, one shared `api` object
**Source:** `webapp/src/api.ts:464-507` (fetch wrappers) + `:509-635` (single `api` object literal)
**Apply to:** every new `/api/genai-pasta/*` endpoint needs one function inside the existing `api = {...}` object, using `json<T>`/`post<T>` — never a second client object, never a raw `fetch()` call inside `ClassificacaoPasta.tsx` itself.

## No Analog Found

None — every file in this phase's scope has a strong, directly-analogous, already-shipped precedent in this codebase (the phase's own RESEARCH.md concludes the same: "almost no genuinely new technical risk").

## Open Items Carried From RESEARCH.md / UI-SPEC (not resolved by pattern-mapping, planner must route)

These are not pattern questions — they are decisions RESEARCH.md and the UI-SPEC both explicitly flagged as unresolved and out of this agent's scope to lock:

1. **`SCORES_REFERENCIA["llm_pasta"]` numeric value** — do not silently hardcode during planning; RESEARCH.md Pitfall 2/Open Question 1.
2. **Exact shape of the `pasta_classificacoes_genai` persistence table** — the shape mapped above (mirroring `NomeClassificado`) is RESEARCH.md's own proposal, not a locked upstream decision; RESEARCH.md Pattern 3/Open Question 4 recommends presenting it to the user as a ready-to-approve design in the plan, not silently building it.
3. **CLI/env override for `classificacao_pasta_genai`** — recommend TOML+UI-only (matching `reconhecimento_facial`), but this is a judgment call per RESEARCH.md Open Question 2, not a hard requirement.
4. **Exact payload shape sent per folder (GENAI-02)** — RESEARCH.md Open Question 3 recommends a narrower, folder-scoped dataclass (not `ClusterInfo` reused verbatim) that explicitly marks which field(s) are already known, so D-02's "only propose the missing field" instruction can be enforced in the prompt itself.
5. **Exact mount point of `<ClassificacaoPasta>` inside `Review.tsx`'s render tree** — this session read the header bar, list rows, and `PorQue` sections of `Review.tsx`, but not its outermost return wrapper; confirm the conditional-mount site directly against the file before implementing (see the Review.tsx Pattern Assignment's "Modal open/close wiring" note).

## Metadata

**Analog search scope:** `fotoorganizer/classification/`, `fotoorganizer/models/`, `fotoorganizer/repositories/`, `fotoorganizer/database/migrations/versions/`, `fotoorganizer/config/`, `fotoorganizer/server/`, `fotoorganizer/cli.py`, `tests/`, `webapp/src/api.ts`, `webapp/src/components/`, `webapp/src/ui/` — all directories named in RESEARCH.md's Recommended Project Structure and UI-SPEC's Layout & Component Inventory.
**Files scanned (read directly this session):** `fotoorganizer/classification/lexico.py` (full), `fotoorganizer/classification/advisor.py` (full), `fotoorganizer/classification/engine.py` (targeted: 100-140, 860-1140), `fotoorganizer/classification/confidence.py` (full), `fotoorganizer/models/lexico.py` (full), `fotoorganizer/repositories/lexico.py` (full), `fotoorganizer/config/settings.py` (targeted: 40-140), `fotoorganizer/server/jobs.py` (targeted: 300-340), `fotoorganizer/server/app.py` (targeted: 109-165, 1290-1420), `fotoorganizer/cli.py` (targeted: 97-157), `fotoorganizer/database/migrations/versions/0019_tabelas_de_escrita_exif.py` (full), `tests/test_lexico.py` (full), `webapp/src/api.ts` (targeted: 1-60, 340-420, 460-508, 600-672), `webapp/src/components/EscritaExif.tsx` (full), `webapp/src/components/ModalCaminho.tsx` (full), `webapp/src/components/Review.tsx` (targeted: 140-380, 460-500), `webapp/src/components/Confianca.tsx` (full), `webapp/src/ui/Botao.tsx` (full).
**Pattern extraction date:** 2026-08-18
