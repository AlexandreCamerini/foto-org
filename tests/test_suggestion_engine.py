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
        # Viagem à França: 3 com GPS ao longo de 3 dias, 1 sem GPS no meio.
        for i, dias in enumerate([0, 1, 3]):
            session.add(_media(
                fonte.id, f"franca_{i}.jpg", "/fotos/desorganizadas",
                data=base + timedelta(days=dias), gps=(43.95, 4.8083),
            ))
        session.add(_media(
            fonte.id, "sem_gps.jpg", "/fotos/desorganizadas",
            data=base + timedelta(days=2),
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
    # Sessão qualificou como viagem pela estadia geocodificada (regra 5).
    assert por_campo["viagem"].origem == "geocoding_offline"
    assert "4 fotos entre" in por_campo["viagem"].justificativa
    assert "ao longo de" in por_campo["viagem"].justificativa


def test_vizinhanca_infere_pais_de_fotos_proximas(ambiente):
    factory, engine = ambiente
    engine.gerar()

    _, evidencias = _sugestao_de(factory, "sem_gps.jpg")
    pais = next(e for e in evidencias if e.campo == "pais")
    assert pais.origem == "vizinhanca"
    assert pais.valor == "França"
    assert pais.nivel == ConfidenceLevel.MEDIA
    assert "mesma sessão têm GPS em França" in pais.justificativa


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


def test_viagens_coladas_separadas_pela_passagem_em_casa(migrated_engine):
    """Duas idas à França com só 1 dia em casa no meio: o gap temporal de
    3 dias não separa, a transição casa↔fora sim — devem virar 2 viagens."""
    factory = create_session_factory(migrated_engine)
    base = datetime(2024, 5, 1, 10, 0)
    casa_gps = (-23.55, -46.63)
    with factory() as session:
        fonte = Source(caminho="/fotos")
        session.add(fonte)
        session.flush()
        # Massa de fotos em casa ao longo do ano — estabelece a "casa"
        # (célula modal exige ≥20 fotos com GPS e ≥30% nela).
        for i in range(22):
            session.add(_media(
                fonte.id, f"casa_{i}.jpg", "/fotos/dia a dia",
                data=base - timedelta(days=10 * (i + 1)), gps=casa_gps,
            ))
        # Viagem A (dias 0-2), casa (dias 3-4), viagem B (dias 5-7):
        # nenhuma lacuna chega a 3 dias.
        for i in range(3):
            session.add(_media(
                fonte.id, f"ida_{i}.jpg", "/fotos/DCIM",
                data=base + timedelta(days=i), gps=(43.95, 4.8083),
            ))
        for i in range(2):
            session.add(_media(
                fonte.id, f"pausa_{i}.jpg", "/fotos/DCIM",
                data=base + timedelta(days=3 + i), gps=casa_gps,
            ))
        for i in range(3):
            session.add(_media(
                fonte.id, f"volta_{i}.jpg", "/fotos/DCIM",
                data=base + timedelta(days=5 + i), gps=(43.95, 4.8083),
            ))
        session.commit()

    engine = SuggestionEngine(factory, LocationResolver(FakeGeocoder()))
    resultado = engine.gerar()

    assert resultado["viagens"] == 2
    with factory() as session:
        trips = list(session.scalars(select(Trip)))
    assert len(trips) == 2
    assert {t.nome for t in trips} == {"França"}
    # Períodos distintos: A termina antes de B começar.
    trips.sort(key=lambda t: t.inicio)
    assert trips[0].fim < trips[1].inicio


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


def test_aniversario_na_pasta_nao_vira_viagem(migrated_engine):
    """O caso real: pasta 'Serena 15 Anos', fotos de poucas horas — deve
    virar Eventos/2026/Serena 15 Anos, nunca 'Viagem de 09-05'."""
    factory = create_session_factory(migrated_engine)
    base = datetime(2026, 5, 9, 17, 25)
    with factory() as session:
        fonte = Source(caminho="/fotos")
        session.add(fonte)
        session.flush()
        for i in range(6):
            session.add(_media(
                fonte.id, f"IMG_{i:04d}.jpg", "/fotos/2026/Serena 15 Anos",
                data=base + timedelta(minutes=30 * i),
            ))
        session.commit()

    SuggestionEngine(factory).gerar()

    sugestao, evidencias = _sugestao_de(factory, "IMG_0000.jpg")
    assert sugestao.destino_sugerido == "Eventos/2026/Serena 15 Anos"
    campos = {e.campo: e for e in evidencias}
    assert "viagem" not in campos
    assert campos["evento"].valor == "Serena 15 Anos"
    assert campos["evento"].origem == "pasta"
    assert "indica um evento" in campos["evento"].justificativa
    assert campos["categoria"].valor == "Eventos"


def test_album_curto_vira_evento_nomeado(migrated_engine):
    """Pasta 'Quizomba' (álbum sem keyword), sessão de horas → evento."""
    factory = create_session_factory(migrated_engine)
    base = datetime(2026, 2, 17, 9, 27)
    with factory() as session:
        fonte = Source(caminho="/fotos")
        session.add(fonte)
        session.flush()
        for i in range(4):
            session.add(_media(
                fonte.id, f"IMG_{i:04d}.jpg", "/fotos/2026/Quizomba",
                data=base + timedelta(minutes=45 * i),
            ))
        session.commit()

    SuggestionEngine(factory).gerar()
    sugestao, evidencias = _sugestao_de(factory, "IMG_0000.jpg")
    assert sugestao.destino_sugerido == "Eventos/2026/Quizomba"
    assert all(e.campo != "viagem" for e in evidencias)


def test_pastas_tecnicas_sem_sinal_ficam_neutras(migrated_engine):
    """Sessão de horas em pasta técnica: sem viagem, sem evento inventado."""
    factory = create_session_factory(migrated_engine)
    base = datetime(2025, 5, 24, 14, 0)
    with factory() as session:
        fonte = Source(caminho="/fotos")
        session.add(fonte)
        session.flush()
        for i in range(3):
            session.add(_media(
                fonte.id, f"IMG_{i:04d}.jpg", "/fotos/2025_05_24/[Originals]",
                data=base + timedelta(minutes=10 * i),
            ))
        session.commit()

    SuggestionEngine(factory).gerar()
    sugestao, evidencias = _sugestao_de(factory, "IMG_0000.jpg")
    campos = {e.campo for e in evidencias}
    assert "viagem" not in campos and "evento" not in campos
    assert sugestao.destino_sugerido == "2025"  # só o ano — não inventa


def test_advisor_llm_apoia_sessao_neutra(migrated_engine):
    """Sessão neutra + advisor: vira evento com origem 'llm' (média-baixa)."""
    from fotoorganizer.classification.advisor import AdvisorResult, ClusterInfo

    class FakeAdvisor:
        def __init__(self):
            self.clusters: list[ClusterInfo] = []

        @property
        def local(self):
            return False

        def classificar(self, cluster):
            self.clusters.append(cluster)
            return AdvisorResult(
                categoria="Eventos", evento="Luau da firma",
                justificativa="nomes de arquivo citam 'luau'",
            )

    factory = create_session_factory(migrated_engine)
    base = datetime(2025, 5, 24, 14, 0)
    with factory() as session:
        fonte = Source(caminho="/fotos")
        session.add(fonte)
        session.flush()
        for i in range(3):
            session.add(_media(
                fonte.id, f"luau_{i}.jpg", "/fotos/2025_05_24",
                data=base + timedelta(minutes=10 * i),
            ))
        session.commit()

    advisor = FakeAdvisor()
    SuggestionEngine(factory, advisor=advisor).gerar()

    # Só metadados foram oferecidos ao advisor.
    (cluster,) = advisor.clusters
    assert cluster.n_fotos == 3
    assert cluster.pastas == ("/fotos/2025_05_24",)

    sugestao, evidencias = _sugestao_de(factory, "luau_0.jpg")
    evento = next(e for e in evidencias if e.campo == "evento")
    assert evento.origem == "llm"
    assert evento.nivel == ConfidenceLevel.MEDIA
    assert "LLM (apenas metadados)" in evento.justificativa
    assert sugestao.destino_sugerido == "Eventos/2025/Luau da firma"


def test_advisor_nulo_nao_opina():
    from fotoorganizer.classification.advisor import ClusterInfo, NullAdvisor

    cluster = ClusterInfo(
        pastas=("/x",), exemplos_arquivos=("a.jpg",),
        inicio=datetime(2025, 1, 1), fim=datetime(2025, 1, 1), n_fotos=1,
    )
    advisor = NullAdvisor()
    assert advisor.local is True
    assert advisor.classificar(cluster) is None
