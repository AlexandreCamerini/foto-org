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


# Namespace unificado da curadoria humana: palavra-chave, nota e rótulo que
# alguém escreveu sobre a foto, venha de onde vier.
#
# Existe porque a mesma afirmação chega por vários caminhos. "Selected" está
# no `.lrcat` importado como fonte E no `.xmp` que o mesmo fluxo gravou ao
# lado do arquivo; "Pantanal" pode estar no álbum do Apple Fotos e na
# palavra-chave do IPTC. Gravar cada chegada no namespace da sua origem
# preserva o "de onde veio" e faz a classificação contar a mesma coisa
# duas vezes — confiança somada indevidamente, o defeito que
# `docs/CONFIANCA.md` existe para impedir.
#
# A regra: o namespace de origem continua registrando o que aquela origem
# disse; ESTE registra o conjunto, com cada termo uma vez só. Quem decide lê
# daqui; quem pergunta "por quê?" lê de lá.
NAMESPACE_CURADORIA = "curadoria"


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
    # Palavras-chave que alguém escreveu sobre esta foto, de qualquer um dos
    # quatro formatos que os editores usam, já unificadas e sem repetição.
    #
    # Existe para que a classificação não precise conhecer os quatro. O mesmo
    # "Pantanal" pode chegar como `XMP:TagsList` (digiKam), como
    # `XMP:HierarchicalSubject` (Lightroom), como `XMP:Subject` ou como
    # `IPTC:Keywords` — e chega pelos quatro ao mesmo tempo quando o arquivo
    # passou por mais de um programa. Contar isso como quatro sinais somaria
    # confiança sobre uma afirmação só, que é o que docs/CONFIANCA.md proíbe.
    palavras_chave: tuple[str, ...] = field(default=())
    erro: str | None = None


class MetadataExtractor(Protocol):
    def supported_extensions(self) -> set[str]:
        """Extensões (com ponto, minúsculas) que este extrator entende."""
        ...

    def extract(self, path: Path) -> MediaMetadata:
        """Lê metadados sem nunca levantar exceção por arquivo corrompido."""
        ...
