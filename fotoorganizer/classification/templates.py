"""Templates de destino: {categoria}/{ano} - {viagem}/{pais}/{cidade}…

Regras de renderização:
- segmento cujo(s) placeholder(s) ficaram todos vazios é descartado;
- placeholder vazio no meio de um segmento misto some e sobras de
  separadores ("2024 - ", " - ") são aparadas;
- cada segmento é normalizado para nome de diretório seguro (caracteres
  inválidos, comprimento, pontos/espaços nas bordas);
- se tudo ficar vazio, o destino é "Não classificado" — nunca inventa.
"""

from __future__ import annotations

import re
import string
import unicodedata

TEMPLATE_PADRAO = "{categoria}/{ano} - {viagem}/{pais}/{regiao}/{cidade}"

DESTINO_NAO_CLASSIFICADO = "Não classificado"

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


def _render_segmento(segmento: str, campos: dict[str, str | None]) -> str:
    tinha_placeholder = False
    preencheu_algum = False

    def substituir(match: re.Match) -> str:
        nonlocal tinha_placeholder, preencheu_algum
        tinha_placeholder = True
        valor = campos.get(match.group(1))
        if valor:
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
    segmentos = [
        renderizado
        for seg in template.split("/")
        if (renderizado := _render_segmento(seg, campos))
    ]
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
