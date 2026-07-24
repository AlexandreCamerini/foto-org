"""Fontes tipadas e importador de catálogos externos (F1 do M8)."""

from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import select

from fotoorganizer.config.settings import ScannerSettings
from fotoorganizer.database import create_session_factory
from fotoorganizer.metadata import PurePythonExtractor
from fotoorganizer.models import MediaFile, MetadataEntry, Source, SourceType
from fotoorganizer.sources import (
    ExternalAsset,
    ExternalCatalogImporter,
    ImportMetrics,
)
from tests.fixtures import make_jpeg


class FakeProvider:
    """Provider mínimo: catálogo externo com 2 fotos e metadados ricos."""

    def __init__(self, raiz: Path, assets: list[ExternalAsset]) -> None:
        self._raiz = raiz
        self._assets = assets

    @property
    def tipo(self) -> SourceType:
        return SourceType.GOOGLE_TAKEOUT

    @property
    def raiz(self) -> Path:
        return self._raiz

    @property
    def apelido(self) -> str:
        return "Google Takeout (teste)"

    def iter_assets(self):
        yield from self._assets


@pytest.fixture()
def importer(migrated_engine):
    factory = create_session_factory(migrated_engine)
    return factory, ExternalCatalogImporter(
        factory, PurePythonExtractor(), ScannerSettings()
    )


def test_fonte_padrao_e_pasta(migrated_engine):
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        session.add(Source(caminho="/qualquer"))
        session.commit()
        source = session.scalars(select(Source)).one()
        assert source.tipo == SourceType.PASTA


def test_importa_e_funde_metadados(importer, tmp_path):
    factory, imp = importer
    # Foto SEM data EXIF e sem GPS — o catálogo externo tem os dois.
    foto = make_jpeg(tmp_path / "takeout" / "praia.jpg", data_exif=None)
    asset = ExternalAsset(
        caminho=foto,
        data_capturada=datetime(2025, 11, 2, 15, 30),
        gps_lat=25.2048, gps_lon=55.2708,
        titulo="Praia em Dubai", favorito=True,
        albuns=("Viagem 2025",),
    )
    metrics = imp.importar(FakeProvider(tmp_path / "takeout", [asset]))

    assert metrics.importados == 1 and metrics.erros == 0
    with factory() as session:
        source = session.scalars(select(Source)).one()
        assert source.tipo == SourceType.GOOGLE_TAKEOUT
        media = session.scalars(select(MediaFile)).one()
        # Lacunas preenchidas pelo catálogo externo:
        assert media.data_capturada == datetime(2025, 11, 2, 15, 30)
        assert media.gps_lat == pytest.approx(25.2048)
        entradas = {
            (e.chave, e.valor)
            for e in session.scalars(select(MetadataEntry).where(
                MetadataEntry.namespace == "google"
            ))
        }
        assert ("titulo", "Praia em Dubai") in entradas
        assert ("favorito", "true") in entradas
        assert ("album", "Viagem 2025") in entradas


def test_exif_do_arquivo_vence_o_catalogo_externo(importer, tmp_path):
    factory, imp = importer
    # Foto COM data EXIF — a data divergente do catálogo NÃO sobrescreve.
    foto = make_jpeg(tmp_path / "t" / "com_exif.jpg",
                     data_exif="2024:05:04 10:30:00")
    asset = ExternalAsset(
        caminho=foto, data_capturada=datetime(2020, 1, 1, 0, 0),
    )
    imp.importar(FakeProvider(tmp_path / "t", [asset]))

    with factory() as session:
        media = session.scalars(select(MediaFile)).one()
        assert media.data_capturada == datetime(2024, 5, 4, 10, 30)


def test_reimportar_e_idempotente(importer, tmp_path):
    factory, imp = importer
    foto = make_jpeg(tmp_path / "t" / "a.jpg")
    asset = ExternalAsset(caminho=foto, titulo="Um título")
    provider = FakeProvider(tmp_path / "t", [asset])

    imp.importar(provider)
    metrics = imp.importar(provider)

    assert metrics.pulados == 1 and metrics.importados == 0
    with factory() as session:
        assert len(session.scalars(select(MediaFile)).all()) == 1
        assert len(session.scalars(select(Source)).all()) == 1
        titulos = session.scalars(select(MetadataEntry).where(
            MetadataEntry.chave == "titulo"
        )).all()
        assert len(titulos) == 1  # namespace regravado, não duplicado


def test_arquivo_inacessivel_conta_erro_e_segue(importer, tmp_path):
    factory, imp = importer
    boa = make_jpeg(tmp_path / "t" / "boa.jpg")
    metrics = imp.importar(FakeProvider(tmp_path / "t", [
        ExternalAsset(caminho=tmp_path / "t" / "sumida.jpg"),
        ExternalAsset(caminho=boa),
    ]))
    assert metrics.erros == 1
    assert metrics.importados == 1
