"""Localizações resolvidas, viagens e eventos."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from fotoorganizer.models.base import Base


class Location(Base):
    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(primary_key=True)
    pais: Mapped[str | None]
    regiao: Mapped[str | None]
    cidade: Mapped[str | None]
    local: Mapped[str | None]
    lat: Mapped[float | None]
    lon: Mapped[float | None]
    # Qual serviço/dataset resolveu (ex.: "offline:reverse_geocoder", "pasta").
    fonte: Mapped[str]
    # Chave de cache (ex.: lat/lon arredondados) — evita re-resolver.
    cache_key: Mapped[str | None] = mapped_column(unique=True)


class Trip(Base):
    __tablename__ = "trips"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str]
    inicio: Mapped[datetime | None]
    fim: Mapped[datetime | None]
    location_id: Mapped[int | None] = mapped_column(ForeignKey("locations.id"))
    # Como o grupo foi formado (ex.: "gap_temporal>3d", "gps_cluster").
    metodo: Mapped[str] = mapped_column(Text, default="")


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str]
    tipo: Mapped[str | None]
    inicio: Mapped[datetime | None]
    fim: Mapped[datetime | None]
    metodo: Mapped[str] = mapped_column(Text, default="")
