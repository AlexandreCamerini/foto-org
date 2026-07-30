"""Mede o que o exiftool acrescenta sobre o extrator puro-Python.

A decisão de adotar exiftool (docs/PLANO_METADADOS.md §4) está pendente de
medição: sem número, "exiftool lê mais" é folclore. Este script compara tag a
tag, por formato, na mesma amostra estratificada de docs/COBERTURA_METADADOS.md.

Somente leitura: não abre catálogo, não escreve nada, não altera arquivo.

Uso:
    brew install exiftool          # o passo que exige decisão do dono
    .venv/bin/python scripts/medir_exiftool.py <pasta> [--amostra 300]
"""

from __future__ import annotations

import argparse
import json
import random
import shutil
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fotoorganizer.metadata import PurePythonExtractor  # noqa: E402

EXTENSOES = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".heic", ".hif",
             ".webp", ".cr2", ".cr3", ".nef", ".arw", ".dng", ".raf", ".orf"}
SEMENTE = 20260730  # amostra reproduzível


def amostrar(raiz: Path, quantos: int) -> list[Path]:
    todos = [p for p in raiz.rglob("*")
             if p.is_file() and p.suffix.lower() in EXTENSOES]
    random.Random(SEMENTE).shuffle(todos)
    # Estratifica por extensão para o CR3 não sumir numa amostra de JPEG.
    por_ext: dict[str, list[Path]] = defaultdict(list)
    for p in todos:
        por_ext[p.suffix.lower()].append(p)
    cota = max(1, quantos // max(1, len(por_ext)))
    escolhidos: list[Path] = []
    for arquivos in por_ext.values():
        escolhidos.extend(arquivos[:cota])
    return escolhidos[:quantos]


def tags_exiftool(caminhos: list[Path]) -> dict[Path, dict]:
    """Uma chamada em lote — é assim que o exiftool fica viável."""
    saida = subprocess.run(  # noqa: S603 — sem shell, argumentos em lista
        ["exiftool", "-json", "-G", "-n", *[str(p) for p in caminhos]],
        capture_output=True, text=True, check=False,
    )
    if saida.returncode != 0 and not saida.stdout:
        raise SystemExit(f"exiftool falhou: {saida.stderr[:400]}")
    return {Path(item["SourceFile"]): item for item in json.loads(saida.stdout)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pasta", type=Path)
    ap.add_argument("--amostra", type=int, default=300)
    args = ap.parse_args()

    if shutil.which("exiftool") is None:
        print("exiftool não encontrado. Instale com: brew install exiftool")
        return 1

    caminhos = amostrar(args.pasta.expanduser(), args.amostra)
    if not caminhos:
        print(f"nenhum arquivo de imagem em {args.pasta}")
        return 1
    print(f"{len(caminhos)} arquivos amostrados (semente {SEMENTE})\n")

    extrator = PurePythonExtractor()
    inicio = time.perf_counter()
    puro = {p: extrator.extract(p) for p in caminhos}
    t_puro = time.perf_counter() - inicio

    inicio = time.perf_counter()
    et = tags_exiftool(caminhos)
    t_et = time.perf_counter() - inicio

    por_ext_puro: Counter[str] = Counter()
    por_ext_et: Counter[str] = Counter()
    arquivos_ext: Counter[str] = Counter()
    grupos_so_et: Counter[str] = Counter()

    for p in caminhos:
        ext = p.suffix.lower()
        arquivos_ext[ext] += 1
        por_ext_puro[ext] += len(puro[p].extras)
        tags = et.get(p.resolve(), et.get(p, {}))
        por_ext_et[ext] += max(0, len(tags) - 1)  # menos SourceFile
        for chave in tags:
            if ":" in chave:
                grupos_so_et[chave.split(":", 1)[0]] += 1

    print(f"{'ext':>8} {'arq':>5} {'puro':>8} {'exiftool':>9} {'ganho':>7}")
    for ext in sorted(arquivos_ext):
        n = arquivos_ext[ext]
        a, b = por_ext_puro[ext] / n, por_ext_et[ext] / n
        print(f"{ext:>8} {n:>5} {a:>8.1f} {b:>9.1f} {b / a if a else 0:>6.1f}x")

    print(f"\ntempo puro-Python: {t_puro:.1f}s  ({t_puro / len(caminhos) * 1000:.0f} ms/arquivo)")
    print(f"tempo exiftool:    {t_et:.1f}s  ({t_et / len(caminhos) * 1000:.0f} ms/arquivo, lote único)")
    print("\ngrupos que só o exiftool traz (top 12):")
    for grupo, n in grupos_so_et.most_common(12):
        print(f"   {grupo:<22} em {n} arquivos")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
