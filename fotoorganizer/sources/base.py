"""Contrato dos catálogos externos (Apple Fotos, Google Takeout, ...).

Um provider lê o catálogo de OUTRO app (somente leitura, invariante 1) e
devolve ativos apontando para arquivos reais no disco, junto com os
metadados que aquele catálogo tem e o arquivo às vezes não (GPS de
export sem EXIF, título/álbum, favorito). O importador funde isso ao
catálogo próprio — arquivo primeiro, catálogo externo preenchendo as
lacunas — e registra a origem de cada informação.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterator, Protocol

from fotoorganizer.models import SourceType


@dataclass(slots=True)
class ExternalAsset:
    """Um item do catálogo externo. `caminho` aponta para o arquivo real."""

    caminho: Path
    data_capturada: datetime | None = None
    gps_lat: float | None = None
    gps_lon: float | None = None
    titulo: str | None = None
    descricao: str | None = None
    favorito: bool = False
    albuns: tuple[str, ...] = field(default=())


class ExternalCatalogProvider(Protocol):
    """Componente substituível (como MetadataExtractor e afins)."""

    @property
    def tipo(self) -> SourceType: ...

    @property
    def raiz(self) -> Path:
        """Identidade da fonte no catálogo (caminho da biblioteca/pasta)."""
        ...

    @property
    def apelido(self) -> str: ...

    def iter_assets(self) -> Iterator[ExternalAsset]: ...
