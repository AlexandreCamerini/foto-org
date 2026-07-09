"""Modelo da tabela `photos`."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Photo(Base):
    __tablename__ = "photos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    caminho_original: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    nome_arquivo: Mapped[str] = mapped_column(String, nullable=False)
    tamanho_bytes: Mapped[int] = mapped_column(Integer, nullable=False)

    # Duplicata exata (bytes idênticos) e duplicata visual (imagens parecidas,
    # ex. mesma foto reexportada/comprimida) são coisas diferentes — por isso
    # dois hashes. `hash_md5` é exigido pelo schema original; `hash_perceptual`
    # foi adicionado pra viabilizar a "similaridade visual" das inovações
    # (sem ele não dá pra comparar imagens que não são bit-a-bit iguais).
    hash_md5: Mapped[str] = mapped_column(String, nullable=False, index=True)
    hash_perceptual: Mapped[str | None] = mapped_column(String, nullable=True, index=True)

    data_exif: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    localizacao_exif: Mapped[str | None] = mapped_column(String, nullable=True)
    data_arquivo: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    pasta_fonte: Mapped[str] = mapped_column(String, nullable=False)

    sugestao_agrupamento: Mapped[str | None] = mapped_column(String, nullable=True)
    score_confianca: Mapped[float | None] = mapped_column(Float, nullable=True)
