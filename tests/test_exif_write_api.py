"""Cobertura HTTP do grupo `/api/exif/*` (fotoorganizer/server/app.py, Fase
6, plano 06) — fluxo plano → dry-run → seleção → executar, incluindo as
portas de 409 que a UI depende de ver com a mensagem literal (T-06-32) e a
prova de que a auditoria de um plano EXIF é consultável apesar de
`AuditLog.plan_id` ser sempre `NULL` neste domínio (T-06-36).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from fotoorganizer.config.settings import ScannerSettings, Settings
from fotoorganizer.database import create_session_factory
from fotoorganizer.metadata import PurePythonExtractor
from fotoorganizer.models import Location, MediaFile
from fotoorganizer.scanner import CatalogScanner
from fotoorganizer.security.hashing import sha256_full
from fotoorganizer.server import create_app
from tests.fixtures import make_jpeg


def _aguardar_job(client) -> dict:
    """Mesmo padrão de `tests/test_server_api.py::_aguardar_job` — espera
    o job terminar antes do teste acabar, para não deixar thread órfã
    escrevendo em `tmp_path` depois do teardown."""
    import time

    for _ in range(150):
        estado = client.get("/api/job").json()
        if estado["status"] != "rodando":
            return estado
        time.sleep(0.1)
    raise AssertionError("job não terminou")


@pytest.fixture()
def client_sem_candidato(migrated_engine, tmp_path):
    """Catálogo sem nenhum candidato de escrita EXIF: nenhuma mídia tem GPS
    herdado nem localização resolvida — só assim `criar_plano_exif()`
    devolve `None` e o endpoint responde 409. Isolada da fixture com
    candidato para não precisar desfazer estado entre testes."""
    fotos = tmp_path / "fotos"
    make_jpeg(fotos / "img_0.jpg", seed=0)

    settings = Settings(data_dir=tmp_path / "d", cache_dir=tmp_path / "c")
    factory = create_session_factory(migrated_engine)
    scanner = CatalogScanner(factory, PurePythonExtractor(), ScannerSettings())
    scanner.scan_source(fotos)

    return TestClient(
        create_app(settings, factory), base_url="http://127.0.0.1:8765"
    )


@pytest.fixture()
def client_exif(migrated_engine, tmp_path):
    """Cliente com candidato pronto para escrita EXIF: catálogo escaneado
    normalmente (`make_jpeg`, sem GPS/localização) e depois, na sessão,
    `gps_lat_estimado`/`gps_lon_estimado` + um `Location` ligados às
    mídias — sem isso não há candidato e todo teste cairia no 409
    ("nada a gravar")."""
    fotos = tmp_path / "fotos"
    for i in range(3):
        make_jpeg(fotos / f"img_{i}.jpg", seed=i)

    settings = Settings(data_dir=tmp_path / "d", cache_dir=tmp_path / "c")
    factory = create_session_factory(migrated_engine)
    scanner = CatalogScanner(factory, PurePythonExtractor(), ScannerSettings())
    scanner.scan_source(fotos)

    with factory() as session:
        loc = Location(cidade="Rio de Janeiro", pais="Brasil", fonte="test")
        session.add(loc)
        session.flush()
        for media in session.scalars(select(MediaFile)):
            media.gps_lat_estimado = -22.95
            media.gps_lon_estimado = -43.18
            media.location_id = loc.id
        session.commit()

    return TestClient(
        create_app(settings, factory), base_url="http://127.0.0.1:8765"
    )


def test_criar_plano_sem_candidato_devolve_409(client_sem_candidato):
    resposta = client_sem_candidato.post("/api/exif/plano")
    assert resposta.status_code == 409
    assert "nada a gravar" in resposta.json()["detail"]


def test_criar_plano_e_listar(client_exif):
    plano = client_exif.post("/api/exif/plano").json()
    assert plano["total_itens"] > 0
    assert plano["dry_run_em"] is None

    listagem = client_exif.get("/api/exif").json()
    assert any(p["id"] == plano["id"] for p in listagem)


def test_detalhe_traz_campos_por_campo(client_exif):
    plano = client_exif.post("/api/exif/plano").json()
    detalhe = client_exif.get(f"/api/exif/{plano['id']}").json()
    assert detalhe["itens"]
    for item in detalhe["itens"]:
        campos = item["campos"]
        assert set(campos.keys()) == {"gps", "cidade", "pais"}
        for campo in campos.values():
            assert set(campo.keys()) == {"valor", "status", "motivo"}


def test_executar_sem_dry_run_devolve_409(client_exif):
    plano = client_exif.post("/api/exif/plano").json()
    origens = [
        Path(item["origem"])
        for item in client_exif.get(f"/api/exif/{plano['id']}").json()["itens"]
    ]
    hashes_antes = {p: sha256_full(p) for p in origens}

    resposta = client_exif.post(
        f"/api/exif/{plano['id']}/executar", json={"itens": None}
    )
    assert resposta.status_code == 409
    assert resposta.json()["detail"] == "rode o dry-run antes de gravar"

    assert {p: sha256_full(p) for p in origens} == hashes_antes


def test_dry_run_e_veredito(client_exif):
    plano = client_exif.post("/api/exif/plano").json()
    relatorio = client_exif.post(f"/api/exif/{plano['id']}/dry-run").json()
    assert relatorio["prontos"] >= 1

    detalhe = client_exif.get(f"/api/exif/{plano['id']}").json()
    assert detalhe["dry_run_em"] is not None
    assert detalhe["executavel"] is True


def test_selecao_vazia_devolve_409(client_exif):
    plano = client_exif.post("/api/exif/plano").json()
    client_exif.post(f"/api/exif/{plano['id']}/dry-run")
    origens = [
        Path(item["origem"])
        for item in client_exif.get(f"/api/exif/{plano['id']}").json()["itens"]
    ]
    hashes_antes = {p: sha256_full(p) for p in origens}

    resposta = client_exif.post(
        f"/api/exif/{plano['id']}/executar", json={"itens": []}
    )
    assert resposta.status_code == 409
    assert resposta.json()["detail"] == "nenhum item selecionado para gravar"
    assert {p: sha256_full(p) for p in origens} == hashes_antes


def test_execucao_dispara_job(client_exif):
    plano = client_exif.post("/api/exif/plano").json()
    client_exif.post(f"/api/exif/{plano['id']}/dry-run")

    resposta = client_exif.post(
        f"/api/exif/{plano['id']}/executar", json={"itens": None}
    )
    assert resposta.status_code == 200
    assert resposta.json()["tipo"] == "escrita_exif"

    _aguardar_job(client_exif)


def test_auditoria_do_plano_exif(client_exif):
    plano = client_exif.post("/api/exif/plano").json()
    client_exif.post(f"/api/exif/{plano['id']}/dry-run")

    acoes = [
        linha["acao"]
        for linha in client_exif.get(f"/api/exif/{plano['id']}/auditoria").json()
    ]
    # Prova de que o filtro por `detalhe["exif_plan_id"]` funciona apesar
    # de `AuditLog.plan_id` ser NULL nas linhas deste domínio (T-06-36).
    assert {"plano_exif_criado", "dry_run_exif"} <= set(acoes)


def test_404_em_plano_inexistente(client_exif):
    assert client_exif.get("/api/exif/999999").status_code == 404
    assert client_exif.post("/api/exif/999999/dry-run").status_code == 404
    assert client_exif.post(
        "/api/exif/999999/executar", json={"itens": None}
    ).status_code == 404
    assert client_exif.get("/api/exif/999999/auditoria").status_code == 404
