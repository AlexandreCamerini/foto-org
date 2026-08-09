"""`MediaFile.organizavel` — hybrid property, os dois lados (Python e SQL)
precisam concordar: é o que garante que filtrar em memória e filtrar num
WHERE dão a mesma resposta."""

from sqlalchemy import select

from fotoorganizer.database import create_session_factory
from fotoorganizer.models import MediaFile, MediaRole, Source


def _fonte(session, caminho="/Users/eu/Pictures", apelido="Pictures"):
    source = Source(caminho=caminho, apelido=apelido)
    session.add(source)
    session.flush()
    return source


def _arquivo(session, source, nome, **kw):
    media = MediaFile(
        source_id=source.id, caminho=f"/Users/eu/Pictures/{nome}",
        pasta="/Users/eu/Pictures", nome=nome,
        extensao=nome.rsplit(".", 1)[-1].lower(), tamanho=1, **kw
    )
    session.add(media)
    session.flush()
    return media


def test_arquivo_offline_tira_organizavel_no_lado_python(migrated_engine):
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        f = _fonte(session)
        media = _arquivo(session, f, "sumiu.jpg", arquivo_offline=True)
        session.commit()

        assert media.organizavel is False


def test_arquivo_offline_tira_organizavel_no_lado_sql(migrated_engine):
    """O mesmo predicado, agora dentro de um WHERE — o caminho que
    `repositories/media.py` usa para filtrar a Biblioteca inteira."""
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        f = _fonte(session)
        _arquivo(session, f, "ok.jpg")
        _arquivo(session, f, "sumiu.jpg", arquivo_offline=True)
        session.commit()

        organizaveis = session.scalars(
            select(MediaFile).where(MediaFile.organizavel)
        ).all()
        assert [m.nome for m in organizaveis] == ["ok.jpg"]

        nao_organizaveis = session.scalars(
            select(MediaFile).where(~MediaFile.organizavel)
        ).all()
        assert [m.nome for m in nao_organizaveis] == ["sumiu.jpg"]


def test_arquivo_offline_e_ortogonal_a_papel_e_ausente(migrated_engine):
    """As três razões de não ser organizável continuam valendo cada uma
    por si: testemunha (papel), referência sem arquivo (arquivo_ausente) e
    agora arquivo sumido (arquivo_offline) — nenhuma delas mascara as
    outras duas."""
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        f = _fonte(session)
        testemunha = _arquivo(session, f, "testemunha.jpg",
                              papel=MediaRole.SINAL)
        ausente = _arquivo(session, f, "ausente.jpg", arquivo_ausente=True)
        offline = _arquivo(session, f, "offline.jpg", arquivo_offline=True)
        session.commit()

        assert testemunha.organizavel is False
        assert ausente.organizavel is False
        assert offline.organizavel is False
