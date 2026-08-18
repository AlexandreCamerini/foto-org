"""Regressão de esquema para `ExifWritePlan`/`ExifWriteItem` (Fase 6, D-075).

Razão de existir deste arquivo: travar a armadilha da FK de
`AuditLog.plan_id` (RESEARCH.md Pitfall 5) — aquela coluna tem FK real e
ativa para `operation_plans.id`, então gravar ali o id de um
`ExifWritePlan` (sequência de PK independente) quebra o insert com
`PRAGMA foreign_keys=ON`. E o modelo de status por campo (EXIF-03): GPS,
cidade e país têm status e motivo independentes, não um status único por
item.
"""

from datetime import datetime

import pytest
from sqlalchemy.exc import IntegrityError

from fotoorganizer.database import create_session_factory
from fotoorganizer.models import (
    AuditLog,
    CampoStatus,
    ExifWriteItem,
    ExifWritePlan,
    MediaFile,
    Source,
)


@pytest.fixture()
def ambiente(migrated_engine, tmp_path):
    """1 fonte + 1 mídia mínima, só para satisfazer a FK media_id."""
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        fonte = Source(caminho=str(tmp_path / "origem"))
        session.add(fonte)
        session.flush()
        media = MediaFile(
            source_id=fonte.id,
            caminho=str(tmp_path / "origem" / "IMG_1.jpg"),
            pasta=str(tmp_path / "origem"),
            nome="IMG_1.jpg",
            extensao="jpg",
            tamanho=1024,
            data_capturada=datetime(2024, 1, 1),
        )
        session.add(media)
        session.commit()
        media_id = media.id
    return factory, media_id


def test_roundtrip_do_plano_e_itens(ambiente):
    factory, media_id = ambiente
    with factory() as session:
        plano = ExifWritePlan(nome="teste")
        session.add(plano)
        session.flush()
        item1 = ExifWriteItem(
            plan_id=plano.id,
            media_id=media_id,
            origem="/x/a.jpg",
            status_gps=CampoStatus.GRAVADO,
            status_cidade=CampoStatus.PULADO,
            status_pais=CampoStatus.SEM_VALOR,
        )
        item2 = ExifWriteItem(
            plan_id=plano.id,
            media_id=media_id,
            origem="/x/b.jpg",
            status_gps=CampoStatus.FALHA,
            status_cidade=CampoStatus.PRONTO,
            status_pais=CampoStatus.PENDENTE,
        )
        session.add_all([item1, item2])
        session.commit()
        plano_id = plano.id

    with factory() as session:
        relido = session.get(ExifWritePlan, plano_id)
        assert relido is not None
        assert len(relido.itens) == 2
        por_origem = {item.origem: item for item in relido.itens}
        assert por_origem["/x/a.jpg"].status_gps == CampoStatus.GRAVADO
        assert por_origem["/x/a.jpg"].status_cidade == CampoStatus.PULADO
        assert por_origem["/x/a.jpg"].status_pais == CampoStatus.SEM_VALOR
        assert por_origem["/x/b.jpg"].status_gps == CampoStatus.FALHA
        assert por_origem["/x/b.jpg"].status_cidade == CampoStatus.PRONTO
        assert por_origem["/x/b.jpg"].status_pais == CampoStatus.PENDENTE


def test_audit_log_de_escrita_exif_nao_viola_fk(ambiente):
    factory, media_id = ambiente
    with factory() as session:
        plano = ExifWritePlan(nome="teste")
        session.add(plano)
        session.flush()
        item = ExifWriteItem(plan_id=plano.id, media_id=media_id, origem="/x/a.jpg")
        session.add(item)
        session.flush()

        log = AuditLog(
            plan_id=None,
            acao="escrita_exif",
            detalhe={"exif_plan_id": plano.id, "item_id": item.id},
            resultado="ok",
        )
        session.add(log)
        session.commit()


def test_audit_log_com_plan_id_de_plano_exif_falha(ambiente):
    factory, media_id = ambiente
    with factory() as session:
        plano = ExifWritePlan(nome="teste")
        session.add(plano)
        session.commit()
        plano_id = plano.id

    with factory() as session:
        # Armadilha deliberada: `AuditLog.plan_id` tem FK para
        # `operation_plans.id`, não para `exif_write_plans.id`. Nenhum
        # `OperationPlan` com este id existe, então o insert deve falhar.
        log = AuditLog(
            plan_id=plano_id,
            acao="escrita_exif",
            detalhe={"exif_plan_id": plano_id},
            resultado="ok",
        )
        session.add(log)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()


def test_padroes_do_item(ambiente):
    factory, media_id = ambiente
    with factory() as session:
        plano = ExifWritePlan(nome="teste")
        session.add(plano)
        session.flush()
        item = ExifWriteItem(plan_id=plano.id, media_id=media_id, origem="/x/a.jpg")
        session.add(item)
        session.commit()
        item_id = item.id

    with factory() as session:
        relido = session.get(ExifWriteItem, item_id)
        assert relido.status_gps == CampoStatus.PENDENTE
        assert relido.status_cidade == CampoStatus.PENDENTE
        assert relido.status_pais == CampoStatus.PENDENTE
        assert relido.formato_suportado is True
        assert relido.incluido is True
