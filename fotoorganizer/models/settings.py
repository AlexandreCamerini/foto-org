from __future__ import annotations

from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column

from fotoorganizer.models.base import Base


class ApplicationSetting(Base):
    """Preferências persistidas pela UI (diferente do config.toml, que é
    editado pelo usuário)."""

    __tablename__ = "application_settings"

    chave: Mapped[str] = mapped_column(primary_key=True)
    valor: Mapped[dict | list | str | int | float | bool | None] = mapped_column(JSON)
