"""Plano de escrita EXIF órfão (D-095): EXECUTANDO no banco com o servidor
nascendo é sempre órfão — vira INTERROMPIDA, e "Gravar" retoma.

Espelho de `test_scan_orfao_e_reconciliado_no_boot...` para o domínio de
escrita EXIF.
"""

from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy import select

from fotoorganizer.config.settings import Settings
from fotoorganizer.database import create_session_factory
from fotoorganizer.exif_write.reconciliacao import reconciliar_planos_orfaos
from fotoorganizer.models import (
    AuditLog,
    CampoStatus,
    ExifWriteItem,
    ExifWritePlan,
    ExifWriteStatus,
    MediaFile,
    Source,
)
from fotoorganizer.server.app import create_app


def _plano_orfao(factory, *, n_prontos: int = 2, base: str = "/fotos") -> int:
    """Plano EXECUTANDO com dry-run feito e itens ainda PRONTO — exatamente
    o que sobra no banco quando o processo morre no meio."""
    with factory() as session:
        fonte = Source(caminho=base)
        session.add(fonte)
        session.flush()
        plano = ExifWritePlan(
            nome="órfão", status=ExifWriteStatus.EXECUTANDO,
            dry_run_em=datetime(2026, 9, 23, 1, 0),
        )
        session.add(plano)
        session.flush()
        for i in range(n_prontos + 1):
            media = MediaFile(
                source_id=fonte.id, caminho=f"{base}/{i}.jpg", pasta=base,
                nome=f"{i}.jpg", extensao="jpg", tamanho=1,
            )
            session.add(media)
            session.flush()
            # O último já foi gravado antes da morte: não conta como restante.
            gravado = i == n_prontos
            session.add(ExifWriteItem(
                plan_id=plano.id, media_id=media.id, origem=media.caminho,
                valor_pais="Brasil",
                status_gps=CampoStatus.SEM_VALOR, status_cidade=CampoStatus.SEM_VALOR,
                status_pais=CampoStatus.GRAVADO if gravado else CampoStatus.PRONTO,
                formato_suportado=True, incluido=True,
            ))
        # `executavel` lê `prontos` da auditoria do último dry-run, não do
        # status dos itens (repositories/exif_write.py::_veredito) — a
        # linha que o dry-run real grava antes de a execução começar.
        session.add(AuditLog(plan_id=None, acao="dry_run_exif", detalhe={
            "exif_plan_id": plano.id, "prontos": n_prontos, "problemas": 0,
            "campos_a_gravar": n_prontos, "sidecars": 0,
        }, resultado="ok"))
        session.commit()
        return plano.id


def test_reconcilia_plano_executando_para_interrompida_com_auditoria(
    migrated_engine, tmp_path,
):
    factory = create_session_factory(migrated_engine)
    base = tmp_path / "fotos"
    base.mkdir()
    plan_id = _plano_orfao(factory, n_prontos=2, base=str(base))
    # O item em voo é o primeiro pendente (0.jpg); o exiftool morreu
    # depois de criar o backup dele — é isso que a retomada nunca apontaria.
    (base / "0.jpg_original").write_bytes(b"backup orfao")

    assert reconciliar_planos_orfaos(factory) == 1
    assert reconciliar_planos_orfaos(factory) == 0  # idempotente

    with factory() as session:
        plano = session.get(ExifWritePlan, plan_id)
        assert plano.status == ExifWriteStatus.INTERROMPIDA
        assert plano.dry_run_em is not None  # nada além do status muda
        auditoria = session.scalar(
            select(AuditLog).where(AuditLog.acao == "execucao_exif_interrompida")
        )
        assert auditoria.plan_id is None  # FK é do plano de cópia, nunca daqui
        assert auditoria.detalhe["exif_plan_id"] == plan_id
        assert auditoria.detalhe["itens_restantes"] == 2
        em_voo = auditoria.detalhe["item_em_voo"]
        assert em_voo["origem"] == str(base / "0.jpg")
        assert em_voo["arquivos_deixados"] == [str(base / "0.jpg_original")]
    assert (base / "0.jpg_original").exists()  # apontado, nunca tocado


def test_plano_que_terminou_nao_e_tocado(migrated_engine):
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        session.add(ExifWritePlan(nome="ok", status=ExifWriteStatus.CONCLUIDA))
        session.add(ExifWritePlan(nome="parado", status=ExifWriteStatus.CANCELADA))
        session.commit()
    assert reconciliar_planos_orfaos(factory) == 0
    with factory() as session:
        assert {p.status for p in session.scalars(select(ExifWritePlan))} == {
            ExifWriteStatus.CONCLUIDA, ExifWriteStatus.CANCELADA,
        }


def test_boot_do_servidor_reconcilia_e_o_plano_continua_executavel(
    migrated_engine, tmp_path,
):
    """O que o dono vê ao reabrir o app: o plano não está mais
    "executando", e o botão Gravar continua liberado — rerodar retoma."""
    factory = create_session_factory(migrated_engine)
    plan_id = _plano_orfao(factory)
    settings = Settings(data_dir=tmp_path / "d", cache_dir=tmp_path / "c")

    # O lifespan (startup) é quem reconcilia — daí o context manager.
    with TestClient(
        create_app(settings, factory), base_url="http://127.0.0.1:8765"
    ) as client:
        (plano,) = client.get("/api/exif").json()
        assert plano["id"] == plan_id
        assert plano["status"] == "interrompida"
        assert plano["executavel"] is True


def test_migracao_0023_ida_e_volta_preserva_os_dados(tmp_path):
    """`INTERROMPIDA` não cabe no enum antigo: o downgrade converte para
    ERRO antes de estreitar a coluna, e o upgrade seguinte não perde nada
    (revisão de D-095: a migração não tinha teste)."""
    import sqlite3

    from alembic import command

    from fotoorganizer.database import create_db_engine, upgrade_to_head
    from fotoorganizer.database.migrate import alembic_config

    db = tmp_path / "catalog.db"
    upgrade_to_head(db)
    engine = create_db_engine(db)
    factory = create_session_factory(engine)
    with factory() as session:
        session.add(ExifWritePlan(nome="x", status=ExifWriteStatus.INTERROMPIDA))
        session.add(ExifWritePlan(nome="y", status=ExifWriteStatus.CONCLUIDA))
        session.commit()
    engine.dispose()

    def estado():
        con = sqlite3.connect(db)
        linhas = sorted(con.execute("select nome, status from exif_write_plans"))
        versao = con.execute("select version_num from alembic_version").fetchone()[0]
        largura = next(
            c[2] for c in con.execute("pragma table_info(exif_write_plans)")
            if c[1] == "status"
        )
        con.close()
        return linhas, versao, largura

    assert estado() == ([("x", "INTERROMPIDA"), ("y", "CONCLUIDA")], "0023", "VARCHAR(12)")
    command.downgrade(alembic_config(db), "-1")
    assert estado() == ([("x", "ERRO"), ("y", "CONCLUIDA")], "0022", "VARCHAR(10)")
    command.upgrade(alembic_config(db), "head")
    assert estado() == ([("x", "ERRO"), ("y", "CONCLUIDA")], "0023", "VARCHAR(12)")
