"""CLI interna: varredura headless, operações e benchmark de indexação.

Uso:
    python -m fotoorganizer scan <pasta> [<pasta>...]
    python -m fotoorganizer web [--porta N]
    python -m fotoorganizer planos
    python -m fotoorganizer plano <raiz-destino> [--nome N]
    python -m fotoorganizer dry-run <plano-id>
    python -m fotoorganizer executar <plano-id> --confirmar
    python -m fotoorganizer verificar-arquivos [--segundos N]
    python -m fotoorganizer bench [-n QUANTIDADE]

`executar` exige `--confirmar` porque é a única operação que escreve fora
do catálogo: sem a UI para aprovar, a flag é a aprovação explícita que o
invariante 2 do CLAUDE.md pede.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import tempfile
import time
from pathlib import Path

from fotoorganizer.config import UNSET, aplicar_overrides, load_settings

# Prefixo das env vars que espelham os flags globais abaixo — mesma
# terceira camada de precedência que os flags, então convivem sem conflito:
# se os dois forem passados na mesma invocação, o flag de CLI vence, porque
# é ainda mais explícito que a env var (decisão local a este módulo, não do
# `aplicar_overrides()`, que só recebe o resultado já resolvido).
_ENV_PREFIX = "FOTOORG_"

_ENV_BOOL_VERDADEIRO = ("1", "true", "verdadeiro", "sim", "yes", "on")
_ENV_BOOL_FALSO = ("0", "false", "falso", "nao", "não", "no", "off")


class ErroDeUso(Exception):
    """Erro de uso vindo de env var — sai pelo mesmo caminho do argparse.

    `main()` converte isto em `parser.error()`, então uma env var inválida
    produz exatamente a saída que o flag equivalente já produzia (usage +
    mensagem no stderr, código 2) em vez de um traceback cru.
    """


def _env_bruta(nome: str) -> str | None:
    """Valor da env var já normalizado, ou `None` quando ela não conta.

    Variável ausente e variável exportada vazia (`FOTOORG_DATA_DIR=`) são a
    mesma coisa aqui: nenhuma das duas é o usuário pedindo algo. Tratar `""`
    como valor explícito fazia `data_dir` virar `Path('.')` — um `scan`
    criava catálogo, cache e logs novos no diretório corrente do shell e
    indexava ali, enquanto o catálogo real ficava intacto e simplesmente
    não aparecia.
    """
    valor = os.environ.get(f"{_ENV_PREFIX}{nome}")
    if valor is None:
        return None
    return valor.strip() or None


def _bool_env(nome: str):
    valor = _env_bruta(nome)
    if valor is None:
        return UNSET
    normalizado = valor.lower()
    if normalizado in _ENV_BOOL_VERDADEIRO:
        return True
    if normalizado in _ENV_BOOL_FALSO:
        return False
    # Não adivinhar: um valor irreconhecível virando `False` em silêncio
    # vencia um `true` do TOML sem o usuário saber por quê.
    raise ErroDeUso(
        f"argument {_ENV_PREFIX}{nome}: invalid bool value: {valor!r} "
        f"(use {'/'.join(_ENV_BOOL_VERDADEIRO)} ou "
        f"{'/'.join(_ENV_BOOL_FALSO)})"
    )


def _valor_env(nome: str, tipo):
    valor = _env_bruta(nome)
    if valor is None:
        return UNSET
    try:
        return tipo(valor)
    except (TypeError, ValueError) as exc:
        raise ErroDeUso(
            f"argument {_ENV_PREFIX}{nome}: invalid {tipo.__name__} "
            f"value: {valor!r}"
        ) from exc


def _overrides_de_cli_e_env(
    args: argparse.Namespace | None,
) -> tuple[dict, dict]:
    """Monta os dicts de config (formato de seções do TOML) a partir dos
    flags globais explicitamente passados nesta invocação, com fallback
    para a env var equivalente quando o flag não veio. Campos não tocados
    por nenhuma das duas fontes simplesmente não entram no dict — é isso
    que faz `aplicar_overrides()` deixá-los no valor herdado (TOML/default).

    Devolve `(overrides, derivados)`: o primeiro é o que o usuário pediu
    de verdade e vence o TOML; o segundo é o que a CLI *deduziu* de outro
    flag e por isso tem precedência abaixo do TOML. Ver `aplicar_overrides()`.
    """

    def escolhido(campo: str, env_nome: str, tipo):
        do_cli = getattr(args, campo, UNSET)
        if do_cli is not UNSET:
            return do_cli
        return _bool_env(env_nome) if tipo is bool else _valor_env(env_nome, tipo)

    geral: dict = {}
    scanner: dict = {}
    privacidade: dict = {}
    derivados: dict = {}

    data_dir = escolhido("data_dir", "DATA_DIR", str)
    cache_dir = escolhido("cache_dir", "CACHE_DIR", str)
    if data_dir is not UNSET:
        geral["data_dir"] = data_dir
        # `--data-dir`/`FOTOORG_DATA_DIR` sozinho também isola o cache,
        # senão a varredura fica com o catálogo em `data_dir` mas os
        # thumbnails caindo no cache real do usuário — comportamento
        # herdado de antes desta camada existir. Isto é *dedução*, não
        # pedido: vai no dict de derivados, que perde para um `cache_dir`
        # escrito no TOML e para `--cache-dir`/`FOTOORG_CACHE_DIR`.
        derivados["cache_dir"] = str(Path(data_dir).expanduser() / "cache")
    if cache_dir is not UNSET:
        geral["cache_dir"] = cache_dir

    workers = escolhido("workers", "WORKERS", int)
    if workers is not UNSET:
        scanner["workers"] = workers
    incluir_ocultos = escolhido("incluir_ocultos", "INCLUIR_OCULTOS", bool)
    if incluir_ocultos is not UNSET:
        scanner["incluir_ocultos"] = incluir_ocultos
    seguir_symlinks = escolhido("seguir_symlinks", "SEGUIR_SYMLINKS", bool)
    if seguir_symlinks is not UNSET:
        scanner["seguir_symlinks"] = seguir_symlinks

    servicos_externos = escolhido("servicos_externos", "SERVICOS_EXTERNOS", bool)
    if servicos_externos is not UNSET:
        privacidade["servicos_externos"] = servicos_externos

    overrides = {}
    if geral:
        overrides["geral"] = geral
    if scanner:
        overrides["scanner"] = scanner
    if privacidade:
        overrides["privacidade"] = privacidade
    return overrides, ({"geral": derivados} if derivados else {})


def _settings(args: argparse.Namespace | None = None):
    """Config nas camadas: defaults < derivado < TOML < CLI/env desta
    invocação.

    `--data-dir` (ou `FOTOORG_DATA_DIR`) é o caso mais usado — sobrepor o
    catálogo padrão sem editar a config real do usuário, essencial para
    testar ou diagnosticar sem tocar no catálogo de produção.
    """
    settings = load_settings()
    overrides, derivados = _overrides_de_cli_e_env(args)
    return aplicar_overrides(settings, overrides, derivados)


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


def _build_scanner(db_path: Path, settings):
    """`settings` é obrigatório de propósito: enquanto era opcional e caía
    num `load_settings()` interno, quem esquecesse de passá-lo rodava só com
    defaults+TOML, pulando a camada de CLI/env sem nenhum sinal — foi assim
    que `bench` passou a ignorar `--workers`."""
    from fotoorganizer.database import (
        create_db_engine,
        create_session_factory,
        upgrade_to_head,
    )
    from fotoorganizer.metadata import criar_extrator
    from fotoorganizer.scanner import CatalogScanner
    from fotoorganizer.thumbnails import ThumbnailCache

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
                  "com →. `fotoorganizer reapontar <fonte>` mostra o "
                  "dry-run; com --confirmar, reescreve o catálogo.")
    return 0


def cmd_reapontar(args: argparse.Namespace) -> int:
    """Reaponta uma fonte que remontou noutro ponto — reescreve o catálogo
    (`Source.caminho` + `MediaFile.caminho`), nunca toca em arquivo.

    Sem `--confirmar`, só mostra o dry-run (padrão de `cmd_dry_run`); com
    `--confirmar`, valida uma amostra dos caminhos novos no disco e escreve
    numa transação só, tudo ou nada. `--desfazer <audit_log_id>` reverte um
    reapontamento anterior lendo a entrada de auditoria que ele criou.
    """
    from fotoorganizer.sources.disponibilidade import verificar
    from fotoorganizer.sources.reapontar import (
        ColisaoDeCaminho,
        ReapontamentoInaplicavel,
        ValidacaoFalhou,
        aplicar,
        desfazer_por_auditoria,
        prefixos_do_estado,
        previa,
        resolver_fonte,
    )

    _, factory = _abrir_catalogo(args)

    if args.desfazer is not None:
        try:
            r = desfazer_por_auditoria(factory, args.desfazer)
        except (ReapontamentoInaplicavel, ValidacaoFalhou,
                 ColisaoDeCaminho) as exc:
            print(exc)
            return 1
        print(f"Desfeito a partir do audit_log {args.desfazer}: "
              f"{r.prefixo_antigo} → {r.prefixo_novo} "
              f"({r.linhas_media_files} linha(s), novo audit_log "
              f"{r.audit_log_id}).")
        return 0

    if not args.fonte:
        print("Informe a fonte (id ou apelido), ou --desfazer <audit_log_id>.")
        return 1

    try:
        source_id = resolver_fonte(factory, args.fonte)
    except ReapontamentoInaplicavel as exc:
        print(exc)
        return 1

    estado = next(
        (e for e in verificar(factory) if e.source_id == source_id), None
    )
    if estado is None:
        print(f"fonte não encontrada: {args.fonte}")
        return 1

    try:
        prefixo_antigo, prefixo_novo = prefixos_do_estado(estado)
    except ReapontamentoInaplicavel as exc:
        print(exc)
        return 1

    p = previa(factory, source_id, prefixo_antigo, prefixo_novo)
    print(f"Fonte {p.apelido!r}:")
    print(f"  {p.prefixo_antigo}")
    print(f"  → {p.prefixo_novo}")
    print(f"{p.total_media_files} arquivo(s) de mídia seriam reapontados.")
    if p.total_ignoradas_sem_prefixo:
        print(f"{p.total_ignoradas_sem_prefixo} referência(s) sem esse "
              "prefixo (ex.: apple://…, lightroom://…) ficam intocadas.")
    for antigo, novo in p.amostra:
        print(f"  {antigo}\n    → {novo}")

    if not args.confirmar:
        print("\nDry-run só. Repita com --confirmar para escrever no "
              "catálogo (nenhum arquivo no disco é tocado).")
        return 0

    try:
        r = aplicar(factory, source_id, prefixo_antigo, prefixo_novo)
    except (ValidacaoFalhou, ColisaoDeCaminho) as exc:
        print(f"\n{exc}")
        return 1
    print(f"\n{r.linhas_media_files} linha(s) reapontada(s) "
          f"(audit_log {r.audit_log_id} — use --desfazer {r.audit_log_id} "
          "para reverter).")
    return 0


def cmd_verificar_arquivos(args: argparse.Namespace) -> int:
    """Uma passada da reconciliação de alcance (fase 12, item B): confere se
    arquivos já catalogados ainda existem no disco, sem reler metadado nem
    recalcular hash — barato o bastante para rodar sem esperar por um scan
    completo. Auto-limitada por tempo/percentual; retoma da próxima chamada
    de onde esta parou (checkpoint em `application_settings`, não em
    `ScanSession` — não é um scan de pasta)."""
    from fotoorganizer.scanner.reconciliacao import reconciliar

    _, factory = _abrir_catalogo(args)
    kwargs = {}
    if args.segundos is not None:
        kwargs["orcamento_segundos"] = args.segundos
    resultado = reconciliar(factory, **kwargs)
    print(f"{resultado.verificados} verificado(s) nesta passada: "
          f"{resultado.marcados_offline} ficaram offline, "
          f"{resultado.marcados_online} voltaram online.")
    print(
        "Ciclo completo — a próxima passada recomeça do início."
        if resultado.ciclo_concluido else
        "Orçamento consumido — a próxima passada retoma daqui."
    )
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
    """Benchmark com arquivos sintéticos: indexação a frio e re-scan.

    Sem ``--cache-dir``, as miniaturas sintéticas vão para um diretório
    temporário — nunca para o cache real do usuário (mesmo padrão do
    ``bench.db``, que também não toca no catálogo real).
    """
    from dataclasses import replace

    with tempfile.TemporaryDirectory(prefix="fotobench-") as tmp:
        tmp_path = Path(tmp)
        fotos = tmp_path / "fotos"
        fotos.mkdir()
        print(f"Gerando {args.quantidade} JPEGs sintéticos...")
        for i in range(args.quantidade):
            sub = fotos / f"pasta_{i % 10:02d}"
            sub.mkdir(exist_ok=True)
            _jpeg_sintetico(sub / f"img_{i:05d}.jpg", seed=i)

        # Pelo mesmo caminho de config dos outros comandos: sem isto,
        # `fotoorganizer --workers 16 bench` media o `workers` do TOML/default,
        # não o que foi pedido — um benchmark que ignora o parâmetro que se
        # quer medir.
        cache_dir = (
            Path(args.bench_cache_dir).expanduser() if args.bench_cache_dir
            else tmp_path / "cache"
        )
        # O DB continua no temporário, nunca no de produção; o cache segue
        # a mesma regra, isolado por padrão (mesmo cuidado do bench.db) —
        # `--cache-dir` do bench é opt-in explícito pra medir contra o
        # cache real de propósito.
        settings = replace(_settings(args), cache_dir=cache_dir)
        scanner = _build_scanner(tmp_path / "bench.db", settings)

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
    """Servidor local da UI web — escuta apenas em 127.0.0.1.

    Com ``--porta 0`` o SO escolhe uma porta livre; a porta efetiva é
    anunciada no stdout como ``FOTOORG_READY http://127.0.0.1:<porta>``
    assim que o socket está ligado, para um supervisor (ex.: o shell
    Tauri) saber onde abrir a janela sem depender de porta fixa. O
    ``uvicorn.Server`` instala handlers de SIGINT/SIGTERM, então o
    processo encerra limpo (checkpoint WAL, lifespan) quando o app pai
    o encerra.
    """
    import socket

    import uvicorn

    from fotoorganizer.database import (
        create_db_engine,
        create_session_factory,
        upgrade_to_head,
    )
    from fotoorganizer.server import create_app

    settings = _settings(args)
    settings.ensure_dirs()
    # Log estruturado em arquivo, não só stderr: o servidor costuma morrer
    # junto com o terminal que o abriu, e sem isto a morte não deixa rastro
    # nenhum — dois scans do acervo real (93 mil e 225 mil arquivos)
    # morreram sem uma linha de log que dissesse por quê.
    from fotoorganizer.app.logsetup import setup_logging

    setup_logging(settings.log_dir)
    upgrade_to_head(settings.db_path)
    factory = create_session_factory(create_db_engine(settings.db_path))
    app = create_app(settings, factory)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", args.porta))
    porta = sock.getsockname()[1]
    url = f"http://127.0.0.1:{porta}"

    print(f"Foto Organizer web em {url} (catálogo: {settings.db_path})")
    # Linha estável para o supervisor descobrir a porta (inclusive efêmera).
    print(f"FOTOORG_READY {url}", flush=True)

    # Encerra junto com o pai (shell Tauri): se o app fechar de qualquer
    # forma — inclusive um sinal que não passa pelo handler dele —, o
    # processo é reparentado (ppid muda) e mandamos SIGTERM em nós mesmos,
    # deixando o uvicorn drenar e fazer o checkpoint WAL. Sem órfão.
    if getattr(args, "encerrar_com_pai", False):
        import os
        import signal
        import threading

        pai = os.getppid()

        def _vigia_pai() -> None:
            while True:
                time.sleep(2)
                if os.getppid() != pai:
                    os.kill(os.getpid(), signal.SIGTERM)
                    return

        threading.Thread(target=_vigia_pai, daemon=True).start()

    server = uvicorn.Server(uvicorn.Config(app, log_level="warning"))
    server.run(sockets=[sock])
    return 0


def _build_parser() -> argparse.ArgumentParser:
    """Fatorado de `main()` para os testes poderem exercitar o parser real
    (flags globais + subcomandos) sem rodar o comando inteiro — é o que
    permite testar a camada de overrides de CLI/env com um Namespace
    genuíno, em vez de um `argparse.Namespace(...)` montado à mão."""
    parser = argparse.ArgumentParser(prog="fotoorganizer")
    # Flags globais: terceira camada de precedência sobre `Settings`
    # (defaults < TOML < aqui). `default=UNSET` é o que permite distinguir
    # "flag não passado" de "passado com valor vazio/zero/false" — sem
    # isto, `--workers 0` ou `--no-seguir-symlinks` seriam indistinguíveis
    # de omitir o flag. Ver `fotoorganizer/config/settings.py`.
    parser.add_argument(
        "--data-dir", metavar="PASTA", default=UNSET,
        help="usa outro catálogo em vez do padrão (~/Library/Application "
             "Support/FotoOrganizer) — para testar ou isolar um problema "
             "sem tocar no catálogo real (env: FOTOORG_DATA_DIR)",
    )
    parser.add_argument(
        "--cache-dir", metavar="PASTA", default=UNSET,
        help="usa outro cache de thumbnails em vez do padrão "
             "(env: FOTOORG_CACHE_DIR)",
    )
    parser.add_argument(
        "--workers", type=int, default=UNSET,
        help="workers paralelos do scanner (env: FOTOORG_WORKERS)",
    )
    parser.add_argument(
        "--incluir-ocultos", action=argparse.BooleanOptionalAction, default=UNSET,
        help="varre arquivos/pastas ocultos (env: FOTOORG_INCLUIR_OCULTOS)",
    )
    parser.add_argument(
        "--seguir-symlinks", action=argparse.BooleanOptionalAction, default=UNSET,
        help="atravessa symlinks durante a varredura — desligado por padrão "
             "(env: FOTOORG_SEGUIR_SYMLINKS)",
    )
    parser.add_argument(
        "--servicos-externos", action=argparse.BooleanOptionalAction, default=UNSET,
        help="permite serviços externos opt-in (env: FOTOORG_SERVICOS_EXTERNOS)",
    )
    # `privacidade.reconhecimento_facial` fica de fora desta camada de
    # propósito: é o único campo que continua só em defaults + TOML. Ligar
    # reconhecimento facial (invariante 6) tem de ser uma decisão escrita na
    # config do usuário, não algo que um script de CI, um alias de shell ou
    # uma env var herdada do ambiente consigam ligar de passagem. Se um dia
    # ganhar superfície de CLI, que seja com confirmação explícita.
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
    p_web.add_argument(
        "--encerrar-com-pai", action="store_true",
        help="encerra o servidor se o processo pai morrer (o shell Tauri "
             "passa isto para nunca deixar o backend órfão)",
    )
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

    p_reap = sub.add_parser(
        "reapontar",
        help="reescreve o catálogo para onde um volume remontado voltou "
             "(nunca toca em arquivo)",
    )
    p_reap.add_argument(
        "fonte", nargs="?",
        help="id numérico ou apelido da fonte (omitir com --desfazer)",
    )
    p_reap.add_argument(
        "--confirmar", action="store_true",
        help="aprovação explícita — sem ela só mostra o dry-run",
    )
    p_reap.add_argument(
        "--desfazer", type=int, metavar="AUDIT_LOG_ID",
        help="desfaz um reapontamento anterior, lendo os prefixos da "
             "entrada de auditoria que ele criou (reaponta com eles "
             "trocados) — recuperação, não fluxo normal",
    )
    p_reap.set_defaults(func=cmd_reapontar)

    p_verif = sub.add_parser(
        "verificar-arquivos",
        help="confere se arquivos catalogados ainda existem no disco "
             "(uma passada, auto-limitada — read-only)",
    )
    p_verif.add_argument(
        "--segundos", type=float, default=None,
        help="orçamento de tempo desta passada (padrão: interno do módulo)",
    )
    p_verif.set_defaults(func=cmd_verificar_arquivos)

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
    p_bench.add_argument(
        "--cache-dir", dest="bench_cache_dir", metavar="PASTA",
        help="grava as miniaturas do benchmark aqui em vez de um diretório "
             "temporário — para medir com o cache real do usuário de "
             "propósito. `dest` próprio (não `cache_dir`) para não colidir "
             "com o `--cache-dir` global, que é outra coisa: aquele troca o "
             "cache de produção da invocação inteira; este só isola (ou "
             "não) as miniaturas sintéticas do benchmark.",
    )
    p_bench.set_defaults(func=cmd_bench)

    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.WARNING)
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except ErroDeUso as exc:
        # `parser.error()` levanta SystemExit(2) depois de imprimir usage +
        # mensagem no stderr: env var inválida sai igualzinho ao flag
        # equivalente inválido, em vez de traceback.
        parser.error(str(exc))
