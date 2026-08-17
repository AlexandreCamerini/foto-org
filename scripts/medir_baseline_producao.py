"""Baseline formal de LANC-04: taxa de indexação, tempo de geração de
sugestões e tempo de detecção de duplicatas, medidos contra o acervo real.

Uso:
    .venv/bin/python scripts/medir_baseline_producao.py --listar-fontes
    .venv/bin/python scripts/medir_baseline_producao.py --pasta /caminho/da/raiz [--pasta ...]
    .venv/bin/python scripts/medir_baseline_producao.py --pular-varredura
    .venv/bin/python scripts/medir_baseline_producao.py --data-dir /tmp/dados --pasta /tmp/fotos

Este script é o oposto de `fotoorganizer bench` (`cli.py cmd_bench`): `bench`
mede contra JPEGs sintéticos isolados de propósito ("nunca para o cache real
do usuário"); este mede contra o `catalog.db` de produção, propositalmente
(D-07 — sem número contra o acervo real não existe baseline de regressão).

Decisões de execução (registradas em docs/PERFORMANCE.md para a próxima
rodada repetir):
- P-1: a varredura roda no catálogo real, in place — é a própria rescan que
  D-07 pede, não um passo extra.
- P-2: geração de sugestões e detecção de duplicatas rodam sobre uma CÓPIA
  descartável do catálogo recém-varrido (`shutil.copy2`), nunca in place —
  as duas escrevem como efeito colateral (`Suggestion`, `DuplicateGroup`,
  `DuplicateMember`) e in place deixaria a produção com um lote de sugestões
  auto-geradas que ninguém pediu nem revisou.
- P-3: medição 100% local, o parâmetro `advisor` do motor de sugestões
  recebe `None` literal, sem flag que ligue o advisor LLM opt-in — não
  reprodutível se depender de rede/custo por token.

Nenhum caminho deste script apaga arquivo: a cópia descartável de P-2 é
mantida ao final (invariante 8 do CLAUDE.md — nada que possa ser referência
real é descartado), e o catálogo de produção nunca é tocado por escrita fora
da própria varredura pedida.
"""

from __future__ import annotations

import argparse
import shutil
import signal
import sqlite3
import sys
import time
from dataclasses import dataclass, field, replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fotoorganizer.config import aplicar_overrides, load_settings
from fotoorganizer.config.settings import Settings
from fotoorganizer.database import (
    create_db_engine,
    create_session_factory,
    upgrade_to_head,
)
from fotoorganizer.metadata import criar_extrator
from fotoorganizer.scanner import CatalogScanner
from fotoorganizer.scanner.scanner import ScanMetrics
from fotoorganizer.thumbnails import ThumbnailCache

BACKUP_PADRAO = (
    Path.home()
    / "Library"
    / "Application Support"
    / "FotoOrganizer"
    / "catalog-antes-do-reset-20260816-013503.db"
)

# Tipos de fonte que são importadores (Apple Fotos, Lightroom) — não entram
# na medida de taxa de varredura porque não são `scan_source` de pasta.
# SQLAlchemy grava o NOME do membro do enum (native_enum=False), não o
# `.value` — por isso maiúsculo, igual ao que está na coluna `tipo`.
_TIPOS_IMPORTADOR = {"APPLE_PHOTOS", "LIGHTROOM"}


def _print_progress(metrics: ScanMetrics, caminho: str) -> None:
    sys.stdout.write(
        f"\r{metrics.vistos} vistos | {metrics.indexados} indexados | "
        f"{metrics.pulados} pulados | {metrics.erros} erros | "
        f"{metrics.arquivos_por_segundo:.1f} arq/s   "
    )
    sys.stdout.flush()


def listar_fontes(caminho_backup: Path) -> int:
    """Lê a tabela `sources` do catálogo de BACKUP, somente leitura — nunca
    abre nem toca no catálogo ativo."""
    if not caminho_backup.exists():
        print(f"Backup não encontrado: {caminho_backup}")
        return 1

    # sqlite3 puro (não SQLAlchemy/upgrade_to_head): o backup é um artefato
    # congelado no schema de antes do reset; rodar migração nele mudaria um
    # arquivo que deve permanecer intocado.
    uri = f"file:{caminho_backup}?mode=ro"
    con = sqlite3.connect(uri, uri=True)
    try:
        cur = con.execute(
            "SELECT id, caminho, tipo, disponivel FROM sources ORDER BY id"
        )
        linhas = cur.fetchall()
    finally:
        con.close()

    if not linhas:
        print("Nenhuma fonte encontrada no backup.")
        return 0

    print(f"Fontes em {caminho_backup} ({len(linhas)}):\n")
    for id_, caminho, tipo, disponivel in linhas:
        existe_agora = Path(caminho).expanduser().exists()
        nota = (
            "importador, fora da medida de varredura"
            if tipo in _TIPOS_IMPORTADOR
            else ("existe agora" if existe_agora else "caminho ausente agora")
        )
        print(
            f"  [{id_:>3}] tipo={tipo:<14} disponivel(backup)={bool(disponivel)!s:<5} "
            f"{caminho}"
        )
        print(f"        {nota}")
    return 0


@dataclass
class ResultadoPasta:
    caminho: str
    indexados: int = 0
    pulados: int = 0
    erros: int = 0
    bytes_processados: int = 0
    segundos: float = 0.0
    indisponivel: bool = False


@dataclass
class ResultadoMedicao:
    db_path: str = ""
    pastas: list[ResultadoPasta] = field(default_factory=list)
    total_media_files: int = 0
    sugestoes: dict | None = None
    sugestoes_segundos: float = 0.0
    duplicatas: dict | None = None
    duplicatas_segundos: float = 0.0
    copia_descartavel: str = ""


def _resumir_markdown(r: ResultadoMedicao) -> str:
    linhas = []
    linhas.append(f"Catálogo medido: `{r.db_path}`")
    linhas.append(f"Total de registros em `media_files`: {r.total_media_files}")
    linhas.append("")

    if r.pastas:
        linhas.append("### Taxa de indexação (varredura)")
        linhas.append("")
        linhas.append(
            "| Pasta | Indexados | Pulados | Erros | MB | Segundos | arq/s |"
        )
        linhas.append("|---|---:|---:|---:|---:|---:|---:|")
        total_idx = total_pul = total_err = 0
        total_bytes = 0
        total_seg = 0.0
        for p in r.pastas:
            if p.indisponivel:
                linhas.append(f"| {p.caminho} | indisponível — pulada | | | | | |")
                continue
            arqs = p.indexados / p.segundos if p.segundos > 0 else 0.0
            linhas.append(
                f"| {p.caminho} | {p.indexados} | {p.pulados} | {p.erros} | "
                f"{p.bytes_processados / 1e6:.1f} | {p.segundos:.2f} | {arqs:.0f} |"
            )
            total_idx += p.indexados
            total_pul += p.pulados
            total_err += p.erros
            total_bytes += p.bytes_processados
            total_seg += p.segundos
        arqs_total = total_idx / total_seg if total_seg > 0 else 0.0
        linhas.append(
            f"| **total** | {total_idx} | {total_pul} | {total_err} | "
            f"{total_bytes / 1e6:.1f} | {total_seg:.2f} | {arqs_total:.0f} |"
        )
        linhas.append("")

    if r.sugestoes is not None:
        linhas.append("### Tempo de geração de sugestões")
        linhas.append("")
        linhas.append(f"Tempo total: {r.sugestoes_segundos:.2f}s")
        linhas.append(f"Resultado de `gerar()`: {r.sugestoes}")
        linhas.append("")

    if r.duplicatas is not None:
        linhas.append("### Tempo de detecção de duplicatas")
        linhas.append("")
        linhas.append(f"Tempo total: {r.duplicatas_segundos:.2f}s")
        linhas.append(f"Resultado de `detectar()`: {r.duplicatas}")
        linhas.append("")

    if r.copia_descartavel:
        linhas.append(f"Cópia descartável usada para sugestões/duplicatas (P-2, "
                       f"mantida): `{r.copia_descartavel}`")
        linhas.append("")

    linhas.append("advisor: None (P-3, 100% local)")
    return "\n".join(linhas)


def _montar_settings(args: argparse.Namespace) -> Settings:
    settings = load_settings()
    overrides: dict = {}
    derivados: dict = {}
    if args.data_dir:
        overrides["geral"] = {"data_dir": args.data_dir}
        # Mesma dedução de `_overrides_de_cli_e_env` do cli.py: `--data-dir`
        # sozinho também isola o cache, senão o catálogo fica isolado mas os
        # thumbnails caem no cache real do usuário.
        derivados["geral"] = {
            "cache_dir": str(Path(args.data_dir).expanduser() / "cache")
        }
    return aplicar_overrides(settings, overrides, derivados or None)


def _varrer_pastas(
    settings: Settings, pastas: list[str]
) -> tuple[list[ResultadoPasta], ScanMetrics | None]:
    upgrade_to_head(settings.db_path)
    engine = create_db_engine(settings.db_path)
    factory = create_session_factory(engine)
    scanner = CatalogScanner(
        factory,
        criar_extrator(),
        settings.scanner,
        thumb_cache=ThumbnailCache(settings.cache_dir),
    )

    resultados: list[ResultadoPasta] = []
    for pasta in pastas:
        caminho = Path(pasta).expanduser()
        if not caminho.is_dir():
            print(f"\nAVISO: pasta indisponível, pulando: {caminho}")
            resultados.append(ResultadoPasta(caminho=str(caminho), indisponivel=True))
            continue

        print(f"\nVarrendo {caminho} (catálogo real, in place — P-1)")
        inicio = time.monotonic()
        _, m = scanner.scan_source(caminho, progress=_print_progress)
        segundos = time.monotonic() - inicio
        print()
        resultados.append(
            ResultadoPasta(
                caminho=str(caminho),
                indexados=m.indexados,
                pulados=m.pulados,
                erros=m.erros,
                bytes_processados=m.bytes_processados,
                segundos=segundos,
            )
        )
    engine.dispose()
    return resultados, None


def _copiar_catalogo_descartavel(settings: Settings) -> Path:
    ts = time.strftime("%Y%m%d-%H%M%S")
    destino = settings.data_dir / f"baseline-{ts}.db"
    shutil.copy2(settings.db_path, destino)
    for sufixo in ("-wal", "-shm"):
        origem_extra = Path(str(settings.db_path) + sufixo)
        if origem_extra.exists():
            shutil.copy2(origem_extra, Path(str(destino) + sufixo))
    return destino


def _medir_sugestoes_e_duplicatas(
    copia_db: Path, cache_dir: Path
) -> tuple[dict, float, dict, float]:
    from fotoorganizer.classification import SuggestionEngine
    from fotoorganizer.classification.templates import TEMPLATE_PADRAO
    from fotoorganizer.duplicates import DuplicateDetector
    from fotoorganizer.geolocation import LocationResolver
    from fotoorganizer.geolocation.offline import OfflineGeocoder
    from fotoorganizer.repositories.lexico import LexicoRepository
    from fotoorganizer.repositories.settings import SettingsRepository

    upgrade_to_head(copia_db)
    engine = create_db_engine(copia_db)
    factory = create_session_factory(engine)

    template = SettingsRepository(factory).obter_template(TEMPLATE_PADRAO)
    lexico = LexicoRepository(factory).conhecidos()

    print("\nGerando sugestões (sobre a cópia descartável, P-2, advisor local)...")
    inicio = time.monotonic()
    engine_sug = SuggestionEngine(
        factory,
        LocationResolver(OfflineGeocoder()),
        template=template,
        advisor=None,
        lexico=lexico,
    )
    resultado_sugestoes = engine_sug.gerar()
    segundos_sugestoes = time.monotonic() - inicio
    print(f"  {segundos_sugestoes:.2f}s — {resultado_sugestoes}")

    print("\nDetectando duplicatas (sobre a cópia descartável, P-2)...")
    inicio = time.monotonic()
    detector = DuplicateDetector(factory, ThumbnailCache(cache_dir))
    resultado_duplicatas = detector.detectar(progress=lambda etapa: print(f"  {etapa}"))
    segundos_duplicatas = time.monotonic() - inicio
    print(f"  {segundos_duplicatas:.2f}s — {resultado_duplicatas}")

    engine.dispose()
    return (
        resultado_sugestoes,
        segundos_sugestoes,
        resultado_duplicatas,
        segundos_duplicatas,
    )


def _contar_media_files(db_path: Path) -> int:
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        (n,) = con.execute("SELECT count(*) FROM media_files").fetchone()
    finally:
        con.close()
    return n


def medir(args: argparse.Namespace) -> int:
    settings = _montar_settings(args)
    settings.ensure_dirs()
    resultado = ResultadoMedicao(db_path=str(settings.db_path))

    try:
        if not args.pular_varredura and args.pasta:
            resultado.pastas, _ = _varrer_pastas(settings, args.pasta)
    except KeyboardInterrupt:
        print("\n\nInterrompido pelo usuário — imprimindo o que já foi medido:\n")
        print(_resumir_markdown(resultado))
        return 130

    if not settings.db_path.exists():
        print(f"Catálogo inexistente em {settings.db_path}; nada a medir.")
        return 1

    resultado.total_media_files = _contar_media_files(settings.db_path)

    try:
        copia_db = _copiar_catalogo_descartavel(settings)
        resultado.copia_descartavel = str(copia_db)
        (
            resultado.sugestoes,
            resultado.sugestoes_segundos,
            resultado.duplicatas,
            resultado.duplicatas_segundos,
        ) = _medir_sugestoes_e_duplicatas(copia_db, settings.cache_dir)
    except KeyboardInterrupt:
        print("\n\nInterrompido pelo usuário — imprimindo o que já foi medido:\n")
        print(_resumir_markdown(resultado))
        return 130

    bloco = _resumir_markdown(resultado)
    print("\n" + "=" * 72)
    print(bloco)

    if args.saida:
        Path(args.saida).write_text(bloco, encoding="utf-8")
        print(f"\nBloco gravado em {args.saida}")

    return 0


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Baseline de performance de LANC-04 contra o acervo real."
    )
    p.add_argument(
        "--listar-fontes",
        nargs="?",
        const=str(BACKUP_PADRAO),
        default=None,
        metavar="CAMINHO_DO_BACKUP",
        help="Lista a tabela `sources` do catálogo de BACKUP (somente leitura, "
        "não toca no catálogo ativo).",
    )
    p.add_argument(
        "--pasta",
        action="append",
        default=[],
        help="Raiz a varrer (repetível, ordem preservada).",
    )
    p.add_argument(
        "--data-dir",
        default=None,
        help="Sobrepõe o data_dir das settings; sem isto usa o real de produção.",
    )
    p.add_argument(
        "--pular-varredura",
        action="store_true",
        help="Mede só sugestões e duplicatas sobre o catálogo já existente.",
    )
    p.add_argument(
        "--saida",
        default=None,
        help="Onde gravar o bloco markdown (default: só imprime no stdout).",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)

    if args.listar_fontes is not None:
        return listar_fontes(Path(args.listar_fontes).expanduser())

    if not args.pular_varredura and not args.pasta:
        print("Nada a medir: passe --pasta (uma ou mais) ou --pular-varredura.")
        return 1

    return medir(args)


if __name__ == "__main__":
    # Ctrl-C durante uma medição longa deve imprimir o parcial, não um
    # traceback — o handler default do Python já levanta KeyboardInterrupt,
    # que os blocos try/except em `medir()` capturam; isto só documenta a
    # intenção (SIGINT é o default do Python, nada a instalar aqui).
    signal.signal(signal.SIGINT, signal.default_int_handler)
    sys.exit(main())
