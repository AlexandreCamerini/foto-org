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
