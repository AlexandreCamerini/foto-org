"""Suíte de `ExifWritePlanner.criar_plano_exif` (fotoorganizer/exif_write/planner.py).

Prova EXIF-01 (o plano lista, por arquivo, valor e status por campo),
EXIF-02 (campo já preenchido nunca vira candidato de sobrescrita) e EXIF-05
(formato não suportado vira linha explícita com motivo e oferta de
sidecar), além da regra de auditoria da Pitfall 5 (AuditLog.plan_id nunca
recebe o id de um ExifWritePlan). Nenhum teste aqui precisa do binário
exiftool — o planner é só banco, nunca abre um arquivo de imagem.
"""

from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy import select

from fotoorganizer.database import create_session_factory
from fotoorganizer.exif_write import sync_detect
from fotoorganizer.exif_write.planner import ExifWritePlanner
from fotoorganizer.models import (
    AuditLog,
    CampoStatus,
    ExifWriteItem,
    ExifWritePlan,
    Location,
    MediaFile,
    MetadataEntry,
    Source,
)
from fotoorganizer.security.hashing import sha256_full
from tests.fixtures import make_jpeg


@pytest.fixture()
def ambiente(migrated_engine, tmp_path):
    origem_dir = tmp_path / "origem"
    origem_dir.mkdir()
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        fonte = Source(caminho=str(origem_dir))
        session.add(fonte)
        session.commit()
        fonte_id = fonte.id
    planner = ExifWritePlanner(factory)
    return factory, planner, origem_dir, fonte_id


def _media(
    session,
    fonte_id: int,
    origem_dir,
    rel: str,
    *,
    extensao: str = "jpg",
    gps: tuple[float, float] | None = None,
    gps_estimado: tuple[float, float] | None = None,
    location: Location | None = None,
    conteudo: bytes | None = b"conteudo sintetico",
) -> MediaFile:
    """Cria um MediaFile candidato com as colunas relevantes preenchidas à
    mão — o planner nunca lê o arquivo, então o conteúdo é irrelevante,
    exceto nos testes que comparam hash antes/depois."""
    caminho = origem_dir / rel
    if conteudo is not None:
        if extensao.lower() in ("jpg", "jpeg"):
            make_jpeg(caminho, seed=hash(rel) % 100)
        else:
            caminho.parent.mkdir(parents=True, exist_ok=True)
            caminho.write_bytes(conteudo)

    gps_lat = gps[0] if gps else None
    gps_lon = gps[1] if gps else None
    gps_lat_estimado = gps_estimado[0] if gps_estimado else None
    gps_lon_estimado = gps_estimado[1] if gps_estimado else None

    location_id = None
    if location is not None:
        session.add(location)
        session.flush()
        location_id = location.id

    media = MediaFile(
        source_id=fonte_id, caminho=str(caminho), pasta=str(caminho.parent),
        nome=caminho.name, extensao=extensao, tamanho=caminho.stat().st_size,
        data_capturada=datetime(2024, 1, 1),
        gps_lat=gps_lat, gps_lon=gps_lon,
        gps_lat_estimado=gps_lat_estimado, gps_lon_estimado=gps_lon_estimado,
        location_id=location_id,
    )
    session.add(media)
    session.flush()
    return media


def test_sem_candidato_devolve_none(ambiente):
    """Toda foto já tem gps_lat e nenhuma tem location_id → nenhum
    candidato, criar_plano_exif() devolve None e nenhum plano é criado."""
    factory, planner, origem_dir, fonte_id = ambiente
    with factory() as session:
        _media(session, fonte_id, origem_dir, "a.jpg", gps=(-23.5, -46.6))
        session.commit()

    assert planner.criar_plano_exif() is None
    with factory() as session:
        assert session.scalar(select(ExifWritePlan)) is None


def test_lista_campo_vazio_e_valor_que_entraria(ambiente):
    """Foto sem gps_lat, com gps_lat_estimado/gps_lon_estimado e com
    Location(cidade, pais) vira item com os 3 valores preenchidos e os 3
    status em PENDENTE (EXIF-01)."""
    factory, planner, origem_dir, fonte_id = ambiente
    with factory() as session:
        loc = Location(cidade="Rio de Janeiro", pais="Brasil", fonte="test")
        media = _media(
            session, fonte_id, origem_dir, "a.jpg",
            gps_estimado=(-22.9, -43.2), location=loc,
        )
        media_id = media.id
        session.commit()

    plan_id = planner.criar_plano_exif()
    assert plan_id is not None

    with factory() as session:
        item = session.scalar(
            select(ExifWriteItem).where(ExifWriteItem.media_id == media_id)
        )
        assert item is not None
        assert item.valor_gps_lat == pytest.approx(-22.9)
        assert item.valor_gps_lon == pytest.approx(-43.2)
        assert item.valor_cidade == "Rio de Janeiro"
        assert item.valor_pais == "Brasil"
        assert item.status_gps == CampoStatus.PENDENTE
        assert item.status_cidade == CampoStatus.PENDENTE
        assert item.status_pais == CampoStatus.PENDENTE


def test_campo_ja_preenchido_no_arquivo_sai_como_pulado(ambiente):
    """Foto com gps_lat lido do arquivo e com MetadataEntry(City=...) vira
    item com status_gps == PULADO, status_cidade == PULADO com motivo
    visível, e status_pais ainda elegível (EXIF-02, critério 2)."""
    factory, planner, origem_dir, fonte_id = ambiente
    with factory() as session:
        loc = Location(cidade="Rio de Janeiro", pais="Brasil", fonte="test")
        media = _media(
            session, fonte_id, origem_dir, "a.jpg",
            gps=(-22.9, -43.2), location=loc,
        )
        session.add(MetadataEntry(
            media_id=media.id, namespace="iptc", chave="City",
            valor="Rio de Janeiro",
        ))
        media_id = media.id
        session.commit()

    plan_id = planner.criar_plano_exif()
    assert plan_id is not None

    with factory() as session:
        item = session.scalar(
            select(ExifWriteItem).where(ExifWriteItem.media_id == media_id)
        )
        assert item.status_gps == CampoStatus.PULADO
        assert "já preenchido" in item.motivo_gps
        assert item.status_cidade == CampoStatus.PULADO
        assert "já preenchido: Rio de Janeiro — não sobrescrito" in item.motivo_cidade
        assert item.status_pais == CampoStatus.PENDENTE


def test_campo_sem_valor_inferido(ambiente):
    """Foto com cidade resolvida mas sem gps_lat_estimado vira item com
    status_gps == SEM_VALOR e motivo não-vazio — nunca confundido com
    PULADO."""
    factory, planner, origem_dir, fonte_id = ambiente
    with factory() as session:
        loc = Location(cidade="Rio de Janeiro", fonte="test")
        media = _media(session, fonte_id, origem_dir, "a.jpg", location=loc)
        media_id = media.id
        session.commit()

    plan_id = planner.criar_plano_exif()
    assert plan_id is not None

    with factory() as session:
        item = session.scalar(
            select(ExifWriteItem).where(ExifWriteItem.media_id == media_id)
        )
        assert item.status_gps == CampoStatus.SEM_VALOR
        assert item.motivo_gps
        assert item.status_gps != CampoStatus.PULADO


def test_formato_nao_suportado_vira_linha_com_motivo_e_sidecar(ambiente):
    """Foto .cr3 elegível vira item com formato_suportado is False,
    motivo_nao_suportado contendo 'CR3', sidecar_destino terminando em
    '.CR3.xmp' e incluido is False (EXIF-05, D-05, D-06)."""
    factory, planner, origem_dir, fonte_id = ambiente
    with factory() as session:
        media = _media(
            session, fonte_id, origem_dir, "a/foto.CR3", extensao="cr3",
            gps_estimado=(-22.9, -43.2),
        )
        media_id = media.id
        session.commit()

    plan_id = planner.criar_plano_exif()
    assert plan_id is not None

    with factory() as session:
        item = session.scalar(
            select(ExifWriteItem).where(ExifWriteItem.media_id == media_id)
        )
        assert item.formato_suportado is False
        assert "CR3" in item.motivo_nao_suportado
        assert item.sidecar_destino.endswith(".CR3.xmp")
        assert item.incluido is False


def test_pasta_sincronizada_marcada(ambiente, monkeypatch):
    """Foto cujo caminho cai numa raiz sincronizada simulada vira item com
    pasta_sincronizada não-nulo e incluido is True — aviso, não bloqueio
    (D-07). `formatos.suportado` é forçado a True: a medição real de
    06-04 (D-076) zerou `FORMATOS_APROVADOS`, e este teste prova o
    comportamento de D-07 isolado de D-03/D-04 — qual formato passa no
    teste empírico é outra decisão, medida à parte."""
    factory, planner, origem_dir, fonte_id = ambiente
    monkeypatch.setattr(
        "fotoorganizer.exif_write.formatos.suportado", lambda ext: True
    )
    raiz_sync = origem_dir / "SyncRoot"
    raiz_sync.mkdir()
    monkeypatch.setattr(
        sync_detect, "_RAIZES_SINCRONIZADAS", {"Nuvem de Teste": raiz_sync}
    )

    with factory() as session:
        media = _media(
            session, fonte_id, origem_dir, "SyncRoot/a.jpg",
            gps_estimado=(-22.9, -43.2),
        )
        media_id = media.id
        session.commit()

    plan_id = planner.criar_plano_exif()
    assert plan_id is not None

    with factory() as session:
        item = session.scalar(
            select(ExifWriteItem).where(ExifWriteItem.media_id == media_id)
        )
        assert item.pasta_sincronizada == "Nuvem de Teste"
        assert item.incluido is True


def test_audit_log_do_plano_nao_usa_plan_id(ambiente):
    """Depois de criar, existe uma linha de AuditLog com
    acao == 'plano_exif_criado', plan_id is None e
    detalhe['exif_plan_id'] == plano.id (RESEARCH.md Pitfall 5)."""
    factory, planner, origem_dir, fonte_id = ambiente
    with factory() as session:
        _media(session, fonte_id, origem_dir, "a.jpg", gps_estimado=(-22.9, -43.2))
        session.commit()

    plan_id = planner.criar_plano_exif()
    assert plan_id is not None

    with factory() as session:
        log_row = session.scalar(
            select(AuditLog).where(AuditLog.acao == "plano_exif_criado")
        )
        assert log_row is not None
        assert log_row.plan_id is None
        assert log_row.detalhe["exif_plan_id"] == plan_id


def test_criar_plano_nao_toca_o_disco(ambiente):
    """Hash SHA-256 de cada arquivo de origem é idêntico antes e depois de
    criar_plano_exif(), e nenhum arquivo novo aparece na árvore de
    origem."""
    factory, planner, origem_dir, fonte_id = ambiente
    with factory() as session:
        media = _media(
            session, fonte_id, origem_dir, "a.jpg", gps_estimado=(-22.9, -43.2),
        )
        caminho = media.caminho
        session.commit()

    antes = sha256_full(origem_dir / "a.jpg")
    arquivos_antes = sorted(p.name for p in origem_dir.rglob("*") if p.is_file())

    plan_id = planner.criar_plano_exif()
    assert plan_id is not None

    depois = sha256_full(origem_dir / "a.jpg")
    arquivos_depois = sorted(p.name for p in origem_dir.rglob("*") if p.is_file())

    assert antes == depois
    assert arquivos_antes == arquivos_depois


def test_midia_ja_resolvida_nao_reentra(ambiente):
    """Rodar criar_plano_exif() duas vezes com todos os campos do primeiro
    plano marcados a mão como GRAVADO faz a segunda chamada devolver None;
    se um campo ficar em FALHA, a chamada seguinte cria plano novo com
    aquela mídia."""
    factory, planner, origem_dir, fonte_id = ambiente
    with factory() as session:
        media = _media(
            session, fonte_id, origem_dir, "a.jpg", gps_estimado=(-22.9, -43.2),
        )
        media_id = media.id
        session.commit()

    plan1_id = planner.criar_plano_exif()
    assert plan1_id is not None

    with factory() as session:
        item = session.scalar(
            select(ExifWriteItem).where(ExifWriteItem.media_id == media_id)
        )
        item.status_gps = CampoStatus.GRAVADO
        item.status_cidade = CampoStatus.GRAVADO
        item.status_pais = CampoStatus.GRAVADO
        session.commit()

    assert planner.criar_plano_exif() is None

    with factory() as session:
        item = session.scalar(
            select(ExifWriteItem).where(ExifWriteItem.media_id == media_id)
        )
        item.status_gps = CampoStatus.FALHA
        session.commit()

    plan2_id = planner.criar_plano_exif()
    assert plan2_id is not None
    assert plan2_id != plan1_id

    with factory() as session:
        novo_item = session.scalar(
            select(ExifWriteItem).where(
                ExifWriteItem.media_id == media_id,
                ExifWriteItem.plan_id == plan2_id,
            )
        )
        assert novo_item is not None
