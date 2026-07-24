"""Provider de Google Takeout: sidecars, álbuns, GPS e integração."""

import json
from datetime import datetime

from sqlalchemy import select

from fotoorganizer.config.settings import ScannerSettings
from fotoorganizer.database import create_session_factory
from fotoorganizer.metadata import PurePythonExtractor
from fotoorganizer.models import MediaFile, MetadataEntry
from fotoorganizer.sources import ExternalCatalogImporter, GoogleTakeoutProvider
from tests.fixtures import make_jpeg


def _sidecar(media_path, **campos):
    dados = {
        "title": media_path.name,
        "photoTakenTime": {"timestamp": str(campos.pop("epoch", 1730467800))},
        "geoData": {
            "latitude": campos.pop("lat", 0.0),
            "longitude": campos.pop("lon", 0.0),
        },
    }
    dados.update(campos)
    sidecar = media_path.with_name(media_path.name + ".json")
    sidecar.write_text(json.dumps(dados), encoding="utf-8")
    return sidecar


def _takeout(tmp_path):
    raiz = tmp_path / "Takeout" / "Google Photos"
    raiz.mkdir(parents=True)
    return raiz


def test_sidecar_preenche_gps_e_data(tmp_path):
    raiz = _takeout(tmp_path)
    foto = make_jpeg(raiz / "Photos from 2024" / "IMG_1.jpg", data_exif=None)
    _sidecar(foto, lat=25.2048, lon=55.2708, epoch=1730467800)

    (asset,) = list(GoogleTakeoutProvider(raiz).iter_assets())
    assert asset.gps_lat == 25.2048
    assert asset.data_capturada == datetime.fromtimestamp(1730467800)
    assert asset.albuns == ()  # "Photos from 2024" não é álbum


def test_gps_zero_zero_e_tratado_como_sem_gps(tmp_path):
    raiz = _takeout(tmp_path)
    foto = make_jpeg(raiz / "Photos from 2024" / "IMG_2.jpg")
    _sidecar(foto, lat=0.0, lon=0.0)

    (asset,) = list(GoogleTakeoutProvider(raiz).iter_assets())
    assert asset.gps_lat is None and asset.gps_lon is None


def test_pasta_de_album_e_pessoas(tmp_path):
    raiz = _takeout(tmp_path)
    foto = make_jpeg(raiz / "Viagem Dubai" / "IMG_3.jpg")
    _sidecar(foto, favorited=True, description="Burj Khalifa",
             people=[{"name": "Serena"}, {"name": ""}])

    (asset,) = list(GoogleTakeoutProvider(raiz).iter_assets())
    assert asset.albuns == ("Viagem Dubai",)
    assert asset.favorito is True
    assert asset.descricao == "Burj Khalifa"
    assert asset.pessoas == ("Serena",)


def test_variante_supplemental_metadata_e_arquivo_sem_sidecar(tmp_path):
    raiz = _takeout(tmp_path)
    com = make_jpeg(raiz / "Album" / "IMG_4.jpg")
    sidecar = com.with_name(com.name + ".supplemental-metadata.json")
    sidecar.write_text(json.dumps({
        "photoTakenTime": {"timestamp": "1730467800"},
        "geoData": {"latitude": 1.0, "longitude": 2.0},
    }), encoding="utf-8")
    make_jpeg(raiz / "Album" / "IMG_5.jpg")  # sem sidecar: entra mesmo assim

    assets = {a.caminho.name: a for a in GoogleTakeoutProvider(raiz).iter_assets()}
    assert assets["IMG_4.jpg"].gps_lat == 1.0
    assert assets["IMG_5.jpg"].gps_lat is None


def test_sidecar_de_copia_numerada(tmp_path):
    raiz = _takeout(tmp_path)
    foto = make_jpeg(raiz / "Album" / "IMG_6(1).jpg", data_exif=None)
    sidecar = foto.with_name("IMG_6.jpg(1).json")
    sidecar.write_text(json.dumps({
        "photoTakenTime": {"timestamp": "1730467800"},
        "geoData": {"latitude": 3.0, "longitude": 4.0},
    }), encoding="utf-8")

    (asset,) = list(GoogleTakeoutProvider(raiz).iter_assets())
    assert asset.gps_lat == 3.0


def test_integracao_takeout_no_catalogo(migrated_engine, tmp_path):
    raiz = _takeout(tmp_path)
    foto = make_jpeg(raiz / "Viagem Dubai" / "IMG_7.jpg", data_exif=None)
    _sidecar(foto, lat=25.2, lon=55.3, favorited=True)

    factory = create_session_factory(migrated_engine)
    imp = ExternalCatalogImporter(factory, PurePythonExtractor(),
                                  ScannerSettings())
    metrics = imp.importar(GoogleTakeoutProvider(raiz))

    assert metrics.importados == 1
    with factory() as session:
        media = session.scalars(select(MediaFile)).one()
        assert media.gps_lat == 25.2
        chaves = {
            e.chave for e in session.scalars(select(MetadataEntry).where(
                MetadataEntry.namespace == "google"
            ))
        }
        assert {"album", "favorito", "gps"} <= chaves
