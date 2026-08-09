from datetime import datetime, timezone

from sqlalchemy import inspect, text

from fotoorganizer.database import create_session_factory

TABELAS_ESPERADAS = {
    "sources", "scan_sessions", "media_files", "metadata_entries",
    "locations", "trips", "events",
    "people", "face_embeddings", "face_occurrences",
    "tags", "media_tags",
    "evidence", "suggestions", "suggestion_evidence",
    "duplicate_groups", "duplicate_members",
    "operation_plans", "operation_items", "audit_log",
    "application_settings",
}


def test_migracao_cria_todas_as_tabelas(migrated_engine):
    tabelas = set(inspect(migrated_engine).get_table_names())
    faltando = TABELAS_ESPERADAS - tabelas
    assert not faltando, f"tabelas ausentes: {faltando}"


def test_wal_e_foreign_keys_ativos(migrated_engine):
    with migrated_engine.connect() as conn:
        assert conn.execute(text("PRAGMA journal_mode")).scalar() == "wal"
        assert conn.execute(text("PRAGMA foreign_keys")).scalar() == 1


def test_migracao_e_idempotente(db_path, migrated_engine):
    from fotoorganizer.database import upgrade_to_head

    upgrade_to_head(db_path)  # segunda vez: no-op, não pode falhar


def test_migracao_0014_iguala_os_dois_instantes_do_que_ja_estava_no_catalogo(
    db_path,
):
    """O backfill do segundo instante (`data_capturada_utc`).

    Sem fuso conhecido os dois instantes são iguais — é assim que se diz
    "não sei o fuso desta foto". Quem não tem hora local nenhuma continua
    sem instante absoluto: "não sei o fuso" não pode virar "não sei quando".
    """
    import sqlite3

    from alembic import command

    from fotoorganizer.database.migrate import alembic_config

    cfg = alembic_config(db_path)
    command.upgrade(cfg, "0013")  # o catálogo como estava ANTES desta fatia

    con = sqlite3.connect(db_path)
    con.execute(
        "insert into sources (id, caminho, ativo, disponivel, "
        "padroes_ignorados, criado_em) values (1, '/Volumes/Fotos', 1, 1, "
        "'[]', '2026-01-01 00:00:00')"
    )
    for id_, caminho, data in (
        (1, "/Volumes/Fotos/a.jpg", "2019-07-14 09:00:00"),
        (2, "/Volumes/Fotos/b.jpg", None),
    ):
        con.execute(
            "insert into media_files (id, source_id, caminho, pasta, nome, "
            "extensao, tamanho, status_revisao, indexado_em, data_capturada) "
            "values (?, 1, ?, '/Volumes/Fotos', 'x.jpg', 'jpg', 10, "
            "'NAO_REVISADO', '2026-01-01 00:00:00', ?)",
            (id_, caminho, data),
        )
    con.commit()
    con.close()

    command.upgrade(cfg, "head")

    con = sqlite3.connect(db_path)
    linhas = dict(
        con.execute("select id, data_capturada_utc from media_files")
    )
    con.close()
    assert linhas[1] == "2019-07-14 09:00:00"  # igual à local
    assert linhas[2] is None                   # sem data, sem instante


def test_migracao_0014_retoma_depois_de_morrer_entre_a_coluna_e_o_backfill(
    db_path,
):
    """O `ADD COLUMN` comita sozinho sob pysqlite: se o processo morrer antes
    do backfill, a coluna existe e `alembic_version` ainda diz 0013. Sem
    tolerar isso, toda abertura seguinte do app morreria em "duplicate column
    name" — o catálogo inteiro travado por um acidente de timing.

    Simula exatamente esse estado: coluna criada à mão sobre um banco em
    0013, com uma linha por preencher e outra já preenchida com fuso de
    verdade (uma reimportação que aconteceu no meio-tempo).
    """
    import sqlite3

    from alembic import command

    from fotoorganizer.database.migrate import alembic_config

    cfg = alembic_config(db_path)
    command.upgrade(cfg, "0013")

    con = sqlite3.connect(db_path)
    con.execute(
        "insert into sources (id, caminho, ativo, disponivel, "
        "padroes_ignorados, criado_em) values (1, '/V', 1, 1, '[]', "
        "'2026-01-01 00:00:00')"
    )
    con.execute("alter table media_files add column data_capturada_utc DATETIME")
    for id_, utc in ((1, None), (2, "2019-07-14 12:00:00")):
        con.execute(
            "insert into media_files (id, source_id, caminho, pasta, nome, "
            "extensao, tamanho, status_revisao, indexado_em, data_capturada, "
            "data_capturada_utc) values (?, 1, ?, '/V', 'x.jpg', 'jpg', 10, "
            "'NAO_REVISADO', '2026-01-01 00:00:00', '2019-07-14 14:00:00', ?)",
            (id_, f"/V/{id_}.jpg", utc),
        )
    con.commit()
    con.close()

    command.upgrade(cfg, "head")  # a retomada: termina o serviço, não quebra

    con = sqlite3.connect(db_path)
    linhas = dict(
        con.execute("select id, data_capturada_utc from media_files")
    )
    con.close()
    # A que faltava foi preenchida...
    assert linhas[1] == "2019-07-14 14:00:00"
    # ...e o fuso real escrito no meio-tempo NÃO foi atropelado pelo backfill.
    assert linhas[2] == "2019-07-14 12:00:00"


def test_roundtrip_media_file(migrated_engine):
    from fotoorganizer.models import (
        ConfidenceLevel,
        Evidence,
        MediaFile,
        Source,
    )

    factory = create_session_factory(migrated_engine)
    with factory() as session:
        source = Source(caminho="/Volumes/Fotos", apelido="HD externo")
        media = MediaFile(
            source=source,
            caminho="/Volumes/Fotos/Viagens/日本/IMG_0001.JPG",  # unicode
            pasta="/Volumes/Fotos/Viagens/日本",
            nome="IMG_0001.JPG",
            extensao="jpg",
            tamanho=4_321_000,
            data_capturada=datetime(2024, 5, 4, 10, 30, tzinfo=timezone.utc),
            make="Canon",
            model="EOS R6",
            gps_lat=35.0116,
            gps_lon=135.7681,
            hash_rapido="xx64:abc123",
        )
        session.add(media)
        session.flush()  # garante media.id para a evidência
        session.add(
            Evidence(
                media_id=media.id,
                campo="pais",
                origem="gps",
                valor="Japão",
                nivel=ConfidenceLevel.ALTA,
                score=0.95,
                justificativa="GPS EXIF válido dentro do território do Japão",
                versao_logica="0.1.0",
            )
        )
        session.commit()

    with factory() as session:
        salvo = session.query(MediaFile).one()
        assert salvo.nome == "IMG_0001.JPG"
        assert "日本" in salvo.caminho
        assert salvo.source.apelido == "HD externo"
        evidencia = session.query(Evidence).one()
        assert evidencia.nivel == ConfidenceLevel.ALTA
        assert evidencia.origem == "gps"


def test_constraint_caminho_unico_por_fonte(migrated_engine):
    import pytest
    from sqlalchemy.exc import IntegrityError

    from fotoorganizer.models import MediaFile, Source

    factory = create_session_factory(migrated_engine)
    with factory() as session:
        source = Source(caminho="/tmp/fotos")
        kwargs = dict(
            caminho="/tmp/fotos/a.jpg", pasta="/tmp/fotos", nome="a.jpg",
            extensao="jpg", tamanho=1,
        )
        session.add_all(
            [MediaFile(source=source, **kwargs), MediaFile(source=source, **kwargs)]
        )
        with pytest.raises(IntegrityError):
            session.commit()
