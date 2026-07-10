"""Detecção da "casa" do acervo: a célula GPS modal.

Uma viagem se caracteriza por deslocamento — e deslocamento exige saber de
onde. A casa é a célula (~11 km) com mais fotos, exigindo massa mínima de
evidência para não eleger casa em acervos pequenos ou de uma viagem só.
"""

from __future__ import annotations

import math
from collections import Counter

_MIN_FOTOS_GPS = 20
_FRACAO_MINIMA = 0.30
_PRECISAO_CELULA = 1  # casas decimais ≈ 11 km

RAIO_TERRA_KM = 6371.0


def distancia_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * RAIO_TERRA_KM * math.asin(math.sqrt(a))


def detectar_casa(coords: list[tuple[float, float]]) -> tuple[float, float] | None:
    """Célula modal do acervo, ou None quando a evidência é fraca."""
    if len(coords) < _MIN_FOTOS_GPS:
        return None
    celulas = Counter(
        (round(lat, _PRECISAO_CELULA), round(lon, _PRECISAO_CELULA))
        for lat, lon in coords
    )
    (celula, contagem), = celulas.most_common(1)
    if contagem / len(coords) < _FRACAO_MINIMA:
        return None
    return celula
