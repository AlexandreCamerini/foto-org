"""Reconhecimento de eventos e nomes de álbum nos nomes das pastas.

"Serena 15 Anos" é um aniversário; "Quizomba" é um álbum nomeado;
"2025_05_24" e "[Originals]" são pastas técnicas que não nomeiam nada.
"""

from __future__ import annotations

import re

from fotoorganizer.geolocation.folder_names import _normalizar, identificar_pais
# A lista de sufixos de pacote mora no discovery (módulo folha, sem
# dependência do projeto) para não existir em duas versões que divergem.
from fotoorganizer.scanner.discovery import SUFIXOS_DE_CODIGO
from fotoorganizer.grouping.datas import separar_data

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
    # Etapas de workflow de revelação: dizem em que ponto do tratamento a
    # foto está, não do que ela é. Vivem na folha, logo abaixo do nome de
    # verdade ("Dubai, Thai & Viet/[Developed]").
    r"|developed|revelad[ao]s?|tratad[ao]s?|finalizad[ao]s?|culling"
    r"|picks?|rejects?|descartes?|lixo|previews?|thumbs?|cache|sidecars?"
    r"|fotos?|photos?|imagens|camera|backup|nova pasta|sem titulo|untitled"
    r"|pictures|users|home|volumes|desktop|documents|downloads|library"
    r")\]?$"
)

# Nomes de álbum só fazem sentido perto da folha — subir demais na árvore
# pegaria nomes de usuário e afins.
_PROFUNDIDADE_ALBUM = 3

_CATEGORIAS = {"viagens", "viagem", "familia", "eventos", "album", "albuns"}

# Pastas de arrumação: dizem o que o dono FEZ com as fotos, não do que
# elas são. "Portfolio/Fotos Organizadas/Visconde de Maua - Abril 2015"
# é sobre Visconde de Mauá; as duas primeiras são prateleiras.
_PASTAS_CONTEINER = {
    "portfolio", "portifolio", "fotos organizadas", "organizadas",
    "organizado", "acervo", "catalogo", "biblioteca", "galeria",
    "colecao", "colecoes", "arquivo", "arquivos", "diversos", "geral",
    "varios", "outros", "misc", "temp", "tmp", "novo", "novas",
}


def keyword_de_evento(segmento: str) -> bool:
    norm = _normalizar(segmento)
    return bool(_RE_ANOS.search(norm)) or any(
        kw in norm for kw in _KEYWORDS_EVENTO
    )


def pasta_tecnica(segmento: str) -> bool:
    norm = _normalizar(segmento)
    if _RE_TECNICO.match(norm):
        return True
    # Pacote de software conhecido: aqui o SUFIXO decide sozinho, o miolo não
    # importa. Sem isto, "BoraChurrascoRio.imageset" passou por nome de álbum
    # e batizou 1.314 fotos de um acervo real. É a segunda linha de defesa —
    # a primeira é o scanner nem entrar nessas pastas.
    if segmento.lower().endswith(SUFIXOS_DE_CODIGO):
        return True
    # Contêiner de software com extensão no nome da pasta ("Pictures.wrp2",
    # "Backup.photoslibrary"): o miolo é que diz o que é.
    sem_extensao = re.sub(r"\.[a-z0-9]{1,16}$", "", norm)
    return sem_extensao != norm and bool(_RE_TECNICO.match(sem_extensao))


def nome_de_album(segmento: str) -> bool:
    """Segmento que nomeia conteúdo: não técnico, não país, não categoria,
    não prateleira de arrumação."""
    norm = _normalizar(segmento)
    if not norm or pasta_tecnica(segmento):
        return False
    if identificar_pais(segmento) is not None:
        return False
    return norm not in _CATEGORIAS and norm not in _PASTAS_CONTEINER


def extrair_evento(pastas: list[str]) -> tuple[str | None, bool]:
    """Devolve (nome do evento, veio_de_keyword) a partir dos caminhos das
    pastas de uma sessão. Prefere o segmento mais fundo com keyword; senão
    o nome de álbum mais fundo. (None, False) quando só há pastas técnicas.

    A profundidade decide porque o caminho vai do geral ao específico: a
    pasta folha fala da foto, as de cima falam de onde ela foi guardada.
    Em "Portfolio/Fotos Organizadas/Visconde de Maua - Abril 2015" o nome
    é o último — e sem a data, que é evidência à parte (grouping/datas.py).
    """
    melhor_keyword: tuple[int, str] | None = None
    melhor_album: tuple[int, str] | None = None

    for pasta in pastas:
        segmentos = [s for s in pasta.split("/") if s]
        for i, segmento in enumerate(segmentos):
            # Filho direto de Users/home é nome de usuário, não álbum.
            if i > 0 and _normalizar(segmentos[i - 1]) in ("users", "home"):
                continue
            nivel = len(segmentos) - 1 - i  # 0 = folha
            nome, _data = separar_data(segmento)
            if not nome or not nome_de_album(nome):
                continue
            nome = nome.strip()
            if keyword_de_evento(nome):
                if melhor_keyword is None or nivel < melhor_keyword[0]:
                    melhor_keyword = (nivel, nome)
            elif nivel < _PROFUNDIDADE_ALBUM and (
                melhor_album is None or nivel < melhor_album[0]
            ):
                melhor_album = (nivel, nome)

    if melhor_keyword is not None:
        return melhor_keyword[1], True
    return (melhor_album[1] if melhor_album else None), False
