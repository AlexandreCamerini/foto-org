"""API local da UI web — catálogo, trabalhos de background e operações."""

from pathlib import Path

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

    # base_url local: em produção o servidor só é alcançado em 127.0.0.1 e
    # recusa Host de fora do loopback (ver _exigir_origem_local).
    return TestClient(
        create_app(settings, factory), base_url="http://127.0.0.1:8765"
    )


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
    client = TestClient(
        create_app(settings, factory), base_url="http://127.0.0.1:8765"
    )

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
    client = TestClient(
        create_app(settings, factory), base_url="http://127.0.0.1:8765"
    )

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
    client = TestClient(
        create_app(settings, factory), base_url="http://127.0.0.1:8765"
    )

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
    client = TestClient(
        create_app(settings, factory), base_url="http://127.0.0.1:8765"
    )

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


# -- operações físicas (plano → dry-run → execução) --------------------------
@pytest.fixture()
def operacoes(migrated_engine, tmp_path):
    """Catálogo com 2 fotos já aprovadas para cópia, e uma raiz de destino."""
    from fotoorganizer.models import (
        ConfidenceLevel,
        MediaFile,
        Suggestion,
        SuggestionStatus,
    )

    origem = tmp_path / "fotos"
    destino = tmp_path / "organizadas"
    destino.mkdir()
    for i in range(2):
        make_jpeg(origem / f"f_{i}.jpg", seed=i)

    settings = Settings(data_dir=tmp_path / "d", cache_dir=tmp_path / "c")
    factory = create_session_factory(migrated_engine)
    CatalogScanner(
        factory, PurePythonExtractor(), ScannerSettings()
    ).scan_source(origem)

    with factory() as session:
        for media in session.query(MediaFile).all():
            session.add(Suggestion(
                media_id=media.id, destino_sugerido="Viagens/2024 - Teste",
                template="t", nivel=ConfidenceLevel.ALTA,
                status=SuggestionStatus.APROVADA, versao_logica="test",
            ))
        session.commit()

    cliente = TestClient(
        create_app(settings, factory), base_url="http://127.0.0.1:8765"
    )
    return cliente, origem, destino


def _aguardar_job(client) -> dict:
    import time

    for _ in range(150):
        estado = client.get("/api/job").json()
        if estado["status"] != "rodando":
            return estado
        time.sleep(0.1)
    raise AssertionError("job não terminou")


def test_plano_dry_run_e_execucao_copiam_sem_tocar_origem(operacoes):
    client, origem, destino = operacoes
    originais = {p: p.read_bytes() for p in sorted(origem.rglob("*.jpg"))}

    plano = client.post(
        "/api/operacoes", json={"raiz_destino": str(destino)}
    ).json()
    assert plano["total_itens"] == 2
    assert plano["dry_run_em"] is None

    # Executar sem dry-run é recusado pelo servidor (e pelo executor, por baixo).
    assert client.post(
        f"/api/operacoes/{plano['id']}/executar"
    ).status_code == 409

    relatorio = client.post(f"/api/operacoes/{plano['id']}/dry-run").json()
    assert relatorio["prontos"] == 2
    assert relatorio["problemas"] == []
    assert relatorio["espaco_suficiente"]

    assert client.post(
        f"/api/operacoes/{plano['id']}/executar"
    ).status_code == 200
    assert _aguardar_job(client)["status"] == "concluido"

    copiados = sorted((destino / "Viagens" / "2024 - Teste").glob("*.jpg"))
    assert len(copiados) == 2
    # Invariante 1: nenhum original mexido.
    assert {p: p.read_bytes() for p in sorted(origem.rglob("*.jpg"))} == originais

    detalhe = client.get(f"/api/operacoes/{plano['id']}").json()
    assert detalhe["concluidos"] == 2
    assert [i["status"] for i in detalhe["itens"]] == ["concluida"] * 2

    acoes = [
        linha["acao"]
        for linha in client.get(
            f"/api/operacoes/{plano['id']}/auditoria"
        ).json()
    ]
    assert acoes.count("copia_verificada") == 2
    assert {"plano_criado", "dry_run", "execucao_finalizada"} <= set(acoes)


def test_execucao_nunca_sobrescreve_destino_que_surgiu_depois(operacoes):
    """O destino pode ficar ocupado entre o plano e a execução — a cópia
    exclusiva ('xb') recusa, e o arquivo alheio fica intacto."""
    client, _origem, destino = operacoes
    plano = client.post(
        "/api/operacoes", json={"raiz_destino": str(destino)}
    ).json()
    alvo = Path(client.get(f"/api/operacoes/{plano['id']}").json()["itens"][0]
                ["destino"])
    alvo.parent.mkdir(parents=True, exist_ok=True)
    alvo.write_bytes(b"arquivo de outra pessoa")

    relatorio = client.post(f"/api/operacoes/{plano['id']}/dry-run").json()
    assert relatorio["prontos"] == 1
    assert any("já existe" in p for p in relatorio["problemas"])

    client.post(f"/api/operacoes/{plano['id']}/executar")
    assert _aguardar_job(client)["status"] == "concluido"

    assert alvo.read_bytes() == b"arquivo de outra pessoa"
    detalhe = client.get(f"/api/operacoes/{plano['id']}").json()
    assert detalhe["com_erro"] == 1
    assert detalhe["concluidos"] == 1


def test_plano_exige_aprovadas_e_destino_valido(operacoes):
    client, _origem, destino = operacoes

    assert client.post(
        "/api/operacoes", json={"raiz_destino": "relativo/nao/serve"}
    ).status_code == 422
    assert client.post(
        "/api/operacoes",
        json={"raiz_destino": str(destino / "volume" / "sumido" / "x")},
    ).status_code == 422

    assert client.post(
        "/api/operacoes", json={"raiz_destino": str(destino)}
    ).status_code == 200
    # Só o que já foi COPIADO sai de planos futuros; replanejar o pendente é
    # permitido de propósito (trocar a raiz de destino, por exemplo).
    segundo = client.post(
        "/api/operacoes", json={"raiz_destino": str(destino)}
    ).json()
    assert segundo["total_itens"] == 2

    assert client.get("/api/operacoes/9999").status_code == 404
    assert client.post("/api/operacoes/9999/dry-run").status_code == 404


# -- proteção de origem (CSRF em localhost) ----------------------------------
def test_pagina_externa_nao_dispara_acoes(client):
    """Uma página qualquer aberta no navegador não pode acionar o app:
    POST sem corpo é 'simple request' e chega sem preflight."""
    resposta = client.post(
        "/api/duplicatas/detectar", headers={"origin": "https://evil.example"}
    )
    assert resposta.status_code == 403
    assert client.get(
        "/api/status", headers={"origin": "https://evil.example"}
    ).status_code == 403


def test_host_nao_local_e_recusado(client):
    """DNS rebinding: domínio do atacante resolvendo para 127.0.0.1."""
    assert client.get(
        "/api/status", headers={"host": "evil.example"}
    ).status_code == 403


def test_origem_local_e_ausencia_de_origem_seguem_normais(client):
    assert client.get(
        "/api/status", headers={"origin": "http://127.0.0.1:8765"}
    ).status_code == 200
    assert client.get(
        "/api/status", headers={"origin": "http://localhost:5173"}
    ).status_code == 200
    assert client.get("/api/status").status_code == 200  # curl/CLI
