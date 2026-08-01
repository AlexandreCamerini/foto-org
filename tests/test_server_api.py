"""API local da UI web — catálogo, trabalhos de background e operações."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

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


def test_detalhe_expoe_o_lugar_resolvido(client, migrated_engine):
    """País e cidade existem no catálogo desde o M3, e não saíam de lá: a
    API não devolvia `locations` em resposta alguma. Sem isso a UI não tem
    como mostrar onde a foto foi tirada — nem quando o lugar foi herdado
    de outra câmera."""
    from fotoorganizer.models import Location, MediaFile

    factory = create_session_factory(migrated_engine)
    with factory() as session:
        local = Location(pais="França", regiao="Provence", cidade="Avignon",
                         fonte="offline:reverse_geocode", cache_key="43.9,4.8")
        session.add(local)
        session.flush()
        media = session.scalars(select(MediaFile)).first()
        media.location_id = local.id
        media_id = media.id
        session.commit()

    detalhe = client.get(f"/api/midia/{media_id}").json()
    assert detalhe["local"] == {
        "pais": "França", "regiao": "Provence", "cidade": "Avignon",
        "fonte": "offline:reverse_geocode",
        # Esta foto tem GPS próprio (img_0 do fixture): o lugar é medido.
        "estimado": False,
        "granularidade": "cidade",
    }


def test_detalhe_sem_lugar_omite_a_chave(client):
    achados = client.get("/api/midia", params={"busca": "img_3"}).json()
    detalhe = client.get(f"/api/midia/{achados['itens'][0]['id']}").json()
    assert "local" not in detalhe


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


# -- panorama e lacunas ------------------------------------------------------
@pytest.fixture()
def panorama(migrated_engine, tmp_path):
    """Quatro fotos com buracos diferentes — o caso real em miniatura."""
    fotos = tmp_path / "fotos"
    make_jpeg(fotos / "completa.jpg", seed=1, gps=(43.95, 4.81))
    make_jpeg(fotos / "sem_gps.jpg", seed=2)
    make_jpeg(fotos / "sem_data.jpg", seed=3, data_exif=None)
    make_jpeg(fotos / "anonima.jpg", seed=4, make=None, model=None)

    settings = Settings(data_dir=tmp_path / "d", cache_dir=tmp_path / "c")
    factory = create_session_factory(migrated_engine)
    CatalogScanner(
        factory, PurePythonExtractor(), ScannerSettings()
    ).scan_source(fotos)
    return TestClient(
        create_app(settings, factory), base_url="http://127.0.0.1:8765"
    )


def test_panorama_conta_lacunas_e_facetas(panorama):
    dados = panorama.get("/api/panorama").json()
    assert dados["total"] == 4

    por_chave = {l["chave"]: l["quantidade"] for l in dados["lacunas"]}
    assert por_chave["sem_data"] == 1
    assert por_chave["sem_gps"] == 3
    assert por_chave["sem_camera"] == 1
    assert por_chave["sem_grupo"] == 4
    assert por_chave["sem_sugestao"] == 4
    assert por_chave["erro_leitura"] == 0
    # Toda lacuna tem rótulo legível — nenhuma chave crua chega na tela.
    assert all(l["rotulo"] for l in dados["lacunas"])

    anos = {a["chave"]: a["quantidade"] for a in dados["por_ano"]}
    assert anos == {"2024": 3, "sem data": 1}
    cameras = {c["chave"]: c["quantidade"] for c in dados["por_camera"]}
    assert cameras == {"TestMake TestModel": 3, "desconhecida": 1}

    cruzamento = dados["cruzamento_ano_fonte"]
    assert sum(c["quantidade"] for c in cruzamento) == 4
    assert {c["ano"] for c in cruzamento} == {"2024", "sem data"}


def test_lacuna_filtra_a_biblioteca(panorama):
    """O contrato do panorama: a contagem exibida e o filtro clicado
    devolvem o mesmo conjunto — senão o número mente."""
    for chave, esperado in [("sem_data", 1), ("sem_gps", 3), ("sem_camera", 1)]:
        pagina = panorama.get("/api/midia", params={"lacuna": chave}).json()
        assert pagina["total"] == esperado, chave

    assert panorama.get(
        "/api/midia", params={"lacuna": "sem_data"}
    ).json()["itens"][0]["nome"] == "sem_data.jpg"
    assert panorama.get(
        "/api/midia", params={"lacuna": "inventada"}
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


def test_detalhe_traz_a_foto_que_doou_a_coordenada(client, migrated_engine):
    """A estimativa só é auditável se a doadora for alcançável a partir de
    quem herdou — id, nome, câmera e Δt, não só uma frase."""
    from fotoorganizer.models import MediaFile

    factory = create_session_factory(migrated_engine)
    with factory() as session:
        fotos = list(session.scalars(select(MediaFile).order_by(MediaFile.nome)))
        doadora, herdeira = fotos[0], fotos[1]
        doadora.make, doadora.model = "Apple", "iPhone 15 Pro"
        herdeira.gps_lat = herdeira.gps_lon = None
        herdeira.gps_lat_estimado, herdeira.gps_lon_estimado = 43.95, 4.81
        herdeira.gps_estimado_de_id = doadora.id
        herdeira.gps_estimado_delta_s = 120
        ids = (doadora.id, herdeira.id)
        session.commit()

    detalhe = client.get(f"/api/midia/{ids[1]}").json()
    assert detalhe["gps_lat"] is None
    assert detalhe["gps_estimado"] is True
    assert detalhe["gps_lat_efetivo"] == 43.95
    assert detalhe["estimativa"] == {
        "doadora_id": ids[0], "doadora_nome": "img_0.jpg",
        "doadora_camera": "Apple iPhone 15 Pro",
        "delta_s": 120, "lat": 43.95, "lon": 4.81,
    }


def test_lacuna_sem_coordenada_ignora_quem_tem_estimativa(client, migrated_engine):
    """Mandar o usuário procurar GPS numa foto cujo lugar o sistema já
    estimou é trabalho inventado. A estimativa vira lacuna própria."""
    from fotoorganizer.models import MediaFile

    factory = create_session_factory(migrated_engine)
    with factory() as session:
        foto = session.scalars(
            select(MediaFile).where(MediaFile.gps_lat.is_(None))
        ).first()
        foto.gps_lat_estimado, foto.gps_lon_estimado = 43.95, 4.81
        session.commit()

    lacunas = {l["chave"]: l["quantidade"]
               for l in client.get("/api/panorama").json()["lacunas"]}
    # 5 fotos, 1 com GPS próprio, 1 agora com estimativa → 3 sem nada.
    assert lacunas["sem_gps"] == 3
    assert lacunas["local_estimado"] == 1


def test_metadados_agrupa_por_padrao_com_rotulo_legivel(client, migrated_engine):
    """A pergunta do dono era "mapeamento total das informações gravadas no
    arquivo". Elas já eram escritas em metadata_entries desde o M1 e não
    saíam de lá — nenhum endpoint as devolvia."""
    from fotoorganizer.models import MediaFile, MetadataEntry

    factory = create_session_factory(migrated_engine)
    with factory() as session:
        media = session.scalars(select(MediaFile)).first()
        media_id = media.id
        session.add_all([
            MetadataEntry(media_id=media_id, namespace="iptc",
                          chave="By-line", valor="Alexandre Camerini"),
            MetadataEntry(media_id=media_id, namespace="iptc",
                          chave="Keywords", valor="viagem; franca"),
            MetadataEntry(media_id=media_id, namespace="xmp",
                          chave="dc.rights", valor="(c) 2024"),
        ])
        session.commit()

    dados = client.get(f"/api/midia/{media_id}/metadados").json()
    por_nome = {ns["nome"]: ns for ns in dados["namespaces"]}

    assert dados["total"] >= 3
    assert por_nome["iptc"]["rotulo"] == "IPTC (autor, direitos, palavras-chave)"
    chaves = {i["chave"]: i["valor"] for i in por_nome["iptc"]["itens"]}
    assert chaves["By-line"] == "Alexandre Camerini"
    assert por_nome["xmp"]["itens"][0]["valor"] == "(c) 2024"


def test_metadados_de_foto_sem_nada_devolve_vazio(client):
    achados = client.get("/api/midia", params={"busca": "img_3"}).json()
    dados = client.get(
        f"/api/midia/{achados['itens'][0]['id']}/metadados"
    ).json()
    assert dados["total"] >= 0 and isinstance(dados["namespaces"], list)


def test_confirmar_tipo_grava_a_palavra_do_usuario(client, migrated_engine):
    from fotoorganizer.models import MediaFile

    factory = create_session_factory(migrated_engine)
    with factory() as session:
        media = session.scalars(select(MediaFile)).first()
        media.tipo_imagem = "captura"     # opinião do detector
        media_id = media.id
        session.commit()

    r = client.post(f"/api/midia/{media_id}/tipo", json={"tipo": "foto"})
    assert r.json() == {"tipo_imagem": "foto", "tipo_provisorio": False}

    detalhe = client.get(f"/api/midia/{media_id}").json()
    assert detalhe["tipo_imagem"] == "foto"
    assert detalhe["tipo_provisorio"] is False

    # Devolver ao detector: volta a valer a opinião dele, e a provisoriedade.
    client.post(f"/api/midia/{media_id}/tipo", json={"tipo": None})
    detalhe = client.get(f"/api/midia/{media_id}").json()
    assert detalhe["tipo_imagem"] == "captura"
    assert detalhe["tipo_provisorio"] is True


def test_tipo_invalido_e_recusado(client):
    media_id = client.get("/api/midia").json()["itens"][0]["id"]
    r = client.post(f"/api/midia/{media_id}/tipo", json={"tipo": "meme"})
    assert r.status_code == 422
    assert "meme" in r.json()["detail"]


def test_lugar_herdado_de_longe_nao_entrega_a_cidade(client, migrated_engine):
    """D-025 na borda que o usuário enxerga.

    O motor já emitia só a evidência de país para uma herança de horas, mas
    o detalhe continuava devolvendo a cidade resolvida da coordenada — e a
    tela mostraria "Avignon" com a mesma cara de sempre. A regra tem de
    valer também aqui, senão a interface afirma o que ninguém apurou.
    """
    from fotoorganizer.models import Location, MediaFile

    factory = create_session_factory(migrated_engine)
    with factory() as session:
        local = Location(pais="França", regiao="Provence", cidade="Avignon",
                         fonte="offline:reverse_geocode", cache_key="43.9,4.8")
        session.add(local)
        session.flush()
        media = session.scalars(select(MediaFile)).first()
        media.location_id = local.id
        media.gps_lat = media.gps_lon = None          # sem GPS próprio
        media.gps_lat_estimado, media.gps_lon_estimado = 43.95, 4.81
        media.gps_estimado_delta_s = 4 * 3600          # 4 h de distância
        media_id = media.id
        session.commit()

    local = client.get(f"/api/midia/{media_id}").json()["local"]
    assert local["pais"] == "França"
    assert local["regiao"] is None
    assert local["cidade"] is None
    assert local["granularidade"] == "pais"
    assert local["estimado"] is True


def test_todo_namespace_gravado_tem_rotulo_legivel():
    """O usuário não precisa saber o que é "makernotes" — precisa saber de
    onde o dado veio. Namespace novo no extrator sem rótulo aqui vaza o nome
    técnico para a tela."""
    from fotoorganizer.metadata.exiftool import _GRUPOS
    from fotoorganizer.server.app import ROTULOS_NAMESPACE

    gravados = set(_GRUPOS.values()) | {"libraw", "apple", "google", "lightroom"}
    sem_rotulo = gravados - set(ROTULOS_NAMESPACE)
    assert not sem_rotulo, f"sem rótulo legível: {sorted(sem_rotulo)}"


def test_inventario_expoe_o_acervo_inteiro(client, migrated_engine):
    """O Panorama respondia só sobre o alcançável. Num acervo em NAS e HDs
    externos isso é a minoria — 5.191 de 100.164 num caso real."""
    from fotoorganizer.models import MediaFile, MediaRole, Source

    factory = create_session_factory(migrated_engine)
    with factory() as session:
        gaveta = Source(caminho="/Volumes/photo", apelido="photo",
                        disponivel=False)
        session.add(gaveta)
        session.flush()
        session.add(MediaFile(
            source_id=gaveta.id, caminho="lightroom://UUID-1",
            pasta="/Volumes/photo/Portfolio", nome="a.dng", extensao="dng",
            tamanho=1, arquivo_ausente=True, papel=MediaRole.SINAL,
        ))
        session.commit()

    inv = client.get("/api/inventario").json()
    assert inv["fotos"] > inv["alcancaveis"]
    gaveta_json = next(l for l in inv["lugares"] if l["raiz"] == "/Volumes/photo")
    assert gaveta_json["fotos"] == 1
    assert gaveta_json["alcancaveis"] == 0
    assert gaveta_json["so_no_catalogo"] == 1
    assert gaveta_json["fontes"] == ["photo"]


def test_media_diz_por_que_nao_da_para_abrir(client, migrated_engine):
    """A grade precisa separar "miniatura ainda vindo" de "não tenho o
    arquivo". Sem isso o navegador desenha imagem quebrada, e o dono — que
    abriu a fila num grupo 100% em volume desmontado — concluiu que a tela
    inteira estava quebrada."""
    from fotoorganizer.models import MediaFile, MediaRole, Source

    factory = create_session_factory(migrated_engine)
    with factory() as session:
        gaveta = Source(caminho="/Volumes/photo", apelido="photo",
                        disponivel=False)
        session.add(gaveta)
        session.flush()
        session.add(MediaFile(
            source_id=gaveta.id, caminho="/Volumes/photo/a.dng",
            pasta="/Volumes/photo", nome="a.dng", extensao="dng", tamanho=1,
        ))
        session.add(MediaFile(
            source_id=gaveta.id, caminho="apple://UUID-1", pasta="",
            nome="IMG_1.HEIC", extensao="heic", tamanho=1,
            arquivo_ausente=True, papel=MediaRole.SINAL,
        ))
        session.commit()

    itens = client.get("/api/midia", params={"busca": "a.dng"}).json()["itens"]
    assert itens[0]["motivo_indisponivel"] == "volume ou pasta fora de alcance"

    # Uma foto de fonte disponível não ganha marca nenhuma.
    outras = client.get("/api/midia", params={"busca": "img_0"}).json()["itens"]
    assert outras and outras[0]["motivo_indisponivel"] is None


def test_biblioteca_mostra_o_que_o_app_conhece(client, migrated_engine):
    """O dono mandou o app ler a biblioteca do Apple Fotos, ele leu 44.661
    fotos e a Biblioteca respondeu (0) — elas não têm arquivo local e ficavam
    invisíveis. Aparecer é diferente de ser organizável."""
    from fotoorganizer.models import MediaFile, MediaRole, Source

    factory = create_session_factory(migrated_engine)
    with factory() as session:
        apple = Source(caminho="/Users/eu/Fotos.photoslibrary",
                       apelido="Apple Fotos")
        session.add(apple)
        session.flush()
        session.add(MediaFile(
            source_id=apple.id, caminho="apple://UUID-1", pasta="",
            nome="IMG_1.HEIC", extensao="heic", tamanho=1,
            arquivo_ausente=True, papel=MediaRole.SINAL,
        ))
        session.commit()

    tudo = client.get("/api/midia", params={"alcance": "tudo"}).json()
    organizaveis = client.get(
        "/api/midia", params={"alcance": "organizaveis"}).json()
    faltantes = client.get("/api/midia", params={"alcance": "faltantes"}).json()

    assert tudo["total"] == organizaveis["total"] + faltantes["total"]
    assert faltantes["total"] >= 1
    assert any(i["nome"] == "IMG_1.HEIC" for i in tudo["itens"])
    assert not any(i["nome"] == "IMG_1.HEIC" for i in organizaveis["itens"])

    # A contagem da lateral conta o que a fonte CONHECE — era o (0).
    fontes = {f["apelido"]: f["fotos"] for f in client.get("/api/fontes").json()}
    assert fontes["Apple Fotos"] == 1

    assert client.get("/api/midia", params={"alcance": "xpto"}).status_code == 422


def test_fila_e_grupos_aceitam_recorte_por_fonte(client, migrated_engine):
    """A barra lateral passa a valer na Revisão e em Viagens — antes ela
    definia uma fonte que só a Biblioteca lia, e nas outras telas ficava
    visível e inerte."""
    from fotoorganizer.models import MediaFile, Source

    factory = create_session_factory(migrated_engine)
    with factory() as session:
        outra = Source(caminho="/outra/pasta", apelido="outra")
        session.add(outra)
        session.flush()
        outra_id = outra.id
        session.add(MediaFile(
            source_id=outra_id, caminho="/outra/pasta/z.jpg",
            pasta="/outra/pasta", nome="z.jpg", extensao="jpg", tamanho=1,
        ))
        session.commit()

    todas = client.get("/api/sugestoes").json()
    da_outra = client.get(
        "/api/sugestoes", params={"source_id": outra_id}).json()
    assert len(da_outra["itens"]) <= len(todas["itens"])
    assert all(True for _ in da_outra["itens"])

    # Grupo sem foto da fonte escolhida sai da lista: não é resultado vazio,
    # é um grupo que não pertence a este recorte.
    eventos = client.get("/api/eventos", params={"source_id": outra_id}).json()
    assert eventos == []
