"""D-083: o lugar pela cidade da pasta não entra no plano de escrita EXIF.

O planner seleciona por `gps_lat_estimado IS NOT NULL` (herança de doadora
real). O centroide da pasta vive só em `locations` — por construção nunca
vira coordenada gravada no arquivo original.
"""

from datetime import datetime

from fotoorganizer.database import create_session_factory
from fotoorganizer.exif_write.planner import ExifWritePlanner
from fotoorganizer.geolocation.cidades import FONTE_PASTA
from fotoorganizer.models import Location, MediaFile, Source
from tests.fixtures import make_jpeg


def test_lugar_pela_pasta_nao_vira_candidato_de_escrita_exif(migrated_engine, tmp_path):
    factory = create_session_factory(migrated_engine)
    arquivo = make_jpeg(tmp_path / "canal.jpg")
    with factory() as session:
        fonte = Source(caminho=str(tmp_path))
        session.add(fonte)
        session.flush()
        local = Location(
            pais="Países Baixos", regiao="North Holland", cidade="Amsterdam",
            lat=52.37, lon=4.89, fonte=FONTE_PASTA,
            cache_key="pasta:NL:north holland:amsterdam",
        )
        session.add(local)
        session.flush()
        session.add(MediaFile(
            source_id=fonte.id, caminho=str(arquivo), pasta=str(tmp_path),
            nome="canal.jpg", extensao="jpg", tamanho=arquivo.stat().st_size,
            data_capturada=datetime(2016, 10, 15, 12, 0), location_id=local.id,
        ))
        session.commit()

    assert ExifWritePlanner(factory).criar_plano_exif() is None
