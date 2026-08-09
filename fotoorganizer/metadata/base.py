"""Contrato dos extratores de metadados (componente substituível).

Um extrator NUNCA levanta exceção por arquivo ruim: registra em `erro` e
devolve o que conseguiu ler — o scanner cataloga o arquivo mesmo assim.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Protocol


# Tolerância para relógio adiantado: a câmera do dono pode estar algumas
# horas à frente sem que a foto seja impossível.
_FOLGA_DE_RELOGIO = timedelta(days=1)


def data_plausivel(quando: datetime | None) -> bool:
    """Uma foto não pode ter sido tirada depois de agora.

    Só o limite superior. Não há piso: filme digitalizado com data manual
    pode ser legitimamente de 1950, e um piso arbitrário transformaria acervo
    antigo em erro. Num acervo real isto encontrou exatamente um registro,
    datado de 2100 — e ele bastava para dominar o topo da grade ordenada por
    data e fazer a tela parecer quebrada.

    A data original não se perde: o extrator continua gravando o que o
    arquivo disse na base bruta. O que não entra é a COLUNA, que alimenta
    agrupamento e correlação.
    """
    if quando is None:
        return False
    return quando <= datetime.now() + _FOLGA_DE_RELOGIO


@dataclass(slots=True)
class MediaMetadata:
    # Hora de parede da captura (naive) — o EXIF não tem fuso, e o pouco que
    # tem (`OffsetTimeOriginal`, o `Z` do QuickTime) é descartado hoje por
    # `exiftool.py:_data()` e `purepython.py`.
    data_capturada: datetime | None = None
    # O mesmo instante, absoluto. Nenhum extrator preenche isto ainda: ler o
    # fuso do arquivo exige `_data()` devolver o PAR em vez de só a hora
    # local, o que muda todos os campos de data dos dois extratores de uma
    # vez. Fica para a fase 11, que já vai mexer em fuso (D-038). Enquanto
    # for `None`, quem grava iguala os dois — a forma de dizer "fuso
    # desconhecido".
    data_capturada_utc: datetime | None = None
    make: str | None = None
    model: str | None = None
    lente: str | None = None
    orientacao: int | None = None
    largura: int | None = None
    altura: int | None = None
    gps_lat: float | None = None
    gps_lon: float | None = None
    # Pares brutos relevantes (namespace, chave, valor) para metadata_entries.
    extras: list[tuple[str, str, str]] = field(default_factory=list)
    erro: str | None = None


class MetadataExtractor(Protocol):
    def supported_extensions(self) -> set[str]:
        """Extensões (com ponto, minúsculas) que este extrator entende."""
        ...

    def extract(self, path: Path) -> MediaMetadata:
        """Lê metadados sem nunca levantar exceção por arquivo corrompido."""
        ...
