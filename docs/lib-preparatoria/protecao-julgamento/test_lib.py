from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from lib import (
    EsquemaDivergente,
    LinhaEvidencia,
    LinhaSugestao,
    aplicar_retencao,
    deve_rodar_backup,
    exigir_esquema_compativel,
    executar_backup_com_retencao,
    exportar_julgamento,
    fazer_backup,
    listar_backups,
    nome_backup,
    salvar_export,
    verificar_esquema,
)

# --- 1. export legível -----------------------------------------------------


def _evidencia(**kw) -> LinhaEvidencia:
    base = dict(
        media_id=1, campo="pais", origem="vizinhanca_temporal", valor="Brasil",
        nivel="baixa", score=0.4, justificativa="herdado de outra foto",
        versao_logica="4.1",
    )
    base.update(kw)
    return LinhaEvidencia(**base)


def _sugestao(**kw) -> LinhaSugestao:
    base = dict(
        media_id=1, destino_sugerido="2019/Viagem", nivel="baixa",
        status="pendente", versao_logica="4.1",
    )
    base.update(kw)
    return LinhaSugestao(**base)


def test_exportar_julgamento_inclui_evidencias_e_sugestoes():
    doc = exportar_julgamento(
        [_evidencia()], [_sugestao()], versao_logica_atual="4.1"
    )
    assert doc["versao_logica_atual"] == "4.1"
    assert len(doc["evidencias"]) == 1
    assert doc["evidencias"][0]["campo"] == "pais"
    assert len(doc["sugestoes"]) == 1
    assert doc["sugestoes"][0]["status"] == "pendente"


def test_exportar_julgamento_listas_vazias_produz_documento_valido():
    doc = exportar_julgamento([], [], versao_logica_atual="4.1")
    assert doc["evidencias"] == []
    assert doc["sugestoes"] == []


def test_salvar_export_grava_json_legivel_com_acentuacao(tmp_path):
    doc = exportar_julgamento([_evidencia()], [], versao_logica_atual="4.1")
    destino = tmp_path / "export" / "julgamento.json"
    salvar_export(doc, destino)
    texto = destino.read_text(encoding="utf-8")
    assert "Brasil" in texto
    assert "\\u00e3" not in texto  # ensure_ascii=False preserva "vizinhanca_temporal" etc
    recarregado = json.loads(texto)
    assert recarregado == doc


def test_salvar_export_cria_diretorio_pai(tmp_path):
    destino = tmp_path / "nivel1" / "nivel2" / "julgamento.json"
    salvar_export(exportar_julgamento([], [], versao_logica_atual="4.1"), destino)
    assert destino.is_file()


# --- 2. backup com retenção -------------------------------------------------


def _criar_catalogo_sqlite(caminho: Path) -> None:
    con = sqlite3.connect(caminho)
    con.execute("CREATE TABLE media_files (id INTEGER PRIMARY KEY, nome TEXT)")
    con.execute("INSERT INTO media_files (nome) VALUES ('foto.jpg')")
    con.commit()
    con.close()


def test_nome_backup_usa_stem_e_carimbo_do_mesmo_segundo():
    db = Path("/tmp/catalog.db")
    agora = datetime(2026, 8, 12, 10, 30, 0)
    destino = nome_backup(db, agora)
    assert destino.name == "catalog-backup-20260812-103000.db"
    assert destino.parent == db.parent


def test_fazer_backup_copia_dados_de_verdade(tmp_path):
    db = tmp_path / "catalog.db"
    _criar_catalogo_sqlite(db)
    destino = fazer_backup(db, datetime(2026, 8, 12, 10, 0, 0))
    assert destino.is_file()
    con = sqlite3.connect(destino)
    linhas = con.execute("SELECT nome FROM media_files").fetchall()
    con.close()
    assert linhas == [("foto.jpg",)]


def test_fazer_backup_nao_apaga_nem_altera_o_catalogo_original(tmp_path):
    db = tmp_path / "catalog.db"
    _criar_catalogo_sqlite(db)
    fazer_backup(db, datetime(2026, 8, 12, 10, 0, 0))
    con = sqlite3.connect(db)
    linhas = con.execute("SELECT nome FROM media_files").fetchall()
    con.close()
    assert linhas == [("foto.jpg",)]
    assert db.is_file()


def test_listar_backups_ordena_do_mais_antigo_ao_mais_novo(tmp_path):
    db = tmp_path / "catalog.db"
    _criar_catalogo_sqlite(db)
    fazer_backup(db, datetime(2026, 8, 10, 10, 0, 0))
    fazer_backup(db, datetime(2026, 8, 11, 10, 0, 0))
    fazer_backup(db, datetime(2026, 8, 12, 10, 0, 0))
    nomes = [p.name for p in listar_backups(db)]
    assert nomes == sorted(nomes)
    assert len(nomes) == 3


def test_aplicar_retencao_mantem_so_os_n_mais_recentes(tmp_path):
    db = tmp_path / "catalog.db"
    _criar_catalogo_sqlite(db)
    for dia in (10, 11, 12):
        fazer_backup(db, datetime(2026, 8, dia, 10, 0, 0))
    apagados = aplicar_retencao(db, reter=1)
    restantes = listar_backups(db)
    assert len(apagados) == 2
    assert len(restantes) == 1
    assert "20260812" in restantes[0].name


def test_aplicar_retencao_reter_maior_que_existente_nao_apaga_nada(tmp_path):
    db = tmp_path / "catalog.db"
    _criar_catalogo_sqlite(db)
    fazer_backup(db, datetime(2026, 8, 12, 10, 0, 0))
    apagados = aplicar_retencao(db, reter=5)
    assert apagados == []
    assert len(listar_backups(db)) == 1


def test_aplicar_retencao_negativa_levanta_erro(tmp_path):
    db = tmp_path / "catalog.db"
    _criar_catalogo_sqlite(db)
    with pytest.raises(ValueError):
        aplicar_retencao(db, reter=-1)


def test_executar_backup_com_retencao_deixa_exatamente_n_arquivos(tmp_path):
    db = tmp_path / "catalog.db"
    _criar_catalogo_sqlite(db)
    for dia in (10, 11, 12, 13):
        executar_backup_com_retencao(db, datetime(2026, 8, dia, 10, 0, 0), reter=2)
    assert len(listar_backups(db)) == 2


def test_deve_rodar_backup_primeira_vez_e_sempre_true():
    assert deve_rodar_backup(None, timedelta(days=1), datetime(2026, 8, 12)) is True


def test_deve_rodar_backup_dentro_do_intervalo_e_false():
    ultimo = datetime(2026, 8, 12, 10, 0, 0)
    agora = datetime(2026, 8, 12, 12, 0, 0)
    assert deve_rodar_backup(ultimo, timedelta(days=1), agora) is False


def test_deve_rodar_backup_apos_o_intervalo_e_true():
    ultimo = datetime(2026, 8, 10, 10, 0, 0)
    agora = datetime(2026, 8, 12, 10, 0, 1)
    assert deve_rodar_backup(ultimo, timedelta(days=2), agora) is True


def test_deve_rodar_backup_exatamente_no_limite_e_true():
    ultimo = datetime(2026, 8, 10, 10, 0, 0)
    agora = datetime(2026, 8, 12, 10, 0, 0)
    assert deve_rodar_backup(ultimo, timedelta(days=2), agora) is True


# --- 3. checagem de esquema no boot -----------------------------------------


def _con_com_alembic_version(versao: str | None) -> sqlite3.Connection:
    con = sqlite3.connect(":memory:")
    if versao is not None:
        con.execute("CREATE TABLE alembic_version (version_num VARCHAR(32))")
        con.execute("INSERT INTO alembic_version VALUES (?)", (versao,))
        con.commit()
    return con


def test_verificar_esquema_versao_igual_e_ok():
    con = _con_com_alembic_version("0016")
    resultado = verificar_esquema(con, "0016")
    assert resultado.ok is True
    assert resultado.motivo is None


def test_verificar_esquema_tabela_ausente_e_nao_inicializado():
    con = sqlite3.connect(":memory:")
    resultado = verificar_esquema(con, "0016")
    assert resultado.ok is False
    assert resultado.motivo == "nao_inicializado"
    assert resultado.revisao_encontrada is None


def test_verificar_esquema_versao_antiga_e_desatualizado():
    con = _con_com_alembic_version("0013")
    resultado = verificar_esquema(con, "0016")
    assert resultado.motivo == "desatualizado"
    assert resultado.revisao_encontrada == "0013"


def test_verificar_esquema_versao_mais_nova_que_o_app_e_downgrade():
    con = _con_com_alembic_version("0020")
    resultado = verificar_esquema(con, "0016")
    assert resultado.motivo == "downgrade"


def test_exigir_esquema_compativel_ok_nao_levanta():
    con = _con_com_alembic_version("0016")
    exigir_esquema_compativel(con, "0016")  # não deve levantar


def test_exigir_esquema_compativel_desatualizado_nao_levanta():
    # boot decide migrar; a checagem só bloqueia downgrade.
    con = _con_com_alembic_version("0013")
    exigir_esquema_compativel(con, "0016")  # não deve levantar


def test_exigir_esquema_compativel_downgrade_levanta_com_as_duas_versoes():
    con = _con_com_alembic_version("0020")
    with pytest.raises(EsquemaDivergente, match="0020.*0016|0016.*0020"):
        exigir_esquema_compativel(con, "0016")


# --- cenário D-038: migração interrompida entre ADD COLUMN e commit da versão


def test_migracao_0014_interrompida_e_desatualizado_nao_downgrade():
    # sob pysqlite, ADD COLUMN comita sozinho; uma interrupção deixaria a
    # coluna criada com alembic_version ainda em "0013" — o cenário exato
    # que D-038 descreve. A checagem tem que classificar isso como
    # "desatualizado" (retomável rodando a migração de novo), não como
    # downgrade (que bloquearia para sempre um catálogo só interrompido).
    con = _con_com_alembic_version("0013")
    con.execute("ALTER TABLE alembic_version ADD COLUMN coluna_da_0014 TEXT")
    resultado = verificar_esquema(con, "0014")
    assert resultado.motivo == "desatualizado"
    exigir_esquema_compativel(con, "0014")  # não bloqueia — boot pode remigrar
