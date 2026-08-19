"""Cobertura HTTP de `/api/genai-pasta/*` (fotoorganizer/server/app.py, Fase
7, plano 07-04) — o gate de DOIS consentimentos (T-07-04-01), zero chamada
externa com o recurso desligado, e o 502 never-crash quando a API falha
(T-07-04-05).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from fotoorganizer.classification.location_advisor import PropostaDoModelo
from fotoorganizer.config.settings import PrivacySettings, Settings
from fotoorganizer.database import create_session_factory
from fotoorganizer.models import Evidence, MediaFile, Source
from fotoorganizer.repositories.settings import SettingsRepository
from fotoorganizer.server import create_app


class _ClassificadorFalso:
    """Fake `ClassificadorDePasta` — nunca toca rede. `chamadas` conta
    quantas vezes `classificar()` rodou, para provar zero chamadas com o
    gate fechado (T-07-04-01)."""

    def __init__(self, respostas=None, excecao=None) -> None:
        self._respostas = respostas if respostas is not None else []
        self._excecao = excecao
        self.chamadas = 0

    @property
    def local(self) -> bool:
        return False

    def corpo_da_chamada(self, pastas) -> dict:
        if not pastas:
            return {}
        return {"model": "fake", "max_tokens": 1000,
                "pastas": [p.pasta for p in pastas]}

    def classificar(self, pastas):
        self.chamadas += 1
        if self._excecao is not None:
            raise self._excecao
        return self._respostas


def _fonte(session) -> Source:
    source = Source(caminho="/Users/eu/Pictures", apelido="scan")
    session.add(source)
    session.flush()
    return source


def _arquivo(session, source, pasta, nome) -> MediaFile:
    media = MediaFile(
        source_id=source.id, caminho=f"{pasta}/{nome}", pasta=pasta,
        nome=nome, extensao=nome.rsplit(".", 1)[-1].lower(), tamanho=1,
    )
    session.add(media)
    session.flush()
    return media


@pytest.fixture()
def factory(migrated_engine):
    return create_session_factory(migrated_engine)


@pytest.fixture()
def duas_candidatas(factory):
    """Duas pastas candidatas (categoria E cidade/país vazios): "Peru 2023"
    (vai receber resposta do fake) e "Sem Resposta 2023" (fica de fora da
    resposta do fake, para provar `pastas_sem_resposta`)."""
    with factory() as session:
        source = _fonte(session)
        _arquivo(session, source, "Peru 2023", "img_0.jpg")
        _arquivo(session, source, "Sem Resposta 2023", "img_0.jpg")
        session.commit()
    return factory


def _settings(tmp_path, *, servicos_externos: bool) -> Settings:
    return Settings(
        data_dir=tmp_path / "d", cache_dir=tmp_path / "c",
        privacidade=PrivacySettings(servicos_externos=servicos_externos),
    )


def _cliente(settings: Settings, factory, classificador=None) -> TestClient:
    return TestClient(
        create_app(settings, factory, classificador_pasta_genai=classificador),
        base_url="http://127.0.0.1:8765",
    )


def _resposta_peru() -> PropostaDoModelo:
    return PropostaDoModelo(
        pasta="Peru 2023", cidade="Cusco", pais="Peru",
        categoria="Viagens", evento=None,
        justificativa="nome da pasta é um topônimo conhecido",
    )


# -- config: GET/PUT, gate de dois consentimentos ---------------------------

def test_config_tudo_desligado_por_padrao(tmp_path, factory):
    settings = _settings(tmp_path, servicos_externos=False)
    client = _cliente(settings, factory)

    resposta = client.get("/api/genai-pasta/config")

    assert resposta.status_code == 200
    assert resposta.json() == {
        "servicos_externos": False,
        "classificacao_pasta_genai": False,
    }


def test_habilitar_com_mestre_desligado_devolve_409_com_mensagem_exata(
    tmp_path, factory
):
    settings = _settings(tmp_path, servicos_externos=False)
    client = _cliente(settings, factory)

    resposta = client.put("/api/genai-pasta/config", json={"habilitado": True})

    assert resposta.status_code == 409
    assert resposta.json()["detail"] == (
        "Serviços externos estão desligados nas configurações do app — "
        "habilite [privacidade] servicos_externos antes de usar este "
        "recurso."
    )


def test_habilitar_com_mestre_ligado_grava_e_get_seguinte_reflete(
    tmp_path, factory
):
    settings = _settings(tmp_path, servicos_externos=True)
    client = _cliente(settings, factory)

    resposta_put = client.put("/api/genai-pasta/config", json={"habilitado": True})
    assert resposta_put.status_code == 200
    assert resposta_put.json() == {
        "servicos_externos": True,
        "classificacao_pasta_genai": True,
    }

    resposta_get = client.get("/api/genai-pasta/config")
    assert resposta_get.json() == {
        "servicos_externos": True,
        "classificacao_pasta_genai": True,
    }


# -- gate fechado: 409 e ZERO chamadas externas (T-07-04-01) ----------------

def test_candidatas_com_gate_desligado_devolve_409_sem_chamar_classificador(
    tmp_path, duas_candidatas
):
    settings = _settings(tmp_path, servicos_externos=False)
    fake = _ClassificadorFalso()
    client = _cliente(settings, duas_candidatas, classificador=fake)

    resposta = client.get("/api/genai-pasta/candidatas")

    assert resposta.status_code == 409
    assert fake.chamadas == 0


def test_rodar_com_gate_desligado_devolve_409_e_nada_e_gravado(
    tmp_path, duas_candidatas
):
    settings = _settings(tmp_path, servicos_externos=False)
    fake = _ClassificadorFalso(respostas=[_resposta_peru()])
    client = _cliente(settings, duas_candidatas, classificador=fake)

    resposta = client.post(
        "/api/genai-pasta/rodar", json={"pastas": ["Peru 2023"]}
    )

    assert resposta.status_code == 409
    assert fake.chamadas == 0

    with duas_candidatas() as session:
        from fotoorganizer.models import PastaClassificada
        assert session.query(PastaClassificada).count() == 0


# -- gate aberto: ciclo candidatas → rodar → propostas → aprovar ------------

def test_gate_aberto_rodar_grava_propostas_e_separa_sem_resposta(
    tmp_path, duas_candidatas
):
    settings = _settings(tmp_path, servicos_externos=True)
    SettingsRepository(duas_candidatas).definir_genai_pasta(True)
    fake = _ClassificadorFalso(respostas=[_resposta_peru()])
    client = _cliente(settings, duas_candidatas, classificador=fake)

    resposta = client.post(
        "/api/genai-pasta/rodar",
        json={"pastas": ["Peru 2023", "Sem Resposta 2023"]},
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert fake.chamadas == 1  # D-03: uma chamada só
    assert corpo["pastas_sem_resposta"] == ["Sem Resposta 2023"]
    campos_propostos = {p["campo"] for p in corpo["propostas"] if p["pasta"] == "Peru 2023"}
    assert campos_propostos == {"categoria", "cidade", "pais"}
    for p in corpo["propostas"]:
        assert p["valor_antes"] is None


def test_gate_aberto_candidatas_lista_as_duas_pastas(tmp_path, duas_candidatas):
    settings = _settings(tmp_path, servicos_externos=True)
    SettingsRepository(duas_candidatas).definir_genai_pasta(True)
    client = _cliente(settings, duas_candidatas, classificador=_ClassificadorFalso())

    resposta = client.get("/api/genai-pasta/candidatas")

    assert resposta.status_code == 200
    pastas = {c["pasta"] for c in resposta.json()}
    assert pastas == {"Peru 2023", "Sem Resposta 2023"}


def test_propostas_pendentes_apos_rodar_sem_aprovar(tmp_path, duas_candidatas):
    settings = _settings(tmp_path, servicos_externos=True)
    SettingsRepository(duas_candidatas).definir_genai_pasta(True)
    fake = _ClassificadorFalso(respostas=[_resposta_peru()])
    client = _cliente(settings, duas_candidatas, classificador=fake)

    client.post("/api/genai-pasta/rodar", json={"pastas": ["Peru 2023"]})
    resposta = client.get("/api/genai-pasta/propostas")

    assert resposta.status_code == 200
    pastas = {p["pasta"] for p in resposta.json()}
    assert pastas == {"Peru 2023"}


def test_aprovar_marca_aprovadas_e_descarta_demais_sem_apagar_linha(
    tmp_path, duas_candidatas
):
    settings = _settings(tmp_path, servicos_externos=True)
    SettingsRepository(duas_candidatas).definir_genai_pasta(True)
    fake = _ClassificadorFalso(respostas=[
        _resposta_peru(),
        PropostaDoModelo(
            pasta="Sem Resposta 2023", cidade=None, pais=None,
            categoria="Família", evento=None, justificativa="teste",
        ),
    ])
    client = _cliente(settings, duas_candidatas, classificador=fake)
    client.post(
        "/api/genai-pasta/rodar",
        json={"pastas": ["Peru 2023", "Sem Resposta 2023"]},
    )

    resposta = client.post(
        "/api/genai-pasta/aprovar", json={"pastas": ["Peru 2023"]}
    )

    assert resposta.status_code == 200
    assert resposta.json() == {"aprovadas": 1, "descartadas": 1}

    from fotoorganizer.models import PastaClassificada
    with duas_candidatas() as session:
        # invariante 8: nenhuma linha apagada, mesmo a descartada.
        assert session.query(PastaClassificada).count() == 2


# -- never-crash: 502 sem derrubar o servidor (T-07-04-05) -------------------

def test_rodar_com_cliente_que_falha_devolve_502_e_servidor_continua(
    tmp_path, duas_candidatas
):
    settings = _settings(tmp_path, servicos_externos=True)
    SettingsRepository(duas_candidatas).definir_genai_pasta(True)
    fake = _ClassificadorFalso(excecao=RuntimeError("erro de rede simulado"))
    client = _cliente(settings, duas_candidatas, classificador=fake)

    resposta = client.post(
        "/api/genai-pasta/rodar", json={"pastas": ["Peru 2023"]}
    )

    assert resposta.status_code == 502
    assert "erro de rede simulado" in resposta.json()["detail"]

    # o processo continua respondendo normalmente.
    seguinte = client.get("/api/genai-pasta/config")
    assert seguinte.status_code == 200
