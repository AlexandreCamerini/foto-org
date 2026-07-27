"""Hierarquia geográfica a partir dos nomes das pastas (portado do v1).

Lista estática de países PT/EN — sem API externa. Serve para pastas
nomeadas como as pessoas realmente organizam fotos: .../França/Provence/
Avignon. Sem país reconhecido nos segmentos, NÃO inventa localização:
devolve hierarquia vazia (diferente do v1, que chutava a pasta mais funda
como cidade — removido por violar "não invente localização").
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from pathlib import Path

from fotoorganizer.geolocation.paises import canonizar_pais

_PAISES_RAW = [
    "Brasil", "Brazil", "Portugal", "Espanha", "Spain", "França", "France",
    "Itália", "Italy", "Alemanha", "Germany", "Reino Unido", "United Kingdom",
    "Inglaterra", "England", "Escócia", "Scotland", "Irlanda", "Ireland",
    "Holanda", "Países Baixos", "Netherlands", "Bélgica", "Belgium",
    "Suíça", "Switzerland", "Áustria", "Austria", "Grécia", "Greece",
    "Croácia", "Croatia", "Islândia", "Iceland", "Noruega", "Norway",
    "Suécia", "Sweden", "Dinamarca", "Denmark", "Finlândia", "Finland",
    "Polônia", "Poland", "República Tcheca", "Czech Republic", "Hungria",
    "Hungary", "Turquia", "Turkey", "Marrocos", "Morocco", "Egito", "Egypt",
    "África do Sul", "South Africa", "Estados Unidos", "United States",
    "USA", "EUA", "Canadá", "Canada", "México", "Mexico", "Argentina",
    "Chile", "Peru", "Colômbia", "Colombia", "Uruguai", "Uruguay",
    "Bolívia", "Bolivia", "Equador", "Ecuador", "Paraguai", "Paraguay",
    "Japão", "Japan", "China", "Coreia do Sul", "South Korea", "Tailândia",
    "Thailand", "Vietnã", "Vietnam", "Indonésia", "Indonesia", "Malásia",
    "Malaysia", "Singapura", "Singapore", "Filipinas", "Philippines",
    "Índia", "India", "Emirados Árabes Unidos", "United Arab Emirates",
    "Dubai", "Israel", "Austrália", "Australia", "Nova Zelândia",
    "New Zealand",
]


def _normalizar(texto: str) -> str:
    sem_acento = (
        unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    )
    return sem_acento.strip().lower()


PAISES_NORMALIZADOS: dict[str, str] = {_normalizar(p): p for p in _PAISES_RAW}


def identificar_pais(segmento: str) -> str | None:
    """Nome canônico em português do país escrito no segmento, ou None.

    Devolve SEMPRE a grafia canônica: uma pasta "France" e outra "França"
    dão "França" nas duas, senão o destino ganharia duas pastas para o
    mesmo país — e o mesmo valeria contra o "France" do dataset offline.
    """
    return canonizar_pais(segmento)


@dataclass(frozen=True, slots=True)
class HierarquiaPasta:
    pais: str | None
    regiao: str | None
    cidade: str | None
    segmento_pais: str | None  # segmento original que bateu (justificativa)


def extrair_hierarquia_da_pasta(pasta: str) -> HierarquiaPasta:
    segmentos = [s for s in Path(pasta).parts if s not in ("/", "\\")]

    for i, segmento in enumerate(segmentos):
        pais = identificar_pais(segmento)
        if pais:
            resto = segmentos[i + 1:]
            if not resto:
                return HierarquiaPasta(pais, None, None, segmento)
            if len(resto) == 1:
                return HierarquiaPasta(pais, None, resto[0], segmento)
            return HierarquiaPasta(pais, resto[-2], resto[-1], segmento)

    return HierarquiaPasta(None, None, None, None)
