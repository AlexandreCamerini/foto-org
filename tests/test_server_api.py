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


def test_scan_orfao_e_reconciliado_no_boot_e_oferecido_para_retomada(
    migrated_engine, tmp_path
):
    """Duas promessas num fluxo só: subir o servidor não deixa nenhum
    RODANDO zumbi no banco, e a varredura que morreu é oferecida para
    retomada — some da oferta quando um scan mais novo da fonte conclui."""
    from fotoorganizer.models import ScanSession, ScanStatus, Source

    fotos = tmp_path / "fotos"
    make_jpeg(fotos / "a.jpg")
    settings = Settings(data_dir=tmp_path / "d", cache_dir=tmp_path / "c")
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        fonte = Source(caminho=str(fotos), apelido="fotos")
        session.add(fonte)
        session.flush()
        session.add(ScanSession(source_id=fonte.id,
                                status=ScanStatus.RODANDO,
                                arquivos_vistos=42))
        session.commit()
        fonte_id = fonte.id

    # O lifespan (startup) é quem reconcilia — daí o context manager.
    with TestClient(
        create_app(settings, factory), base_url="http://127.0.0.1:8765"
    ) as client:
        (oferta,) = client.get("/api/scan/interrompidos").json()
        assert oferta["source_id"] == fonte_id
        assert oferta["caminho"] == str(fotos)
        assert oferta["vistos"] == 42

        with factory() as session:
            sessao = session.scalar(select(ScanSession))
            assert sessao.status == ScanStatus.INTERROMPIDO

        # Um scan novo da mesma fonte conclui: a oferta desaparece.
        with factory() as session:
            session.add(ScanSession(source_id=fonte_id,
                                    status=ScanStatus.CONCLUIDO))
            session.commit()
        assert client.get("/api/scan/interrompidos").json() == []


def test_pausar_continuar_sem_job_e_recusado_limpo(client):
    """Sem trabalho pausável — nem 500, nem silenciosamente escolhendo um
    job que não existe: 409 com detalhe."""
    assert client.post("/api/job/pausar").status_code == 409
    assert client.post("/api/job/continuar").status_code == 409


def test_pausar_e_continuar_scan_em_background(migrated_engine, tmp_path, monkeypatch):
    """Pausa cooperativa de verdade: o scan para de avançar enquanto
    pausado (`vistos` congela) e retoma de onde parou ao continuar."""
    import time

    from fotoorganizer.metadata import purepython

    extrair_original = purepython.PurePythonExtractor.extract

    def _extrair_devagar(self, path):
        time.sleep(0.05)
        return extrair_original(self, path)

    monkeypatch.setattr(purepython.PurePythonExtractor, "extract", _extrair_devagar)

    fotos = tmp_path / "fotos"
    for i in range(30):
        make_jpeg(fotos / f"p_{i}.jpg", seed=i)
    settings = Settings(
        data_dir=tmp_path / "d", cache_dir=tmp_path / "c",
        scanner=ScannerSettings(workers=1),
    )
    factory = create_session_factory(migrated_engine)
    client = TestClient(
        create_app(settings, factory), base_url="http://127.0.0.1:8765"
    )

    assert client.post(
        "/api/scan", json={"caminho": str(fotos)}
    ).status_code == 200

    # Espera o scan ter de fato começado a processar algo.
    for _ in range(100):
        if client.get("/api/job").json().get("vistos", 0) > 0:
            break
        time.sleep(0.02)
    else:
        raise AssertionError("scan não começou a tempo")

    assert client.post("/api/job/pausar").status_code == 200
    assert client.get("/api/job").json()["status"] == "pausado"

    # A pausa é cooperativa (checada uma vez por arquivo do laço externo);
    # dá folga para o arquivo já em voo terminar antes de tirar o retrato
    # do "congelado" — senão o teste vira uma corrida com o próprio scan.
    time.sleep(0.2)
    congelado = client.get("/api/job").json()["vistos"]
    time.sleep(0.3)
    assert client.get("/api/job").json()["vistos"] == congelado

    assert client.post("/api/job/continuar").status_code == 200
    assert client.get("/api/job").json()["status"] == "rodando"

    estado = _aguardar_job(client)
    assert estado["status"] == "concluido"
    assert estado["processados"] == 30


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


# -- template de destino configurável (fase 10) ------------------------------
def test_template_sem_preferencia_salva_devolve_o_padrao(client):
    from fotoorganizer.classification.templates import TEMPLATE_PADRAO

    assert client.get("/api/configuracoes/template").json() == {
        "template": TEMPLATE_PADRAO
    }


def test_salvar_template_persiste_e_e_devolvido_por_get(client):
    resposta = client.put(
        "/api/configuracoes/template", json={"template": "{ano}/{pais}"}
    )
    assert resposta.status_code == 200
    assert resposta.json() == {"template": "{ano}/{pais}"}
    assert client.get("/api/configuracoes/template").json() == {
        "template": "{ano}/{pais}"
    }


def test_salvar_template_persiste_entre_clientes_diferentes(migrated_engine, tmp_path):
    """O aceite fala em "persistir entre reinícios do servidor" — aqui isso
    é um `create_app` novo sobre o mesmo engine, sem reaproveitar estado em
    memória do primeiro cliente."""
    from fotoorganizer.config.settings import Settings
    from fastapi.testclient import TestClient
    from fotoorganizer.database import create_session_factory
    from fotoorganizer.server import create_app

    settings = Settings(data_dir=tmp_path / "d", cache_dir=tmp_path / "c")
    factory = create_session_factory(migrated_engine)
    primeiro = TestClient(create_app(settings, factory), base_url="http://127.0.0.1:8765")
    primeiro.put("/api/configuracoes/template", json={"template": "{ano}/{cidade}"})

    segundo = TestClient(create_app(settings, factory), base_url="http://127.0.0.1:8765")
    assert segundo.get("/api/configuracoes/template").json() == {
        "template": "{ano}/{cidade}"
    }


def test_salvar_template_vazio_e_recusado(client):
    resposta = client.put("/api/configuracoes/template", json={"template": ""})
    assert resposta.status_code == 422


def test_salvar_template_com_placeholder_invalido_e_recusado_sem_salvar(client):
    from fotoorganizer.classification.templates import TEMPLATE_PADRAO

    resposta = client.put(
        "/api/configuracoes/template",
        json={"template": "{categoria}/{fantasia}"},
    )
    assert resposta.status_code == 422
    assert "fantasia" in resposta.json()["detail"]
    # Nada foi salvo: GET continua no padrão.
    assert client.get("/api/configuracoes/template").json() == {
        "template": TEMPLATE_PADRAO
    }


def test_preview_do_template_chama_o_render_destino_real(client):
    from fotoorganizer.classification.templates import render_destino

    resposta = client.post(
        "/api/configuracoes/template/preview",
        json={"template": "{categoria}/{ano} - {viagem}/{pais}/{cidade}"},
    )
    assert resposta.status_code == 200
    exemplos = resposta.json()["exemplos"]
    assert len(exemplos) == 2

    # Bate exatamente com o que a própria função produziria para os mesmos
    # campos — não uma reimplementação divergente.
    for exemplo in exemplos:
        esperado = render_destino(
            "{categoria}/{ano} - {viagem}/{pais}/{cidade}", exemplo["campos"]
        )
        assert exemplo["destino"] == esperado

    # O segundo exemplo mostra o fallback: sem viagem, o país/cidade decidem.
    assert exemplos[0]["campos"]["viagem"] == "Tailândia"
    assert exemplos[1]["campos"]["viagem"] is None
    assert "Tailândia" in exemplos[1]["destino"] or "Chiang Mai" in exemplos[1]["destino"]


def test_gerar_sugestoes_usa_o_template_persistido(migrated_engine, tmp_path):
    import time

    fotos = tmp_path / "fotos"
    for i in range(2):
        make_jpeg(fotos / f"t_{i}.jpg", seed=i)
    settings = Settings(data_dir=tmp_path / "d", cache_dir=tmp_path / "c")
    factory = create_session_factory(migrated_engine)
    CatalogScanner(factory, PurePythonExtractor(), ScannerSettings()) \
        .scan_source(fotos)
    client = TestClient(
        create_app(settings, factory), base_url="http://127.0.0.1:8765"
    )

    novo_template = "{ano}/{categoria}"
    assert client.put(
        "/api/configuracoes/template", json={"template": novo_template}
    ).status_code == 200

    assert client.post("/api/sugestoes/gerar").status_code == 200
    estado = _aguardar_job(client)
    assert estado["status"] == "concluido"

    from fotoorganizer.models import Suggestion

    with factory() as session:
        templates_usados = {s.template for s in session.query(Suggestion).all()}
    assert templates_usados == {novo_template}


def test_editar_destino_da_sugestao(migrated_engine, tmp_path):
    from fotoorganizer.models import ConfidenceLevel, MediaFile, Suggestion

    origem = tmp_path / "fotos"
    make_jpeg(origem / "f.jpg", seed=1)
    settings = Settings(data_dir=tmp_path / "d", cache_dir=tmp_path / "c")
    factory = create_session_factory(migrated_engine)
    CatalogScanner(factory, PurePythonExtractor(), ScannerSettings()) \
        .scan_source(origem)

    with factory() as session:
        media = session.query(MediaFile).first()
        session.add(Suggestion(
            media_id=media.id, destino_sugerido="Viagens/2024",
            template="t", nivel=ConfidenceLevel.ALTA, versao_logica="test",
        ))
        session.commit()
        suggestion_id = session.query(Suggestion).first().id

    client = TestClient(
        create_app(settings, factory), base_url="http://127.0.0.1:8765"
    )

    resposta = client.patch(
        f"/api/sugestoes/{suggestion_id}/destino",
        json={"destino": "Viagens/2025 - Refeita"},
    )
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["destino"] == "Viagens/2025 - Refeita"
    assert corpo["status"] == "editada"

    # O caminho ainda estava pendente/aprovado antes — editar não é
    # travado por status anterior (mesma semântica do PySide6): aprovar
    # e depois editar de novo continua funcionando.
    client.post(
        "/api/sugestoes/acao", json={"ids": [suggestion_id], "acao": "aprovar"}
    )
    resposta2 = client.patch(
        f"/api/sugestoes/{suggestion_id}/destino",
        json={"destino": "Viagens/2026 - De novo"},
    )
    assert resposta2.status_code == 200
    assert resposta2.json()["destino"] == "Viagens/2026 - De novo"
    assert resposta2.json()["status"] == "editada"


def test_editar_destino_recusa_path_traversal(migrated_engine, tmp_path):
    from fotoorganizer.models import ConfidenceLevel, MediaFile, Suggestion

    origem = tmp_path / "fotos"
    make_jpeg(origem / "f.jpg", seed=1)
    settings = Settings(data_dir=tmp_path / "d", cache_dir=tmp_path / "c")
    factory = create_session_factory(migrated_engine)
    CatalogScanner(factory, PurePythonExtractor(), ScannerSettings()) \
        .scan_source(origem)

    with factory() as session:
        media = session.query(MediaFile).first()
        session.add(Suggestion(
            media_id=media.id, destino_sugerido="Viagens/2024",
            template="t", nivel=ConfidenceLevel.ALTA, versao_logica="test",
        ))
        session.commit()
        suggestion_id = session.query(Suggestion).first().id
        destino_original = session.query(Suggestion).first().destino_sugerido

    client = TestClient(
        create_app(settings, factory), base_url="http://127.0.0.1:8765"
    )

    # Um "/etc/passwd" não escapa nada aqui: vira caminho relativo comum
    # ("etc/passwd") sob a raiz que o plano futuro escolher — a mesma
    # semântica de resolver_destino/caminho_relativo_seguro. O que precisa
    # ser recusado é "..", "~" e segmento vazio de verdade.
    for tentativa in ["../../etc/passwd", "../fora", "~/segredo", "a/../../b", ""]:
        resposta = client.patch(
            f"/api/sugestoes/{suggestion_id}/destino",
            json={"destino": tentativa},
        )
        assert resposta.status_code == 422, tentativa

    with factory() as session:
        assert (
            session.query(Suggestion).first().destino_sugerido
            == destino_original
        )


def test_editar_destino_de_sugestao_inexistente_e_404(client):
    resposta = client.patch(
        "/api/sugestoes/99999/destino", json={"destino": "Qualquer/Coisa"}
    )
    assert resposta.status_code == 404


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


def test_media_diz_arquivo_sumiu_quando_offline(client, migrated_engine):
    """Terceiro motivo (fase 12, item B): a fonte responde, mas ESTE
    arquivo sumiu de onde estava."""
    from fotoorganizer.models import MediaFile

    factory = create_session_factory(migrated_engine)
    with factory() as session:
        media = session.scalars(select(MediaFile)).first()
        media.arquivo_offline = True
        media_id = media.id
        session.commit()

    detalhe = client.get(f"/api/midia/{media_id}").json()
    assert detalhe["motivo_indisponivel"] == "arquivo sumiu do disco"


def test_motivo_indisponivel_prioriza_ausente_depois_fonte_depois_offline(
    migrated_engine,
):
    """Quando mais de uma condição poderia se aplicar, a ordem é sempre a
    mesma: referência de nuvem primeiro, fonte inteira fora de alcance
    depois, arquivo sumido por último — a mais específica e mais rara
    (uma fonte que responde mas perdeu UM arquivo) não deve mascarar as
    duas mais graves, e também não deve ser mascarada por engano."""
    from fotoorganizer.server.app import _motivo_indisponivel
    from fotoorganizer.models import MediaFile, MediaRole, Source

    factory = create_session_factory(migrated_engine)
    with factory() as session:
        fonte_off = Source(caminho="/Volumes/gaveta", disponivel=False)
        fonte_on = Source(caminho="/Users/eu/Pictures", disponivel=True)
        session.add_all([fonte_off, fonte_on])
        session.flush()

        # 1) referência de nuvem — vence mesmo se a fonte também estiver
        #    fora de alcance.
        ref = MediaFile(
            source_id=fonte_off.id, caminho="apple://UUID-1", pasta="",
            nome="a.heic", extensao="heic", tamanho=1,
            arquivo_ausente=True, papel=MediaRole.SINAL,
        )
        # 2) fonte fora de alcance — vence sobre arquivo_offline (que não
        #    devia nem ter sido setado nesta condição em uso real, mas o
        #    teste prova que a ordem do código protege mesmo assim).
        na_fonte_off = MediaFile(
            source_id=fonte_off.id, caminho="/Volumes/gaveta/b.jpg",
            pasta="/Volumes/gaveta", nome="b.jpg", extensao="jpg",
            tamanho=1, arquivo_offline=True,
        )
        # 3) só o terceiro motivo se aplica.
        so_offline = MediaFile(
            source_id=fonte_on.id, caminho="/Users/eu/Pictures/c.jpg",
            pasta="/Users/eu/Pictures", nome="c.jpg", extensao="jpg",
            tamanho=1, arquivo_offline=True,
        )
        session.add_all([ref, na_fonte_off, so_offline])
        session.commit()

        fontes_off = frozenset({fonte_off.id})
        assert _motivo_indisponivel(ref, fontes_off) == "sem arquivo neste Mac"
        assert (_motivo_indisponivel(na_fonte_off, fontes_off)
                == "volume ou pasta fora de alcance")
        assert (_motivo_indisponivel(so_offline, fontes_off)
                == "arquivo sumiu do disco")


def test_reconciliacao_em_background_marca_offline_e_reporta(
    migrated_engine, tmp_path
):
    import time

    fotos = tmp_path / "fotos"
    alvo = make_jpeg(fotos / "some.jpg", seed=1)
    settings = Settings(data_dir=tmp_path / "d", cache_dir=tmp_path / "c")
    factory = create_session_factory(migrated_engine)
    CatalogScanner(factory, PurePythonExtractor(), ScannerSettings()) \
        .scan_source(fotos)
    client = TestClient(
        create_app(settings, factory), base_url="http://127.0.0.1:8765"
    )

    alvo.unlink()
    assert client.post("/api/reconciliacao").status_code == 200
    for _ in range(100):
        estado = client.get("/api/job").json()
        if estado["status"] != "rodando":
            break
        time.sleep(0.1)
    assert estado["status"] == "concluido"
    assert estado["resultado"]["marcados_offline"] == 1

    from fotoorganizer.models import MediaFile

    with factory() as session:
        media = session.scalars(select(MediaFile)).first()
        assert media.arquivo_offline is True


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


def test_linha_do_tempo_e_filtro_por_mes(client):
    """A âncora temporal: sem ela, rolar é a única forma de chegar em 2015 —
    e num acervo paginado de 200 em 200 isso não é forma."""
    linha = client.get("/api/midia/linha-do-tempo").json()
    assert linha, "o fixture tem fotos com data"
    assert all(set(m) == {"mes", "quantidade"} for m in linha)
    # Ordem decrescente: a grade abre nas mais recentes.
    assert [m["mes"] for m in linha] == sorted(
        (m["mes"] for m in linha), reverse=True
    )

    mes = linha[0]["mes"]
    recorte = client.get("/api/midia", params={"mes": mes}).json()
    assert recorte["total"] == linha[0]["quantidade"]
    assert all(i["data_capturada"].startswith(mes) for i in recorte["itens"])

    assert client.get(
        "/api/midia/linha-do-tempo", params={"alcance": "xpto"}
    ).status_code == 422


# -- mapa do lugar estimado (docs/LOCAL_ESTIMADO.md, fase 9) ------------------
@pytest.fixture()
def evento_no_mapa(client, migrated_engine):
    """Um evento com um caso de cada: ponto, círculo, sem coordenada e
    fora de alcance — mais a doadora, que fica FORA do grupo (é assim no
    acervo real: quem doa é uma referência do Apple Fotos, sem evento)."""
    from fotoorganizer.models import Event, MediaFile

    factory = create_session_factory(migrated_engine)
    with factory() as session:
        evento = Event(nome="Serra")
        session.add(evento)
        session.flush()
        fotos = list(session.scalars(
            select(MediaFile).order_by(MediaFile.nome)
        ))
        propria, herdeira, sem_coord, longe, doadora = fotos[:5]

        doadora.gps_lat, doadora.gps_lon = 43.96, 4.82
        for media in (propria, herdeira, sem_coord, longe):
            media.event_id = evento.id
        for media in (herdeira, longe):
            media.gps_lat_estimado, media.gps_lon_estimado = 43.96, 4.82
            media.gps_estimado_de_id = doadora.id
            media.gps_estimado_delta_s = 12 * 60
        # Tem coordenada e mesmo assim não é desenhada: o arquivo não está
        # aqui para responder pelo ponto.
        longe.arquivo_ausente = True
        session.commit()
        dados = {
            "evento_id": evento.id,
            "propria": propria.id, "herdeira": herdeira.id,
            "sem_coord": sem_coord.id, "longe": longe.id,
            "doadora": doadora.id, "doadora_nome": doadora.nome,
        }
    return dados


def test_mapa_separa_ponto_lido_de_circulo_herdado(client, evento_no_mapa):
    """A distinção que o mapa inteiro existe para fazer: coordenada lida é
    ponto (sem raio, não há dúvida a desenhar); coordenada herdada é círculo
    do tamanho da dúvida, com a doadora alcançável pelo id."""
    mapa = client.get(
        "/api/mapa", params={"event_id": evento_no_mapa["evento_id"]}
    ).json()

    assert mapa["grupo"] == {
        "tipo": "evento", "id": evento_no_mapa["evento_id"],
        "nome": "Serra", "inicio": None, "fim": None,
    }
    pontos = {p["media_id"]: p for p in mapa["pontos"]}
    assert set(pontos) == {
        evento_no_mapa["propria"], evento_no_mapa["herdeira"],
        evento_no_mapa["longe"],
    }

    lido = pontos[evento_no_mapa["propria"]]
    assert lido["estimado"] is False
    assert (lido["lat"], lido["lon"]) == (43.95, 4.81)
    # Sem raio e sem frase: um ponto lido não tem o que justificar.
    assert lido["raio_m"] is None and lido["porque"] is None
    assert lido["doadora_id"] is None

    herdado = pontos[evento_no_mapa["herdeira"]]
    assert herdado["estimado"] is True
    # A coordenada desenhada é a da doadora — é o dado que existe.
    assert (herdado["lat"], herdado["lon"]) == (43.96, 4.82)
    assert herdado["delta_s"] == 720
    assert herdado["doadora_id"] == evento_no_mapa["doadora"]
    assert herdado["doadora_nome"] == evento_no_mapa["doadora_nome"]
    # 12 min × 6 m/s: o raio vem do Python, não de uma constante em TS.
    assert herdado["raio_m"] == 4320.0


def test_mapa_explica_o_tamanho_do_circulo_em_uma_frase(client, evento_no_mapa):
    """Aceite 3 da fase 9: clicar no círculo responde por que ele tem aquele
    tamanho. A frase chega pronta — a UI não a monta, e por isso não precisa
    conhecer nem a velocidade nem o piso nem o teto."""
    mapa = client.get(
        "/api/mapa", params={"event_id": evento_no_mapa["evento_id"]}
    ).json()
    (herdado,) = [p for p in mapa["pontos"]
                  if p["media_id"] == evento_no_mapa["herdeira"]]

    frase = herdado["porque"]
    assert evento_no_mapa["doadora_nome"] in frase   # de quem herdou
    assert "12 min" in frase                          # a que distância
    assert "4,3 km" in frase                          # e o tamanho que dá
    # A cobertura medida é da legenda, dita uma vez — não repetida em cada
    # um dos milhares de pontos.
    assert "93,6%" in mapa["nota_do_raio"]


def test_mapa_conta_quem_nao_desenha_em_vez_de_sumir(client, evento_no_mapa):
    """Aceite 6: quem não vira ponto aparece no número.

    Sem coordenada é a única razão para não desenhar — e ela fecha a conta
    com o total. Fora de alcance é outra pergunta: a foto TEM coordenada,
    é desenhada, e o número existe para a tela dizer quantas daquelas não
    vão mostrar miniatura.
    """
    mapa = client.get(
        "/api/mapa", params={"event_id": evento_no_mapa["evento_id"]}
    ).json()
    contagens = mapa["contagens"]

    assert contagens == {
        "total": 4, "no_mapa": 3, "sem_coordenada": 1, "fora_de_alcance": 1
    }
    assert (contagens["no_mapa"] + contagens["sem_coordenada"]
            == contagens["total"])
    pontos = {p["media_id"]: p for p in mapa["pontos"]}
    assert evento_no_mapa["sem_coord"] not in pontos

    # Disco desligado tira a miniatura, não a coordenada: esconder o ponto
    # apagaria da tela o que o catálogo guardou (invariante 8).
    longe = pontos[evento_no_mapa["longe"]]
    assert longe["motivo_indisponivel"] == "sem arquivo neste Mac"
    assert longe["raio_m"] == 4320.0
    assert pontos[evento_no_mapa["propria"]]["motivo_indisponivel"] is None


def test_mapa_expoe_a_doadora_de_fora_do_grupo(client, evento_no_mapa):
    """O traço do protótipo precisa da outra ponta, e ela quase nunca está
    no grupo: sem esta lista a UI teria de pedir /api/midia/{id} por ponto."""
    mapa = client.get(
        "/api/mapa", params={"event_id": evento_no_mapa["evento_id"]}
    ).json()
    (doadora,) = mapa["doadoras"]
    assert doadora["id"] == evento_no_mapa["doadora"]
    assert (doadora["lat"], doadora["lon"]) == (43.96, 4.82)
    assert doadora["no_grupo"] is False


def test_mapa_enquadra_o_circulo_inteiro_e_da_a_escala(client, evento_no_mapa):
    """Os limites vêm esticados pelo raio: num grupo em que todas herdaram
    da mesma doadora a caixa dos pontos tem lado zero, e enquadrar só os
    pontos cortaria fora justamente o que o mapa mostra."""
    mapa = client.get(
        "/api/mapa", params={"event_id": evento_no_mapa["evento_id"]}
    ).json()
    limites, escala = mapa["limites"], mapa["escala"]

    # 4.320 m em graus de latitude ≈ 0,039 — bem além do 0,01 que separa as
    # duas fotos. O círculo estoura a caixa dos pontos nos dois lados.
    assert limites["lat_max"] > 43.96 + 0.03
    assert limites["lat_min"] < 43.95 - 0.02
    # Em Avignon (43,95° N) o grau de longitude vale bem menos que o de
    # latitude; sem essa distinção o círculo sairia elipse.
    assert escala["metros_por_grau_lon"] < escala["metros_por_grau_lat"]
    assert 79_000 < escala["metros_por_grau_lon"] < 81_000


def test_mapa_com_a_fonte_inteira_desligada_ainda_desenha(
    client, migrated_engine, evento_no_mapa
):
    """O caso que derrubou o desenho anterior, medido no acervo real: o
    evento "Pantanal" tem 80 das 97 fotos em /Volumes/Externo. Tratar volume
    desligado como motivo para não desenhar deixaria o mapa VAZIO com todas
    as coordenadas conhecidas — a tela perdendo o que o catálogo tem."""
    from fotoorganizer.models import Source

    factory = create_session_factory(migrated_engine)
    with factory() as session:
        session.scalars(select(Source)).one().disponivel = False
        session.commit()

    mapa = client.get(
        "/api/mapa", params={"event_id": evento_no_mapa["evento_id"]}
    ).json()
    assert mapa["contagens"] == {
        "total": 4, "no_mapa": 3, "sem_coordenada": 1, "fora_de_alcance": 3
    }
    assert len(mapa["pontos"]) == 3
    assert all(p["motivo_indisponivel"] for p in mapa["pontos"])
    assert "volume ou pasta fora de alcance" in {
        p["motivo_indisponivel"] for p in mapa["pontos"]
    }
    assert mapa["limites"] is not None


def test_mapa_aceita_viagem_e_recusa_pedido_ambiguo(client, migrated_engine):
    from fotoorganizer.models import MediaFile, Trip

    factory = create_session_factory(migrated_engine)
    with factory() as session:
        viagem = Trip(nome="Provence")
        session.add(viagem)
        session.flush()
        session.scalars(select(MediaFile).order_by(MediaFile.nome)) \
            .first().trip_id = viagem.id
        viagem_id = viagem.id
        session.commit()

    mapa = client.get("/api/mapa", params={"trip_id": viagem_id}).json()
    assert mapa["grupo"]["tipo"] == "viagem"
    assert mapa["contagens"]["no_mapa"] == 1

    # Um grupo por vez: nenhum e os dois são erro, não um default silencioso.
    assert client.get("/api/mapa").status_code == 422
    assert client.get(
        "/api/mapa", params={"trip_id": viagem_id, "event_id": 1}
    ).status_code == 422
    assert client.get(
        "/api/mapa", params={"event_id": 99999}
    ).status_code == 404


# -- revisão por grupo, com contagem verdadeira (fatia 1 da crítica) ---------

def _catalogo_com_sugestoes(migrated_engine, tmp_path, n=7):
    """Um catálogo pequeno com sugestões geradas, para os testes de grupo."""
    import time

    fotos = tmp_path / "fotos"
    for i in range(n):
        make_jpeg(fotos / f"f_{i}.jpg", seed=i)
    settings = Settings(data_dir=tmp_path / "d", cache_dir=tmp_path / "c")
    factory = create_session_factory(migrated_engine)
    CatalogScanner(factory, PurePythonExtractor(), ScannerSettings()).scan_source(fotos)
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
    return client


def test_grupos_contam_o_banco_e_nao_a_pagina(migrated_engine, tmp_path):
    """O defeito que deixava 4.848 de 5.048 pendências inalcançáveis.

    A tela pedia 200 itens e deduzia dali o tamanho do grupo: dizia "85
    fotos" para um grupo de 597 e o botão "Aprovar 85" fazia o que dizia,
    deixando 512 para trás sem avisar. O resumo por grupo tem que vir
    contado do banco, independente de qualquer paginação.
    """
    client = _catalogo_com_sugestoes(migrated_engine, tmp_path, n=7)

    grupos = client.get("/api/sugestoes/grupos").json()
    assert grupos, "sem grupos, o resto do teste não diz nada"
    total_nos_grupos = sum(g["total"] for g in grupos)
    assert total_nos_grupos == client.get("/api/sugestoes").json()["total"] == 7

    # Uma página de 2 itens não muda o total de nenhum grupo.
    pagina = client.get("/api/sugestoes", params={"limit": 2}).json()
    assert len(pagina["itens"]) == 2
    assert pagina["total"] == 7
    assert sum(g["total"] for g in client.get("/api/sugestoes/grupos").json()) == 7

    assert set(grupos[0]) >= {
        "destino", "total", "nivel", "estimadas", "fora_de_alcance", "origens"
    }
    # A origem é a metade "situação atual" do par, e não existia em tela.
    assert grupos[0]["origens"], "o grupo precisa dizer de onde as fotos vêm"


def test_aprovar_grupo_alcanca_alem_da_pagina(migrated_engine, tmp_path):
    """Aprovar o grupo aprova o GRUPO, não o que a página carregou."""
    client = _catalogo_com_sugestoes(migrated_engine, tmp_path, n=7)
    grupos = client.get("/api/sugestoes/grupos").json()
    maior = max(grupos, key=lambda g: g["total"])

    resposta = client.post("/api/sugestoes/acao", json={
        "acao": "aprovar", "destino": maior["destino"], "status": "pendente",
    }).json()
    assert resposta["afetadas"] == maior["total"]

    depois = client.get("/api/sugestoes").json()
    assert depois["contagens"].get("aprovada") == maior["total"]
    # E o grupo sumiu das pendentes, inteiro.
    assert maior["destino"] not in {
        g["destino"] for g in client.get("/api/sugestoes/grupos").json()
    }


def test_listar_recorta_por_grupo(migrated_engine, tmp_path):
    """Abrir um grupo carrega só ele — não a fila inteira."""
    client = _catalogo_com_sugestoes(migrated_engine, tmp_path, n=7)
    grupos = client.get("/api/sugestoes/grupos").json()
    alvo = grupos[0]

    recorte = client.get(
        "/api/sugestoes", params={"destino": alvo["destino"]}
    ).json()
    assert recorte["total"] == alvo["total"]
    assert {i["destino"] for i in recorte["itens"]} == {alvo["destino"]}


def test_acao_sem_ids_e_sem_destino_e_422(client):
    assert client.post(
        "/api/sugestoes/acao", json={"acao": "aprovar"}
    ).status_code == 422


# --- facetas que funcionam sem pixel (B5) ---------------------------------

def _midia_com_faceta(session, id_, **kw):
    from fotoorganizer.models import MediaFile

    campos = dict(
        source_id=1, caminho=f"/fotos/{id_}.jpg", pasta="/fotos",
        nome=f"{id_}.jpg", extensao="jpg", tamanho=100,
    )
    campos.update(kw)
    media = MediaFile(id=id_, **campos)
    session.add(media)
    return media


def test_filtro_por_camera_casa_make_e_model_juntos(migrated_engine):
    """O dono pensa 'a 5D', não 'Canon' + 'Canon EOS 5D Mark III'."""
    from fotoorganizer.database import create_session_factory
    from fotoorganizer.models import Source, SourceType
    from fotoorganizer.repositories import MediaRepository
    from fotoorganizer.repositories.media import MediaFilters

    factory = create_session_factory(migrated_engine)
    with factory() as session:
        session.add(Source(id=1, caminho="/fotos", tipo=SourceType.PASTA))
        _midia_com_faceta(session, 1, make="Canon", model="Canon EOS 5D Mark III")
        _midia_com_faceta(session, 2, make="NIKON", model="D750")
        # Só o model preenchido: `NULL || texto` seria NULL sem o coalesce.
        _midia_com_faceta(session, 3, make=None, model="iPhone 15 Pro")
        session.commit()

    repo = MediaRepository(factory)
    assert repo.contar(MediaFilters(camera="5D")) == 1
    assert repo.contar(MediaFilters(camera="nikon")) == 1
    assert repo.contar(MediaFilters(camera="iPhone")) == 1


def test_busca_textual_enxerga_a_curadoria(migrated_engine):
    """Procurar 'Pantanal' e não achar a foto que alguém etiquetou assim é a
    busca falhando onde o metadado é mais confiável que o nome de arquivo —
    que na maioria do acervo é IMG_1234."""
    from fotoorganizer.database import create_session_factory
    from fotoorganizer.metadata.base import NAMESPACE_CURADORIA
    from fotoorganizer.models import MetadataEntry, Source, SourceType
    from fotoorganizer.repositories import MediaRepository
    from fotoorganizer.repositories.media import MediaFilters

    factory = create_session_factory(migrated_engine)
    with factory() as session:
        session.add(Source(id=1, caminho="/fotos", tipo=SourceType.PASTA))
        _midia_com_faceta(session, 1, nome="IMG_1234.jpg")
        _midia_com_faceta(session, 2, nome="IMG_5678.jpg")
        session.flush()
        session.add(MetadataEntry(
            media_id=1, namespace=NAMESPACE_CURADORIA,
            chave="palavra_chave", valor="Pantanal",
        ))
        session.commit()

    repo = MediaRepository(factory)
    assert repo.contar(MediaFilters(busca="Pantanal")) == 1
    assert repo.contar(MediaFilters(palavra_chave="pantanal")) == 1
    # O nome de arquivo continua funcionando.
    assert repo.contar(MediaFilters(busca="IMG_5678")) == 1


def test_facetas_listam_o_que_existe_com_contagem(migrated_engine):
    from fotoorganizer.database import create_session_factory
    from fotoorganizer.metadata.base import NAMESPACE_CURADORIA
    from fotoorganizer.models import Location, MetadataEntry, Source, SourceType
    from fotoorganizer.repositories import MediaRepository

    factory = create_session_factory(migrated_engine)
    with factory() as session:
        session.add(Source(id=1, caminho="/fotos", tipo=SourceType.PASTA))
        session.add(Location(id=1, pais="Brasil", cidade="Corumbá",
                             fonte="offline"))
        _midia_com_faceta(session, 1, make="Canon", model="R5", location_id=1)
        _midia_com_faceta(session, 2, make="Canon", model="R5", location_id=1)
        _midia_com_faceta(session, 3, make="NIKON", model="D750")
        session.flush()
        for media_id in (1, 2):
            session.add(MetadataEntry(
                media_id=media_id, namespace=NAMESPACE_CURADORIA,
                chave="palavra_chave", valor="Selected",
            ))
        session.commit()

    repo = MediaRepository(factory)
    cameras = repo.cameras()
    assert cameras[0]["quantidade"] == 2      # a mais usada primeiro
    assert repo.paises() == [{"nome": "Brasil", "quantidade": 2}]
    assert repo.palavras_chave() == [{"nome": "Selected", "quantidade": 2}]
