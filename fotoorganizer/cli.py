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


def _settings(args: argparse.Namespace | None = None):
    """Config do TOML, com `--data-dir` sobrepondo o catálogo padrão.

    Sem isso não há como rodar contra um catálogo limpo sem editar a config
    real do usuário — o que torna qualquer diagnóstico de suporte invasivo.
    """
    from dataclasses import replace

    settings = load_settings()
    data_dir = getattr(args, "data_dir", None)
    if data_dir:
        raiz = Path(data_dir).expanduser()
        settings = replace(settings, data_dir=raiz, cache_dir=raiz / "cache")
    return settings


def _abrir_catalogo(args: argparse.Namespace | None = None):
    """Settings + session factory com o schema já migrado."""
    from fotoorganizer.database import (
        create_db_engine,
        create_session_factory,
        upgrade_to_head,
    )

    settings = _settings(args)
    settings.ensure_dirs()
    upgrade_to_head(settings.db_path)
    return settings, create_session_factory(create_db_engine(settings.db_path))


def _build_scanner(db_path: Path, settings=None):
    from fotoorganizer.database import (
        create_db_engine,
        create_session_factory,
        upgrade_to_head,
    )
    from fotoorganizer.metadata import criar_extrator
    from fotoorganizer.scanner import CatalogScanner
    from fotoorganizer.thumbnails import ThumbnailCache

    settings = settings or load_settings()
    upgrade_to_head(db_path)
    engine = create_db_engine(db_path)
    factory = create_session_factory(engine)
    return CatalogScanner(
        factory, criar_extrator(), settings.scanner,
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
    settings = _settings(args)
    settings.ensure_dirs()
    scanner = _build_scanner(settings.db_path, settings)

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


def cmd_inventario(args: argparse.Namespace) -> int:
    """O que existe e onde — inclusive o que não está alcançável agora."""
    from fotoorganizer.repositories.inventario import levantar

    _settings, factory = _abrir_catalogo(args)
    inv = levantar(factory)
    if not inv.fotos:
        print("Catálogo vazio. Use `scan` ou `importar` primeiro.")
        return 0

    print(f"{inv.fotos} fotos conhecidas, de {inv.total_registros} registros")
    print(f"({inv.alcancaveis} alcançáveis agora)\n")

    largura = max((len(l.raiz) for l in inv.lugares), default=10)
    for lugar in inv.lugares:
        estado = (f"{lugar.alcancaveis} alcançáveis"
                  if lugar.alcancaveis == lugar.fotos
                  else f"{lugar.so_no_catalogo} só no catálogo")
        print(f"  {lugar.raiz:<{largura}}  {lugar.fotos:>7}  {estado}")
        print(f"  {'':<{largura}}  {'':>7}  via {', '.join(lugar.fontes)}")
    if inv.sem_caminho:
        print(f"\n  {'(sem arquivo local)':<{largura}}  {inv.sem_caminho:>7}  "
              "referências de nuvem")
    return 0


def cmd_volumes(args: argparse.Namespace) -> int:
    """Onde cada fonte está — e o que está fora de alcance agora."""
    from fotoorganizer.sources.disponibilidade import verificar

    _settings, factory = _abrir_catalogo(args)
    estados = verificar(factory)
    if not estados:
        print("Nenhuma fonte cadastrada.")
        return 0

    largura = max(len(e.apelido) for e in estados)
    for e in estados:
        marca = "✓" if e.disponivel else ("→" if e.mudou_de_lugar else "·")
        print(f"  {marca} {e.apelido:<{largura}}  {e.resumo()}")
        print(f"    {e.caminho}")
        if e.volume is not None:
            aviso = "" if e.volume.estavel else "   (identidade frágil: é o caminho)"
            print(f"    volume: {e.volume.identidade}{aviso}")

    fora = [e for e in estados if not e.disponivel]
    if fora:
        print(f"\n{len(fora)} de {len(estados)} fontes fora de alcance.")
        if any(e.mudou_de_lugar for e in fora):
            print("Alguma voltou noutro ponto de montagem — veja as marcadas "
                  "com →. Reaponte a fonte para o caminho novo antes de varrer.")
    return 0


def cmd_importar(args: argparse.Namespace) -> int:
    """Importa catálogo externo. Existe como comando porque o Acesso Total ao
    Disco é concedido por app: rodar daqui, no terminal do usuário, usa a
    permissão do terminal — sem precisar autorizar o app que abriu o servidor."""
    from fotoorganizer.metadata import criar_extrator
    from fotoorganizer.sources import (
        ApplePhotosProvider,
        ExternalCatalogImporter,
        GoogleTakeoutProvider,
        LightroomProvider,
    )
    from fotoorganizer.sources.apple_photos import ApplePhotosError
    from fotoorganizer.sources.lightroom import LightroomError
    from fotoorganizer.thumbnails import ThumbnailCache

    settings, factory = _abrir_catalogo(args)
    if args.fonte == "apple":
        provider = ApplePhotosProvider(
            Path(args.caminho).expanduser() if args.caminho else None
        )
    elif args.fonte == "lightroom":
        if not args.caminho:
            print("Informe o arquivo .lrcat do Lightroom Classic.")
            return 1
        provider = LightroomProvider(Path(args.caminho).expanduser())
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
        factory, criar_extrator(), settings.scanner,
        thumb_cache=ThumbnailCache(settings.cache_dir),
    )
    try:
        metrics = importer.importar(provider, progress=progresso)
    except (ApplePhotosError, LightroomError) as exc:
        print(f"\n{exc}")
        return 1
    print(f"\n{metrics.importados} importados, {metrics.pulados} pulados, "
          f"{metrics.erros} erros")
    return 0


def cmd_planos(args: argparse.Namespace) -> int:
    from fotoorganizer.repositories import OperationRepository

    _, factory = _abrir_catalogo(args)
    planos = OperationRepository(factory).listar_planos()
    if not planos:
        print("Nenhum plano. Crie um com: fotoorganizer plano <raiz-destino>")
        return 0
    for p in planos:
        print(f"[{p.id}] {p.nome}\n"
              f"     {p.status.value} · {p.total_itens} itens · "
              f"{p.concluidos} copiados · {p.com_conflito} conflitos · "
              f"{p.com_erro} erros de execução\n"
              f"     {_veredito_legivel(p)}")
    return 0


def _veredito_legivel(p) -> str:
    """O que o dry-run disse — a linha que decide se dá para executar.

    Sem ela o resumo mostrava "0 erros · dry-run: ✓" para um plano com as
    97 origens num volume desmontado, que lê como "pronto para copiar".
    """
    if p.dry_run_em is None:
        return "dry-run: não rodado (obrigatório antes de copiar)"
    quando = p.dry_run_em.strftime("%d/%m %H:%M")
    if p.prontos is None:
        return f"dry-run {quando}: sem veredito registrado"
    if not p.prontos:
        return (f"dry-run {quando}: NENHUM arquivo copiável "
                f"({p.problemas} problemas) — não há o que executar")
    if p.problemas:
        return (f"dry-run {quando}: {p.prontos} de {p.total_itens} prontos, "
                f"{p.problemas} com problema")
    return f"dry-run {quando}: {p.prontos} prontos, sem problemas"


def cmd_plano(args: argparse.Namespace) -> int:
    from fotoorganizer.operations import OperationPlanner
    from fotoorganizer.repositories import OperationRepository

    _, factory = _abrir_catalogo(args)
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

    _, factory = _abrir_catalogo(args)
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

    _, factory = _abrir_catalogo(args)

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

    settings = _settings(args)
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
    parser.add_argument(
        "--data-dir", metavar="PASTA",
        help="usa outro catálogo em vez do padrão (~/Library/Application "
             "Support/FotoOrganizer) — para testar ou isolar um problema "
             "sem tocar no catálogo real",
    )
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
        "importar",
        help="importa Apple Fotos, Google Takeout ou Lightroom (read-only)"
    )
    sub.add_parser(
        "volumes", help="onde cada fonte está e o que está fora de alcance"
    ).set_defaults(func=cmd_volumes)

    sub.add_parser(
        "inventario", help="o que existe e onde, inclusive fora de alcance"
    ).set_defaults(func=cmd_inventario)

    p_imp.add_argument("fonte", choices=["apple", "takeout", "lightroom"])
    p_imp.add_argument(
        "caminho", nargs="?",
        help="pasta do Takeout, arquivo .lrcat do Lightroom; para apple, "
             "biblioteca alternativa (opcional)",
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
