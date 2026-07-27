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
    @property
    def fonte(self) -> str:
        """Identidade E VERSÃO do provedor ("offline:reverse_geocode/2").

        Lugar resolvido fica em cache no catálogo. Sem uma versão aqui,
        mudar a nomenclatura (país em português, região sem o rótulo
        administrativo) só valeria para coordenadas novas — as fotos já
        resolvidas guardariam para sempre o nome antigo. Trocar esta
        string faz o resolver reescrever as linhas em cache.
        """
        ...

    def resolve(self, lat: float, lon: float) -> GeoResult | None:
        """Resolve coordenadas para lugar. None se não souber — nunca inventa."""
        ...
