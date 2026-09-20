"""Vocabulário de segmentos de pasta — módulo folha, sem dependência do projeto.

O que um segmento de caminho diz por si só: se é pasta técnica
("[Originals]", "2025_05_24"), se carrega palavra de evento ("15 anos",
"casamento"). Mora aqui, e não em `grouping/eventos.py`, porque
`geolocation/` também precisa disso (o país de "Israel e Maria Casamento"
não é Israel) e importar de `eventos.py` fecharia um ciclo — o mesmo
motivo de `SUFIXOS_DE_CODIGO` viver em `scanner/discovery.py`.
"""

from __future__ import annotations

import re
import unicodedata


def normalizar(texto: str) -> str:
    """Sem acento, sem caixa, sem espaço nas bordas."""
    sem_acento = (
        unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    )
    return sem_acento.strip().lower()


# Palavras que indicam evento (comparadas sem acento/caixa).
KEYWORDS_EVENTO = {
    "aniversario", "casamento", "formatura", "batizado", "cha de bebe",
    "festa", "natal", "reveillon", "ano novo", "pascoa", "churrasco",
    "show", "festival", "despedida", "confraternizacao", "bodas",
}
# "15 anos", "1 ano" — aniversários por idade.
RE_ANOS = re.compile(r"\b\d{1,3}\s*anos?\b")

# Pastas técnicas: datas, contadores de câmera, subpastas de workflow.
RE_TECNICO = re.compile(
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


def keyword_de_evento(segmento: str) -> bool:
    norm = normalizar(segmento)
    return bool(RE_ANOS.search(norm)) or any(kw in norm for kw in KEYWORDS_EVENTO)


def segmento_tecnico(segmento: str) -> bool:
    """Só a regra de nome; a de sufixo de pacote (`.photoslibrary`) fica
    em `grouping/eventos.pasta_tecnica`, que precisa do scanner."""
    return bool(RE_TECNICO.match(normalizar(segmento)))
