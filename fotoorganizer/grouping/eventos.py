"""Reconhecimento de eventos e nomes de álbum nos nomes das pastas.

"Serena 15 Anos" é um aniversário; "Quizomba" é um álbum nomeado;
"2025_05_24" e "[Originals]" são pastas técnicas que não nomeiam nada.
"""

from __future__ import annotations

import re

from fotoorganizer.geolocation.folder_names import _normalizar, identificar_pais

# Palavras que indicam evento (comparadas sem acento/caixa).
_KEYWORDS_EVENTO = {
    "aniversario", "casamento", "formatura", "batizado", "cha de bebe",
    "festa", "natal", "reveillon", "ano novo", "pascoa", "churrasco",
    "show", "festival", "despedida", "confraternizacao", "bodas",
}
# "15 anos", "1 ano" — aniversários por idade.
_RE_ANOS = re.compile(r"\b\d{1,3}\s*anos?\b")

# Pastas técnicas: datas, contadores de câmera, subpastas de workflow.
_RE_TECNICO = re.compile(
    r"^\[?("
    r"\d{4}([-_ .]\d{1,2}){0,2}"        # 2025, 2025_05, 2025-05-24
    r"|\d{1,2}([-_ .]\d{1,2})?"          # 05, 05_24
    r"|img[-_ ]?\d*|dsc[-_ ]?\d*|dcim"
    r"|originals?|exports?|edits?|edicoes|raw|jpe?g|selecao|selects?"
    r"|fotos?|photos?|imagens|camera|backup|nova pasta|sem titulo|untitled"
    r"|pictures|users|home|volumes|desktop|documents|downloads|library"
    r")\]?$"
)

# Nomes de álbum só fazem sentido perto da folha — subir demais na árvore
# pegaria nomes de usuário e afins.
_PROFUNDIDADE_ALBUM = 3

_CATEGORIAS = {"viagens", "viagem", "familia", "eventos", "album", "albuns"}


def keyword_de_evento(segmento: str) -> bool:
    norm = _normalizar(segmento)
    return bool(_RE_ANOS.search(norm)) or any(
        kw in norm for kw in _KEYWORDS_EVENTO
    )


def pasta_tecnica(segmento: str) -> bool:
    return bool(_RE_TECNICO.match(_normalizar(segmento)))


def nome_de_album(segmento: str) -> bool:
    """Segmento que nomeia conteúdo: não técnico, não país, não categoria."""
    norm = _normalizar(segmento)
    if not norm or pasta_tecnica(segmento):
        return False
    if identificar_pais(segmento) is not None:
        return False
    return norm not in _CATEGORIAS


def extrair_evento(pastas: list[str]) -> tuple[str | None, bool]:
    """Devolve (nome do evento, veio_de_keyword) a partir dos caminhos das
    pastas de uma sessão. Prefere o segmento mais fundo com keyword; senão
    o nome de álbum mais fundo. (None, False) quando só há pastas técnicas."""
    candidato_album: str | None = None
    for pasta in pastas:
        segmentos = [s for s in pasta.split("/") if s]
        for i, segmento in enumerate(segmentos):
            # Filho direto de Users/home é nome de usuário, não álbum.
            if i > 0 and _normalizar(segmentos[i - 1]) in ("users", "home"):
                continue
            nivel = len(segmentos) - 1 - i  # 0 = folha
            if keyword_de_evento(segmento) and nome_de_album(segmento):
                return segmento.strip(), True
            if (candidato_album is None and nivel < _PROFUNDIDADE_ALBUM
                    and nome_de_album(segmento)):
                candidato_album = segmento.strip()
    return candidato_album, False
