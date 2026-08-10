"""Regra determinística para grupos EXATO (mesmo SHA-256).

Bytes idênticos não deixam ambiguidade sobre o CONTEÚDO — a única pergunta
que sobra é qual caminho merece ser a referência de trabalho. Critério, em
ordem de desempate: fonte própria (pasta escaneada) antes de catálogo
externo; caminho mais organizado (mais segmentos) antes de raiz solta; nome
descritivo antes de padrão de câmera (`IMG_1234`) ou puramente numérico;
`id` menor como último desempate, para o resultado ser estável entre
execuções repetidas do detector.
"""

from __future__ import annotations

import re

from fotoorganizer.models import MediaFile, SourceType

_NOME_GENERICO = re.compile(
    r"^(img|dsc|dscn|dcim|pxl|mvimg|vid|mov|p|photo|foto)[_-]?\d+$",
    re.IGNORECASE,
)


def _generico(nome: str) -> bool:
    base = nome.rsplit(".", 1)[0]
    return bool(_NOME_GENERICO.match(base)) or base.isdigit()


def _profundidade(pasta: str) -> int:
    return len([parte for parte in pasta.split("/") if parte])


def _pontuacao(media: MediaFile) -> tuple[int, int, int, int]:
    fonte_externa = 0 if media.source.tipo == SourceType.PASTA else 1
    return (
        fonte_externa,
        -_profundidade(media.pasta),
        1 if _generico(media.nome) else 0,
        media.id,
    )


def escolher_principal_automatico(membros: list[MediaFile]) -> MediaFile:
    """O membro preferido do grupo — vira PRINCIPAL; os demais, VERSAO."""
    return min(membros, key=_pontuacao)
