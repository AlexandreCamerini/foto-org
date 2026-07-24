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
