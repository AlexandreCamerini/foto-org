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


def test_fonte_reutilizada_entre_scans(scanner_env, tmp_path):
    scanner, extractor, factory = scanner_env
    make_jpeg(tmp_path / "a.jpg")
    scanner.scan_source(tmp_path)
    scanner.scan_source(tmp_path)
    with factory() as session:
        assert len(session.scalars(select(Source)).all()) == 1
