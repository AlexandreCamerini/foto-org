"""CLI interna: varredura headless, operações e benchmark de indexação.

Uso:
    python -m fotoorganizer scan <pasta> [<pasta>...]
    python -m fotoorganizer web [--porta N]
    python -m fotoorganizer planos
    python -m fotoorganizer plano <raiz-destino> [--nome N]
    python -m fotoorganizer dry-run <plano-id>
    python -m fotoorganizer executar <plano-id> --confirmar
    python -m fotoorganizer bench [-n QUANTIDADE]

`executar` exige `--confirmar` porque é a única operação que escreve fora
do catálogo: sem a UI para aprovar, a flag é a aprovação explícita que o
invariante 2 do CLAUDE.md pede.
"""

from __future__ import annotations

import argparse
import logging
import sys
import tempfile
import time
from pathlib import Path

from fotoorganizer.config import load_settings


def _abrir_catalogo():
    """Settings + session factory com o schema já migrado."""
    from fotoorganizer.database import (
        create_db_engine,
        create_session_factory,
        upgrade_to_head,
    )

    settings = load_settings()
    settings.ensure_dirs()
    upgrade_to_head(settings.db_path)
    return settings, create_session_factory(create_db_engine(settings.db_path))


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
        scan, metrics = scanner.scan_source(
            Path(pasta), progress=_print_progress,
            reprocessar=args.reprocessar,
        )
        print(
            f"\n{scan.status.value}: {metrics.indexados} indexados, "
            f"{metrics.pulados} pulados, {metrics.erros} erros, "
            f"{metrics.bytes_processados / 1e6:.1f} MB em "
            f"{metrics.segundos_decorridos:.1f}s"
        )
    return 0


def cmd_importar(args: argparse.Namespace) -> int:
    """Importa catálogo externo. Existe como comando porque o Acesso Total ao
    Disco é concedido por app: rodar daqui, no terminal do usuário, usa a
    permissão do terminal — sem precisar autorizar o app que abriu o servidor."""
    from fotoorganizer.metadata import PurePythonExtractor
    from fotoorganizer.sources import (
        ApplePhotosProvider,
        ExternalCatalogImporter,
        GoogleTakeoutProvider,
    )
    from fotoorganizer.sources.apple_photos import ApplePhotosError
    from fotoorganizer.thumbnails import ThumbnailCache

    settings, factory = _abrir_catalogo()
    if args.fonte == "apple":
        provider = ApplePhotosProvider(
            Path(args.caminho).expanduser() if args.caminho else None
        )
    else:
        if not args.caminho:
            print("Informe a pasta do Takeout descompactado.")
            return 1
        pasta = Path(args.caminho).expanduser()
        if not pasta.is_dir():
            print(f"Pasta não encontrada: {pasta}")
            return 1
        provider = GoogleTakeoutProvider(pasta, ler_arquivos=args.ler_arquivos)

    def progresso(metrics, _caminho: str) -> None:
        sys.stdout.write(
            f"\r{metrics.vistos} vistos | {metrics.importados} importados | "
            f"{metrics.pulados} pulados | {metrics.erros} erros   "
        )
        sys.stdout.flush()

    print(f"Importando {provider.apelido} (somente leitura) para "
          f"{settings.db_path}")
    importer = ExternalCatalogImporter(
        factory, PurePythonExtractor(), settings.scanner,
        thumb_cache=ThumbnailCache(settings.cache_dir),
    )
    try:
        metrics = importer.importar(provider, progress=progresso)
    except ApplePhotosError as exc:
        print(f"\n{exc}")
        return 1
    print(f"\n{metrics.importados} importados, {metrics.pulados} pulados, "
          f"{metrics.erros} erros")
    return 0


def cmd_planos(args: argparse.Namespace) -> int:
    from fotoorganizer.repositories import OperationRepository

    _, factory = _abrir_catalogo()
    planos = OperationRepository(factory).listar_planos()
    if not planos:
        print("Nenhum plano. Crie um com: fotoorganizer plano <raiz-destino>")
        return 0
    for p in planos:
        dry = p.dry_run_em.strftime("%d/%m %H:%M") if p.dry_run_em else "—"
        print(f"[{p.id}] {p.nome}\n"
              f"     {p.status.value} · {p.total_itens} itens · "
              f"{p.concluidos} copiados · {p.com_conflito} conflitos · "
              f"{p.com_erro} erros · dry-run: {dry}")
    return 0


def cmd_plano(args: argparse.Namespace) -> int:
    from fotoorganizer.operations import OperationPlanner
    from fotoorganizer.repositories import OperationRepository

    _, factory = _abrir_catalogo()
    raiz = Path(args.destino).expanduser()
    plan_id = OperationPlanner(factory).criar_plano(raiz, args.nome)
    if plan_id is None:
        print("Nenhuma sugestão aprovada aguardando cópia — nada a planejar.")
        return 1
    plano = OperationRepository(factory).plano(plan_id)
    print(f"Plano {plan_id} criado: {plano.total_itens} itens para {raiz}"
          f" ({plano.com_conflito} com conflito)")
    print(f"Próximo passo: fotoorganizer dry-run {plan_id}")
    return 0


def cmd_dry_run(args: argparse.Namespace) -> int:
    from fotoorganizer.operations import OperationExecutor

    _, factory = _abrir_catalogo()
    r = OperationExecutor(factory).dry_run(args.plano_id)
    print(f"Prontos: {r['prontos']} · {r['bytes_necessarios'] / 1e6:.1f} MB")
    if r["bytes_livres"] is not None:
        print(f"Livre no destino: {r['bytes_livres'] / 1e9:.1f} GB "
              f"({'suficiente' if r['espaco_suficiente'] else 'INSUFICIENTE'})")
    for problema in r["problemas"]:
        print(f"  ! {problema}")
    if r["prontos"]:
        print(f"Para copiar: fotoorganizer executar {args.plano_id} --confirmar")
    return 0


def cmd_executar(args: argparse.Namespace) -> int:
    from fotoorganizer.operations import DryRunObrigatorio, OperationExecutor

    if not args.confirmar:
        print("Execução copia arquivos de verdade. Repita com --confirmar.")
        return 1

    _, factory = _abrir_catalogo()

    def progresso(n: int, total: int, origem: str) -> None:
        sys.stdout.write(f"\r{n}/{total} — {Path(origem).name}      ")
        sys.stdout.flush()

    try:
        stats = OperationExecutor(factory).executar(
            args.plano_id, progress=progresso
        )
    except DryRunObrigatorio as exc:
        print(f"\n{exc}")
        return 1
    print(f"\n{stats['copiados']} copiados · {stats['pulados']} pulados · "
          f"{stats['erros']} erros")
    return 1 if stats["erros"] else 0


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


def cmd_web(args: argparse.Namespace) -> int:
    """Servidor local da UI web — escuta apenas em 127.0.0.1."""
    import uvicorn

    from fotoorganizer.database import (
        create_db_engine,
        create_session_factory,
        upgrade_to_head,
    )
    from fotoorganizer.server import create_app

    settings = load_settings()
    settings.ensure_dirs()
    upgrade_to_head(settings.db_path)
    factory = create_session_factory(create_db_engine(settings.db_path))
    app = create_app(settings, factory)
    print(f"Foto Organizer web em http://127.0.0.1:{args.porta} "
          f"(catálogo: {settings.db_path})")
    uvicorn.run(app, host="127.0.0.1", port=args.porta, log_level="warning")
    return 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.WARNING)
    parser = argparse.ArgumentParser(prog="fotoorganizer")
    sub = parser.add_subparsers(dest="comando", required=True)

    p_scan = sub.add_parser("scan", help="varre pastas para o catálogo (read-only)")
    p_scan.add_argument("pastas", nargs="+")
    p_scan.add_argument(
        "--reprocessar", action="store_true",
        help="relê arquivos já indexados (para capturar metadados novos)",
    )
    p_scan.set_defaults(func=cmd_scan)

    p_web = sub.add_parser("web", help="UI web local (127.0.0.1)")
    p_web.add_argument("--porta", type=int, default=8765)
    p_web.set_defaults(func=cmd_web)

    p_imp = sub.add_parser(
        "importar", help="importa Apple Fotos ou Google Takeout (read-only)"
    )
    p_imp.add_argument("fonte", choices=["apple", "takeout"])
    p_imp.add_argument(
        "caminho", nargs="?",
        help="pasta do Takeout; para apple, biblioteca alternativa (opcional)",
    )
    p_imp.add_argument(
        "--ler-arquivos", action="store_true",
        help="takeout: abrir cada imagem (EXIF, hash, miniatura). Por padrão "
             "só o sidecar e a entrada de diretório são lidos",
    )
    p_imp.set_defaults(func=cmd_importar)

    p_planos = sub.add_parser("planos", help="lista os planos de operação")
    p_planos.set_defaults(func=cmd_planos)

    p_plano = sub.add_parser(
        "plano", help="cria plano de cópia das sugestões aprovadas"
    )
    p_plano.add_argument("destino", help="raiz de destino da árvore organizada")
    p_plano.add_argument("--nome")
    p_plano.set_defaults(func=cmd_plano)

    p_dry = sub.add_parser("dry-run", help="simula um plano sem tocar em nada")
    p_dry.add_argument("plano_id", type=int)
    p_dry.set_defaults(func=cmd_dry_run)

    p_exec = sub.add_parser("executar", help="copia os arquivos do plano")
    p_exec.add_argument("plano_id", type=int)
    p_exec.add_argument("--confirmar", action="store_true",
                        help="aprovação explícita — sem ela nada é copiado")
    p_exec.set_defaults(func=cmd_executar)

    p_bench = sub.add_parser("bench", help="benchmark de indexação com fixtures")
    p_bench.add_argument("-n", "--quantidade", type=int, default=500)
    p_bench.set_defaults(func=cmd_bench)

    args = parser.parse_args(argv)
    return args.func(args)
