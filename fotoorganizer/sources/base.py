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
    """Um item do catálogo externo.

    `caminho` aponta para o arquivo real quando ele deve ser LIDO. Quando é
    `None`, o item é uma REFERÊNCIA e nenhum byte de imagem é aberto — só o
    que o catálogo externo e a entrada de diretório dizem sobre ele.

    Dois casos caem aí, por motivos diferentes: o original que está só na
    nuvem (Apple), e o arquivo que existe em disco mas não deve entrar como
    acervo (uma exportação do Takeout que o dono vai apagar depois). Em
    ambos o valor está em doar data, GPS e contexto para a correlação — GPS
    de celular é o que localiza a foto de câmera — e `referencia` dá ao item
    uma identidade estável no lugar do caminho.

    `nome` e `tamanho` são informação do arquivo, não conteúdo dele: vêm da
    entrada de diretório e são material de correlação por si (nome igual e
    tamanho igual casam duas cópias sem abrir nenhuma das duas).
    """

    caminho: Path | None
    referencia: str | None = None
    # Onde o catálogo externo acredita que o arquivo está. Numa referência,
    # é a única pista de LUGAR que sobra — e é justamente o que responde
    # "onde estão minhas fotos?" com o disco desligado. Não é aberto.
    caminho_original: Path | None = None
    nome: str | None = None
    tamanho: int | None = None
    # Hora de parede da captura (naive), como o resto do catálogo.
    data_capturada: datetime | None = None
    # O mesmo instante, absoluto, quando o catálogo externo souber o fuso —
    # `None` quando não souber, e aí o importador iguala os dois (a forma de
    # dizer "fuso desconhecido"). Só um catálogo externo pode preencher isto
    # hoje: o arquivo em si não carrega fuso que o app leia (D-038).
    data_capturada_utc: datetime | None = None
    gps_lat: float | None = None
    gps_lon: float | None = None
    titulo: str | None = None
    descricao: str | None = None
    favorito: bool = False
    albuns: tuple[str, ...] = field(default=())
    # Pessoas nomeadas pelo catálogo externo (o app não roda reconhecimento
    # facial por padrão — invariante 6 — mas aproveita o que o usuário já
    # nomeou em outro lugar, como qualquer outro metadado importado).
    pessoas: tuple[str, ...] = field(default=())
    # Etiquetas que o dono escreveu noutro app. Como álbum e pessoa, é
    # intenção declarada — não inferência nossa.
    palavras_chave: tuple[str, ...] = field(default=())


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
