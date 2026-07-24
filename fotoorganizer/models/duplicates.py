from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import Enum, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fotoorganizer.models.base import Base, utcnow


class DuplicateLevel(enum.StrEnum):
    EXATO = "exato"           # mesmo hash criptográfico
    CONTEUDO = "conteudo"     # mesmos pixels, metadados/compressão diferentes
    VISUAL = "visual"         # perceptualmente semelhantes (phash)
    # Frames da mesma câmera a segundos de distância: rajada/variações de
    # uma cena, não cópias — o usuário escolhe o melhor, não "remove dups".
    SEQUENCIA = "sequencia"


class DuplicateRole(enum.StrEnum):
    INDEFINIDO = "indefinido"
    PRINCIPAL = "principal"
    VERSAO = "versao"
    IGNORADO = "ignorado"


class DuplicateGroup(Base):
    __tablename__ = "duplicate_groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    nivel: Mapped[DuplicateLevel] = mapped_column(
        Enum(DuplicateLevel, native_enum=False)
    )
    criado_em: Mapped[datetime] = mapped_column(default=utcnow)

    membros: Mapped[list["DuplicateMember"]] = relationship(
        back_populates="grupo", cascade="all, delete-orphan"
    )


class DuplicateMember(Base):
    __tablename__ = "duplicate_members"
    __table_args__ = (UniqueConstraint("group_id", "media_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("duplicate_groups.id"))
    media_id: Mapped[int] = mapped_column(ForeignKey("media_files.id"))
    papel: Mapped[DuplicateRole] = mapped_column(
        Enum(DuplicateRole, native_enum=False), default=DuplicateRole.INDEFINIDO
    )

    grupo: Mapped[DuplicateGroup] = relationship(back_populates="membros")
