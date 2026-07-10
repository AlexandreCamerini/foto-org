"""Validação de caminhos para operações físicas.

Proteções: path traversal (destino calculado nunca escapa da raiz),
destino dentro da própria origem (recursão) e segmentos normalizados.
"""

from __future__ import annotations

from pathlib import Path

from fotoorganizer.classification.templates import normalizar_segmento


class CaminhoInvalido(ValueError):
    pass


def caminho_relativo_seguro(relativo: str) -> Path:
    """Sanitiza um caminho relativo (ex.: destino sugerido/editado):
    normaliza cada segmento e rejeita qualquer forma de escape."""
    partes = []
    for bruto in relativo.replace("\\", "/").split("/"):
        segmento = bruto.strip()
        if segmento in ("", "."):
            continue
        if segmento == ".." or segmento.startswith("~"):
            raise CaminhoInvalido(f"segmento proibido em {relativo!r}: {bruto!r}")
        limpo = normalizar_segmento(segmento)
        if not limpo:
            raise CaminhoInvalido(f"segmento vazio após normalizar: {bruto!r}")
        partes.append(limpo)
    if not partes:
        raise CaminhoInvalido(f"caminho relativo vazio: {relativo!r}")
    return Path(*partes)


def resolver_destino(raiz: Path, relativo: str) -> Path:
    """raiz + relativo sanitizado, com garantia pós-resolução de que o
    resultado continua dentro da raiz (defesa em profundidade)."""
    raiz_resolvida = raiz.expanduser().resolve()
    destino = (raiz_resolvida / caminho_relativo_seguro(relativo)).resolve()
    if not destino.is_relative_to(raiz_resolvida):
        raise CaminhoInvalido(f"{relativo!r} escapa da raiz {raiz}")
    return destino


def destino_recursivo(arvore_origem: Path, raiz_destino: Path) -> bool:
    """True se a raiz de destino está dentro da árvore da fonte — copiar
    para dentro da própria origem faria o próximo scan indexar as cópias."""
    try:
        raiz = raiz_destino.expanduser().resolve()
        origem = arvore_origem.expanduser().resolve()
        return raiz.is_relative_to(origem)
    except OSError:
        return True  # na dúvida, bloqueia
