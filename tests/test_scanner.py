import os
import threading
import time

import pytest
from sqlalchemy import select

from fotoorganizer.config.settings import ScannerSettings
from fotoorganizer.database import create_session_factory
from fotoorganizer.metadata import PurePythonExtractor
from fotoorganizer.models import MediaFile, ScanStatus, Source
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
