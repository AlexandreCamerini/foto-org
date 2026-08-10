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


def _pontuacao(
    media: MediaFile, metadados: dict[int, int] | None = None
) -> tuple[int, int, int, int, int]:
    fonte_externa = 0 if media.source.tipo == SourceType.PASTA else 1
    # Quantidade de metadado conhecido, como penúltimo desempate. A ideia vem
    # do Immich, que pré-seleciona a duplicata a manter por tamanho em bytes e
    # por contagem de campos EXIF; o tamanho não serve aqui — num grupo EXATO
    # os bytes são idênticos por definição — mas a contagem serve, e serve
    # mais: neste acervo o metadado É o ativo, e a mesma foto vista por duas
    # fontes pode ter chegado mais rica de um lado.
    #
    # Entra ANTES do `id` e depois de todo o resto de propósito: não muda
    # nenhuma decisão que os critérios anteriores já resolviam bem, só troca
    # um desempate arbitrário (o menor id, que é ordem de indexação) por um
    # com significado.
    riqueza = -(metadados or {}).get(media.id, 0)
    return (
        fonte_externa,
        -_profundidade(media.pasta),
        1 if _generico(media.nome) else 0,
        riqueza,
        media.id,
    )


def escolher_principal_automatico(
    membros: list[MediaFile], metadados: dict[int, int] | None = None
) -> MediaFile:
    """O membro preferido do grupo — vira PRINCIPAL; os demais, VERSAO.

    `metadados` mapeia `media_id` → quantidade de entradas de metadado. É
    opcional: sem ele a regra é exatamente a de antes, e quem chama sem contar
    nada continua funcionando.
    """
    return min(membros, key=lambda m: _pontuacao(m, metadados))
