"""API de reapontamento — `POST /api/fontes/{id}/reapontar[/preview]` e
`GET /api/fontes/reapontamentos`. Mesma disciplina do CLI: dry-run sempre
disponível, escrita só com confirmação explícita no corpo."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from fotoorganizer.config.settings import Settings
from fotoorganizer.database import create_session_factory
from fotoorganizer.models import AuditLog, MediaFile, Source
from fotoorganizer.server import create_app


@pytest.fixture()
def ambiente(migrated_engine, tmp_path, monkeypatch):
    """Uma fonte "/Volumes/photo/DCIM" com o volume remontado em
    "/Volumes/photo 1" — o mesmo cenário sintético de test_reapontar.py,
    montado a partir da API em vez de chamar as funções direto."""
    import fotoorganizer.security.volumes as volumes
    import fotoorganizer.sources.disponibilidade as disp

    caminho_antigo = "/Volumes/photo/DCIM"
    novo_ponto = tmp_path / "photo 1"
    (novo_ponto / "DCIM").mkdir(parents=True)
    for i in range(3):
        (novo_ponto / "DCIM" / f"img_{i}.jpg").write_bytes(b"x")

    factory = create_session_factory(migrated_engine)
    with factory() as session:
        source = Source(caminho=caminho_antigo, apelido="photo",
                         volume_id="uuid:ABC-123")
        session.add(source)
        session.flush()
        for i in range(3):
            session.add(MediaFile(
                source_id=source.id, caminho=f"{caminho_antigo}/img_{i}.jpg",
                pasta=caminho_antigo, nome=f"img_{i}.jpg", extensao="jpg",
                tamanho=1,
            ))
        session.commit()
        source_id = source.id

    monkeypatch.setattr(volumes.os.path, "ismount", lambda p: str(p) == "/")
    monkeypatch.setattr(disp, "montado_em", lambda ident: novo_ponto)
    original_exists = disp.Path.exists

    def _exists_dublado(self):
        return False if str(self) == caminho_antigo else original_exists(self)

    monkeypatch.setattr(disp.Path, "exists", _exists_dublado)

    settings = Settings(data_dir=tmp_path / "d", cache_dir=tmp_path / "c")
    client = TestClient(
        create_app(settings, factory), base_url="http://127.0.0.1:8765"
    )
    return client, factory, source_id, caminho_antigo, novo_ponto


def test_reapontamentos_lista_a_fonte_que_mudou_de_lugar(ambiente):
    client, _factory, source_id, caminho_antigo, novo_ponto = ambiente
    (item,) = client.get("/api/fontes/reapontamentos").json()
    assert item["source_id"] == source_id
    assert item["prefixo_antigo"] == caminho_antigo
    assert item["prefixo_novo"] == str(novo_ponto / "DCIM")


def test_preview_nao_escreve_nada(ambiente):
    client, factory, source_id, caminho_antigo, novo_ponto = ambiente
    resp = client.post(f"/api/fontes/{source_id}/reapontar/preview")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_media_files"] == 3
    assert body["prefixo_novo"] == str(novo_ponto / "DCIM")
    assert len(body["amostra"]) == 3

    with factory() as session:
        assert session.scalar(select(Source)).caminho == caminho_antigo


def test_reapontar_sem_confirmar_e_recusado(ambiente):
    client, factory, source_id, caminho_antigo, _novo_ponto = ambiente
    resp = client.post(f"/api/fontes/{source_id}/reapontar", json={})
    assert resp.status_code == 422
    with factory() as session:
        assert session.scalar(select(Source)).caminho == caminho_antigo


def test_reapontar_confirmado_reescreve_e_audita(ambiente):
    client, factory, source_id, caminho_antigo, novo_ponto = ambiente
    resp = client.post(
        f"/api/fontes/{source_id}/reapontar", json={"confirmar": True}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["linhas_media_files"] == 3
    assert body["prefixo_novo"] == str(novo_ponto / "DCIM")

    with factory() as session:
        assert session.scalar(select(Source)).caminho == str(novo_ponto / "DCIM")
        caminhos = {m.caminho for m in session.scalars(select(MediaFile))}
        assert caminhos == {
            str(novo_ponto / "DCIM" / f"img_{i}.jpg") for i in range(3)
        }
        auditoria = session.scalar(select(AuditLog))
        assert auditoria.acao == "reapontar_fonte"
        assert auditoria.detalhe["prefixo_antigo"] == caminho_antigo


def test_reapontar_ignora_referencias_de_catalogo_externo(
    migrated_engine, tmp_path, monkeypatch,
):
    """Repro do bug real: uma fonte com `MediaFile.caminho` do tipo
    `apple://uuid` (`sources/importer.py`) ao lado de caminhos de arquivo de
    verdade. A API nunca pode fatiar a referência pelo prefixo do disco —
    isso a destruiria em silêncio (invariante 8)."""
    import fotoorganizer.security.volumes as volumes
    import fotoorganizer.sources.disponibilidade as disp

    caminho_antigo = "/Volumes/photo/DCIM"
    novo_ponto = tmp_path / "photo 1"
    (novo_ponto / "DCIM").mkdir(parents=True)
    (novo_ponto / "DCIM" / "img_0.jpg").write_bytes(b"x")

    factory = create_session_factory(migrated_engine)
    with factory() as session:
        source = Source(caminho=caminho_antigo, apelido="photo",
                         volume_id="uuid:ABC-123")
        session.add(source)
        session.flush()
        session.add(MediaFile(
            source_id=source.id, caminho=f"{caminho_antigo}/img_0.jpg",
            pasta=caminho_antigo, nome="img_0.jpg", extensao="jpg",
            tamanho=1,
        ))
        session.add(MediaFile(
            source_id=source.id, caminho="apple://UUID-REFERENCIA",
            pasta="", nome="UUID-REFERENCIA", extensao="", tamanho=0,
        ))
        session.commit()
        source_id = source.id

    monkeypatch.setattr(volumes.os.path, "ismount", lambda p: str(p) == "/")
    monkeypatch.setattr(disp, "montado_em", lambda ident: novo_ponto)
    original_exists = disp.Path.exists

    def _exists_dublado(self):
        return False if str(self) == caminho_antigo else original_exists(self)

    monkeypatch.setattr(disp.Path, "exists", _exists_dublado)

    settings = Settings(data_dir=tmp_path / "d", cache_dir=tmp_path / "c")
    client = TestClient(
        create_app(settings, factory), base_url="http://127.0.0.1:8765"
    )

    preview = client.post(f"/api/fontes/{source_id}/reapontar/preview").json()
    assert preview["total_media_files"] == 1
    assert preview["total_ignoradas_sem_prefixo"] == 1

    resp = client.post(
        f"/api/fontes/{source_id}/reapontar", json={"confirmar": True}
    )
    assert resp.status_code == 200
    assert resp.json()["linhas_media_files"] == 1

    with factory() as session:
        caminhos = {m.caminho for m in session.scalars(select(MediaFile))}
        assert caminhos == {
            str(novo_ponto / "DCIM" / "img_0.jpg"),
            "apple://UUID-REFERENCIA",  # intocada, byte a byte
        }


def test_reapontar_fonte_inexistente_e_404(migrated_engine, tmp_path):
    factory = create_session_factory(migrated_engine)
    settings = Settings(data_dir=tmp_path / "d", cache_dir=tmp_path / "c")
    client = TestClient(
        create_app(settings, factory), base_url="http://127.0.0.1:8765"
    )
    resp = client.post("/api/fontes/999/reapontar/preview")
    assert resp.status_code == 404


def test_reapontar_fonte_que_nao_e_volume_e_409(migrated_engine, tmp_path):
    """Guarda de segurança também na API: fonte fora da convenção
    /Volumes/<nome> não vira um replace genérico."""
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        pasta = tmp_path / "pasta_local"
        pasta.mkdir()
        session.add(Source(caminho=str(pasta), apelido="local"))
        session.commit()
        source_id = session.scalar(select(Source)).id

    settings = Settings(data_dir=tmp_path / "d", cache_dir=tmp_path / "c")
    client = TestClient(
        create_app(settings, factory), base_url="http://127.0.0.1:8765"
    )
    resp = client.post(f"/api/fontes/{source_id}/reapontar/preview")
    assert resp.status_code == 409
