"""Templates de destino: {categoria}/{ano} - {viagem}/{pais}/{cidade}…

Regras de renderização:
- segmento cujo(s) placeholder(s) ficaram todos vazios é descartado;
- placeholder vazio no meio de um segmento misto some e sobras de
  separadores ("2024 - ", " - ") são aparadas;
- cada segmento é normalizado para nome de diretório seguro (caracteres
  inválidos, comprimento, pontos/espaços nas bordas);
- valor que já apareceu acima no caminho não repete: "2025 - Tailândia –
  Vietnã/Tailândia/Chiang Mai/Chiang Mai" vira "2025 - Tailândia –
  Vietnã/Chiang Mai". A comparação é por parte inteira, nunca por
  pedaço de palavra — senão "York" sumiria sob "New York";
- se tudo ficar vazio, o destino é "Não classificadas" — nunca inventa.
  Quem enche esse ramo por ano e mês é o motor (classification/engine.py),
  que tem a data; aqui só existe a raiz.
"""

from __future__ import annotations

import re
import string
import unicodedata

TEMPLATE_PADRAO = "{categoria}/{ano} - {viagem}/{evento}/{pais}/{regiao}/{cidade}"

DESTINO_NAO_CLASSIFICADO = "Não classificadas"

_MAX_SEGMENTO = 80
# Inválidos em APFS/exFAT/NTFS + controles. "/" separa segmentos, nunca
# entra num nome.
_CHARS_INVALIDOS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_PLACEHOLDER = re.compile(r"\{(\w+)\}")


def normalizar_segmento(texto: str, max_len: int = _MAX_SEGMENTO) -> str:
    texto = unicodedata.normalize("NFC", texto)
    texto = _CHARS_INVALIDOS.sub("_", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    # Bordas problemáticas em vários filesystems (". nome .", "nome...").
    texto = texto.strip(". ")
    if len(texto) > max_len:
        texto = texto[:max_len].rstrip(". ")
    return texto


# Separadores que compõem um segmento a partir de vários valores
# ("2025 - Tailândia – Vietnã"). Quebrar por eles dá as partes que contam
# como "já apareceu".
_RE_PARTES = re.compile(r"\s+[-–—]\s+")


def _chave(texto: str) -> str:
    """Forma comparável: sem acento, sem caixa, espaços colapsados."""
    sem_acento = (
        unicodedata.normalize("NFKD", texto)
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    return re.sub(r"\s+", " ", sem_acento).strip().lower()


def _partes(segmento: str) -> set[str]:
    return {
        chave for parte in _RE_PARTES.split(segmento)
        if (chave := _chave(parte))
    }


def _render_segmento(
    segmento: str, campos: dict[str, str | None], vistos: set[str]
) -> str:
    tinha_placeholder = False
    preencheu_algum = False

    def substituir(match: re.Match) -> str:
        nonlocal tinha_placeholder, preencheu_algum
        tinha_placeholder = True
        valor = campos.get(match.group(1))
        # Valor que já apareceu acima no caminho não repete: a pasta
        # "Tailândia" dentro de "2025 - Tailândia – Vietnã" não informa
        # nada e só afunda a árvore.
        if valor and _chave(str(valor)) not in vistos:
            preencheu_algum = True
            return str(valor)
        return ""

    resultado = _PLACEHOLDER.sub(substituir, segmento)
    if tinha_placeholder and not preencheu_algum:
        return ""
    # Sobras de separadores de placeholders vazios: "2024 - " → "2024".
    resultado = resultado.strip(" -–—_" + string.whitespace)
    resultado = re.sub(r"\s+[-–—]\s+[-–—]\s+", " - ", resultado)
    return normalizar_segmento(resultado)


def render_destino(template: str, campos: dict[str, str | None]) -> str:
    vistos: set[str] = set()
    segmentos: list[str] = []
    for seg in template.split("/"):
        renderizado = _render_segmento(seg, campos, vistos)
        if renderizado:
            segmentos.append(renderizado)
            vistos |= _partes(renderizado)
    return "/".join(segmentos) if segmentos else DESTINO_NAO_CLASSIFICADO


def resolver_colisao(destino: str, existentes: set[str]) -> str:
    """Sufixa " (2)", " (3)"… até não colidir. Nunca sobrescreve nome usado."""
    if destino not in existentes:
        return destino
    for i in range(2, 10_000):
        candidato = f"{destino} ({i})"
        if candidato not in existentes:
            return candidato
    raise RuntimeError(f"sem variação livre para {destino!r}")
