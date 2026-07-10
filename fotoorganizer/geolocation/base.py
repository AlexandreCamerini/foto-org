"""Contrato dos provedores de geocodificação (componente substituível).

O padrão do app é 100% offline. Um provider externo (opt-in) implementaria
o mesmo Protocol — a troca não afeta o resto da aplicação.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class GeoResult:
    pais: str | None
    regiao: str | None
    cidade: str | None
    fonte: str  # ex.: "offline:reverse_geocode"


class GeocodingProvider(Protocol):
    def resolve(self, lat: float, lon: float) -> GeoResult | None:
        """Resolve coordenadas para lugar. None se não souber — nunca inventa."""
        ...
