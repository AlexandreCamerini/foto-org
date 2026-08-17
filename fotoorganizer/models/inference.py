"""Evidências estruturadas e sugestões — rastreabilidade das decisões.

Cada inferência responde: qual campo, de onde veio, com que confiança e por
quê. A regra de agregação está em docs/CONFIANCA.md; aqui só se persiste.
"""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import Column, Enum, ForeignKey, Index, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fotoorganizer.models.base import Base, utcnow


class ConfidenceLevel(enum.StrEnum):
    ALTA = "alta"
    MEDIA = "media"
    BAIXA = "baixa"


class SuggestionStatus(enum.StrEnum):
    PENDENTE = "pendente"
    APROVADA = "aprovada"
    REJEITADA = "rejeitada"
    EDITADA = "editada"


suggestion_evidence = Table(
    "suggestion_evidence",
    Base.metadata,
    Column("suggestion_id", ForeignKey("suggestions.id"), primary_key=True),
    Column("evidence_id", ForeignKey("evidence.id"), primary_key=True),
)


class Evidence(Base):
    __tablename__ = "evidence"
    __table_args__ = (Index("ix_evidence_media_id", "media_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    media_id: Mapped[int] = mapped_column(ForeignKey("media_files.id"))
    # Campo alvo: data | pais | regiao | cidade | local | viagem | evento |
    # categoria | pessoa ...
    campo: Mapped[str]
    # Origem: exif | gps | pasta | nome_arquivo | vizinhanca | visao |
    # geocoding | usuario ...
    origem: Mapped[str]
    valor: Mapped[str] = mapped_column(Text)
    nivel: Mapped[ConfidenceLevel] = mapped_column(
        Enum(ConfidenceLevel, native_enum=False)
    )
    score: Mapped[float]
    justificativa: Mapped[str] = mapped_column(Text)
    versao_logica: Mapped[str]
    criado_em: Mapped[datetime] = mapped_column(default=utcnow)


class Suggestion(Base):
    __tablename__ = "suggestions"
    __table_args__ = (
        Index("ix_suggestions_status", "status"),
        # Consumidor: engine.py:1042,1083,1106; server/app.py:724;
        # repositories/media.py:118,149; repositories/suggestions.py:119,296;
        # operations/planner.py:60; operations/inventario.py:161 — busca
        # pesadamente consultada por media_id (Inspetor, filtro
        # "sem_sugestao", join do planejador). Migração 0018.
        Index("ix_suggestions_media_id", "media_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    media_id: Mapped[int] = mapped_column(ForeignKey("media_files.id"))
    destino_sugerido: Mapped[str] = mapped_column(Text)
    template: Mapped[str]
    nivel: Mapped[ConfidenceLevel] = mapped_column(
        Enum(ConfidenceLevel, native_enum=False)
    )
    status: Mapped[SuggestionStatus] = mapped_column(
        Enum(SuggestionStatus, native_enum=False), default=SuggestionStatus.PENDENTE
    )
    versao_logica: Mapped[str]
    criado_em: Mapped[datetime] = mapped_column(default=utcnow)
    revisado_em: Mapped[datetime | None]

    evidencias: Mapped[list[Evidence]] = relationship(secondary=suggestion_evidence)
