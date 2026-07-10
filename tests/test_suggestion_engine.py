from dataclasses import dataclass
from datetime import datetime, timedelta

import pytest
from sqlalchemy import select

from fotoorganizer.classification import SuggestionEngine
from fotoorganizer.database import create_session_factory
from fotoorganizer.geolocation import GeoResult, LocationResolver
from fotoorganizer.models import (
    ConfidenceLevel,
    Evidence,
    MediaFile,
    Source,
    Suggestion,
    SuggestionStatus,
    Trip,
)
from fotoorganizer.repositories import SuggestionRepository


@dataclass
class FakeGeocoder:
    def resolve(self, lat, lon):
        if 40 < lat < 46:
            return GeoResult("França", "Provence", "Avignon", "fake")
        return None


def _media(source_id, nome, pasta, data=None, mtime=None, gps=None):
    return MediaFile(
        source_id=source_id, caminho=f"{pasta}/{nome}", pasta=pasta, nome=nome,
        extensao="jpg", tamanho=100, data_capturada=data, mtime=mtime,
        gps_lat=gps[0] if gps else None, gps_lon=gps[1] if gps else None,
    )


@pytest.fixture()
def ambiente(migrated_engine):
    factory = create_session_factory(migrated_engine)
    base = datetime(2024, 5, 4, 10, 0)
    with factory() as session:
        fonte = Source(caminho="/fotos")
        session.add(fonte)
        session.flush()
        # Viagem à França: 3 com GPS, 1 sem GPS na mesma janela temporal.
        for i in range(3):
            session.add(_media(
                fonte.id, f"franca_{i}.jpg", "/fotos/desorganizadas",
                data=base + timedelta(hours=i), gps=(43.95, 4.8083),
            ))
        session.add(_media(
            fonte.id, "sem_gps.jpg", "/fotos/desorganizadas",
            data=base + timedelta(hours=5),
        ))
        # Pasta nomeada por país, sem GPS, meses depois.
        session.add(_media(
            fonte.id, "toquio.jpg", "/fotos/Japão/Tóquio",
            data=base + timedelta(days=120),
        ))
        # Sem nada: só mtime.
        session.add(_media(
            fonte.id, "misteriosa.jpg", "/fotos/baguncа",
            mtime=base + timedelta(days=300),
        ))
        session.commit()
    engine = SuggestionEngine(factory, LocationResolver(FakeGeocoder()))
    return factory, engine


def _sugestao_de(factory, nome) -> tuple[Suggestion, list[Evidence]]:
    with factory() as session:
        media = session.scalar(select(MediaFile).where(MediaFile.nome == nome))
        sugestao = session.scalar(
            select(Suggestion).where(Suggestion.media_id == media.id)
        )
        evidencias = list(
            session.scalars(select(Evidence).where(Evidence.media_id == media.id))
        )
        if sugestao is not None:
            _ = sugestao.evidencias  # carrega antes de fechar
        return sugestao, evidencias


def test_gps_gera_destino_com_alta_e_justificativas(ambiente):
    factory, engine = ambiente
    stats = engine.gerar()
    assert stats["sugestoes"] == 6

    sugestao, evidencias = _sugestao_de(factory, "franca_0.jpg")
    assert "França" in sugestao.destino_sugerido
    assert "Avignon" in sugestao.destino_sugerido
    assert "2024" in sugestao.destino_sugerido

    por_campo = {e.campo: e for e in evidencias}
    assert por_campo["data"].origem == "exif"
    assert por_campo["data"].nivel == ConfidenceLevel.ALTA
    assert por_campo["pais"].origem == "geocoding_offline"
    assert "geocodificação offline" in por_campo["pais"].justificativa
    assert por_campo["viagem"].origem == "agrupamento"
    assert "4 fotos próximas" in por_campo["viagem"].justificativa


def test_vizinhanca_infere_pais_de_fotos_proximas(ambiente):
    factory, engine = ambiente
    engine.gerar()

    _, evidencias = _sugestao_de(factory, "sem_gps.jpg")
    pais = next(e for e in evidencias if e.campo == "pais")
    assert pais.origem == "vizinhanca"
    assert pais.valor == "França"
    assert pais.nivel == ConfidenceLevel.MEDIA
    assert "3 fotos da mesma viagem" in pais.justificativa


def test_pasta_da_pais_com_media_confianca(ambiente):
    factory, engine = ambiente
    engine.gerar()

    sugestao, evidencias = _sugestao_de(factory, "toquio.jpg")
    pais = next(e for e in evidencias if e.campo == "pais")
    assert (pais.origem, pais.valor) == ("pasta", "Japão")
    cidade = next(e for e in evidencias if e.campo == "cidade")
    assert cidade.valor == "Tóquio"
    assert "Japão/Tóquio" in sugestao.destino_sugerido


def test_sem_evidencia_fica_baixa_e_nao_inventa(ambiente):
    factory, engine = ambiente
    engine.gerar()

    sugestao, evidencias = _sugestao_de(factory, "misteriosa.jpg")
    assert sugestao.nivel == ConfidenceLevel.BAIXA
    campos = {e.campo for e in evidencias}
    assert "pais" not in campos and "cidade" not in campos
    data = next(e for e in evidencias if e.campo == "data")
    assert data.origem == "fs"


def test_viagem_nomeada_pelo_pais_dominante(ambiente):
    factory, engine = ambiente
    engine.gerar()
    with factory() as session:
        nomes = set(session.scalars(select(Trip.nome)))
    assert "França" in nomes


def test_destino_nao_duplica_ano_nem_pais(ambiente):
    factory, engine = ambiente
    engine.gerar()
    sugestao, _ = _sugestao_de(factory, "franca_0.jpg")
    # "{ano} - {viagem}" compõe "2024 - França"; {pais} some por ser igual
    # ao rótulo da viagem — nada de "2024 - 2024" nem "França/França".
    assert sugestao.destino_sugerido == "Viagens/2024 - França/Provence/Avignon"


def test_regeneracao_preserva_decisao_do_usuario(ambiente):
    factory, engine = ambiente
    engine.gerar()
    repo = SuggestionRepository(factory)

    sugestao, _ = _sugestao_de(factory, "toquio.jpg")
    repo.editar_destino(sugestao.id, "Meu/Destino/Especial")

    stats = engine.gerar()
    assert stats["preservadas"] == 1

    depois, _ = _sugestao_de(factory, "toquio.jpg")
    assert depois.id == sugestao.id
    assert depois.destino_sugerido == "Meu/Destino/Especial"
    assert depois.status == SuggestionStatus.EDITADA


def test_regeneracao_de_pendentes_nao_duplica(ambiente):
    factory, engine = ambiente
    engine.gerar()
    engine.gerar()
    with factory() as session:
        from sqlalchemy import func

        total = session.scalar(select(func.count(Suggestion.id)))
        assert total == 6
