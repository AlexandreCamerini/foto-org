"""Modelo de confiança — implementação de docs/CONFIANCA.md.

Cada evidência carrega o score de referência da sua origem; a confiança de
uma sugestão é a do elo mais fraco entre os campos usados no destino.
Nada de somas arbitrárias.
"""

from __future__ import annotations

from fotoorganizer.models import ConfidenceLevel

# Tabela de referência (docs/CONFIANCA.md). Origem → score.
SCORES_REFERENCIA: dict[str, float] = {
    "exif": 0.95,          # data DateTimeOriginal coerente
    "gps": 0.95,           # coordenadas GPS EXIF válidas
    "geocoding_offline": 0.85,
    "geocoding_externo": 0.75,
    "pasta": 0.60,         # país/cidade extraído do nome da pasta
    "vizinhanca": 0.55,    # inferido de fotos próximas no tempo
    "agrupamento": 0.70,   # viagem por lacuna temporal
    "fs": 0.40,            # data do filesystem (sem EXIF)
    "visao": 0.30,         # apenas análise visual
    "usuario": 1.00,       # correção manual prevalece sobre tudo
}

_LIMIAR_ALTA = 0.8
_LIMIAR_MEDIA = 0.5


def nivel_para_score(score: float) -> ConfidenceLevel:
    if score >= _LIMIAR_ALTA:
        return ConfidenceLevel.ALTA
    if score >= _LIMIAR_MEDIA:
        return ConfidenceLevel.MEDIA
    return ConfidenceLevel.BAIXA


def elo_mais_fraco(scores: list[float]) -> tuple[ConfidenceLevel, float]:
    """Confiança agregada = menor score entre os campos usados."""
    if not scores:
        return ConfidenceLevel.BAIXA, 0.0
    menor = min(scores)
    return nivel_para_score(menor), menor
