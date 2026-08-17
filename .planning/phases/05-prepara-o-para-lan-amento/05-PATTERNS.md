# Phase 5: Preparação para lançamento - Pattern Map

**Mapped:** 2026-08-17
**Files analyzed:** 13 (10 confirmed, 3 conditional/verification-triggered)
**Analogs found:** 10 / 10 confirmed files (3 conditional files intentionally deferred, see § No Analog Found)

**Framing note:** Per RESEARCH.md, Phase 5 is verification-and-fix, not net-new construction. Most "files to modify" are small, surgical diffs (add an `Index(...)` line, add one PRAGMA line) against files that already contain 3-8 nearly-identical precedents in the same file. The two genuinely new files (`0018_*.py` migration, `tests/test_indices.py`) each have one exact same-repo analog to copy wholesale.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `fotoorganizer/models/catalog.py` (`MediaFile.__table_args__`, `Source` class) | model | CRUD (schema declaration) | same file, `MediaFile.__table_args__` lines 117-137 | exact (self-analog, add lines to existing tuple) |
| `fotoorganizer/models/inference.py` (`Suggestion.__table_args__`) | model | CRUD (schema declaration) | same file, `Evidence.__table_args__` line 41 | exact |
| `fotoorganizer/models/operations.py` (`OperationItem`, `AuditLog`) | model | CRUD (schema declaration) | `fotoorganizer/models/inference.py` line 41 (adding `__table_args__` to a class that has none yet) | role-match |
| `fotoorganizer/models/duplicates.py` (`DuplicateMember.__table_args__`) | model | CRUD (schema declaration) | same file line 58 (extend existing tuple) | exact |
| `fotoorganizer/models/people.py` (`FaceOccurrence`) | model | CRUD (schema declaration) | `fotoorganizer/models/inference.py` line 41 (adding `__table_args__` to a class that has none yet) | role-match |
| `fotoorganizer/database/engine.py` (`_set_sqlite_pragmas`) | config | request-response (connection setup) | same file lines 11-17 (append one line) | exact |
| `fotoorganizer/database/migrations/versions/0018_*.py` | migration | batch (DDL) | `fotoorganizer/database/migrations/versions/0017_indice_trip_id_event_id.py` (whole file) | exact |
| `tests/test_indices.py` | test | request-response (query-plan assertion) | `tests/test_database.py` (whole file, esp. `test_wal_e_foreign_keys_ativos`) | exact |
| `docs/PERFORMANCE.md` | config (doc) | batch (append-per-measurement-round) | `docs/AVALIACAO_UX.md` (whole file, structural pattern) | exact |
| `scripts/medir_baseline_producao.py` (name at planner's discretion) | utility | batch (one-shot timed CLI script) | `fotoorganizer/cli.py` `cmd_bench` lines 566-612, and `scripts/avaliar_agrupamento.py` (standalone-script shape) | role-match |
| `src-tauri/src/main.rs` | config/native-shell | event-driven | *(conditional — only if LANC-01 verification finds a bug, D-03)* | n/a — see § No Analog Found |
| `fotoorganizer/cli.py` (`cmd_web`) | controller | request-response | *(conditional — only if LANC-01 verification finds a bug, D-03)* | n/a — see § No Analog Found |
| `webapp/src/components/ModalCaminho.tsx` / `Panorama.tsx` / `PhotoGrid.tsx` / `Trips.tsx` | component | event-driven | *(conditional — only if LANC-03 uninstructed test finds a blocker, D-05)* | n/a — see § No Analog Found |

## Pattern Assignments

### `fotoorganizer/models/catalog.py` (model, schema declaration)

**Analog:** same file — `MediaFile.__table_args__` (lines 117-137), and `Source` class (lines 70-93, currently has **no** `__table_args__` at all).

**Imports already present** (lines 8-16):
```python
from sqlalchemy import (
    JSON,
    Enum,
    ForeignKey,
    Index,
    Text,
    UniqueConstraint,
    and_,
)
```
No new imports needed — `Index` is already imported.

**Core pattern — extend `MediaFile.__table_args__`** (lines 117-137, exact text to extend):
```python
class MediaFile(Base):
    __tablename__ = "media_files"
    __table_args__ = (
        UniqueConstraint("source_id", "caminho"),
        Index("ix_media_files_hash_rapido", "hash_rapido"),
        Index("ix_media_files_data_capturada", "data_capturada"),
        Index("ix_media_files_mtime_tamanho", "mtime", "tamanho"),
        Index("ix_media_files_papel", "papel"),
        Index("ix_media_files_arquivo_offline", "arquivo_offline"),
        Index("ix_media_files_trip_id", "trip_id"),
        Index("ix_media_files_event_id", "event_id"),
        # ADD (new migration 0018 — real consumer: _sob_a_pasta,
        # repositories/media.py:171, and /api/pastas tree click):
        # Index("ix_media_files_pasta", "pasta"),
        # ADD (new migration 0018 — real consumer: repositories/media.py:278,356):
        # Index("ix_media_files_location_id", "location_id"),
        # ADD (drift reconciliation only — index already exists in the DB via
        # migrations 0005/0006/0007, model file never mirrored it; NO new
        # migration needed for these three, per RESEARCH.md Pitfall 2):
        # Index("ix_media_files_gps_estimado_de_id", "gps_estimado_de_id"),
        # Index("ix_media_files_tipo_imagem", "tipo_imagem"),
        # Index("ix_media_files_tipo_confirmado", "tipo_confirmado"),
    )
```
Every existing entry already carries a comment justifying the index by real consumer (lines 129-134 for the `trip_id`/`event_id` precedent) — new entries should follow the same commenting convention, citing the query-site file:line from RESEARCH.md's Code Examples table.

**`Source` class needs its first `__table_args__`** (currently lines 70-93 have none; DB already has `ix_sources_volume_id` from migration 0011, drift-only fix, no new migration):
```python
class Source(Base):
    __tablename__ = "sources"
    __table_args__ = (Index("ix_sources_volume_id", "volume_id"),)
    # ... existing columns unchanged
```

---

### `fotoorganizer/models/inference.py` (model, schema declaration)

**Analog:** same file, `Evidence.__table_args__` (line 41) — exact same one-`Index`-tuple shape needed for `Suggestion`.

**Core pattern** (line 63, extend the existing tuple):
```python
class Suggestion(Base):
    __tablename__ = "suggestions"
    __table_args__ = (
        Index("ix_suggestions_status", "status"),
        # ADD (new migration 0018 — heavily queried per-media lookup:
        # engine.py:1042,1083,1106; server/app.py:724;
        # repositories/media.py:118,149; repositories/suggestions.py:119,296;
        # operations/planner.py:60; operations/inventario.py:161):
        Index("ix_suggestions_media_id", "media_id"),
    )
```
`Index` is already imported in this file (line 12).

---

### `fotoorganizer/models/operations.py` (model, schema declaration)

**Analog:** `fotoorganizer/models/inference.py` line 41 — shape for adding `__table_args__` to a class that currently has none.

**Imports — need to add `Index`** (current imports, line 12):
```python
from sqlalchemy import JSON, Enum, ForeignKey, Text
```
becomes:
```python
from sqlalchemy import JSON, Enum, ForeignKey, Index, Text
```

**Core pattern — `OperationItem`** (currently lines 48-67, no `__table_args__`):
```python
class OperationItem(Base):
    __tablename__ = "operation_items"
    __table_args__ = (
        # Consumer: repositories/operations.py:71,141 (list items of a plan
        # — the Operations screen's core query); operations/executor.py:272.
        Index("ix_operation_items_plan_id", "plan_id"),
        # Consumer: operations/planner.py:68 (check pending ops per media).
        Index("ix_operation_items_media_id", "media_id"),
    )
    # ... existing columns unchanged (id, plan_id, media_id, ...)
```

**Core pattern — `AuditLog`** (currently lines 70-79, no `__table_args__`):
```python
class AuditLog(Base):
    __tablename__ = "audit_log"
    __table_args__ = (
        # Consumer: repositories/operations.py:95,128; operations/executor.py:131,163
        # (audit trail per plan — dry-run + execution log).
        Index("ix_audit_log_plan_id", "plan_id"),
    )
    # ... existing columns unchanged
```

---

### `fotoorganizer/models/duplicates.py` (model, schema declaration)

**Analog:** same file, `DuplicateMember.__table_args__` (line 58) — extend the existing tuple, same file already imports nothing extra needed except `Index`.

**Imports — need to add `Index`** (line 6):
```python
from sqlalchemy import Enum, ForeignKey, UniqueConstraint
```
becomes:
```python
from sqlalchemy import Enum, ForeignKey, Index, UniqueConstraint
```

**Core pattern** (line 58, extend):
```python
class DuplicateMember(Base):
    __tablename__ = "duplicate_members"
    __table_args__ = (
        UniqueConstraint("group_id", "media_id"),
        # Consumer: operations/planner.py:79; duplicates/detector.py:302
        # ("which group is this media in" reverse lookup). NOT covered by the
        # UniqueConstraint above — media_id is only the SECOND column there,
        # not usable as a leading-column index for a media_id-only filter.
        Index("ix_duplicate_members_media_id", "media_id"),
    )
```

---

### `fotoorganizer/models/people.py` (model, schema declaration)

**Analog:** `fotoorganizer/models/inference.py` line 41 — shape for adding `__table_args__` to a class with none.

**Imports — need to add `Index`** (line 12):
```python
from sqlalchemy import JSON, Enum, ForeignKey, LargeBinary
```
becomes:
```python
from sqlalchemy import Enum, ForeignKey, Index, JSON, LargeBinary
```

**Core pattern — `FaceOccurrence`** (currently lines 52-63, no `__table_args__`; both columns have a real query-site consumer per RESEARCH.md's table, `repositories/people.py:42,108,109` — do NOT confuse with `FaceEmbedding.person_id`, a *different* class in the same file which RESEARCH.md's Open Question 1 recommends **excluding** for lack of an observed consumer):
```python
class FaceOccurrence(Base):
    __tablename__ = "face_occurrences"
    __table_args__ = (
        Index("ix_face_occurrences_media_id", "media_id"),
        Index("ix_face_occurrences_person_id", "person_id"),
    )
    # ... existing columns unchanged
```
`FaceEmbedding` (lines 39-49, same file) is intentionally **not** touched — no query-site usage found (RESEARCH.md Open Question 1 recommendation: exclude).

---

### `fotoorganizer/database/engine.py` (config, connection setup)

**Analog:** same file (whole file is only 37 lines — already fully in context, no re-read needed).

**Exact change** (lines 11-17):
```python
def _set_sqlite_pragmas(dbapi_connection, _record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.execute("PRAGMA case_sensitive_like=ON")  # NEW — required for
    # `pasta` prefix-LIKE (_sob_a_pasta, repositories/media.py:171) to use
    # ix_media_files_pasta. Verified (RESEARCH.md Pitfall 3) not to affect
    # any .ilike() call (compiles to lower(x) LIKE lower(y), independent of
    # this pragma) or .not_like() call (leading-wildcard pattern, never
    # index-eligible regardless).
    cursor.close()
```
**LOAD-BEARING:** per RESEARCH.md Pitfall 3, the `Index("ix_media_files_pasta", "pasta")` addition in `catalog.py` is *necessary but not sufficient* — this PRAGMA line is required in the same change for LANC-02's stated success criterion ("usam índice, não table scan") to actually hold for the `pasta` prefix query. Both files must land together.

---

### `fotoorganizer/database/migrations/versions/0018_*.py` (migration, batch DDL)

**Analog:** `fotoorganizer/database/migrations/versions/0017_indice_trip_id_event_id.py` (whole file, 39 lines, already fully in context) — most recent, most directly analogous prior migration; single-purpose index-only migration with the same `op.batch_alter_table(...).create_index(...)` shape needed here.

**Full template to copy** (docstring convention: cite which query does a SCAN today, which screen/endpoint triggers it, per-index — same convention as 0017's docstring):
```python
"""índices de FK ausentes (fase 5, LANC-02)

<justificativa por índice, mesmo padrão das migrações 0005/0017: qual
consulta faz SCAN hoje, qual tela/endpoint aciona, medido ou observado por
grep de uso real>

Revision ID: 0018
Revises: 0017
Create Date: <data>

"""
from typing import Sequence, Union

from alembic import op

revision: str = '0018'
down_revision: Union[str, None] = '0017'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('media_files', schema=None) as batch_op:
        batch_op.create_index('ix_media_files_pasta', ['pasta'], unique=False)
        batch_op.create_index('ix_media_files_location_id', ['location_id'], unique=False)
    with op.batch_alter_table('suggestions', schema=None) as batch_op:
        batch_op.create_index('ix_suggestions_media_id', ['media_id'], unique=False)
    with op.batch_alter_table('operation_items', schema=None) as batch_op:
        batch_op.create_index('ix_operation_items_plan_id', ['plan_id'], unique=False)
        batch_op.create_index('ix_operation_items_media_id', ['media_id'], unique=False)
    with op.batch_alter_table('audit_log', schema=None) as batch_op:
        batch_op.create_index('ix_audit_log_plan_id', ['plan_id'], unique=False)
    with op.batch_alter_table('duplicate_members', schema=None) as batch_op:
        batch_op.create_index('ix_duplicate_members_media_id', ['media_id'], unique=False)
    with op.batch_alter_table('face_occurrences', schema=None) as batch_op:
        batch_op.create_index('ix_face_occurrences_media_id', ['media_id'], unique=False)
        batch_op.create_index('ix_face_occurrences_person_id', ['person_id'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('face_occurrences', schema=None) as batch_op:
        batch_op.drop_index('ix_face_occurrences_person_id')
        batch_op.drop_index('ix_face_occurrences_media_id')
    with op.batch_alter_table('duplicate_members', schema=None) as batch_op:
        batch_op.drop_index('ix_duplicate_members_media_id')
    with op.batch_alter_table('audit_log', schema=None) as batch_op:
        batch_op.drop_index('ix_audit_log_plan_id')
    with op.batch_alter_table('operation_items', schema=None) as batch_op:
        batch_op.drop_index('ix_operation_items_media_id')
        batch_op.drop_index('ix_operation_items_plan_id')
    with op.batch_alter_table('suggestions', schema=None) as batch_op:
        batch_op.drop_index('ix_suggestions_media_id')
    with op.batch_alter_table('media_files', schema=None) as batch_op:
        batch_op.drop_index('ix_media_files_location_id')
        batch_op.drop_index('ix_media_files_pasta')
```
**Do NOT** add `create_index` calls for `ix_sources_volume_id`, `ix_media_files_gps_estimado_de_id`, `ix_media_files_tipo_imagem`, `ix_media_files_tipo_confirmado` in this migration — those four already exist in the live DB schema (migrations 0005/0006/0007/0011); adding a `create_index` for them here will fail at `upgrade_to_head()` with a duplicate-index error (RESEARCH.md Pitfall 2's explicit warning sign). Those four are model-file-only fixes, no migration.

---

### `tests/test_indices.py` (test, query-plan assertion)

**Analog:** `tests/test_database.py` (whole file, 207 lines, already fully in context) — specifically the `migrated_engine` fixture usage (from `tests/conftest.py` lines 14-19) and the raw-`text()`-query pattern in `test_wal_e_foreign_keys_ativos` (lines 25-28).

**Fixture already available, no new fixture needed** (`tests/conftest.py` lines 14-19):
```python
@pytest.fixture()
def migrated_engine(db_path):
    from fotoorganizer.database import create_db_engine, upgrade_to_head

    upgrade_to_head(db_path)
    engine = create_db_engine(db_path)
    yield engine
    engine.dispose()
```

**Core pattern to copy** (mirrors `test_wal_e_foreign_keys_ativos`, `tests/test_database.py` lines 25-28):
```python
from sqlalchemy import text


def test_pasta_usa_indice_nao_scan(migrated_engine):
    """LANC-02's actual success criterion: SEARCH, not SCAN.

    Ver RESEARCH.md Pitfall 3 — um Index() sozinho na coluna `pasta` NÃO
    basta; o teste teria passado com o índice criado e a pragma ausente se
    só checasse "índice existe", por isso a asserção é sobre o plano de
    consulta, não sobre o schema.
    """
    with migrated_engine.connect() as conn:
        plano = conn.execute(
            text(
                "EXPLAIN QUERY PLAN "
                "SELECT * FROM media_files WHERE pasta LIKE '/some/prefix/%' ESCAPE '\\'"
            )
        ).fetchall()
    detalhe = " ".join(row[3] for row in plano)
    assert "SEARCH" in detalhe
    assert "ix_media_files_pasta" in detalhe
    assert "SCAN media_files" not in detalhe
```
Needs data seeded first (some rows in `media_files` with a matching `source_id`/`pasta`) if `EXPLAIN QUERY PLAN` on an empty table doesn't reliably choose the index — verify empirically; if it does not, follow `test_roundtrip_media_file`'s `Source`/`MediaFile` construction pattern (`tests/test_database.py` lines 138-177) to seed one row before asserting the plan.

---

### `docs/PERFORMANCE.md` (config/doc, append-per-measurement-round)

**Analog:** `docs/AVALIACAO_UX.md` (whole file, 418 lines) — **structural finding from this mapping pass**: the file is not a single one-off report. It accumulates as multiple dated top-level (`# `) sections appended over time:
```
# Rodada de 2026-08-06 — pós-correções de scan + feedback do dono
## A. Crítica de fluxo (app vivo, `agente-ux`)
## B. Auditoria de consistência visual (`agente-arte`)
## C. Feedback do dono (2026-08-06) — Fase 5, diagnosticado com evidência
## D. Priorização consolidada (A + B, ordenada por valor/esforço)
# Avaliação de UX — fase 6
## 1. Por que parece um site
## 2. O problema difícil: a interface mostra conclusão, não decisão
...
## Comparação com o mercado
```
This is the correct analog for D-09's requirement ("vira a referência canônica para medir regressão de performance em fases futuras") — each future baseline re-measurement should **append a new dated `# ` section**, not rewrite the file. `docs/PERFORMANCE.md`'s first section should follow this shape:
```markdown
# Baseline de 2026-08-17 — pós-reset do catálogo (fase 5, LANC-04)

Contexto: `catalog.db` foi zerado em 2026-08-16 ... primeira varredura
completa desde então, medida contra o acervo real (~99 mil registros
conhecidos).

## Metodologia
<decisão registrada: medido em cópia do catalog.db recém-varrido, ou in
place — RESEARCH.md Pitfall 4 exige que esta escolha fique documentada
aqui para reprodutibilidade>

## Taxa de indexação (varredura)
| Métrica | Valor |
|---|---|
| Arquivos indexados | ... |
| Tempo total | ... |
| Taxa (arq/s) | ... |

## Tempo de geração de sugestões
...

## Tempo de detecção de duplicatas
...
```

---

### `scripts/medir_baseline_producao.py` (utility, one-shot timed CLI script)

**Analog 1 (timing shape):** `fotoorganizer/cli.py` `cmd_bench` (lines 566-612, already fully in context).

**Analog 2 (standalone-script shape, not a `cli.py` subcommand):** `scripts/avaliar_agrupamento.py` (lines 1-23 read) — the repo's convention for a one-off measurement script that lives in `scripts/` and imports directly from `fotoorganizer.*`, run via `.venv/bin/python scripts/<nome>.py`, not wired into `argparse`/`_build_parser()`.

**Core timing pattern to copy** (`fotoorganizer/cli.py` lines 600-611):
```python
inicio = time.monotonic()
_, m1 = scanner.scan_source(fotos)
frio = time.monotonic() - inicio
print(f"Indexação a frio : {m1.indexados} arquivos em {frio:.2f}s "
      f"({m1.indexados / frio:.0f} arq/s)")
```

**Standalone-script header convention to copy** (`scripts/avaliar_agrupamento.py` lines 1-19):
```python
"""<descrição em uma linha>.

Uso: .venv/bin/python scripts/<nome>.py

<contexto/decisão de por que este script existe>
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fotoorganizer.<modulo> import <o que for preciso>
```

**Critical divergence from `cmd_bench`:** `cmd_bench` is deliberately isolated from production data (temp dir, temp DB — "nunca para o cache real do usuário"). Per D-07, this new script must do the **opposite** — point at the real, freshly-rescanned `catalog.db` — while still following Pitfall 4's guidance: decide explicitly (and document in `docs/PERFORMANCE.md`) whether `SuggestionEngine.gerar()`/`DuplicateDetector.detectar()` run against a **throwaway copy** of `catalog.db` (safer — mirrors `cmd_bench`'s isolation philosophy, applied one level up) or in place. Only the scan-rate portion needs to touch the real catalog directly (D-07: the rescan itself is the measurement opportunity, not a separate pass).

## Shared Patterns

### Index declaration + docstring-justification convention
**Source:** `fotoorganizer/models/catalog.py` lines 117-137 (comments on `ix_media_files_arquivo_offline`, `ix_media_files_trip_id`, `ix_media_files_event_id`)
**Apply to:** every new `Index(...)` line added in this phase (catalog.py, inference.py, operations.py, duplicates.py, people.py)
```python
# `_agrupamentos` (server/app.py, /api/viagens e /api/eventos) filtra por
# estas duas colunas uma vez por grupo — sem índice, cada uma delas é um
# SCAN completo da tabela (medido: 477 mil linhas)... índice quando o custo
# de escrita se justifica por um consumidor real e mensurável (D-072).
Index("ix_media_files_trip_id", "trip_id"),
```
Every index in this codebase carries an inline comment citing the real query-site consumer (file:line) and, where measured, the row-count cost of the missing index. New indexes in this phase should cite RESEARCH.md's Code Examples table (file:line per column) the same way.

### Alembic migration shape
**Source:** `fotoorganizer/database/migrations/versions/0017_indice_trip_id_event_id.py` (whole file)
**Apply to:** `0018_*.py`
One `op.batch_alter_table(table, schema=None) as batch_op: batch_op.create_index(name, [col], unique=False)` block per table touched, symmetric `drop_index` in `downgrade()`, revision docstring citing what SCANs today and which screen/endpoint triggers it.

### Test fixture for migrated DB
**Source:** `tests/conftest.py` lines 14-19 (`migrated_engine` fixture, already exists — no new fixture needed)
**Apply to:** `tests/test_indices.py`

## No Analog Found

Files that only get modified conditionally, on a real defect being found during verification (not planned construction — D-03, D-05). Do not fabricate a pattern assignment for these; if the conditional path triggers, use the reference noted:

| File | Role | Data Flow | Reason | If triggered, reference |
|---|---|---|---|---|
| `src-tauri/src/main.rs` | native shell / config | event-driven | LANC-01 is verification-only per D-02; modify only if verification finds an orphan-process/crash/serve bug (D-03) | Existing two-layer orphan-prevention design: `RunEvent::ExitRequested` → SIGTERM (Rust side, this file) + `_vigia_pai` ppid-poll self-SIGTERM (`fotoorganizer/cli.py` lines 671-678, already read) — fix within this established split, don't replace it |
| `fotoorganizer/cli.py` (`cmd_web`, lines 615-681) | controller | request-response | Same as above — conditional on D-03 finding | Already read in full; `FOTOORG_READY` stdout contract (line 658) and `--encerrar-com-pai` flag (line 664) are the two integration points a fix would touch |
| `webapp/src/components/ModalCaminho.tsx`, `Panorama.tsx`, `PhotoGrid.tsx`, `Trips.tsx` | component | event-driven | LANC-03 is validation-only per D-04/D-05; modify only if the uninstructed user test surfaces a real blocker | `.planning/phases/04-consist-ncia-visual-secund-ria/04-06-SUMMARY.md` documents what Phase 4 already wired (3 empty-state entry points → shared `ModalCaminho.tsx` with scan progress + surfaced error) — any fix should extend that existing shared modal, not introduce a new component or wizard |

## Metadata

**Analog search scope:** `fotoorganizer/models/*.py` (all 9 files, 6 read in full or targeted), `fotoorganizer/database/{engine.py,migrations/versions/*.py}`, `fotoorganizer/repositories/media.py`, `fotoorganizer/cli.py`, `tests/{conftest.py,test_database.py}`, `docs/AVALIACAO_UX.md` (structure grep across full 418 lines), `scripts/` (directory listing + one file read for standalone-script shape), `src-tauri/src/main.rs` (listed, not read — conditional file, per advisor guidance not to over-read a file that may not change).
**Files scanned:** ~20 read/grepped, 10 confirmed pattern assignments produced.
**Pattern extraction date:** 2026-08-17

---

*Phase: 5-Preparação para lançamento*
*Patterns mapped: 2026-08-17*
