"""Contrato dos extratores de metadados (componente substituível).

Um extrator NUNCA levanta exceção por arquivo ruim: registra em `erro` e
devolve o que conseguiu ler — o scanner cataloga o arquivo mesmo assim.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Protocol


@dataclass(slots=True)
class MediaMetadata:
    data_capturada: datetime | None = None
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
