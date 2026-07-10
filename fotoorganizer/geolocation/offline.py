"""Geocodificação reversa offline (dataset local, nenhum dado sai da máquina).

O reverse_geocode carrega ~cidades do GeoNames e monta uma árvore na
primeira consulta (~alguns segundos) — por isso o import é lazy e o
resolver deve rodar fora da thread da UI.
"""

from __future__ import annotations

import logging

from fotoorganizer.geolocation.base import GeoResult

log = logging.getLogger(__name__)

FONTE = "offline:reverse_geocode"


class OfflineGeocoder:
    def __init__(self) -> None:
        self._modulo = None

    def _carregar(self):
        if self._modulo is None:
            log.info("geocoding offline: carregando dataset local…")
            import reverse_geocode

            self._modulo = reverse_geocode
        return self._modulo

    def resolve(self, lat: float, lon: float) -> GeoResult | None:
        try:
            rg = self._carregar()
            resultado = rg.search([(lat, lon)])[0]
        except Exception as exc:
            log.warning("geocoding offline falhou para %s,%s: %s", lat, lon, exc)
            return None
        return GeoResult(
            pais=resultado.get("country") or None,
            regiao=resultado.get("state") or None,
            cidade=resultado.get("city") or None,
            fonte=FONTE,
        )
