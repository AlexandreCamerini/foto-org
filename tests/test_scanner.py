import os
import threading
import time
from pathlib import Path

import pytest
from sqlalchemy import select

from fotoorganizer.config.settings import ScannerSettings
from fotoorganizer.database import create_session_factory
from fotoorganizer.metadata import PurePythonExtractor
from fotoorganizer.models import MediaFile, MediaRole, ScanStatus, Source
from fotoorganizer.scanner import CatalogScanner, ScanControl
from tests.fixtures import make_corrupt_jpeg, make_jpeg, make_png


class CountingExtractor(PurePythonExtractor):
    """Conta quantos arquivos foram realmente lidos (prova do incremental).
    Com lock: a extração roda em threads do pool do scanner."""

    def __init__(self):
        self._lock = threading.Lock()
        self.chamadas = 0

    def extract(self, path):
        with self._lock:
            self.chamadas += 1
        return super().extract(path)


@pytest.fixture()
def scanner_env(migrated_engine):
    factory = create_session_factory(migrated_engine)
    extractor = CountingExtractor()
    scanner = CatalogScanner(factory, extractor, ScannerSettings())
    return scanner, extractor, factory


def _make_library(root, n=5):
    for i in range(n):
        make_jpeg(root / f"pasta_{i % 2}" / f"img_{i:03d}.jpg", seed=i)


def test_scan_indexa_tudo(scanner_env, tmp_path):
    scanner, extractor, factory = scanner_env
    _make_library(tmp_path, n=5)
    make_png(tmp_path / "extra.png")

    scan, metrics = scanner.scan_source(tmp_path)

    assert scan.status == ScanStatus.CONCLUIDO
    assert metrics.indexados == 6
    assert metrics.erros == 0
    with factory() as session:
        arquivos = session.scalars(select(MediaFile)).all()
        assert len(arquivos) == 6
        jpg = next(a for a in arquivos if a.nome == "img_000.jpg")
        assert jpg.data_capturada is not None
        assert jpg.hash_rapido and jpg.hash_rapido.startswith("xxh3:")
        assert jpg.make == "TestMake"


def test_scan_iguala_os_dois_instantes_quando_o_exif_nao_traz_fuso(
    scanner_env, tmp_path
):
    """O caso comum de todo scan hoje: o EXIF dá a hora de parede e não dá o
    fuso. A hora local e o instante absoluto saem iguais — e a igualdade é
    como este catálogo diz "não sei o fuso desta foto", nunca "foi tirada em
    UTC". Nenhuma linha nova fica com hora local e absoluto nulo."""
    scanner, _extractor, factory = scanner_env
    _make_library(tmp_path, n=5)
    make_jpeg(tmp_path / "img.jpg", data_exif="2019:07:14 14:00:00")

    scanner.scan_source(tmp_path)

    with factory() as session:
        media = session.scalars(select(MediaFile).where(
            MediaFile.nome == "img.jpg"
        )).one()
        assert media.data_capturada is not None
        assert media.data_capturada_utc == media.data_capturada
        # O invariante, sobre a passada inteira: hora local preenchida e
        # instante absoluto nulo diria "não sei quando", que é outra coisa —
        # e bem pior — do que "não sei o fuso".
        tortas = session.scalars(select(MediaFile).where(
            MediaFile.data_capturada.is_not(None),
            MediaFile.data_capturada_utc.is_(None),
        )).all()
        assert tortas == []


def test_scan_respeita_o_fuso_quando_o_extrator_souber_ler(
    migrated_engine, tmp_path
):
    """O gancho da fase 11: no dia em que o extrator ler `OffsetTimeOriginal`,
    `MediaMetadata.data_capturada_utc` chega preenchido e a coluna absoluta
    para de ser cópia da local. Nenhum extrator faz isso hoje — o teste guarda
    o contrato para que a fase 11 não precise descobri-lo de novo."""
    from datetime import datetime, timedelta

    class ExtratorComFuso(PurePythonExtractor):
        def extract(self, path):
            meta = super().extract(path)
            if meta.data_capturada is not None:
                meta.data_capturada_utc = (
                    meta.data_capturada - timedelta(hours=2)  # foto em Roma
                )
            return meta

    factory = create_session_factory(migrated_engine)
    scanner = CatalogScanner(factory, ExtratorComFuso(), ScannerSettings())
    make_jpeg(tmp_path / "roma.jpg", data_exif="2019:07:14 14:00:00")

    scanner.scan_source(tmp_path)

    with factory() as session:
        media = session.scalars(select(MediaFile)).one()
        assert media.data_capturada == datetime(2019, 7, 14, 14, 0)
        assert media.data_capturada_utc == datetime(2019, 7, 14, 12, 0)


def test_scan_nao_grava_instante_absoluto_sem_hora_de_parede(
    migrated_engine, tmp_path
):
    """A mesma guarda que `sources/importer.py` já tem, no ponto de extensão
    criado para a fase 11: um `.mov` cujo `QuickTime:CreateDate` venha só em
    UTC não pode virar linha que sabe quando a foto foi tirada sem saber que
    horas eram."""
    from datetime import datetime

    class ExtratorSoComUTC(PurePythonExtractor):
        def extract(self, path):
            meta = super().extract(path)
            meta.data_capturada = None
            meta.data_capturada_utc = datetime(2019, 7, 14, 12, 0)
            return meta

    factory = create_session_factory(migrated_engine)
    scanner = CatalogScanner(factory, ExtratorSoComUTC(), ScannerSettings())
    make_jpeg(tmp_path / "so_utc.jpg", data_exif="2019:07:14 14:00:00")

    scanner.scan_source(tmp_path)

    with factory() as session:
        media = session.scalars(select(MediaFile)).one()
        assert media.data_capturada is None
        assert media.data_capturada_utc is None


def test_segunda_passada_nao_rele_inalterados(scanner_env, tmp_path):
    scanner, extractor, factory = scanner_env
    _make_library(tmp_path, n=5)

    scanner.scan_source(tmp_path)
    assert extractor.chamadas == 5

    _, metrics = scanner.scan_source(tmp_path)
    assert extractor.chamadas == 5  # nenhum arquivo relido
    assert metrics.pulados == 5
    assert metrics.indexados == 0


def test_arquivo_modificado_e_relido(scanner_env, tmp_path):
    scanner, extractor, factory = scanner_env
    alvo = make_jpeg(tmp_path / "foto.jpg", seed=1)
    scanner.scan_source(tmp_path)

    time.sleep(0.01)
    make_jpeg(alvo, seed=2, size=(128, 96))  # conteúdo e tamanho novos
    os.utime(alvo, (time.time(), time.time()))

    _, metrics = scanner.scan_source(tmp_path)
    assert metrics.indexados == 1
    with factory() as session:
        arquivos = session.scalars(select(MediaFile)).all()
        assert len(arquivos) == 1  # atualizado, não duplicado
        assert arquivos[0].largura == 128


def test_corrompido_nao_interrompe_scan(scanner_env, tmp_path):
    scanner, extractor, factory = scanner_env
    make_jpeg(tmp_path / "boa.jpg")
    make_corrupt_jpeg(tmp_path / "ruim.jpg")

    scan, metrics = scanner.scan_source(tmp_path)

    assert scan.status == ScanStatus.CONCLUIDO
    assert metrics.indexados == 2  # corrompida entra no catálogo com erro
    with factory() as session:
        ruim = session.scalar(
            select(MediaFile).where(MediaFile.nome == "ruim.jpg")
        )
        assert ruim is not None
        assert ruim.erro_leitura is not None
        boa = session.scalar(select(MediaFile).where(MediaFile.nome == "boa.jpg"))
        assert boa.erro_leitura is None


def test_extracao_que_excede_o_teto_vira_erro_e_o_scan_segue(
    migrated_engine, tmp_path, monkeypatch
):
    """Segundo cinto além do teto do exiftool: se QUALQUER extração passar
    do limite (filesystem de rede parado, lib presa), a foto vira erro de
    leitura em vez de congelar a fila inteira em RODANDO."""
    import fotoorganizer.scanner.scanner as mod
    monkeypatch.setattr(mod, "_EXTRACAO_TIMEOUT_S", 0.2)

    class ExtractorLento(PurePythonExtractor):
        def extract(self, path):
            if path.name == "presa.jpg":
                time.sleep(1.5)  # termina (o pool precisa poder fechar),
                # mas só bem depois do teto do teste
            return super().extract(path)

    factory = create_session_factory(migrated_engine)
    scanner = CatalogScanner(factory, ExtractorLento(), ScannerSettings())
    make_jpeg(tmp_path / "boa.jpg")
    make_jpeg(tmp_path / "presa.jpg", seed=2)

    scan, metrics = scanner.scan_source(tmp_path)

    assert scan.status == ScanStatus.CONCLUIDO
    assert metrics.erros == 1
    assert metrics.indexados == 1
    with factory() as session:
        boa = session.scalar(select(MediaFile).where(MediaFile.nome == "boa.jpg"))
        assert boa is not None and boa.erro_leitura is None


def test_cancelamento_e_retomada(scanner_env, tmp_path):
    scanner, extractor, factory = scanner_env
    _make_library(tmp_path, n=20)

    control = ScanControl()

    def cancela_no_meio(metrics, caminho):
        if metrics.vistos >= 7:
            control.cancelar()

    scan, metrics = scanner.scan_source(
        tmp_path, progress=cancela_no_meio, control=control
    )
    assert scan.status == ScanStatus.PAUSADO
    assert metrics.vistos < 20

    # Retomada: re-varre, pula o que já foi indexado e completa o resto.
    scan2, metrics2 = scanner.scan_source(tmp_path)
    assert scan2.status == ScanStatus.CONCLUIDO
    with factory() as session:
        assert len(session.scalars(select(MediaFile)).all()) == 20


def test_sessao_rodando_orfa_vira_interrompida_no_boot(scanner_env):
    """O processo morre (fechou o app, dormiu o Mac) e a sessão fica
    RODANDO para sempre no banco — foi o que aconteceu duas vezes no
    acervo real, com dias de diferença. No boot do servidor nenhum job
    pode estar rodando ainda: RODANDO ali é sempre órfã."""
    from fotoorganizer.models import ScanSession
    from fotoorganizer.scanner import reconciliar_orfas

    _, _, factory = scanner_env
    with factory() as session:
        fonte = Source(caminho="/tmp/fantasma")
        session.add(fonte)
        session.flush()
        session.add(ScanSession(source_id=fonte.id,
                                status=ScanStatus.RODANDO,
                                arquivos_vistos=93408))
        session.add(ScanSession(source_id=fonte.id,
                                status=ScanStatus.CONCLUIDO))
        session.commit()

    assert reconciliar_orfas(factory) == 1

    with factory() as session:
        sessoes = session.scalars(select(ScanSession)).all()
        por_status = {s.status for s in sessoes}
        assert ScanStatus.RODANDO not in por_status
        orfa = next(s for s in sessoes if s.arquivos_vistos == 93408)
        assert orfa.status == ScanStatus.INTERROMPIDO
        assert orfa.finalizado_em is not None


def test_fonte_indisponivel(scanner_env, tmp_path):
    scanner, extractor, factory = scanner_env
    scan, metrics = scanner.scan_source(tmp_path / "volume_desconectado")

    assert scan.status == ScanStatus.ERRO
    assert metrics.vistos == 0
    with factory() as session:
        source = session.scalars(select(Source)).one()
        assert source.disponivel is False


def test_scan_deixa_thumbnail_pronta_no_cache(migrated_engine, tmp_path):
    from fotoorganizer.thumbnails import ThumbnailCache

    fotos = tmp_path / "fotos"
    make_jpeg(fotos / "a.jpg", seed=1)
    cache = ThumbnailCache(tmp_path / "cache")
    factory = create_session_factory(migrated_engine)
    scanner = CatalogScanner(
        factory, PurePythonExtractor(), ScannerSettings(), thumb_cache=cache
    )

    scanner.scan_source(fotos)

    with factory() as session:
        media = session.scalars(select(MediaFile)).one()
    assert media.hash_rapido is not None
    assert cache.get(media.hash_rapido) is not None  # gerada durante o scan


def test_testemunha_nao_ganha_thumbnail(migrated_engine, tmp_path):
    """SINAL nunca aparece na grade, na revisão nem no plano — a miniatura
    dele no scan é custo puro. Medido no acervo real: 2 GB de cache e
    leitura integral de RAW pelo SMB para imagens que ninguém veria. A
    testemunha continua doando data/GPS/câmera (a extração roda), e o
    phash das duplicatas ainda pode lê-la sob demanda; só a thumb sai."""
    from fotoorganizer.thumbnails import ThumbnailCache

    fotos = tmp_path / "fotos"
    make_jpeg(fotos / "acervo.jpg", seed=1)
    make_jpeg(
        fotos / "Biblioteca.photoslibrary" / "resources" / "interna.jpg",
        seed=2,
    )
    cache = ThumbnailCache(tmp_path / "cache")
    factory = create_session_factory(migrated_engine)
    scanner = CatalogScanner(
        factory, PurePythonExtractor(), ScannerSettings(), thumb_cache=cache
    )

    scanner.scan_source(fotos)

    with factory() as session:
        arquivos = {m.nome: m for m in session.scalars(select(MediaFile))}
    acervo, interna = arquivos["acervo.jpg"], arquivos["interna.jpg"]
    assert cache.get(acervo.hash_rapido) is not None
    assert cache.get(interna.hash_rapido) is None      # nada gerado
    assert interna.data_capturada is not None          # o sinal continua doando


def test_fonte_reutilizada_entre_scans(scanner_env, tmp_path):
    scanner, extractor, factory = scanner_env
    make_jpeg(tmp_path / "a.jpg")
    scanner.scan_source(tmp_path)
    scanner.scan_source(tmp_path)
    with factory() as session:
        assert len(session.scalars(select(Source)).all()) == 1


def test_arquivo_que_some_e_marcado_offline(scanner_env, tmp_path):
    """O terceiro estado de alcance (fase 12, item B): a FONTE continua
    montada, mas um arquivo específico sumiu de onde estava. Sem isto ele
    fica indistinguível de "sempre esteve lá"."""
    scanner, extractor, factory = scanner_env
    alvo = make_jpeg(tmp_path / "some.jpg", seed=1)
    make_jpeg(tmp_path / "fica.jpg", seed=2)
    scanner.scan_source(tmp_path)

    alvo.unlink()
    scan, metrics = scanner.scan_source(tmp_path)

    assert scan.status == ScanStatus.CONCLUIDO
    with factory() as session:
        sumido = session.scalar(
            select(MediaFile).where(MediaFile.nome == "some.jpg")
        )
        fica = session.scalar(
            select(MediaFile).where(MediaFile.nome == "fica.jpg")
        )
        assert sumido.arquivo_offline is True
        assert fica.arquivo_offline is False
        # Metadado antigo continua no catálogo — nada foi apagado nem relido
        # (não há mais arquivo para ler).
        assert sumido.data_capturada is not None


def test_arquivo_que_volta_e_marcado_online_de_novo(scanner_env, tmp_path):
    scanner, extractor, factory = scanner_env
    alvo = make_jpeg(tmp_path / "vai_e_volta.jpg", seed=1)
    scanner.scan_source(tmp_path)

    alvo.unlink()
    scanner.scan_source(tmp_path)
    with factory() as session:
        antes = session.scalar(
            select(MediaFile).where(MediaFile.nome == "vai_e_volta.jpg")
        )
        assert antes.arquivo_offline is True

    time.sleep(0.01)
    make_jpeg(alvo, seed=3, size=(128, 96))  # "volta" com conteúdo novo
    os.utime(alvo, (time.time(), time.time()))
    scan, metrics = scanner.scan_source(tmp_path)

    assert scan.status == ScanStatus.CONCLUIDO
    with factory() as session:
        depois = session.scalar(
            select(MediaFile).where(MediaFile.nome == "vai_e_volta.jpg")
        )
        assert depois.arquivo_offline is False


def test_scan_cancelado_nao_marca_sumico_em_massa(scanner_env, tmp_path):
    """O cenário do NAS caindo no meio do walk: se a varredura só viu um
    punhado de arquivos antes de ser cancelada, a diferença entre
    `conhecidos` e `vistos` seria quase o acervo inteiro — marcar sumiço
    aqui confundiria interrupção com desaparecimento real."""
    scanner, extractor, factory = scanner_env
    _make_library(tmp_path, n=20)
    scanner.scan_source(tmp_path)

    control = ScanControl()

    def cancela_no_meio(metrics, caminho):
        if metrics.vistos >= 5:
            control.cancelar()

    scan, metrics = scanner.scan_source(
        tmp_path, progress=cancela_no_meio, control=control
    )
    assert scan.status == ScanStatus.PAUSADO

    with factory() as session:
        arquivos = session.scalars(select(MediaFile)).all()
        assert all(not a.arquivo_offline for a in arquivos)


def test_referencia_externa_no_mesmo_source_nunca_vira_offline(
    scanner_env, tmp_path
):
    """Achado 1 da revisão: o Google Takeout padrão (`ler_arquivos=False`)
    grava `takeout://referencia` sob uma `Source` cujo caminho é uma pasta
    comum (`sources/importer.py`). Se o usuário escanear essa mesma pasta
    pela CLI/UI, `_get_or_create_source` reaproveita a fonte existente —
    e, sem o filtro, toda referência dela virava `arquivo_offline=True`,
    porque ela nunca aparece no walk (não é caminho de filesystem)."""
    scanner, extractor, factory = scanner_env
    make_jpeg(tmp_path / "real.jpg", seed=1)

    with factory() as session:
        fonte = Source(caminho=str(tmp_path.expanduser()))
        session.add(fonte)
        session.flush()
        session.add(MediaFile(
            source_id=fonte.id, caminho="takeout://ref-1", pasta="",
            nome="IMG_1.jpg", extensao="jpg", tamanho=1,
            arquivo_ausente=True, papel=MediaRole.SINAL,
        ))
        session.commit()

    scan, metrics = scanner.scan_source(tmp_path)

    assert scan.status == ScanStatus.CONCLUIDO
    with factory() as session:
        referencia = session.scalar(
            select(MediaFile).where(MediaFile.caminho == "takeout://ref-1")
        )
        assert referencia.arquivo_offline is False
        assert referencia.arquivo_ausente is True  # continua intocada


def test_diretorio_ilegivel_no_meio_do_walk_nao_marca_sumico(
    scanner_env, tmp_path, monkeypatch
):
    """Achado 2 da revisão, o mais grave: `iter_media_files` engole
    `OSError` por diretório e só PARA de produzir itens dali pra frente —
    sem levantar exceção nenhuma. O scan fechava como CONCLUIDO achando
    que tinha visto a árvore inteira, e arquivos que continuavam no disco
    (só não puderam ser enumerados) saíam marcados `arquivo_offline=True`.

    Determinístico via mock de `os.scandir` — não depende de permissão de
    filesystem específica do ambiente onde o teste roda (ver também
    `test_subpasta_sem_permissao_real_nao_marca_sumico`, com `chmod` de
    verdade, pulado quando não é seguro de reproduzir)."""
    scanner, extractor, factory = scanner_env
    _make_library(tmp_path, n=6)  # pasta_0 e pasta_1, 3 arquivos cada
    scanner.scan_source(tmp_path)

    import fotoorganizer.scanner.discovery as discovery_mod

    pasta_com_falha = tmp_path / "pasta_0"
    original_scandir = discovery_mod.os.scandir

    def scandir_com_falha(path):
        if Path(path) == pasta_com_falha:
            raise OSError(13, "Permission denied")
        return original_scandir(path)

    monkeypatch.setattr(discovery_mod.os, "scandir", scandir_com_falha)

    scan, metrics = scanner.scan_source(tmp_path)

    # O scan fecha CONCLUIDO (não houve cancelamento) — é exatamente por
    # isso que confiar só em `scan.status == CONCLUIDO` não bastava.
    assert scan.status == ScanStatus.CONCLUIDO
    with factory() as session:
        arquivos = session.scalars(select(MediaFile)).all()
        assert all(not a.arquivo_offline for a in arquivos)


@pytest.mark.skipif(
    hasattr(os, "getuid") and os.getuid() == 0,
    reason="root ignora permissão de diretório — chmod não bloqueia stat/scandir",
)
def test_subpasta_sem_permissao_real_nao_marca_sumico(scanner_env, tmp_path):
    """A mesma guarda do teste acima, mas com uma permissão de verdade
    (o cenário que a revisão reproduziu originalmente com `chmod 000`)."""
    scanner, extractor, factory = scanner_env
    protegida = tmp_path / "protegida"
    make_jpeg(protegida / "dentro.jpg", seed=1)
    make_jpeg(tmp_path / "fora.jpg", seed=2)
    scanner.scan_source(tmp_path)

    os.chmod(protegida, 0)
    try:
        scan, metrics = scanner.scan_source(tmp_path)
    finally:
        os.chmod(protegida, 0o755)

    assert scan.status == ScanStatus.CONCLUIDO
    with factory() as session:
        arquivos = session.scalars(select(MediaFile)).all()
        assert all(not a.arquivo_offline for a in arquivos)


def test_padrao_ignorado_novo_nao_marca_arquivo_existente_como_sumido(
    scanner_env, tmp_path
):
    """Guarda 2 (confirmação por `Path.exists()` antes de marcar): um
    arquivo pode sair do walk sem ter sido apagado — o usuário mudou
    `padroes_ignorados` (ou a extensão suportada) entre duas passadas. Sem
    esta guarda, mudar um filtro de scan marcaria acervo real como
    sumido."""
    scanner, extractor, factory = scanner_env
    fica_fora_do_walk = make_jpeg(
        tmp_path / "pasta_ignorada" / "still_here.jpg", seed=1
    )
    make_jpeg(tmp_path / "outra.jpg", seed=2)
    scanner.scan_source(tmp_path)

    with factory() as session:
        source = session.scalars(select(Source)).one()
        source.padroes_ignorados = ["pasta_ignorada/*"]
        session.commit()

    scan, metrics = scanner.scan_source(tmp_path)

    assert scan.status == ScanStatus.CONCLUIDO
    assert fica_fora_do_walk.exists()  # nunca foi apagado de verdade
    with factory() as session:
        arquivo = session.scalar(
            select(MediaFile).where(MediaFile.nome == "still_here.jpg")
        )
        assert arquivo.arquivo_offline is False


def test_reprocessar_relê_arquivo_inalterado(migrated_engine, tmp_path):
    """Sem esta porta, extração nova nunca alcança o que já foi catalogado:
    o incremental pula por (tamanho, mtime, inode) e o arquivo não mudou."""
    from sqlalchemy import func, select

    from fotoorganizer.models import MetadataEntry

    fotos = tmp_path / "fotos"
    make_jpeg(fotos / "a.jpg", seed=1)
    factory = create_session_factory(migrated_engine)
    scanner = CatalogScanner(factory, PurePythonExtractor(), ScannerSettings())

    _, m1 = scanner.scan_source(fotos)
    assert m1.indexados == 1

    _, m2 = scanner.scan_source(fotos)
    assert (m2.indexados, m2.pulados) == (0, 1)      # incremental preservado

    _, m3 = scanner.scan_source(fotos, reprocessar=True)
    assert (m3.indexados, m3.pulados) == (1, 0)

    # Reler não pode empilhar outra cópia das mesmas tags.
    with factory() as session:
        antes = session.scalar(select(func.count(MetadataEntry.id)))
    scanner.scan_source(fotos, reprocessar=True)
    with factory() as session:
        assert session.scalar(select(func.count(MetadataEntry.id))) == antes
        assert antes > 0
