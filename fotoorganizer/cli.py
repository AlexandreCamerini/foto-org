"""CLI interna: varredura headless e benchmark de indexação.

Uso:
    python -m fotoorganizer scan <pasta> [<pasta>...]
    python -m fotoorganizer bench [-n QUANTIDADE]

A GUI continua sendo o modo padrão (`python -m fotoorganizer` sem args).
"""

from __future__ import annotations

import argparse
import logging
import sys
import tempfile
import time
from pathlib import Path

from fotoorganizer.config import load_settings


def _build_scanner(db_path: Path):
    from fotoorganizer.database import (
        create_db_engine,
        create_session_factory,
        upgrade_to_head,
    )
    from fotoorganizer.metadata import PurePythonExtractor
    from fotoorganizer.scanner import CatalogScanner
    from fotoorganizer.thumbnails import ThumbnailCache

    settings = load_settings()
    upgrade_to_head(db_path)
    engine = create_db_engine(db_path)
    factory = create_session_factory(engine)
    return CatalogScanner(
        factory, PurePythonExtractor(), settings.scanner,
        thumb_cache=ThumbnailCache(settings.cache_dir),
    )


def _print_progress(metrics, caminho: str) -> None:
    sys.stdout.write(
        f"\r{metrics.vistos} vistos | {metrics.indexados} indexados | "
        f"{metrics.pulados} pulados | {metrics.erros} erros | "
        f"{metrics.arquivos_por_segundo:.1f} arq/s   "
    )
    sys.stdout.flush()


def cmd_scan(args: argparse.Namespace) -> int:
    settings = load_settings()
    settings.ensure_dirs()
    scanner = _build_scanner(settings.db_path)

    for pasta in args.pastas:
        print(f"Varrendo {pasta} (somente leitura, catálogo em {settings.db_path})")
        scan, metrics = scanner.scan_source(Path(pasta), progress=_print_progress)
        print(
            f"\n{scan.status.value}: {metrics.indexados} indexados, "
            f"{metrics.pulados} pulados, {metrics.erros} erros, "
            f"{metrics.bytes_processados / 1e6:.1f} MB em "
            f"{metrics.segundos_decorridos:.1f}s"
        )
    return 0


def _jpeg_sintetico(path: Path, seed: int) -> None:
    from PIL import Image

    cor = ((seed * 37) % 256, (seed * 73) % 256, (seed * 151) % 256)
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (64, 48), cor).save(path)


def cmd_bench(args: argparse.Namespace) -> int:
    """Benchmark com arquivos sintéticos: indexação a frio e re-scan."""
    with tempfile.TemporaryDirectory(prefix="fotobench-") as tmp:
        tmp_path = Path(tmp)
        fotos = tmp_path / "fotos"
        fotos.mkdir()
        print(f"Gerando {args.quantidade} JPEGs sintéticos...")
        for i in range(args.quantidade):
            sub = fotos / f"pasta_{i % 10:02d}"
            sub.mkdir(exist_ok=True)
            _jpeg_sintetico(sub / f"img_{i:05d}.jpg", seed=i)

        scanner = _build_scanner(tmp_path / "bench.db")

        inicio = time.monotonic()
        _, m1 = scanner.scan_source(fotos)
        frio = time.monotonic() - inicio

        inicio = time.monotonic()
        _, m2 = scanner.scan_source(fotos)
        quente = time.monotonic() - inicio

        print(f"Indexação a frio : {m1.indexados} arquivos em {frio:.2f}s "
              f"({m1.indexados / frio:.0f} arq/s)")
        print(f"Re-scan (pulando): {m2.pulados} pulados em {quente:.2f}s "
              f"({m2.vistos / quente:.0f} arq/s)")
    return 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.WARNING)
    parser = argparse.ArgumentParser(prog="fotoorganizer")
    sub = parser.add_subparsers(dest="comando", required=True)

    p_scan = sub.add_parser("scan", help="varre pastas para o catálogo (read-only)")
    p_scan.add_argument("pastas", nargs="+")
    p_scan.set_defaults(func=cmd_scan)

    p_bench = sub.add_parser("bench", help="benchmark de indexação com fixtures")
    p_bench.add_argument("-n", "--quantidade", type=int, default=500)
    p_bench.set_defaults(func=cmd_bench)

    args = parser.parse_args(argv)
    return args.func(args)
