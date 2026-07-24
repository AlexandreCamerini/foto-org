"""API local da UI web (F1 do M9) — read-only sobre o catálogo."""

import pytest
from fastapi.testclient import TestClient

from fotoorganizer.config.settings import ScannerSettings, Settings
from fotoorganizer.database import create_session_factory
from fotoorganizer.metadata import PurePythonExtractor
from fotoorganizer.scanner import CatalogScanner
from fotoorganizer.server import create_app
from tests.fixtures import make_jpeg


@pytest.fixture()
def client(migrated_engine, tmp_path):
    fotos = tmp_path / "fotos"
    for i in range(5):
        make_jpeg(fotos / f"img_{i}.jpg", seed=i,
                  gps=(43.95, 4.81) if i == 0 else None)

    settings = Settings(data_dir=tmp_path / "d", cache_dir=tmp_path / "c")
    factory = create_session_factory(migrated_engine)
    scanner = CatalogScanner(factory, PurePythonExtractor(), ScannerSettings())
    scanner.scan_source(fotos)

    return TestClient(create_app(settings, factory))


def test_status_e_fontes(client):
    status = client.get("/api/status").json()
    assert status["total"] == 5
    (fonte,) = client.get("/api/fontes").json()
    assert fonte["tipo"] == "pasta"
    assert fonte["fotos"] == 5


def test_listagem_paginada(client):
    pagina = client.get("/api/midia", params={"limit": 2}).json()
    assert pagina["total"] == 5
    assert len(pagina["itens"]) == 2
    resto = client.get("/api/midia", params={"limit": 500, "offset": 4}).json()
    assert len(resto["itens"]) == 1


def test_busca_e_detalhe(client):
    achados = client.get("/api/midia", params={"busca": "img_3"}).json()
    assert achados["total"] == 1
    media_id = achados["itens"][0]["id"]

    detalhe = client.get(f"/api/midia/{media_id}").json()
    assert detalhe["nome"] == "img_3.jpg"
    assert detalhe["make"] == "TestMake"

    assert client.get("/api/midia/99999").status_code == 404


def test_thumb_e_preview_sao_jpeg(client):
    media_id = client.get("/api/midia").json()["itens"][0]["id"]

    thumb = client.get(f"/api/midia/{media_id}/thumb")
    assert thumb.status_code == 200
    assert thumb.headers["content-type"] == "image/jpeg"
    assert thumb.content[:2] == b"\xff\xd8"  # SOI de JPEG

    preview = client.get(f"/api/midia/{media_id}/preview")
    assert preview.status_code == 200
    assert preview.content[:2] == b"\xff\xd8"


def test_scan_em_background_indexa_e_reporta(migrated_engine, tmp_path):
    import time

    fotos = tmp_path / "novas"
    for i in range(4):
        make_jpeg(fotos / f"n_{i}.jpg", seed=i)
    settings = Settings(data_dir=tmp_path / "d", cache_dir=tmp_path / "c")
    factory = create_session_factory(migrated_engine)
    client = TestClient(create_app(settings, factory))

    resposta = client.post("/api/scan", json={"caminho": str(fotos)})
    assert resposta.status_code == 200

    for _ in range(100):
        estado = client.get("/api/job").json()
        if estado["status"] != "rodando":
            break
        time.sleep(0.1)
    assert estado["status"] == "concluido"
    assert estado["processados"] == 4
    assert client.get("/api/status").json()["total"] == 4

    # Pasta inexistente e tipo de import inválido: erros claros.
    assert client.post(
        "/api/scan", json={"caminho": "/nao/existe"}
    ).status_code == 422
    assert client.post(
        "/api/importar", json={"tipo": "dropbox"}
    ).status_code == 422


def test_import_takeout_em_background(migrated_engine, tmp_path):
    import json as jsonlib
    import time

    raiz = tmp_path / "Takeout" / "Google Photos"
    foto = make_jpeg(raiz / "Album" / "IMG.jpg", data_exif=None)
    foto.with_name(foto.name + ".json").write_text(jsonlib.dumps({
        "photoTakenTime": {"timestamp": "1730467800"},
        "geoData": {"latitude": 1.0, "longitude": 2.0},
    }), encoding="utf-8")
    settings = Settings(data_dir=tmp_path / "d", cache_dir=tmp_path / "c")
    factory = create_session_factory(migrated_engine)
    client = TestClient(create_app(settings, factory))

    resposta = client.post(
        "/api/importar",
        json={"tipo": "google_takeout", "caminho": str(raiz)},
    )
    assert resposta.status_code == 200
    for _ in range(100):
        estado = client.get("/api/job").json()
        if estado["status"] != "rodando":
            break
        time.sleep(0.1)
    assert estado["status"] == "concluido"
    assert estado["processados"] == 1
    (fonte,) = client.get("/api/fontes").json()
    assert fonte["tipo"] == "google_takeout"


def test_gerar_sugestoes_e_aprovar(migrated_engine, tmp_path):
    import time

    fotos = tmp_path / "fotos"
    for i in range(3):
        make_jpeg(fotos / f"f_{i}.jpg", seed=i)
    settings = Settings(data_dir=tmp_path / "d", cache_dir=tmp_path / "c")
    factory = create_session_factory(migrated_engine)
    scanner = CatalogScanner(factory, PurePythonExtractor(), ScannerSettings())
    scanner.scan_source(fotos)
    client = TestClient(create_app(settings, factory))

    assert client.post("/api/sugestoes/gerar").status_code == 200
    for _ in range(150):
        estado = client.get("/api/job").json()
        if estado["status"] != "rodando":
            break
        time.sleep(0.1)
    assert estado["status"] == "concluido"

    pendentes = client.get("/api/sugestoes").json()
    assert len(pendentes["itens"]) == 3

    ids = [s["id"] for s in pendentes["itens"][:2]]
    resultado = client.post(
        "/api/sugestoes/acao", json={"ids": ids, "acao": "aprovar"}
    ).json()
    assert resultado["afetadas"] == 2
    depois = client.get("/api/sugestoes").json()
    assert depois["contagens"]["aprovada"] == 2
    assert len(depois["itens"]) == 1

    assert client.post(
        "/api/sugestoes/acao", json={"ids": ids, "acao": "explodir"}
    ).status_code == 422


def test_filtro_por_viagem(client, migrated_engine):
    from fotoorganizer.models import MediaFile, Trip

    factory = create_session_factory(migrated_engine)
    with factory() as session:
        trip = Trip(nome="Teste")
        session.add(trip)
        session.flush()
        media = session.query(MediaFile).first()
        media.trip_id = trip.id
        trip_id = trip.id
        session.commit()

    filtrado = client.get("/api/midia", params={"trip_id": trip_id}).json()
    assert filtrado["total"] == 1


def test_duplicatas_detectar_e_decidir(migrated_engine, tmp_path):
    import shutil
    import time

    fotos = tmp_path / "fotos"
    original = make_jpeg(fotos / "original.jpg", seed=7)
    shutil.copy(original, fotos / "copia.jpg")
    settings = Settings(data_dir=tmp_path / "d", cache_dir=tmp_path / "c")
    factory = create_session_factory(migrated_engine)
    CatalogScanner(factory, PurePythonExtractor(), ScannerSettings()) \
        .scan_source(fotos)
    client = TestClient(create_app(settings, factory))

    assert client.post("/api/duplicatas/detectar").status_code == 200
    for _ in range(100):
        estado = client.get("/api/job").json()
        if estado["status"] != "rodando":
            break
        time.sleep(0.1)
    assert estado["status"] == "concluido"

    (grupo,) = client.get("/api/duplicatas").json()
    assert grupo["nivel"] == "exato"

    principal = grupo["membros"][0]["media_id"]
    client.post(f"/api/duplicatas/{grupo['id']}/principal",
                json={"media_id": principal})
    (depois,) = client.get("/api/duplicatas").json()
    assert depois["decidido"] is True
    papeis = {m["media_id"]: m["papel"] for m in depois["membros"]}
    assert papeis[principal] == "principal"

    client.post(f"/api/duplicatas/{grupo['id']}/desfazer")
    (final,) = client.get("/api/duplicatas").json()
    assert final["decidido"] is False


def test_filtros_viagens_sugestoes_duplicatas_respondem(client):
    filtros = client.get("/api/midia/filtros").json()
    assert "jpg" in filtros["extensoes"]
    assert client.get("/api/viagens").json() == []
    assert client.get("/api/eventos").json() == []
    sugestoes = client.get("/api/sugestoes").json()
    assert sugestoes["itens"] == []
    assert client.get("/api/duplicatas").json() == []
    assert client.get(
        "/api/sugestoes", params={"status": "invalido"}
    ).status_code == 422
