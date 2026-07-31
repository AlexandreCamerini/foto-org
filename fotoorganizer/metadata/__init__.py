"""Extratores de metadados — componente substituível (Protocol)."""

from __future__ import annotations

import logging

from fotoorganizer.metadata.base import MediaMetadata, MetadataExtractor
from fotoorganizer.metadata.exiftool import ExifToolExtractor
from fotoorganizer.metadata.purepython import PurePythonExtractor

log = logging.getLogger(__name__)

__all__ = [
    "MediaMetadata", "MetadataExtractor",
    "ExifToolExtractor", "PurePythonExtractor",
    "criar_extrator",
]


def criar_extrator(preferir_exiftool: bool = True) -> MetadataExtractor:
    """O melhor extrator disponível nesta máquina.

    Com exiftool instalado, ele manda: num CR3 de acervo real são 361 tags
    contra 8 do libraw, e é ele quem entrega `Make`/`Model` — sem os quais
    não há correção de deriva de relógio nem "outra origem" na herança de
    GPS. Sem exiftool o app funciona igual, com menos sinal.

    A escolha mora aqui, e não em cada chamador, para não existirem quatro
    versões da mesma decisão divergindo com o tempo.
    """
    if preferir_exiftool and ExifToolExtractor.disponivel():
        log.info("metadados: exiftool disponível — usando extrator completo")
        return ExifToolExtractor()
    log.info("metadados: exiftool ausente — usando extrator puro-Python")
    return PurePythonExtractor()
