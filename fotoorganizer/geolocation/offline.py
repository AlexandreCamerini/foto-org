"""Geocodificação reversa offline (dataset local, nenhum dado sai da máquina).

O reverse_geocode carrega ~cidades do GeoNames e monta uma árvore na
primeira consulta (~alguns segundos) — por isso o import é lazy e o
resolver deve rodar fora da thread da UI.
"""

from __future__ import annotations

import logging

from fotoorganizer.geolocation.base import GeoResult
from fotoorganizer.geolocation.paises import limpar_regiao, pais_por_codigo

log = logging.getLogger(__name__)

# /2: país canonizado pelo código ISO e região sem rótulo administrativo
# em inglês. Bump obrigatório a cada mudança de nomenclatura — é o que
# reescreve os lugares já em cache (ver GeocodingProvider.fonte).
FONTE = "offline:reverse_geocode/2"


class OfflineGeocoder:
    def __init__(self) -> None:
        self._modulo = None

    @property
    def fonte(self) -> str:
        return FONTE

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
        # O dataset é GeoNames em inglês. O código ISO é a chave estável
        # para o nome em português; se vier um código desconhecido, o nome
        # original entra como está — melhor em inglês do que ausente.
        pais = pais_por_codigo(resultado.get("country_code"))
        return GeoResult(
            pais=pais or resultado.get("country") or None,
            # Cidade fica no idioma local: "Hoi An" e "Chiang Mai" são os
            # nomes certos dos lugares, não erros de tradução.
            regiao=limpar_regiao(resultado.get("state")),
            cidade=resultado.get("city") or None,
            fonte=FONTE,
        )
