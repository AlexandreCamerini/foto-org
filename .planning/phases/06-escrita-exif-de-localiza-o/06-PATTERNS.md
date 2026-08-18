# Phase 6: Escrita EXIF de localização - Pattern Map

**Mapped:** 2026-08-18
**Files analyzed:** 14 (new) + 4 (modified)
**Analogs found:** 18 / 18 (sidecar XMP write folded into writer.py's analog, not counted separately)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|----------------|
| `fotoorganizer/exif_write/writer.py` (`ExifToolWriter`) | service | file-I/O (subprocess mutation) | `fotoorganizer/metadata/exiftool.py` (`ExifToolExtractor`) | role-match (write vs. read, same subprocess discipline) |
| `fotoorganizer/exif_write/planner.py` | service | CRUD (plan build) | `fotoorganizer/operations/planner.py` (`OperationPlanner`) | exact (dry-run plan builder, same shape) |
| `fotoorganizer/exif_write/executor.py` | service | CRUD + file-I/O | `fotoorganizer/operations/executor.py` (`OperationExecutor`) | exact (dry-run→approve→execute→audit shape) |
| `fotoorganizer/exif_write/sync_detect.py` | utility | transform (path→verdict) | `fotoorganizer/security/volumes.py` (`identificar`/`volume_desmontado`) | role-match (pure path/filesystem classification, no I/O beyond stat) |
| `fotoorganizer/models/exif_write.py` (`ExifWritePlan`, `ExifWriteItem`) | model | CRUD | `fotoorganizer/models/operations.py` (`OperationPlan`, `OperationItem`, `AuditLog`) | exact (structurally parallel per locked architecture) |
| `fotoorganizer/database/migrations/versions/00XX_exif_write_tables.py` | migration | batch | `fotoorganizer/database/migrations/versions/0018_indices_de_fk_ausentes.py` | role-match (most recent migration; use as commentary/structure template, not content) |
| `fotoorganizer/server/app.py` (new `/api/exif/*` routes) | route | request-response | `fotoorganizer/server/app.py` `/api/operacoes*` routes (lines 1191-1283) | exact (same file, same author, same request-response shape) |
| `fotoorganizer/server/jobs.py` (new `iniciar_escrita_exif` + `_rodar_escrita_exif`) | service | event-driven (background thread) | `fotoorganizer/server/jobs.py` `iniciar_execucao`/`_rodar_execucao` (lines 123-133, 218+) | exact (same file, same background-job pattern) |
| `scripts/testar_escrita_exif.py` | utility (standalone script) | batch | `scripts/calibrar_raio_incerteza.py` | role-match (standalone measurement script feeding a `docs/DECISOES.md` entry; this one writes to disposable copies instead of being read-only) |
| `tests/test_exif_write.py` | test | CRUD | `tests/test_operations.py` | exact (same fixture shape: `migrated_engine` + `tmp_path` + `create_session_factory`) |
| `tests/fixtures.py` (extend, e.g. GPS-filled variant) | utility | transform | `tests/fixtures.py::make_jpeg` (existing, already supports `gps=` param) | exact — likely no new function needed, reuse `make_jpeg(gps=...)` |
| `webapp/src/components/EscritaExif.tsx` | component | request-response | `webapp/src/components/Operations.tsx` | exact (explicit precedent per CONTEXT.md/UI-SPEC.md) |
| `webapp/src/components/EscritaExif.test.tsx` | test | request-response | `webapp/src/components/Operations.test.tsx` | exact |
| `webapp/src/App.tsx` (add `"Localização"` tab) | route/provider | request-response | `webapp/src/App.tsx` existing `ABAS`/`DICAS`/tab-render block (lines 24-30, 41-43, 309) | exact (same file) |
| `webapp/src/api.ts` (new `planoExif`/`dryRunExif`/`executarExif` calls, new types) | service (API client) | request-response | `webapp/src/api.ts` existing `planos`/`plano`/`criarPlano`/`dryRun`/`auditoria` functions (used by `Operations.tsx`) | exact — read alongside `Operations.tsx` usage; not re-read separately, same shape as `api.planos()`/`api.dryRun()` |

## Pattern Assignments

### `fotoorganizer/exif_write/writer.py` (service, file-I/O)

**Analog:** `fotoorganizer/metadata/exiftool.py` (`ExifToolExtractor`)

**Module docstring / safety framing pattern** (lines 1-21):
```python
"""Extrator via exiftool, em processo persistente (`-stay_open`).
...
Segurança (invariante 5): sem `shell=True`, argumentos em lista, caminho
resolvido e recusado se não for arquivo comum. Um caminho com `\n` quebraria
o protocolo do `-stay_open` — é rejeitado antes de chegar lá.

Nunca levanta exceção por arquivo: devolve `MediaMetadata` com `erro`
preenchido, e o scanner cataloga assim mesmo.
"""
```
Adapt this framing for the writer: state explicitly that writer errors never raise past a single item (mirrors `_executar_item`'s try/except in `operations/executor.py`), and that every write is verified by tag-diff, not exit code (per RESEARCH.md Pitfall 2 — this is the one place the analog's "trust the subprocess" pattern must NOT be copied verbatim).

**Availability check pattern** (lines 307-309):
```python
@staticmethod
def disponivel(binario: str | None = None) -> bool:
    return shutil.which(binario or "exiftool") is not None
```
Copy verbatim for the writer — same gate the read path already uses (RESEARCH.md: "if exiftool is absent, EXIF write must be entirely unavailable, mirrors the existing read path's `disponivel()` check").

**Subprocess invocation discipline** — do NOT copy the `-stay_open` persistent-process shape (`_garantir`, lines 318-328). RESEARCH.md explicitly recommends one short-lived `subprocess.run` per write instead (write volume is bounded, unlike the full-scan read path). Use invariant-5-compliant list args, no `shell=True`, exactly as the reader does it, but with `subprocess.run` per RESEARCH.md's Pattern 1:
```python
def escrever(origem: Path, campos: dict, destino: Path | None = None) -> subprocess.CompletedProcess:
    alvo = destino or origem
    args = ["exiftool"]
    if "gps" in campos:
        lat, lon = campos["gps"]
        args += [
            f"-GPSLatitude={abs(lat)}", f"-GPSLatitudeRef={'N' if lat >= 0 else 'S'}",
            f"-GPSLongitude={abs(lon)}", f"-GPSLongitudeRef={'E' if lon >= 0 else 'W'}",
        ]
    if "cidade" in campos:
        args += [f"-IPTC:City={campos['cidade']}", f"-XMP:City={campos['cidade']}"]
    if "pais" in campos:
        args += [
            f"-IPTC:Country-PrimaryLocationName={campos['pais']}",
            f"-XMP:Country={campos['pais']}",
        ]
    args.append(str(alvo))
    return subprocess.run(args, capture_output=True, text=True, check=False)
```
(Source: RESEARCH.md "Pattern 1: Writer method shape", verified this session against exiftool 13.55.)

**Sidecar XMP write (D-06)** — same method, different `destino`: calling `escrever(origem, campos, destino=origem.with_suffix(origem.suffix + ".xmp"))` (target `foto.<ext>.xmp`) produces a standalone XMP sidecar with the identical argument list, verified working this session (XMP group only — no IPTC group for a bare `.xmp` target). No separate class or method needed; this is the same analog (`escrever()` above), not a new pattern to source elsewhere.

**Sync-folder detection** (own function, `sync_detect.py`) — closest analog is `security/volumes.py`'s pure-path, no-exception style:
```python
def volume_desmontado(caminho: Path | str) -> Path | None:
    partes = Path(caminho).expanduser().parts
    if len(partes) < 3 or partes[1] != "Volumes":
        return None
    raiz = Path(partes[0], partes[1], partes[2])
    return None if os.path.ismount(raiz) else raiz
```
Mirror this shape (pure `pathlib`/`os.path`, never raises, returns `None`/verdict) for `pasta_sincronizada(caminho: Path) -> str | None`. RESEARCH.md's Code Examples section has the concrete implementation already verified against this machine's `~/Library/Mobile Documents` and `~/Library/CloudStorage`.

---

### `fotoorganizer/exif_write/planner.py` (service, CRUD)

**Analog:** `fotoorganizer/operations/planner.py` (`OperationPlanner`)

**Imports pattern** (lines 1-34):
```python
from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from fotoorganizer.models import (
    AuditLog, DuplicateMember, DuplicateRole, MediaFile,
    OperationItem, OperationPlan, OperationStatus, Source,
    Suggestion, SuggestionStatus,
)
from fotoorganizer.security.paths import (
    CaminhoInvalido, destino_recursivo, resolver_destino,
)

log = logging.getLogger(__name__)
```
For the exif planner, swap `OperationItem`/`OperationPlan` for `ExifWriteItem`/`ExifWritePlan`, drop `security.paths` (not needed — no destination path resolution, in-place write), add `MetadataExtractor`/`ExifToolExtractor` import for the emptiness check and `fotoorganizer.exif_write.sync_detect` for D-07.

**Constructor + `criar_plano`-shaped method** (lines 48-56):
```python
class OperationPlanner:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._factory = session_factory

    def criar_plano(self, raiz_destino: Path, nome: str | None = None) -> int | None:
        """Cria um plano de CÓPIA... Devolve o id do plano, ou None se não
        havia nada a planejar."""
```
Same signature shape for `criar_plano_exif() -> int | None` — global scope per UI-SPEC.md ("one dry-run plan covering every catalogued file with an empty field and an inferred value"), no `raiz_destino` param needed (in-place write has no destination root).

**Row-append + AuditLog-on-create pattern** (lines 119-133):
```python
session.add(OperationItem(
    plan_id=plano.id, media_id=media.id,
    origem=str(origem), destino=destino_str,
    conflito=conflito,
    status=OperationStatus.PLANEJADA,
))
...
session.add(AuditLog(
    plan_id=plano.id, acao="plano_criado",
    detalhe={"raiz": str(raiz), "itens": len(pendentes)},
    resultado="ok",
))
session.commit()
```
Copy this shape for `ExifWriteItem` rows, but per RESEARCH.md Pitfall 5: **do not** set `AuditLog.plan_id = exif_plan.id` (real enforced FK to `operation_plans.id`, `PRAGMA foreign_keys=ON`). Leave `plan_id=None`, carry `{"exif_plan_id": plano.id, ...}` inside `detalhe` instead.

**Per-item classification logic to add (no direct analog — new decision tree)**: for each candidate `MediaFile`, call the existing `MetadataExtractor.extract()` (same call the scanner already uses) to determine which of GPS/city/country are empty; call `pasta_sincronizada()` (D-07); check extension against the measured allowlist from `scripts/testar_escrita_exif.py`'s output (D-05) to decide Type A/B/C row classification per UI-SPEC.md.

---

### `fotoorganizer/exif_write/executor.py` (service, CRUD + file-I/O)

**Analog:** `fotoorganizer/operations/executor.py` (`OperationExecutor`)

**Dry-run guard pattern** (lines 54-55, 138-161):
```python
class DryRunObrigatorio(RuntimeError):
    pass
...
def executar(self, plan_id: int, ...) -> dict:
    ...
    plano = session.get(OperationPlan, plan_id)
    if plano.dry_run_em is None:
        raise DryRunObrigatorio(
            "execute o dry-run antes de qualquer operação física"
        )
    prontos = self._prontos_no_ultimo_dry_run(session, plan_id)
    if prontos == 0:
        raise DryRunObrigatorio(
            "o último dry-run não encontrou nenhum arquivo copiável — ..."
        )
```
Copy this exact guard shape for the exif executor (EXIF-01's "nothing written before approval" requirement) — reuse the class name pattern (`DryRunObrigatorioExif` or share the exception class if imported).

**Per-item try/except with typed error handling** (lines 196-252, esp. 242-252):
```python
except FileExistsError:
    item.status = OperationStatus.ERRO
    item.erro = "destino já existe — sobrescrita bloqueada"
    stats["erros"] += 1
    self._audit_item(session, item, "copia", "bloqueada_sobrescrita")
except OSError as exc:
    item.status = OperationStatus.ERRO
    item.erro = ("disco cheio" if exc.errno == errno.ENOSPC else str(exc))
    stats["erros"] += 1
    self._audit_item(session, item, "copia", f"erro: {item.erro}")
```
Structurally mirror this for `_executar_item` in the new executor, but replace the pass/fail signal: **do not** treat `subprocess.CompletedProcess.returncode` as success (RESEARCH.md Pitfall 2 — exit 0 with a silently-skipped tag is the central failure mode this phase exists to catch). Success/failure must come from the pre/post full-tag diff (RESEARCH.md Pattern 2), producing a **per-field** result (`gravado`/`falha`/`pulado`), not a per-item binary outcome — this is the one place the analog's binary status model does not transfer; the new `ExifWriteItem` needs per-field status columns or a JSON breakdown, not a single `status` enum value covering all 3 fields.

**Audit-item helper pattern** (lines 276-283):
```python
def _audit_item(self, session: Session, item: OperationItem, acao: str,
                resultado: str) -> None:
    session.add(AuditLog(
        plan_id=item.plan_id, acao=acao,
        detalhe={"origem": item.origem, "destino": item.destino,
                 "hash_pre": item.hash_pre, "hash_pos": item.hash_pos},
        resultado=resultado,
    ))
```
Copy shape, but (per Pitfall 5) `plan_id=None` and move `item.plan_id`/exif-plan id into `detalhe`. Extend `detalhe` with the tag-diff breakdown (which of GPS/cidade/país landed) so a single audit row already carries EXIF-03's partial-failure detail.

**`_prontos_no_ultimo_dry_run` staticmethod pattern** (lines 122-135) — copy verbatim shape (query latest `AuditLog` row by `acao="dry_run"`, read `detalhe["prontos"]`), adjusted for the `detalhe` JSON payload change from Pitfall 5.

---

### `fotoorganizer/exif_write/sync_detect.py` (utility, transform)

**Analog:** `fotoorganizer/security/volumes.py`

**Never-raises, path-only classification pattern** (lines 62-74):
```python
def volume_desmontado(caminho: Path | str) -> Path | None:
    """... Falha de `diskutil` nunca levanta — devolve a identidade mais
    fraca e segue."""
    partes = Path(caminho).expanduser().parts
    if len(partes) < 3 or partes[1] != "Volumes":
        return None
    raiz = Path(partes[0], partes[1], partes[2])
    return None if os.path.ismount(raiz) else raiz
```
This is the shape to mirror: pure filesystem check, `try/except OSError: return <safe default>` where needed, never propagates. RESEARCH.md already has the concrete `pasta_sincronizada()` implementation verified against this machine — use it directly (Code Examples section, `_RAIZES_SINCRONIZADAS` dict + `Path.resolve()` + `is_relative_to()`).

---

### `fotoorganizer/models/exif_write.py` (model, CRUD)

**Analog:** `fotoorganizer/models/operations.py`

**Full file is the template** (93 lines) — `OperationStatus`/`OperationType` enums, `OperationPlan`, `OperationItem`, `AuditLog`:
```python
class OperationStatus(enum.StrEnum):
    PLANEJADA = "planejada"
    APROVADA = "aprovada"
    EXECUTANDO = "executando"
    CONCLUIDA = "concluida"
    CANCELADA = "cancelada"
    ERRO = "erro"

class OperationPlan(Base):
    __tablename__ = "operation_plans"
    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str]
    status: Mapped[OperationStatus] = mapped_column(
        Enum(OperationStatus, native_enum=False), default=OperationStatus.PLANEJADA
    )
    dry_run_em: Mapped[datetime | None]
    criado_em: Mapped[datetime] = mapped_column(default=utcnow)
    itens: Mapped[list["OperationItem"]] = relationship(
        back_populates="plano", cascade="all, delete-orphan"
    )

class OperationItem(Base):
    __tablename__ = "operation_items"
    __table_args__ = (
        Index("ix_operation_items_plan_id", "plan_id"),
        Index("ix_operation_items_media_id", "media_id"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("operation_plans.id"))
    media_id: Mapped[int] = mapped_column(ForeignKey("media_files.id"))
    ...
    hash_pre: Mapped[str | None]
    hash_pos: Mapped[str | None]
    erro: Mapped[str | None] = mapped_column(Text)
```
Key deltas for `ExifWritePlan`/`ExifWriteItem` (do not copy blindly):
- No `OperationType` equivalent needed (only one operation: write).
- `ExifWriteItem` needs **per-field** status, not one `status` column — add e.g. `status_gps`/`status_cidade`/`status_pais` (or a JSON `campos` column) per EXIF-03's per-field partial-failure requirement (see executor.py analog notes above). This is the sharpest structural deviation from the analog.
- Add `formato_suportado: Mapped[bool]`, `motivo_nao_suportado: Mapped[str | None]`, `sidecar_destino: Mapped[str | None]` for EXIF-05/D-06.
- Add `pasta_sincronizada: Mapped[str | None]` for D-07 (nullable — service name or `None`).
- `hash_pre`/`hash_pos` fields: RESEARCH.md's locked architecture explicitly demotes file hash to an audit *fact*, not the pass/fail criterion (diff-of-tags is) — keep the columns (useful audit trail, same `sha256_full()` reuse from `security/hashing.py`) but do not gate `status` on them.
- `AuditLog` is **reused as-is, unchanged** — no new model needed for audit; see Shared Patterns below for the FK caveat (Pitfall 5).

**Index comment convention** (lines 50-58) — this codebase documents every index with its consumer file:line in a comment above `__table_args__`. Follow this convention for any new indexes on `ExifWriteItem` (e.g. `plan_id`, `media_id`).

---

### `fotoorganizer/database/migrations/versions/00XX_exif_write_tables.py` (migration, batch)

**Analog:** `fotoorganizer/database/migrations/versions/0018_indices_de_fk_ausentes.py`

**Docstring-as-rationale convention** (lines 1-53) — every migration in this repo opens with a prose docstring naming the phase/decision, listing each schema change with its consumer, and citing `Revision ID`/`Revises`/`Create Date`. Follow this convention: name D-075, list each new table/column with which planner/executor code will read it. This migration is a `create_table` migration, not `batch_alter_table` on an existing table — structurally closer to whichever earlier migration first created `operation_plans`/`operation_items`/`audit_log` (not read this session; if needed, `grep -rn "operation_plans" fotoorganizer/database/migrations/versions/` will locate it) — but the **docstring/revision-header convention** shown here is what to copy regardless of which migration created the analog tables.

**Revision header boilerplate** (lines 54-61):
```python
from typing import Sequence, Union
from alembic import op

revision: str = '00XX'
down_revision: Union[str, None] = '0018'  # or latest at plan time
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
```
Copy verbatim (just update `revision`/`down_revision`).

---

### `fotoorganizer/server/app.py` (new `/api/exif/*` routes)

**Analog:** same file, `/api/operacoes*` routes (lines 1191-1283)

**Serialization-helper + list/detail/dry-run/execute route group pattern**:
```python
def _plano_json(row) -> dict:
    return {
        "id": row.id, "nome": row.nome, "status": row.status.value,
        "dry_run_em": row.dry_run_em.isoformat() if row.dry_run_em else None,
        "criado_em": row.criado_em.isoformat(),
        "total_itens": row.total_itens, "concluidos": row.concluidos,
        "com_conflito": row.com_conflito, "com_erro": row.com_erro,
        "prontos": row.prontos, "problemas": row.problemas,
        "executavel": row.executavel,
    }

@app.get("/api/operacoes")
def listar_planos() -> list[dict]:
    return [_plano_json(p) for p in operation_repo.listar_planos()]

@app.post("/api/operacoes")
def criar_plano(body: PlanoBody) -> dict:
    ...
    plan_id = planner.criar_plano(raiz, body.nome)
    if plan_id is None:
        raise HTTPException(409, "nenhuma sugestão aprovada aguardando cópia")
    return _plano_json(operation_repo.plano(plan_id))

@app.post("/api/operacoes/{plan_id}/dry-run")
def dry_run_plano(plan_id: int) -> dict:
    """Só lê: confere origens, destinos livres e espaço em disco."""
    if operation_repo.plano(plan_id) is None:
        raise HTTPException(404, "plano não encontrado")
    return executor.dry_run(plan_id)

@app.post("/api/operacoes/{plan_id}/executar")
def executar_plano(plan_id: int) -> dict:
    plano = operation_repo.plano(plan_id)
    if plano is None:
        raise HTTPException(404, "plano não encontrado")
    if plano.dry_run_em is None:
        raise HTTPException(409, "rode o dry-run antes de executar")
    if not jobs.iniciar_execucao(plan_id):
        raise HTTPException(409, "já existe um trabalho em andamento")
    return jobs.estado()
```
Mirror this exact route group shape for `POST /api/exif/plano`, `POST /api/exif/{plan_id}/dry-run`, `POST /api/exif/{plan_id}/executar`, `GET /api/exif/{plan_id}`, `GET /api/exif/{plan_id}/auditoria`. Key deltas: `criar_plano` needs no `PlanoBody`/`raiz_destino` (global scope, no destination text field per UI-SPEC.md); the `_plano_json` equivalent needs the Type A/B/C row breakdown UI-SPEC.md describes (field-level status, not just item-level).

**Dependency-injection wiring pattern** (lines 448-454, inside `create_app`):
```python
operation_repo = OperationRepository(session_factory)
planner = OperationPlanner(session_factory)
executor = OperationExecutor(session_factory)
jobs = JobManager(settings, session_factory)
```
Add `exif_write_repo = ExifWriteRepository(session_factory)`, `exif_planner = ExifWritePlanner(session_factory)`, `exif_executor = ExifWriteExecutor(session_factory)` alongside these, same `create_app` scope, same construction order (repo → planner → executor → jobs already wired).

---

### `fotoorganizer/server/jobs.py` (background execution)

**Analog:** same file, `iniciar_execucao`/`_rodar_execucao` (lines 123-133, 218+)

**Job-start method pattern** (lines 123-133):
```python
def iniciar_execucao(self, plan_id: int) -> bool:
    """Executa um plano aprovado. O controle nasce aqui, na thread do
    pedido, para que um cancelamento imediato não se perca."""
    if self.ocupado():
        return False
    controle = ExecutionControl()
    self._exec_control = controle
    return self._iniciar(
        "operacao", f"plano {plan_id}", self._rodar_execucao,
        plan_id, controle,
    )
```
Copy this shape for `iniciar_escrita_exif(self, plan_id: int) -> bool`, tipo string `"escrita_exif"` (new job type — frontend polling via `StatusBar.tsx`/`useJob` hook needs to recognize it, per RESEARCH.md's Architectural Responsibility Map: "reuse, don't reinvent").

**Background worker + progress-callback pattern** (lines 218-222, `_rodar_execucao`):
```python
def _rodar_execucao(self, plan_id: int, controle: ExecutionControl) -> None:
    executor = OperationExecutor(self._factory)
    def progresso(n: int, total: int, origem: str) -> None:
        self._atualizar(vistos=total, processados=n, ...)
```
Same shape for `_rodar_escrita_exif`, constructing the new exif executor and wiring its progress callback the same way.

---

### `scripts/testar_escrita_exif.py` (standalone script, batch)

**Analog:** `scripts/calibrar_raio_incerteza.py`

**Docstring contract pattern** (lines 1-41):
```python
#!/usr/bin/env python3
"""Calibra o raio de incerteza do lugar herdado contra o acervo real.

SOMENTE LEITURA: abre o catálogo em modo `ro`, não escreve nada, não toca em
nenhum arquivo original. ...
Uso:
    .venv/bin/python scripts/calibrar_raio_incerteza.py
    ...
Resultado documentado em docs/LOCAL_ESTIMADO.md.
"""
```
Adapt this exact framing but flip the safety claim per RESEARCH.md: **this script is explicitly NOT read-only** — state loudly in the docstring that it writes to disposable `shutil.copy2` copies in a scratch tmp dir, never to `catalog.db` or real files, and that "Resultado documentado em `docs/DECISOES.md`" (D-03's decision entry, same rigor as D-026/D-074).

**Path/import bootstrap + read-only catalog query pattern** (lines 43-58):
```python
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fotoorganizer.config import paths  # noqa: E402
```
Copy this bootstrap. For the catalog query, use `sqlite3.connect(f"file:{db}?mode=ro", uri=True)` (RESEARCH.md Pattern 3, step 1) grouped by extension, matching this script's `argparse`/`--db` convention.

---

### `tests/test_exif_write.py` (test, CRUD)

**Analog:** `tests/test_operations.py`

**Fixture pattern** (lines 1-70, `ambiente` fixture):
```python
@pytest.fixture()
def ambiente(migrated_engine, tmp_path):
    """3 fotos aprovadas..."""
    origem_dir = tmp_path / "origem"
    ...
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        fonte = Source(caminho=str(origem_dir))
        session.add(fonte)
        session.flush()
        ...
        session.commit()
```
Copy this `migrated_engine` + `tmp_path` + `create_session_factory` fixture shape for the new test file's `ambiente` fixture, building `MediaFile` rows with synthetic JPEGs from `tests/fixtures.py::make_jpeg` (some with `gps=None` for the "will write" case, some with `gps=(lat, lon)` for the "already filled, must skip" case — EXIF-02).

**Imports pattern** (lines 1-31) — mirror the grouped stdlib/sqlalchemy/`fotoorganizer.models`/`fotoorganizer.operations`/`fotoorganizer.repositories` import block shape for the new file's `fotoorganizer.models`/`fotoorganizer.exif_write`/`fotoorganizer.repositories` imports.

---

### `webapp/src/components/EscritaExif.tsx` (component, request-response)

**Analog:** `webapp/src/components/Operations.tsx` (full file, 331 lines — explicit precedent per CONTEXT.md D-01 and UI-SPEC.md)

**Imports pattern** (lines 1-8):
```tsx
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { api } from "../api";
import type { Plano, RelatorioDryRun } from "../api";
import type { Job } from "../hooks/useJob";
import Botao from "../ui/Botao";
```
Same import shape; swap `Plano`/`RelatorioDryRun` for new `PlanoExif`/`RelatorioDryRunExif` types added to `webapp/src/api.ts`.

**"Veredito" summary-line function pattern** (lines 42-54):
```tsx
function veredito(p: Plano): string {
  if (p.dry_run_em === null) return "sem dry-run — nada pode ser copiado ainda";
  const quando = new Date(p.dry_run_em).toLocaleString();
  if (p.prontos === null) return `dry-run em ${quando}`;
  if (p.prontos === 0)
    return `dry-run ${quando}: nenhum arquivo copiável (${p.problemas} problemas)`;
  if (p.problemas)
    return `dry-run ${quando}: ${p.prontos} prontos, ${p.problemas} com problema`;
  return `dry-run ${quando}: ${p.prontos} prontos, sem problemas`;
}
```
Copy shape verbatim (UI-SPEC.md explicitly calls out this function as the reuse target), adjust copy for "gravar" verb.

**Two-pane layout + sidebar plan-list + mutation wiring pattern** (lines 59-135, esp. 66-92, 115-176): copy the `useQuery`/`useMutation` wiring for `planos`/`plano`/`auditoria` queries and `criar`/`dryRun` mutations verbatim in structure; the sidebar `<aside className="w-72 ...">` block (lines 136-176) is a direct structural copy.

**What NOT to copy**: the `destino` text input (lines 60, 118-123, 84-92) — UI-SPEC.md is explicit that this phase writes in place, no destination field. The row rendering block (lines 280-308) needs a full rewrite per UI-SPEC.md's three row types (A/B/C) with checkboxes — no existing checkbox pattern in the codebase (confirmed by RESEARCH.md Pitfall 6, grep-verified zero matches for `type="checkbox"` across `webapp/src/components/*.tsx`). Build `<input type="checkbox">` fresh, Tailwind-styled per UI-SPEC.md's exact classes (`border-borda-forte` unchecked, `--color-acento` checked fill).

**`<details>` audit collapsible pattern** (lines 310-324) — reuse verbatim per UI-SPEC.md ("reused verbatim from `Operations.tsx`").

---

### `webapp/src/App.tsx` (tab registration)

**Analog:** same file (lines 24-30, 41-43, 64, 309)

```tsx
const ABAS = [
  ...
  "Operações",
  // add "Localização" after this, per UI-SPEC.md
];

const DICAS: Record<string, string> = {
  ...
  Operações: "plano → dry-run → cópia verificada; o original nunca é tocado",
  // add Localização: "revise o plano linha a linha; desmarque o que não quer gravar — o original só muda depois de aprovar"
};

const ABAS_COM_FONTE = ["Biblioteca", "Revisão", "Viagens"];
// Localização is NOT added here — global scope, per UI-SPEC.md explicit discretion call

{aba === "Operações" && <Operations job={job} />}
// add: {aba === "Localização" && <EscritaExif job={job} />}
```

### `webapp/src/api.ts` (API client, request-response)

**Analog:** same file, `Plano`/`ItemPlano`/`RelatorioDryRun`/`LinhaAuditoria` types (lines 306-350) + `planos`/`plano`/`criarPlano`/`dryRun`/`auditoria` client functions (lines 523-530) + `json`/`post` fetch helpers (lines 393-410)

**Fetch-helper pattern, error message preserved from server** (lines 393-410):
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
Reuse `json`/`post` verbatim (module-level helpers, not per-domain) — no new fetch wrapper needed. `post`'s `dados.detail` extraction matters here specifically: the FastAPI `HTTPException(409, "rode o dry-run antes de executar")` pattern used in the `/api/operacoes` routes (and to be mirrored in `/api/exif` routes) surfaces its message through this exact path.

**Type definitions to mirror** (lines 306-333, 335-341):
```typescript
export interface Plano {
  id: number;
  nome: string;
  status: string;
  dry_run_em: string | null;
  criado_em: string;
  total_itens: number;
  concluidos: number;
  com_conflito: number;
  com_erro: number;
  prontos: number | null;
  problemas: number | null;
  executavel: boolean;
}

export interface ItemPlano {
  id: number;
  origem: string;
  destino: string;
  status: string;
  conflito: string | null;
  erro: string | null;
}

export type PlanoDetalhe = Plano & { itens: ItemPlano[] };

export interface RelatorioDryRun {
  prontos: number;
  problemas: string[];
  bytes_necessarios: number;
  bytes_livres: number | null;
  espaco_suficiente: boolean;
}
```
Define `PlanoExif`/`ItemPlanoExif`/`PlanoExifDetalhe`/`RelatorioDryRunExif` mirroring this shape. Key deltas per UI-SPEC.md/RESEARCH.md: `ItemPlanoExif` needs per-field status (not a single `status: string` — see `models/exif_write.py` notes above) plus `formato_suportado`/`motivo_nao_suportado`/`sidecar_destino`/`pasta_sincronizada` fields to drive the Type A/B/C row rendering.

**Client function pattern** (lines 523-530):
```typescript
planos: () => json<Plano[]>("/api/operacoes"),
plano: (id: number) => json<PlanoDetalhe>(`/api/operacoes/${id}`),
criarPlano: (raiz_destino: string, nome?: string) =>
  post<Plano>("/api/operacoes", { raiz_destino, nome }),
dryRun: (id: number) =>
  post<RelatorioDryRun>(`/api/operacoes/${id}/dry-run`),
auditoria: (id: number) =>
  json<LinhaAuditoria[]>(`/api/operacoes/${id}/auditoria`),
```
Add to the same `api` object literal: `planosExif: () => json<PlanoExif[]>("/api/exif")`, `planoExif: (id) => json<PlanoExifDetalhe>(\`/api/exif/${id}\`)`, `criarPlanoExif: () => post<PlanoExif>("/api/exif/plano")` (no `raiz_destino`/`nome` params — global scope, no destination field per UI-SPEC.md), `dryRunExif: (id) => post<RelatorioDryRunExif>(\`/api/exif/${id}/dry-run\`)`, `auditoriaExif: (id) => json<LinhaAuditoria[]>(\`/api/exif/${id}/auditoria\`)` (reuse `LinhaAuditoria` type as-is — audit row shape is unchanged). `executarPlanoExif` goes through the `Job`/`useJob` hook path (`job.executarPlano`-equivalent), same as `Operations.tsx` calls `job.executarPlano(plano.id)` rather than a direct `api.*` call — no new `api.ts` entry needed for execution itself, only for job-kickoff if `useJob` requires a new method.

---

### `webapp/src/components/EscritaExif.test.tsx` (test, request-response)

**Analog:** `webapp/src/components/Operations.test.tsx` (full file, 203 lines)

**Test-double `Job` factory pattern** (lines 9-23):
```tsx
function jobParado(sobrescrever: Partial<Job> = {}): Job {
  return {
    estado: { status: "nenhum" },
    rodando: false,
    limpar: vi.fn(),
    escanear: vi.fn(),
    importarApple: vi.fn(),
    importarTakeout: vi.fn(),
    gerarSugestoes: vi.fn(),
    detectarDuplicatas: vi.fn(),
    executarPlano: vi.fn(async () => {}),
    cancelar: vi.fn(),
    ...sobrescrever,
  } as Job;
}
```
Copy verbatim — same `Job` type, same mock shape; `EscritaExif.tsx` takes the same `job: Job` prop as `Operations.tsx`.

**Fixture-builder + route-stub pattern** (lines 25-80):
```tsx
function plano(dry_run_em: string | null, veredito: object = {}) {
  return {
    id: 1, nome: "Cópia para /destino", status: "planejada", dry_run_em,
    criado_em: "2026-07-26T10:00:00", total_itens: 2, concluidos: 0,
    com_conflito: 0, com_erro: 0,
    prontos: dry_run_em ? 2 : null, problemas: dry_run_em ? 0 : null,
    executavel: dry_run_em !== null,
    ...veredito,
  };
}
...
function rotas(dry_run_em: string | null, veredito: object = {}) {
  return {
    "/api/operacoes": [plano(dry_run_em, veredito)],
    "/api/operacoes/1": { ...plano(dry_run_em, veredito), itens: ITENS },
    "/api/operacoes/1/auditoria": [ /* ... */ ],
  };
}
```
Mirror this shape for `/api/exif`, `/api/exif/1`, `/api/exif/1/auditoria` route stubs, with `planoExif()`/`itensExif` builders reflecting the new per-field status shape.

**`servirApi`/`montar` test-harness pattern** (lines 1-7, used throughout):
```tsx
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import Operations from "./Operations";
import type { Job } from "../hooks/useJob";
import { montar, servirApi } from "../test/servidor";
```
Reuse `montar`/`servirApi` from `../test/servidor` unchanged — same test harness the whole component test suite already shares (not `Operations`-specific).

**Assertion style — bind to exact user-facing copy** (lines 83-98, 116-144): tests assert on visible strings (`"sem dry-run — nada pode ser copiado ainda"`, disabled-button `title` attributes) rather than internal state. Mirror this for `EscritaExif.test.tsx`, using UI-SPEC.md's Copywriting Contract table as the source of truth for exact strings to assert on (e.g. `"Nada para gravar"`, `"falha — País: valor rejeitado pelo exiftool (ver auditoria)"`).

**Case not covered by the analog, needs new tests**: `Operations.test.tsx` has no checkbox-interaction test (no checkboxes exist in `Operations.tsx`) — the new file needs fresh tests for D-02's per-row deselect behavior and D-06's Type-B default-unchecked state, with no existing test to pattern-match against (same "no analog" gap as the checkbox UI itself, see No Analog Found below).

---

---

## Shared Patterns

### Dry-run-before-write guard (`DryRunObrigatorio`)
**Source:** `fotoorganizer/operations/executor.py` lines 54-55, 138-161
**Apply to:** `fotoorganizer/exif_write/executor.py`
```python
class DryRunObrigatorio(RuntimeError):
    pass
...
if plano.dry_run_em is None:
    raise DryRunObrigatorio("execute o dry-run antes de qualquer operação física")
```

### AuditLog reuse with `plan_id=NULL` workaround
**Source:** `fotoorganizer/models/operations.py` line 90 (`ForeignKey("operation_plans.id")`) + `fotoorganizer/database/engine.py` (`PRAGMA foreign_keys=ON`)
**Apply to:** every write path in `exif_write/planner.py` and `exif_write/executor.py` that logs to `AuditLog`
```python
# NEVER: AuditLog(plan_id=exif_plan.id, ...)  -- violates the FK to operation_plans
# ALWAYS:
session.add(AuditLog(
    plan_id=None, acao="...",
    detalhe={"exif_plan_id": exif_plan.id, "item_id": item.id, ...},
    resultado="...",
))
```
This is a **correction**, not a straightforward reuse — RESEARCH.md Pitfall 5 flags this explicitly as a gap in the milestone-level architecture doc.

### Safe subprocess invocation (invariant 5)
**Source:** `fotoorganizer/metadata/exiftool.py` lines 321-327 (list args, no `shell=True`), `fotoorganizer/security/volumes.py` lines 99-102 (same discipline)
**Apply to:** `fotoorganizer/exif_write/writer.py`, `scripts/testar_escrita_exif.py`
```python
subprocess.run([binario, *args], capture_output=True, text=True, check=False)
```
Never string-interpolate into a shell command; always list args.

### Hash reuse for audit trail (not pass/fail criterion)
**Source:** `fotoorganizer/security/hashing.py` (`sha256_full`)
**Apply to:** `fotoorganizer/exif_write/executor.py` — call `sha256_full(origem)` before/after as an audit fact (`hash_pre`/`hash_pos` columns), but the diff-of-tags (RESEARCH.md Pattern 2) — not hash equality — is what determines `status`. A location write is *expected* to change the file's hash; treating hash change as failure would reject every successful write.

### Job-manager background execution + progress polling
**Source:** `fotoorganizer/server/jobs.py` `iniciar_execucao`/`_rodar_execucao`/`_iniciar`/`_atualizar` (lines 123-234)
**Apply to:** new `iniciar_escrita_exif`/`_rodar_escrita_exif` methods on the same `JobManager` class
```python
def _iniciar(self, tipo: str, alvo: str, funcao, *args) -> bool:
    if self.ocupado():
        return False
    ...
    self._thread = threading.Thread(target=funcao, args=args, daemon=True, name=f"job-{tipo}")
    self._thread.start()
    return True
```

### Route group shape (list/detail/dry-run/execute)
**Source:** `fotoorganizer/server/app.py` lines 1191-1283
**Apply to:** new `/api/exif/*` routes in the same file
- `GET /api/exif` (list plans) mirrors `GET /api/operacoes`
- `POST /api/exif/plano` (create) mirrors `POST /api/operacoes` (minus `PlanoBody`/destination)
- `GET /api/exif/{plan_id}` mirrors `GET /api/operacoes/{plan_id}`
- `POST /api/exif/{plan_id}/dry-run` mirrors `POST /api/operacoes/{plan_id}/dry-run`
- `POST /api/exif/{plan_id}/executar` mirrors `POST /api/operacoes/{plan_id}/executar` (404/409 HTTPException pattern identical)

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| Checkbox-per-row UI (inside `EscritaExif.tsx`) | UI element | request-response | RESEARCH.md Pitfall 6, grep-verified: zero `type="checkbox"` / `checked=` occurrences anywhere in `webapp/src/components/*.tsx`. `Duplicates.tsx`'s "mark as primary" button and `Mapa.tsx`/`ArvoreDePastas.tsx`'s `selecionado` state are single-select, not batch-with-per-item-opt-out. Build fresh per UI-SPEC.md's exact spec (native `<input type="checkbox">`, Tailwind-styled, `Set<number>`/`Map<number, boolean>` local state). |
| Per-tag diff verification logic (inside `writer.py` or a new `diff.py`) | utility | transform | No existing tag-diff comparator in the codebase — closest adjacent code is `metadata/exiftool.py`'s `_converter`/`extract()` which *reads* tags but never diffs two tag dumps. Build fresh using RESEARCH.md Pattern 2's scaffolding-tag allowlist; reuse `extractor.extract()` for both "antes" and "depois" calls (this part is direct reuse, only the diff/compare logic itself is new). |

## Metadata

**Analog search scope:** `fotoorganizer/operations/`, `fotoorganizer/models/`, `fotoorganizer/security/`, `fotoorganizer/metadata/`, `fotoorganizer/server/`, `fotoorganizer/database/migrations/versions/`, `scripts/`, `tests/`, `webapp/src/components/`, `webapp/src/App.tsx`
**Files scanned (read directly):** `operations/executor.py`, `operations/planner.py`, `models/operations.py`, `security/paths.py`, `security/hashing.py`, `security/volumes.py`, `metadata/exiftool.py` (imports + `ExifToolExtractor` class), `server/app.py` (imports + operations route group + wiring), `server/jobs.py` (job-start + background-worker methods), `webapp/src/components/Operations.tsx` (full), `webapp/src/components/Operations.test.tsx` (full), `webapp/src/App.tsx` (tab registration), `webapp/src/api.ts` (fetch helpers + `Plano`/`ItemPlano`/`RelatorioDryRun` types + `api` object literal), `tests/test_operations.py` (imports + fixture), `tests/fixtures.py` (full), `scripts/calibrar_raio_incerteza.py` (docstring + bootstrap), `database/migrations/versions/0018_indices_de_fk_ausentes.py` (full), `repositories/operations.py` (full)
**Pattern extraction date:** 2026-08-18
