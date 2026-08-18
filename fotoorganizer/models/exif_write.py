"""Planos de escrita EXIF de localização em campo vazio (D-075, Fase 6).

Estruturalmente paralelo a `models/operations.py` (`OperationPlan`/
`OperationItem`) mas **sem herdar deles** nem se relacionar com eles — a
tabela `exif_write_plans`/`exif_write_items` é um domínio de escrita
independente do de cópia física.

`AuditLog` (`models/operations.py`) é reusado como está para a trilha de
auditoria da escrita EXIF, mas sempre com `plan_id=None`: aquela coluna tem
FK real e ativa para `operation_plans.id`, e gravar ali o id de um
`ExifWritePlan` (sequência de PK independente) derruba o insert com
`PRAGMA foreign_keys=ON` (RESEARCH.md Pitfall 5, verificado empiricamente).
O id do plano EXIF viaja em `AuditLog.detalhe` (JSON), como
`{"exif_plan_id": ...}`.
"""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import Enum, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fotoorganizer.models.base import Base, utcnow


class ExifWriteStatus(enum.StrEnum):
    PLANEJADA = "planejada"
    EXECUTANDO = "executando"
    CONCLUIDA = "concluida"
    CANCELADA = "cancelada"
    ERRO = "erro"


class CampoStatus(enum.StrEnum):
    """Status de um campo individual (GPS, cidade ou país) dentro de um
    `ExifWriteItem`. `PULADO` e `SEM_VALOR` são estados distintos porque
    significam coisas diferentes para o dono: `PULADO` é "o arquivo já
    tinha o campo preenchido, não sobrescrevemos" (EXIF-02); `SEM_VALOR` é
    "o motor não inferiu nada para este campo" — a UI mostra uma cópia
    diferente para cada um."""

    PENDENTE = "pendente"
    PRONTO = "pronto"
    PULADO = "pulado"
    SEM_VALOR = "sem_valor"
    GRAVADO = "gravado"
    FALHA = "falha"


class ExifWritePlan(Base):
    __tablename__ = "exif_write_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str]
    status: Mapped[ExifWriteStatus] = mapped_column(
        Enum(ExifWriteStatus, native_enum=False), default=ExifWriteStatus.PLANEJADA
    )
    dry_run_em: Mapped[datetime | None]
    criado_em: Mapped[datetime] = mapped_column(default=utcnow)

    itens: Mapped[list["ExifWriteItem"]] = relationship(
        back_populates="plano", cascade="all, delete-orphan"
    )


class ExifWriteItem(Base):
    __tablename__ = "exif_write_items"
    __table_args__ = (
        # Consumidor: repositories/exif_write.py (lista os itens de um
        # plano de escrita EXIF). Migração 0019.
        Index("ix_exif_write_items_plan_id", "plan_id"),
        # Consumidor: exif_write/planner.py (checa escritas pendentes por
        # mídia). Migração 0019.
        Index("ix_exif_write_items_media_id", "media_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("exif_write_plans.id"))
    media_id: Mapped[int] = mapped_column(ForeignKey("media_files.id"))
    origem: Mapped[str] = mapped_column(Text)

    valor_gps_lat: Mapped[float | None]
    valor_gps_lon: Mapped[float | None]
    valor_cidade: Mapped[str | None]
    valor_pais: Mapped[str | None]

    # exiftool não é atômico por tag dentro de uma invocação (RESEARCH.md
    # Pitfall 2): "gravou cidade e país e falhou o GPS" é um resultado real
    # e frequente que um único enum `status` não sabe expressar. Três
    # colunas de status independentes, uma por campo, são a exigência de
    # EXIF-03 ("incluindo falha parcial").
    status_gps: Mapped[CampoStatus] = mapped_column(
        Enum(CampoStatus, native_enum=False), default=CampoStatus.PENDENTE
    )
    status_cidade: Mapped[CampoStatus] = mapped_column(
        Enum(CampoStatus, native_enum=False), default=CampoStatus.PENDENTE
    )
    status_pais: Mapped[CampoStatus] = mapped_column(
        Enum(CampoStatus, native_enum=False), default=CampoStatus.PENDENTE
    )
    motivo_gps: Mapped[str | None] = mapped_column(Text)
    motivo_cidade: Mapped[str | None] = mapped_column(Text)
    motivo_pais: Mapped[str | None] = mapped_column(Text)

    formato_suportado: Mapped[bool] = mapped_column(default=True)
    motivo_nao_suportado: Mapped[str | None] = mapped_column(Text)
    sidecar_destino: Mapped[str | None] = mapped_column(Text)
    pasta_sincronizada: Mapped[str | None]

    # Materializa D-02 (o dono desmarca item pontual antes de confirmar). O
    # planner nasce com `False` para linha de sidecar (D-06 é opt-in) e
    # `True` para o resto.
    incluido: Mapped[bool] = mapped_column(default=True)

    # Fato de auditoria, nunca critério de aprovação: a escrita é mutação
    # intencional, o hash do arquivo muda sempre por construção. Quem
    # aprova é o diff de tags, não o hash.
    hash_pre: Mapped[str | None]
    hash_pos: Mapped[str | None]

    backup_original: Mapped[str | None] = mapped_column(Text)
    erro: Mapped[str | None] = mapped_column(Text)

    plano: Mapped[ExifWritePlan] = relationship(back_populates="itens")
