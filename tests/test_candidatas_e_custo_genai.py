"""Pré-filtro D-01 de pastas candidatas e estimativa de custo (D-04/D-05,
decisão híbrida D-079) da classificação de pasta por GenAI.
"""

from datetime import datetime

from fotoorganizer.classification.candidatas_de_pasta import (
    CandidataDePasta,
    candidatas,
)
from fotoorganizer.database import create_session_factory
from fotoorganizer.models import ConfidenceLevel, Evidence, MediaFile, MediaRole, Source


# -- fixtures locais, no molde de tests/test_inventario.py -----------------

def _fonte(session, apelido="scan") -> Source:
    source = Source(caminho="/Users/eu/Pictures", apelido=apelido)
    session.add(source)
    session.flush()
    return source


def _arquivo(session, source, pasta, nome, organizavel=True, **kw) -> MediaFile:
    extras = {}
    if not organizavel:
        extras["papel"] = MediaRole.SINAL
    extras.update(kw)
    media = MediaFile(
        source_id=source.id, caminho=f"{pasta}/{nome}", pasta=pasta,
        nome=nome, extensao=nome.rsplit(".", 1)[-1].lower(), tamanho=1,
        **extras,
    )
    session.add(media)
    session.flush()
    return media


def _evidencia(session, media_id, campo, valor="x") -> None:
    session.add(Evidence(
        media_id=media_id, campo=campo, origem="teste", valor=valor,
        nivel=ConfidenceLevel.ALTA, score=0.9,
        justificativa="fixture de teste", versao_logica="0.1.0",
    ))


# -- candidatas() — pré-filtro D-01 -----------------------------------------

def test_candidata_pasta_sem_categoria(migrated_engine):
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        fonte = _fonte(session)
        m = _arquivo(session, fonte, "/Users/eu/Pictures/Praia", "a.jpg")
        _evidencia(session, m.id, "cidade")
        session.commit()

        resultado = candidatas(session, set())

    assert resultado == [CandidataDePasta(
        pasta="/Users/eu/Pictures/Praia", n_fotos=1,
        campos_ausentes=("categoria",), periodo=None,
    )]


def test_candidata_pasta_sem_cidade_pais(migrated_engine):
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        fonte = _fonte(session)
        m = _arquivo(session, fonte, "/Users/eu/Pictures/Sem categoria", "a.jpg")
        _evidencia(session, m.id, "categoria", "Viagens")
        session.commit()

        resultado = candidatas(session, set())

    assert len(resultado) == 1
    assert resultado[0].campos_ausentes == ("cidade_pais",)


def test_candidata_pasta_com_os_dois_campos_vazios_na_ordem(migrated_engine):
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        fonte = _fonte(session)
        _arquivo(session, fonte, "/Users/eu/Pictures/Nova", "a.jpg")
        session.commit()

        resultado = candidatas(session, set())

    assert len(resultado) == 1
    assert resultado[0].campos_ausentes == ("categoria", "cidade_pais")


def test_pasta_completa_nao_e_candidata(migrated_engine):
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        fonte = _fonte(session)
        m = _arquivo(session, fonte, "/Users/eu/Pictures/Completa", "a.jpg")
        _evidencia(session, m.id, "categoria", "Família")
        _evidencia(session, m.id, "pais", "Brasil")
        session.commit()

        resultado = candidatas(session, set())

    assert resultado == []


def test_pasta_ja_classificada_nao_e_candidata(migrated_engine):
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        fonte = _fonte(session)
        _arquivo(session, fonte, "/Users/eu/Pictures/Ja Feita", "a.jpg")
        session.commit()

        resultado = candidatas(session, {"/Users/eu/Pictures/Ja Feita"})

    assert resultado == []


def test_candidata_ignora_evidencia_de_midia_nao_organizavel(migrated_engine):
    """Uma miniatura (papel=SINAL) com `categoria` inferida não pode
    "completar" uma pasta cuja foto real (organizável) continua vazia."""
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        fonte = _fonte(session)
        real = _arquivo(session, fonte, "/Users/eu/Pictures/Mista", "a.jpg")
        miniatura = _arquivo(
            session, fonte, "/Users/eu/Pictures/Mista", "thumb.jpg",
            organizavel=False,
        )
        _evidencia(session, miniatura.id, "categoria", "Viagens")
        session.commit()

        resultado = candidatas(session, set())

    assert len(resultado) == 1
    assert resultado[0].n_fotos == 1
    assert "categoria" in resultado[0].campos_ausentes


def test_pasta_so_com_nao_acervo_nao_e_candidata(migrated_engine):
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        fonte = _fonte(session)
        _arquivo(
            session, fonte, "/Users/eu/Pictures/So Miniatura", "thumb.jpg",
            organizavel=False,
        )
        session.commit()

        resultado = candidatas(session, set())

    assert resultado == []


def test_candidata_conta_apenas_midia_organizavel_em_n_fotos(migrated_engine):
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        fonte = _fonte(session)
        _arquivo(session, fonte, "/Users/eu/Pictures/Duas", "a.jpg")
        _arquivo(session, fonte, "/Users/eu/Pictures/Duas", "b.jpg")
        _arquivo(
            session, fonte, "/Users/eu/Pictures/Duas", "thumb.jpg",
            organizavel=False,
        )
        session.commit()

        resultado = candidatas(session, set())

    assert len(resultado) == 1
    assert resultado[0].n_fotos == 2


def test_candidata_periodo_none_sem_data(migrated_engine):
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        fonte = _fonte(session)
        _arquivo(session, fonte, "/Users/eu/Pictures/Sem Data", "a.jpg")
        session.commit()

        resultado = candidatas(session, set())

    assert resultado[0].periodo is None


def test_candidata_periodo_do_menor_ao_maior(migrated_engine):
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        fonte = _fonte(session)
        _arquivo(
            session, fonte, "/Users/eu/Pictures/Viagem", "a.jpg",
            data_capturada=datetime(2024, 3, 19),
        )
        _arquivo(
            session, fonte, "/Users/eu/Pictures/Viagem", "b.jpg",
            data_capturada=datetime(2024, 3, 12),
        )
        session.commit()

        resultado = candidatas(session, set())

    assert resultado[0].periodo == "2024-03-12 a 2024-03-19"


def test_candidatas_ordenadas_por_pasta_deterministico(migrated_engine):
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        fonte = _fonte(session)
        _arquivo(session, fonte, "/Users/eu/Pictures/Zebra", "a.jpg")
        _arquivo(session, fonte, "/Users/eu/Pictures/Alfa", "b.jpg")
        _arquivo(session, fonte, "/Users/eu/Pictures/Meio", "c.jpg")
        session.commit()

        resultado = candidatas(session, set())

    assert [c.pasta for c in resultado] == [
        "/Users/eu/Pictures/Alfa",
        "/Users/eu/Pictures/Meio",
        "/Users/eu/Pictures/Zebra",
    ]
