"""Hierarquia geográfica a partir dos nomes das pastas (portado do v1).

Tabela estática de países (`paises.py`) — sem API externa. Serve para pastas
nomeadas como as pessoas realmente organizam fotos: .../França/Provence/
Avignon. Sem país reconhecido nos segmentos, NÃO inventa localização:
devolve hierarquia vazia (diferente do v1, que chutava a pasta mais funda
como cidade — removido por violar "não invente localização").
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from fotoorganizer.geolocation.paises import canonizar_pais, paises_no_segmento
# `_normalizar` continua exportado daqui: engine, classifier, albuns e
# tipo_imagem importam deste módulo; a definição mora no módulo folha.
from fotoorganizer.grouping.segmentos import normalizar as _normalizar  # noqa: F401
from fotoorganizer.grouping.segmentos import segmento_tecnico


def identificar_pais(segmento: str) -> str | None:
    """Nome canônico em português do país escrito no segmento, ou None.

    Devolve SEMPRE a grafia canônica: uma pasta "France" e outra "França"
    dão "França" nas duas, senão o destino ganharia duas pastas para o
    mesmo país — e o mesmo valeria contra o "France" do dataset offline.

    Tolera o que vem junto no segmento ("Chile e Atacama Abr.18" → Chile),
    mas um segmento que lista DOIS países não tem um país só: devolve None
    e deixa a lista para `identificar_paises`.
    """
    pais = canonizar_pais(segmento)
    if pais is not None:
        return pais
    paises = paises_no_segmento(segmento)
    return paises[0] if len(paises) == 1 else None


@dataclass(frozen=True, slots=True)
class HierarquiaPasta:
    pais: str | None
    regiao: str | None
    cidade: str | None
    segmento_pais: str | None  # segmento original que bateu (justificativa)


def extrair_hierarquia_da_pasta(pasta: str) -> HierarquiaPasta:
    """Primeiro segmento que é UM país decide; o que vem abaixo dele é
    região/cidade — pulando subpasta técnica ("[Developed]", "2019").
    Segmento que lista vários destinos ("Peru-Bolivia-Chile") não escolhe
    país: a varredura continua, porque a viagem multi-país costuma ter a
    pasta de cada país logo abaixo (".../Peru-Bolivia-Chile/Peru/Cusco").
    A sobra do próprio segmento ("Atacama" em "Chile e Atacama Abr.18") NÃO
    vira cidade aqui — só quando o dataset offline confirmar que é lugar
    (fatia 2 de D-082); antes disso seria inventar localização."""
    segmentos = [s for s in Path(pasta).parts if s not in ("/", "\\")]

    for i, segmento in enumerate(segmentos):
        pais = identificar_pais(segmento)
        if pais:
            resto = [s for s in segmentos[i + 1:] if not segmento_tecnico(s)]
            if not resto:
                return HierarquiaPasta(pais, None, None, segmento)
            if len(resto) == 1:
                return HierarquiaPasta(pais, None, resto[0], segmento)
            return HierarquiaPasta(pais, resto[-2], resto[-1], segmento)

    return HierarquiaPasta(None, None, None, None)
