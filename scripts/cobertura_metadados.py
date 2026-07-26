#!/usr/bin/env python3
"""Mede quais campos de metadados ficam vazios numa amostra real.

Somente leitura: nenhum catálogo é escrito, nenhum arquivo é tocado. Serve
para decidir *onde* vale ampliar a extração antes de escrever código —
ampliar no escuro custa migração e teste sem ganho comprovado.

Uso:
    python scripts/cobertura_metadados.py <pasta> [<pasta>...] [-n 400]
"""

from __future__ import annotations

import argparse
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fotoorganizer.metadata import PurePythonExtractor  # noqa: E402

CAMPOS = [
    "data_capturada", "make", "model", "lente", "orientacao",
    "largura", "altura", "gps_lat",
]


def amostrar(
    raizes: list[Path], quantidade: int, semente: int, extensoes: frozenset[str]
) -> list[Path]:
    """Amostra estratificada por pasta: uma coleção com 20 mil fotos numa
    única viagem não pode dominar o retrato."""
    por_pasta: dict[Path, list[Path]] = {}
    for raiz in raizes:
        for caminho in raiz.rglob("*"):
            if caminho.is_file() and caminho.suffix.lower() in extensoes:
                por_pasta.setdefault(caminho.parent, []).append(caminho)
    if not por_pasta:
        return []

    rng = random.Random(semente)
    for arquivos in por_pasta.values():
        rng.shuffle(arquivos)

    amostra: list[Path] = []
    pastas = sorted(por_pasta)
    while len(amostra) < quantidade and any(por_pasta[p] for p in pastas):
        for pasta in pastas:
            if por_pasta[pasta] and len(amostra) < quantidade:
                amostra.append(por_pasta[pasta].pop())
    return amostra


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("pastas", nargs="+", type=Path)
    parser.add_argument("-n", "--quantidade", type=int, default=400)
    parser.add_argument("--semente", type=int, default=20260726)
    args = parser.parse_args()

    extractor = PurePythonExtractor()
    amostra = amostrar(
        [p.expanduser() for p in args.pastas], args.quantidade, args.semente,
        frozenset(extractor.supported_extensions()),
    )
    if not amostra:
        print("Nenhum arquivo suportado encontrado.")
        return 1
    vazios = Counter()
    por_extensao: Counter = Counter()
    extras_vistos: Counter = Counter()
    erros = 0

    for caminho in amostra:
        meta = extractor.extract(caminho)
        por_extensao[caminho.suffix.lower()] += 1
        if meta.erro:
            erros += 1
        for campo in CAMPOS:
            if getattr(meta, campo) is None:
                vazios[campo] += 1
        for origem, chave, _valor in meta.extras:
            extras_vistos[f"{origem}:{chave}"] += 1

    total = len(amostra)
    print(f"Amostra: {total} arquivos de {len(args.pastas)} raiz(es), "
          f"{erros} com erro de leitura")
    print(f"Formatos: {dict(por_extensao.most_common())}\n")
    print(f"{'campo':<16} {'vazios':>7} {'%':>6}")
    for campo in CAMPOS:
        n = vazios[campo]
        print(f"{campo:<16} {n:>7} {100 * n / total:>5.1f}%")
    if extras_vistos:
        print(f"\nExtras já capturados: {dict(extras_vistos.most_common(10))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
