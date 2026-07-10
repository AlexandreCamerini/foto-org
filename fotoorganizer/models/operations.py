"""Planos de operação física e trilha de auditoria.

Único domínio autorizado a tocar o filesystem fora do catálogo (invariante
1–3): sempre plano → dry-run → aprovação → cópia verificada por hash.
"""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import JSON, Enum, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fotoorganizer.models.base import Base, utcnow


class OperationStatus(enum.StrEnum):
    PLANEJADA = "planejada"
    APROVADA = "aprovada"
    EXECUTANDO = "executando"
    CONCLUIDA = "concluida"
    CANCELADA = "cancelada"
    ERRO = "erro"


class OperationType(enum.StrEnum):
    # MVP só copia. Mover/excluir não existem por decisão de segurança.
    COPIAR = "copiar"


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

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("operation_plans.id"))
    media_id: Mapped[int] = mapped_column(ForeignKey("media_files.id"))
    operacao: Mapped[OperationType] = mapped_column(
        Enum(OperationType, native_enum=False), default=OperationType.COPIAR
    )
    origem: Mapped[str] = mapped_column(Text)
    destino: Mapped[str] = mapped_column(Text)
    conflito: Mapped[str | None] = mapped_column(Text)
    status: Mapped[OperationStatus] = mapped_column(
        Enum(OperationStatus, native_enum=False), default=OperationStatus.PLANEJADA
    )
    hash_pre: Mapped[str | None]
    hash_pos: Mapped[str | None]
    erro: Mapped[str | None] = mapped_column(Text)

    plano: Mapped[OperationPlan] = relationship(back_populates="itens")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    quando: Mapped[datetime] = mapped_column(default=utcnow)
    plan_id: Mapped[int | None] = mapped_column(ForeignKey("operation_plans.id"))
    acao: Mapped[str]
    detalhe: Mapped[dict | None] = mapped_column(JSON)
    resultado: Mapped[str]
