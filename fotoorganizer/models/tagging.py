from __future__ import annotations

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from fotoorganizer.models.base import Base


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(unique=True)
    # Ex.: "categoria", "cena", "rotulo_visual", "usuario".
    tipo: Mapped[str]


class MediaTag(Base):
    __tablename__ = "media_tags"
    __table_args__ = (UniqueConstraint("media_id", "tag_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    media_id: Mapped[int] = mapped_column(ForeignKey("media_files.id"))
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id"))
    origem: Mapped[str]
    score: Mapped[float | None]
