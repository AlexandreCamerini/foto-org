"""Pessoas conhecidas e ocorrências de rosto.

Recurso desativado por padrão (invariante 6). Embeddings são armazenados
criptografados; um perfil pode ser apagado por completo (cascade).
"""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import JSON, Enum, ForeignKey, LargeBinary
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fotoorganizer.models.base import Base, utcnow


class FaceState(enum.StrEnum):
    DETECTADO = "detectado"
    POSSIVEL = "possivel"
    CONFIRMADO = "confirmado"
    INCORRETO = "incorreto"


class Person(Base):
    __tablename__ = "people"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str]
    # Ex.: "familiar" — habilita a sugestão de categoria "família".
    relacao: Mapped[str | None]
    criado_em: Mapped[datetime] = mapped_column(default=utcnow)

    embeddings: Mapped[list["FaceEmbedding"]] = relationship(
        back_populates="person", cascade="all, delete-orphan"
    )


class FaceEmbedding(Base):
    __tablename__ = "face_embeddings"

    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("people.id"))
    # Vetor criptografado (chave no Keychain) — nunca em claro no banco.
    blob_criptografado: Mapped[bytes] = mapped_column(LargeBinary)
    modelo: Mapped[str]
    criado_em: Mapped[datetime] = mapped_column(default=utcnow)

    person: Mapped[Person] = relationship(back_populates="embeddings")


class FaceOccurrence(Base):
    __tablename__ = "face_occurrences"

    id: Mapped[int] = mapped_column(primary_key=True)
    media_id: Mapped[int] = mapped_column(ForeignKey("media_files.id"))
    # Nulo enquanto for apenas "rosto detectado".
    person_id: Mapped[int | None] = mapped_column(ForeignKey("people.id"))
    bbox: Mapped[dict | None] = mapped_column(JSON)
    estado: Mapped[FaceState] = mapped_column(
        Enum(FaceState, native_enum=False), default=FaceState.DETECTADO
    )
    similaridade: Mapped[float | None]
