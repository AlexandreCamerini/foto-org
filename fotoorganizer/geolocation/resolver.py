"""Resolve coordenadas → Location com cache na tabela `locations`.

Coordenadas são arredondadas a 3 casas (~110 m) para formar a chave de
cache: fotos tiradas no mesmo lugar reusam a mesma linha e o dataset só é
consultado uma vez por lugar.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from fotoorganizer.geolocation.base import GeocodingProvider
from fotoorganizer.models import Location

_PRECISAO = 3


def cache_key(lat: float, lon: float) -> str:
    return f"{round(lat, _PRECISAO):.3f},{round(lon, _PRECISAO):.3f}"


class LocationResolver:
    def __init__(self, provider: GeocodingProvider) -> None:
        self._provider = provider

    def resolve(self, session: Session, lat: float, lon: float) -> Location | None:
        chave = cache_key(lat, lon)
        location = session.scalar(select(Location).where(Location.cache_key == chave))
        if location is not None:
            return location

        resultado = self._provider.resolve(lat, lon)
        if resultado is None:
            return None
        location = Location(
            pais=resultado.pais,
            regiao=resultado.regiao,
            cidade=resultado.cidade,
            lat=lat,
            lon=lon,
            fonte=resultado.fonte,
            cache_key=chave,
        )
        session.add(location)
        session.flush()
        return location
