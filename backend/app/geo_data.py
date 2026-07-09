"""Lista compacta de países (PT/EN) usada pra reconhecer hierarquia
geográfica no nome das pastas. Não é exaustiva nem depende de API externa —
é um dicionário estático, suficiente pra pastas nomeadas por país como as
pessoas realmente organizam fotos de viagem."""

from __future__ import annotations

import unicodedata

_PAISES_RAW = [
    "Brasil", "Brazil",
    "Portugal",
    "Espanha", "Spain",
    "França", "France",
    "Itália", "Italy",
    "Alemanha", "Germany",
    "Reino Unido", "United Kingdom", "Inglaterra", "England", "Escócia", "Scotland",
    "Irlanda", "Ireland",
    "Holanda", "Países Baixos", "Netherlands",
    "Bélgica", "Belgium",
    "Suíça", "Switzerland",
    "Áustria", "Austria",
    "Grécia", "Greece",
    "Croácia", "Croatia",
    "Islândia", "Iceland",
    "Noruega", "Norway",
    "Suécia", "Sweden",
    "Dinamarca", "Denmark",
    "Finlândia", "Finland",
    "Polônia", "Poland",
    "República Tcheca", "Czech Republic",
    "Hungria", "Hungary",
    "Turquia", "Turkey",
    "Marrocos", "Morocco",
    "Egito", "Egypt",
    "África do Sul", "South Africa",
    "Estados Unidos", "United States", "USA", "EUA",
    "Canadá", "Canada",
    "México", "Mexico",
    "Argentina",
    "Chile",
    "Peru",
    "Colômbia", "Colombia",
    "Uruguai", "Uruguay",
    "Bolívia", "Bolivia",
    "Equador", "Ecuador",
    "Paraguai", "Paraguay",
    "Japão", "Japan",
    "China",
    "Coreia do Sul", "South Korea",
    "Tailândia", "Thailand",
    "Vietnã", "Vietnam",
    "Indonésia", "Indonesia",
    "Malásia", "Malaysia",
    "Singapura", "Singapore",
    "Filipinas", "Philippines",
    "Índia", "India",
    "Emirados Árabes Unidos", "United Arab Emirates", "Dubai",
    "Israel",
    "Austrália", "Australia",
    "Nova Zelândia", "New Zealand",
]


def _normalizar(texto: str) -> str:
    """Remove acento e baixa a caixa — "São Paulo" e "sao paulo" batem igual."""
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return sem_acento.strip().lower()


PAISES_NORMALIZADOS: dict[str, str] = {_normalizar(pais): pais for pais in _PAISES_RAW}


def identificar_pais(segmento_pasta: str) -> str | None:
    """Devolve o nome "canônico" do país (na forma original da lista) se o
    segmento de pasta bater com um país conhecido, senão `None`."""
    return PAISES_NORMALIZADOS.get(_normalizar(segmento_pasta))
