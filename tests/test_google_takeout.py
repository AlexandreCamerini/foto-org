"""Provider de Google Takeout: sidecars, álbuns, GPS e integração."""

import json
import time
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
    # O epoch do Takeout é o instante ABSOLUTO. A asserção anterior comparava
    # com `datetime.fromtimestamp(epoch)` — o mesmo cálculo do código, no fuso
    # da máquina — e por isso passava em qualquer fuso, inclusive com o valor
    # errado. O esperado agora é o instante fixo, escrito por extenso.
    assert asset.data_capturada == datetime(2024, 11, 1, 13, 30)
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

    assets = {a.nome: a for a in GoogleTakeoutProvider(raiz).iter_assets()}
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


def test_takeout_entra_como_doador_sem_abrir_a_imagem(migrated_engine, tmp_path):
    """Por padrão o Takeout doa sinais e não vira acervo: nome e tamanho
    vêm da entrada de diretório, mas nenhum byte de imagem é lido — sem
    hash, sem EXIF, sem miniatura."""
    raiz = _takeout(tmp_path)
    foto = make_jpeg(raiz / "Viagem Dubai" / "IMG_8.jpg", data_exif=None)
    _sidecar(foto, lat=25.2, lon=55.3)

    factory = create_session_factory(migrated_engine)
    imp = ExternalCatalogImporter(factory, PurePythonExtractor(),
                                  ScannerSettings())
    imp.importar(GoogleTakeoutProvider(raiz))

    with factory() as session:
        media = session.scalars(select(MediaFile)).one()
        assert media.arquivo_ausente is True
        assert media.hash_rapido is None  # não houve leitura do arquivo
        assert media.nome == "IMG_8.jpg"
        assert media.extensao == "jpg"
        assert media.tamanho == foto.stat().st_size
        assert media.caminho == "google://Viagem Dubai/IMG_8.jpg"


def test_ler_arquivos_cataloga_de_verdade(migrated_engine, tmp_path):
    """Quando o Takeout *é* o acervo, o modo explícito volta a abrir a
    imagem e o item deixa de ser referência."""
    raiz = _takeout(tmp_path)
    foto = make_jpeg(raiz / "Album" / "IMG_9.jpg")
    _sidecar(foto, lat=25.2, lon=55.3)

    factory = create_session_factory(migrated_engine)
    imp = ExternalCatalogImporter(factory, PurePythonExtractor(),
                                  ScannerSettings())
    imp.importar(GoogleTakeoutProvider(raiz, ler_arquivos=True))

    with factory() as session:
        media = session.scalars(select(MediaFile)).one()
        assert media.arquivo_ausente is False
        assert media.hash_rapido is not None
        assert media.caminho == str(foto)


def test_epoch_nao_depende_do_fuso_da_maquina(tmp_path, monkeypatch):
    """Regressão: `datetime.fromtimestamp(epoch)` sem fuso fazia a hora
    gravada depender de onde a importação rodou — a mesma foto virava 13h em
    São Paulo, 18h em Paris e 16h em UTC. O epoch do Takeout é o instante
    absoluto e não muda de lugar."""
    raiz = _takeout(tmp_path)
    foto = make_jpeg(raiz / "Photos from 2020" / "IMG_TZ.jpg", data_exif=None)
    _sidecar(foto, epoch=1592668800)  # 2020-06-20 16:00:00 UTC

    vistos = set()
    for zona in ("America/Sao_Paulo", "Europe/Paris", "UTC", "Asia/Tokyo"):
        monkeypatch.setenv("TZ", zona)
        time.tzset()
        (asset,) = list(GoogleTakeoutProvider(raiz).iter_assets())
        vistos.add(asset.data_capturada)
    time.tzset()

    assert vistos == {datetime(2020, 6, 20, 16, 0)}


def test_instante_absoluto_do_google_e_gravado(tmp_path):
    """O epoch é a informação de fuso mais confiável que o Takeout tem.
    Descartá-la era jogar fora o único dado bom da fonte.

    Os dois instantes saem iguais porque o JSON não diz a hora de parede da
    captura — e é assim que este catálogo escreve "não sei o fuso"."""
    raiz = _takeout(tmp_path)
    foto = make_jpeg(raiz / "Photos from 2020" / "IMG_ABS.jpg", data_exif=None)
    _sidecar(foto, epoch=1592668800)

    (asset,) = list(GoogleTakeoutProvider(raiz).iter_assets())
    assert asset.data_capturada_utc == datetime(2020, 6, 20, 16, 0)
    assert asset.data_capturada == asset.data_capturada_utc


def test_sidecar_sem_data_nao_inventa_instante(tmp_path):
    raiz = _takeout(tmp_path)
    foto = make_jpeg(raiz / "Album" / "IMG_SD.jpg", data_exif=None)
    sidecar = foto.with_name(foto.name + ".json")
    sidecar.write_text(json.dumps({"title": foto.name}), encoding="utf-8")

    (asset,) = list(GoogleTakeoutProvider(raiz).iter_assets())
    assert asset.data_capturada is None
    assert asset.data_capturada_utc is None
