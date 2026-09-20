from dataclasses import dataclass
from datetime import datetime, timedelta

import pytest
from sqlalchemy import func, select

from fotoorganizer.classification import SuggestionEngine
from fotoorganizer.classification.confidence import nivel_para_score
from fotoorganizer.database import create_session_factory
from fotoorganizer.geolocation import GeoResult, LocationResolver
from fotoorganizer.geolocation.timezones import TZ_POR_PAIS
from fotoorganizer.grouping.correlacao import campos_confiaveis
from fotoorganizer.metadata.base import NAMESPACE_CURADORIA
from fotoorganizer.models import (
    ConfidenceLevel,
    Evidence,
    Event,
    Location,
    MediaFile,
    MediaRole,
    MetadataEntry,
    Source,
    SourceType,
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


def _media(source_id, nome, pasta, data=None, mtime=None, gps=None,
           make=None, model=None, hash_rapido=None, phash=None):
    return MediaFile(
        source_id=source_id, caminho=f"{pasta}/{nome}", pasta=pasta, nome=nome,
        extensao="jpg", tamanho=100, data_capturada=data, mtime=mtime,
        gps_lat=gps[0] if gps else None, gps_lon=gps[1] if gps else None,
        make=make, model=model, hash_rapido=hash_rapido,
        hash_perceptual=phash,
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
    assert "2024" in sugestao.destino_sugerido
    # A viagem é UMA pasta: a cidade não vira nível abaixo dela, mas
    # continua registrada como evidência (e visível no inspetor).
    assert "Avignon" not in sugestao.destino_sugerido

    por_campo = {e.campo: e for e in evidencias}
    assert por_campo["cidade"].valor == "Avignon"
    assert por_campo["data"].origem == "exif"
    assert por_campo["data"].nivel == ConfidenceLevel.ALTA
    assert por_campo["pais"].origem == "geocoding_offline"
    assert "geocodificação offline" in por_campo["pais"].justificativa
    # Sessão qualificou como viagem pela estadia geocodificada (regra 5).
    assert por_campo["viagem"].origem == "geocoding_offline"
    assert "4 fotos entre" in por_campo["viagem"].justificativa
    assert "ao longo de" in por_campo["viagem"].justificativa


def test_lugar_suprimido_do_caminho_continua_vinculado_a_sugestao(ambiente):
    """A viagem é uma pasta só, então cidade não vira nível abaixo dela.
    Mas o lugar é a resposta a "por que aqui?", e quem serializa isso para a
    API é `Suggestion.evidencias` — não basta existir em `evidence`."""
    factory, engine = ambiente
    engine.gerar()

    sugestao, todas = _sugestao_de(factory, "franca_0.jpg")
    vinculadas = {e.campo: e for e in sugestao.evidencias}

    assert "Avignon" not in sugestao.destino_sugerido
    assert vinculadas["cidade"].valor == "Avignon"
    assert vinculadas["pais"].valor == "França"
    # Contexto não decide destino: o elo mais fraco continua saindo só do
    # que virou pasta (docs/CONFIANCA.md proíbe misturar).
    decidiram = [e.score for c, e in vinculadas.items()
                 if c not in ("pais", "regiao", "cidade")]
    assert sugestao.nivel == nivel_para_score(min(decidiram))


def test_gps_herdado_dentro_de_viagem_chega_a_sugestao(migrated_engine):
    """O caso do dono: câmera sem GPS herda do telefone, e a foto cai numa
    viagem. A viagem nomeia a pasta e suprime a cidade do caminho — a
    justificativa da herança não pode sumir junto."""
    factory = create_session_factory(migrated_engine)
    base = datetime(2024, 5, 4, 10, 0)
    with factory() as session:
        camera = Source(caminho="/fotos/Viagens/Camera")
        telefone = Source(caminho="/fotos/Viagens/iPhone")
        session.add_all([camera, telefone])
        session.flush()
        for i in range(4):
            session.add(_media(
                camera.id, f"cam_{i}.jpg", "/fotos/Viagens/Camera",
                data=base + timedelta(hours=6 * i),
                make="Canon", model="EOS R5",
            ))
            session.add(_media(
                telefone.id, f"tel_{i}.jpg", "/fotos/Viagens/iPhone",
                data=base + timedelta(hours=6 * i, minutes=2),
                gps=(43.95, 4.8083), make="Apple", model="iPhone 15",
            ))
        session.commit()

    engine = SuggestionEngine(factory, LocationResolver(FakeGeocoder()))
    engine.gerar()

    sugestao, _ = _sugestao_de(factory, "cam_0.jpg")
    vinculadas = {e.campo: e for e in sugestao.evidencias}
    heranca = vinculadas.get("cidade")
    assert heranca is not None, "a cidade herdada precisa chegar à sugestão"
    assert heranca.origem == "vizinhanca_temporal"
    assert "herdado de 'tel_0.jpg'" in heranca.justificativa
    assert "iPhone 15" in heranca.justificativa


def test_fotos_sem_data_de_captura_nao_viram_viagem(migrated_engine):
    """mtime é quando o arquivo chegou ao disco, não quando a foto foi
    tirada. Um lote de arquivos sem EXIF (captura de tela, arquivo
    recuperado) não pode virar uma viagem na data do scan."""
    factory = create_session_factory(migrated_engine)
    chegada = datetime(2026, 7, 29, 14, 0)
    with factory() as session:
        fonte = Source(caminho="/fotos")
        session.add(fonte)
        session.flush()
        # O gatilho real: basta UM arquivo sem EXIF numa pasta cujo nome
        # classifica a sessão como viagem. O período sai do mtime, e a
        # viagem nasce datada no dia do scan.
        session.add(_media(
            fonte.id, "sem_exif_viagem.jpg", "/fotos/Viagens/2024 - França",
            mtime=chegada,
        ))
        for i in range(4):
            session.add(_media(
                fonte.id, f"sem_exif_{i}.png", "/fotos/Diversos",
                mtime=chegada + timedelta(minutes=i),
            ))
        session.commit()

    engine = SuggestionEngine(factory, LocationResolver(FakeGeocoder()))
    stats = engine.gerar()

    assert stats["viagens"] == 0
    assert stats["eventos"] == 0
    with factory() as session:
        assert session.scalar(select(Trip)) is None
    # As fotos continuam catalogadas e com sugestão — só não inventam viagem.
    assert stats["sugestoes"] == 5


def test_data_no_nome_do_arquivo_vira_evidencia_media(migrated_engine):
    """Critério de aceite da fase 2: foto sem EXIF mas com nome
    IMG-20240315-WA0012.jpg ganha evidência de data com origem no nome do
    arquivo e confiança média — em vez de cair no mtime (baixa), que muda
    a cada cópia entre discos."""
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        fonte = Source(caminho="/fotos")
        session.add(fonte)
        session.flush()
        session.add(_media(
            fonte.id, "IMG-20240315-WA0012.jpg", "/fotos/WhatsApp",
            mtime=datetime(2026, 7, 29, 14, 0),  # chegou ao disco em 2026
        ))
        session.commit()

    SuggestionEngine(factory, LocationResolver(FakeGeocoder())).gerar()

    with factory() as session:
        data = session.scalar(
            select(Evidence).where(Evidence.campo == "data")
        )
        assert data.origem == "nome_arquivo"
        assert data.nivel == ConfidenceLevel.MEDIA
        assert data.valor.startswith("2024-03-15")
        assert "20240315" in data.justificativa
        # O ano do destino vem do nome, não do mtime: a foto recebida em
        # 2024 não pode ser arquivada como 2026.
        sugestao = session.scalar(select(Suggestion))
        assert "2024" in sugestao.destino_sugerido
        assert "2026" not in sugestao.destino_sugerido


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
    # D-083: "Tóquio" é confirmada no dataset offline e sai com a grafia
    # dele ("Tokyo") — a mesma que o geocoding reverso dá às fotos com GPS,
    # senão a mesma cidade viraria duas pastas no destino.
    assert cidade.valor == "Tokyo"
    assert "confirmada no dataset offline" in cidade.justificativa
    assert "Japão/Tokyo" in sugestao.destino_sugerido


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


def test_uma_viagem_e_uma_pasta_so(ambiente):
    factory, engine = ambiente
    engine.gerar()
    # "{ano} - {viagem}" compõe "2024 - França"; nada de "2024 - 2024"
    # nem "França/França". E a geografia não desce abaixo da viagem: as
    # fotos da mesma viagem caem TODAS na mesma pasta, tenham GPS ou não.
    destinos = {
        _sugestao_de(factory, nome)[0].destino_sugerido
        for nome in ["franca_0.jpg", "franca_1.jpg", "franca_2.jpg",
                     "sem_gps.jpg"]
    }
    assert destinos == {"Viagens/2024 - França"}


def test_gps_herdado_de_outra_fonte_gera_evidencia_e_destino(migrated_engine):
    """Câmera sem GPS + telefone com GPS na mesma cena: a foto da câmera
    herda a localização, com evidência explicando de quem veio."""
    factory = create_session_factory(migrated_engine)
    base = datetime(2024, 5, 4, 10, 0)
    with factory() as session:
        pasta_raw = Source(caminho="/fotos/raw")
        fonte_tel = Source(caminho="/fotos/DCIM")
        session.add_all([pasta_raw, fonte_tel])
        session.flush()
        # 3 fotos da câmera SEM GPS…
        for i in range(3):
            session.add(_media(
                pasta_raw.id, f"raw_{i}.jpg", "/fotos/raw",
                data=base + timedelta(minutes=5 * i),
                make="Canon", model="EOS R6",
            ))
        # …e 2 do telefone COM GPS, minutos de distância.
        for i in range(2):
            session.add(_media(
                fonte_tel.id, f"tel_{i}.jpg", "/fotos/DCIM",
                data=base + timedelta(minutes=5 * i + 1),
                gps=(43.95, 4.8083), make="Apple", model="iPhone 15",
            ))
        session.commit()

    engine = SuggestionEngine(factory, LocationResolver(FakeGeocoder()))
    resultado = engine.gerar()
    assert resultado["herancas_gps"] == 3

    sugestao, evidencias = _sugestao_de(factory, "raw_0.jpg")
    origens = {e.origem for e in evidencias}
    assert "vizinhanca_temporal" in origens
    heranca = next(e for e in evidencias if e.origem == "vizinhanca_temporal")
    assert "herdado de 'tel_0.jpg'" in heranca.justificativa
    assert "iPhone 15" in heranca.justificativa
    # A localização herdada chega ao destino sugerido.
    assert "Avignon" in sugestao.destino_sugerido


def test_gps_herdado_da_propria_camera_com_receptor_confirmado(migrated_engine):
    """Regra 1 (D-086): a EOS 5D Mark IV tem receptor GPS embutido
    confirmado (D-029) — quando falha numa foto, a foto vizinha do MESMO
    rolo pode doar. A confiança cai para baixa (mecanismo, não amostra
    medida) e a justificativa explica o motivo."""
    factory = create_session_factory(migrated_engine)
    base = datetime(2024, 5, 4, 10, 0)
    with factory() as session:
        fonte = Source(caminho="/fotos/raw")
        session.add(fonte)
        session.flush()
        session.add(_media(
            fonte.id, "5d_0.jpg", "/fotos/raw", data=base,
            make="Canon", model="Canon EOS 5D Mark IV",
        ))
        session.add(_media(
            fonte.id, "5d_1.jpg", "/fotos/raw",
            data=base + timedelta(minutes=2), gps=(43.95, 4.8083),
            make="Canon", model="Canon EOS 5D Mark IV",
        ))
        session.commit()

    engine = SuggestionEngine(factory, LocationResolver(FakeGeocoder()))
    resultado = engine.gerar()
    assert resultado["herancas_gps"] == 1

    sugestao, evidencias = _sugestao_de(factory, "5d_0.jpg")
    de_heranca = [e for e in evidencias if e.origem == "vizinhanca_temporal"]
    heranca = de_heranca[0]
    assert "receptor de GPS embutido" in heranca.justificativa
    # Achado da 3ª e 4ª rodadas de revisão: "a 2min de distância" sozinho
    # implicava precisão de cidade — a frase precisa dizer que só o país
    # foi afirmado, E dizer o motivo certo (falta de amostra, não o Δt,
    # que aqui é curto o bastante para sustentar cidade em condições
    # normais).
    assert "só o país é afirmado" in heranca.justificativa
    assert "sem amostra medida de acurácia" in heranca.justificativa
    assert heranca.nivel == ConfidenceLevel.BAIXA
    # Achado da 2ª rodada de revisão: sem amostra medida, só país pode
    # sustentar o destino sugerido — cidade/região vazavam para a cópia
    # (`operations/planner.py` lê `destino_sugerido`) mesmo depois do
    # planner EXIF e da tela de detalhe já recusarem a mesma cidade.
    assert {e.campo for e in de_heranca} == {"pais"}
    assert "Avignon" not in (sugestao.destino_sugerido or "")
    assert "França" in (sugestao.destino_sugerido or "")


def test_desempate_de_doadora_prefere_pasta_sobre_catalogo_externo(
    migrated_engine,
):
    """Repro de ponta a ponta de D-032: no mesmo segundo, o catálogo Apple
    Fotos grava 'casa' (coordenada que pode ter sido atribuída no app, não
    medida) e a câmera real (pasta, EXIF) grava o lugar verdadeiro, longe
    dali. Uma órfã sem GPS no mesmo instante tem que herdar da câmera, não
    da 'casa' — sem o desempate, dependia da ordem incidental da consulta
    ao banco."""
    factory = create_session_factory(migrated_engine)
    base = datetime(2019, 4, 19, 13, 50, 12)

    @dataclass
    class GeocoderQualquerLugar:
        def resolve(self, lat, lon):
            if lat < -20:
                return GeoResult("Brasil", "Rio de Janeiro", "Penedo", "fake")
            return GeoResult("Brasil", "Rio de Janeiro", "Casa", "fake")

    with factory() as session:
        fonte_apple = Source(caminho="/apple", tipo=SourceType.APPLE_PHOTOS)
        fonte_pasta = Source(caminho="/pasta", tipo=SourceType.PASTA)
        fonte_organizada = Source(caminho="/organizada", tipo=SourceType.PASTA)
        session.add_all([fonte_apple, fonte_pasta, fonte_organizada])
        session.flush()
        session.add(_media(
            fonte_apple.id, "casa.jpg", "/apple", data=base,
            gps=(-22.9657, -43.1892),
        ))
        session.add(_media(
            fonte_pasta.id, "096A5942.CR2", "/pasta", data=base,
            gps=(-22.3301, -44.6185), make="Canon", model="EOS R6",
        ))
        session.add(_media(
            fonte_organizada.id, "orfa.jpg", "/organizada", data=base,
        ))
        session.commit()

    engine = SuggestionEngine(factory, LocationResolver(GeocoderQualquerLugar()))
    engine.gerar()

    sugestao, evidencias = _sugestao_de(factory, "orfa.jpg")
    de_heranca = [e for e in evidencias if e.origem == "vizinhanca_temporal"]
    assert de_heranca   # herdou algo
    for e in de_heranca:
        assert "096A5942.CR2" in e.justificativa
        assert "casa.jpg" not in e.justificativa
    cidade = next((e for e in de_heranca if e.campo == "cidade"), None)
    assert cidade is not None and cidade.valor == "Penedo"


def test_deriva_de_relogio_corrigida_pelas_ancoras(migrated_engine):
    """Câmera 3h atrasada: as cópias no 'takeout' (mesmo phash, hora
    certa) ancoram o offset e a herança volta a funcionar."""
    factory = create_session_factory(migrated_engine)
    base = datetime(2024, 5, 4, 10, 0)
    with factory() as session:
        pasta_raw = Source(caminho="/fotos/raw")
        takeout = Source(caminho="/fotos/takeout")
        session.add_all([pasta_raw, takeout])
        session.flush()
        # Âncoras: 2 fotos da câmera (hora errada) + cópias com GPS e hora
        # certa no takeout (mesmo phash).
        for i in range(2):
            session.add(_media(
                pasta_raw.id, f"anc_{i}.jpg", "/fotos/raw",
                data=base + timedelta(minutes=i),
                make="Canon", model="EOS R6", phash=f"ph_{i}",
            ))
            session.add(_media(
                takeout.id, f"anc_takeout_{i}.jpg", "/fotos/takeout",
                data=base + timedelta(hours=3, minutes=i),
                gps=(43.95, 4.8083), phash=f"ph_{i}",
            ))
        # Foto nova da câmera sem cópia; doadora do takeout 1min depois
        # (na linha do tempo corrigida).
        session.add(_media(
            pasta_raw.id, "nova.jpg", "/fotos/raw",
            data=base + timedelta(minutes=30),
            make="Canon", model="EOS R6",
        ))
        session.add(_media(
            takeout.id, "doadora.jpg", "/fotos/takeout",
            data=base + timedelta(hours=3, minutes=31),
            gps=(43.95, 4.8083),
        ))
        session.commit()

    engine = SuggestionEngine(factory, LocationResolver(FakeGeocoder()))
    engine.gerar()

    _, evidencias = _sugestao_de(factory, "nova.jpg")
    assert any(e.origem == "vizinhanca_temporal" for e in evidencias)


def test_viagem_multipais_rotulada_pelas_pernas(migrated_engine):
    """21 dias fora passando por 2 países (sem casa conhecida): uma viagem
    só, nomeada pelas pernas em ordem cronológica de chegada."""

    @dataclass
    class GeocoderDoisPaises:
        def resolve(self, lat, lon):
            if lat > 20:
                return GeoResult("Emirados Árabes", None, "Dubai", "fake")
            return GeoResult("Tailândia", None, "Bangkok", "fake")

    factory = create_session_factory(migrated_engine)
    base = datetime(2025, 11, 1, 10, 0)
    with factory() as session:
        fonte = Source(caminho="/fotos")
        session.add(fonte)
        session.flush()
        for i in range(4):  # Dubai primeiro…
            session.add(_media(
                fonte.id, f"dubai_{i}.jpg", "/fotos/DCIM",
                data=base + timedelta(days=i), gps=(25.2, 55.3),
            ))
        for i in range(4):  # …Tailândia depois, com mais dias.
            session.add(_media(
                fonte.id, f"thai_{i}.jpg", "/fotos/DCIM",
                data=base + timedelta(days=6 + 2 * i), gps=(13.75, 100.5),
            ))
        session.commit()

    engine = SuggestionEngine(factory, LocationResolver(GeocoderDoisPaises()))
    resultado = engine.gerar()

    assert resultado["viagens"] == 1
    with factory() as session:
        trip = session.scalars(select(Trip)).one()
    assert trip.nome == "Emirados Árabes – Tailândia"


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


def test_aniversario_de_manha_e_show_a_noite_viram_dois_eventos(migrated_engine):
    """O caso da fase 8 (docs/prompts/fase-8-eventos-e-decisao.md, Problema 3
    e critério de aceite 5): mesmo dia, mesma pasta, mesma câmera — só o
    ritmo de disparo separa. Sem `_subdividir` (antes do commit 6214828), a
    sessão inteira virava um único Event, de 08:00 a 22:27. Ver
    docs/EVENTOS.md."""
    factory = create_session_factory(migrated_engine)
    base = datetime(2026, 5, 9, 8, 0)
    with factory() as session:
        fonte = Source(caminho="/fotos")
        session.add(fonte)
        session.flush()
        manha = list(range(0, 90, 3))         # 30 fotos, uma a cada 3 min
        noite = list(range(780, 870, 3))      # 13h depois, mesmo ritmo
        for i, m in enumerate(manha + noite):
            session.add(_media(
                fonte.id, f"IMG_{i:04d}.jpg", "/fotos/2026/Aniversário da Ana",
                data=base + timedelta(minutes=m),
            ))
        session.commit()

    SuggestionEngine(factory).gerar()

    with factory() as session:
        midias = list(session.scalars(
            select(MediaFile).order_by(MediaFile.nome)
        ))
        assert len(midias) == 60
        ids_manha = {m.event_id for m in midias[:30]}
        ids_noite = {m.event_id for m in midias[30:]}
        assert None not in ids_manha | ids_noite
        assert len(ids_manha) == 1 and len(ids_noite) == 1
        assert ids_manha != ids_noite  # dois Event distintos, não um do dia inteiro

        eventos = list(session.scalars(select(Event)))
        assert len(eventos) == 2
        for evento in eventos:
            assert evento.nome == "Aniversário da Ana"
            # Cada Event cobre só o próprio bloco (~87 min), não o dia inteiro
            # (14h27 de 08:00 a 22:27) — é isso que prova a separação.
            assert (evento.fim - evento.inicio) < timedelta(hours=2)


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
    # Nada nomeia a foto: vai para o ramo de não classificadas, quebrado
    # por ano e mês. Nenhum nome é inventado.
    assert sugestao.destino_sugerido == "Não classificadas/2025/mai.2025"


def test_palavra_chave_curadoria_decide_categoria_sem_pasta(migrated_engine):
    """Pasta técnica sem sinal, mas a foto tem palavra-chave XMP/IPTC
    'Viagem' (D-051, regra 4) — decide a categoria mesmo sem a pasta dizer
    nada, o caso que a cascata antiga não cobria."""
    factory = create_session_factory(migrated_engine)
    base = datetime(2025, 6, 10, 9, 0)
    with factory() as session:
        fonte = Source(caminho="/fotos")
        session.add(fonte)
        session.flush()
        medias = []
        for i in range(3):
            m = _media(
                fonte.id, f"IMG_{i:04d}.jpg", "/fotos/2025_06_10/[Originals]",
                data=base + timedelta(minutes=10 * i),
            )
            session.add(m)
            medias.append(m)
        session.flush()
        session.add(MetadataEntry(
            media_id=medias[0].id, namespace=NAMESPACE_CURADORIA,
            chave="palavra_chave", valor="Viagem",
        ))
        session.commit()

    SuggestionEngine(factory).gerar()
    sugestao, evidencias = _sugestao_de(factory, "IMG_0000.jpg")
    campos = {e.campo: e for e in evidencias}
    assert campos["categoria"].valor == "Viagens"
    assert campos["categoria"].origem == "curadoria"
    assert "palavra-chave 'Viagem'" in campos["categoria"].justificativa


def test_curadoria_nao_sobrepoe_sessao_de_alta_confianca(ambiente):
    """Achado da revisão da Fase A: palavra-chave de curadoria (0.55) não
    pode fragmentar uma sessão já decidida por GPS/geocodificação
    (0.85-0.95) — sem isso, uma foto isolada da mesma viagem sairia com
    categoria diferente das irmãs só por causa de uma tag de álbum
    externo que apenas coincide no tempo."""
    factory, engine = ambiente
    with factory() as session:
        franca_1 = session.scalar(
            select(MediaFile).where(MediaFile.nome == "franca_1.jpg")
        )
        session.add(MetadataEntry(
            media_id=franca_1.id, namespace=NAMESPACE_CURADORIA,
            chave="palavra_chave", valor="Evento",
        ))
        session.commit()

    engine.gerar()

    for nome in ("franca_0.jpg", "franca_1.jpg", "franca_2.jpg"):
        _, evidencias = _sugestao_de(factory, nome)
        campos = {e.campo: e for e in evidencias}
        assert campos["categoria"].valor == "Viagens", (
            f"{nome} deveria seguir a sessão (GPS), não a curadoria"
        )
        assert campos["categoria"].origem != "curadoria"


def test_pasta_vence_palavra_chave_curadoria_divergente(migrated_engine):
    """Pasta explícita ainda manda quando a palavra-chave diverge — o
    sinal único da pasta continua acima de qualquer outro (D-034)."""
    factory = create_session_factory(migrated_engine)
    base = datetime(2025, 6, 10, 9, 0)
    with factory() as session:
        fonte = Source(caminho="/fotos")
        session.add(fonte)
        session.flush()
        m = _media(fonte.id, "IMG_0000.jpg", "/fotos/Família", data=base)
        session.add(m)
        session.flush()
        session.add(MetadataEntry(
            media_id=m.id, namespace=NAMESPACE_CURADORIA,
            chave="palavra_chave", valor="Evento",
        ))
        session.commit()

    SuggestionEngine(factory).gerar()
    sugestao, evidencias = _sugestao_de(factory, "IMG_0000.jpg")
    campos = {e.campo: e for e in evidencias}
    assert campos["categoria"].valor == "Família"
    assert campos["categoria"].origem == "pasta"


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


def test_advisor_llm_promove_sessao_neutra_a_viagem(migrated_engine):
    """A mesma assimetria medida em docs/AVALIACAO_UX.md (seção C.4): o
    advisor sabe dizer 'Viagens', mas só 'Eventos' fazia algo além de
    preencher a categoria — a sessão nunca virava um Trip de verdade, nunca
    aparecia na aba Viagens. Aqui o LLM diz 'Viagens' e um nome de viagem
    (não de evento), e uma Trip precisa nascer, com a mesma origem 'llm'
    que o caminho de Evento já tinha."""
    from fotoorganizer.classification.advisor import AdvisorResult

    class FakeAdvisorDeViagem:
        def __init__(self):
            self.clusters = []

        @property
        def local(self):
            return False

        def classificar(self, cluster):
            self.clusters.append(cluster)
            return AdvisorResult(
                categoria="Viagens", evento="Fim de semana em Búzios",
                justificativa="nomes de pasta e período de 3 dias fora de casa",
            )

    factory = create_session_factory(migrated_engine)
    base = datetime(2025, 6, 6, 9, 0)
    with factory() as session:
        fonte = Source(caminho="/fotos")
        session.add(fonte)
        session.flush()
        for i in range(3):
            session.add(_media(
                fonte.id, f"buzios_{i}.jpg", "/fotos/2025_06",
                data=base + timedelta(hours=6 * i),
            ))
        session.commit()

    advisor = FakeAdvisorDeViagem()
    resultado = SuggestionEngine(factory, advisor=advisor).gerar()
    assert resultado["viagens"] == 1
    assert resultado["eventos"] == 0

    with factory() as session:
        trip = session.scalar(select(Trip))
        assert trip is not None
        assert trip.nome == "Fim de semana em Búzios"
        assert trip.metodo == "llm"
        media = session.scalar(
            select(MediaFile).where(MediaFile.nome == "buzios_0.jpg")
        )
        assert media.trip_id == trip.id

    sugestao, evidencias = _sugestao_de(factory, "buzios_0.jpg")
    viagem = next(e for e in evidencias if e.campo == "viagem")
    assert viagem.origem == "llm"
    assert "LLM (apenas metadados)" in viagem.justificativa
    assert sugestao.destino_sugerido == "Viagens/2025 - Fim de semana em Búzios"


def test_advisor_llm_viagem_sem_nome_usa_pais_dominante(migrated_engine):
    """Sem nome de viagem do LLM (só a categoria), o rótulo cai para o país
    já geocodificado da sessão — nunca para um rótulo vazio. A sessão fica
    curta demais (poucas horas) para a cascata decidir viagem sozinha
    (regra 5 exige dias), mas o país já foi geocodificado antes do
    advisor ser consultado."""
    from fotoorganizer.classification.advisor import AdvisorResult

    class FakeAdvisorSoCategoria:
        @property
        def local(self):
            return False

        def classificar(self, cluster):
            return AdvisorResult(
                categoria="Viagens", evento=None,
                justificativa="GPS num único país, sessão curta",
            )

    factory = create_session_factory(migrated_engine)
    base = datetime(2025, 9, 1, 10, 0)
    with factory() as session:
        fonte = Source(caminho="/fotos")
        session.add(fonte)
        session.flush()
        for i in range(3):
            session.add(_media(
                fonte.id, f"escala_{i}.jpg", "/fotos/Diversos",
                data=base + timedelta(hours=i), gps=(43.95, 4.81),
            ))
        session.commit()

    advisor = FakeAdvisorSoCategoria()
    SuggestionEngine(
        factory, LocationResolver(FakeGeocoder()), advisor=advisor,
    ).gerar()

    with factory() as session:
        trip = session.scalar(select(Trip))
        assert trip is not None
        assert trip.nome == "França"


def test_advisor_nulo_nao_opina():
    from fotoorganizer.classification.advisor import ClusterInfo, NullAdvisor

    cluster = ClusterInfo(
        pastas=("/x",), exemplos_arquivos=("a.jpg",),
        inicio=datetime(2025, 1, 1), fim=datetime(2025, 1, 1), n_fotos=1,
    )
    advisor = NullAdvisor()
    assert advisor.local is True
    assert advisor.classificar(cluster) is None


# -- data e nome no mesmo segmento de pasta -----------------------------
def test_pasta_com_lugar_e_data_nomeia_o_evento_e_confirma_o_ano(
    migrated_engine,
):
    """Caso real: "Visconde de Maua - Abril 2015" sob duas pastas de
    arrumação. O nome vem da folha (não de "Portfolio"), a data vira
    evidência própria e o ano do EXIF continua mandando no destino."""
    factory = create_session_factory(migrated_engine)
    pasta = ("/Volumes/photo/Portfolio/Fotos Organizadas/"
             "Visconde de Maua - Abril 2015")
    with factory() as session:
        fonte = Source(caminho="/Volumes/photo")
        session.add(fonte)
        session.flush()
        for i in range(3):
            session.add(_media(
                fonte.id, f"1W0B328{i}.dng", pasta,
                data=datetime(2015, 4, 18, 14, i),
            ))
        session.commit()

    SuggestionEngine(factory).gerar()
    sugestao, evidencias = _sugestao_de(factory, "1W0B3280.dng")

    assert sugestao.destino_sugerido == "Eventos/2015/Visconde de Maua"

    por_campo = {e.campo: e for e in evidencias}
    assert por_campo["evento"].valor == "Visconde de Maua"
    # A data da pasta é registrada e diz que confere com o EXIF.
    assert por_campo["ano"].valor == "2015"
    assert por_campo["ano"].origem == "pasta"
    assert "Abril 2015" in por_campo["ano"].justificativa
    assert "confere com o EXIF" in por_campo["ano"].justificativa
    # ...mas não entra no cálculo do elo mais fraco: quem deu o ano ao
    # destino foi o EXIF.
    assert "ano" not in {e.campo for e in sugestao.evidencias}


def test_data_da_pasta_que_diverge_do_exif_e_denunciada(migrated_engine):
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        fonte = Source(caminho="/fotos")
        session.add(fonte)
        session.flush()
        session.add(_media(
            fonte.id, "a.jpg", "/fotos/Pantanal Jul.2023",
            data=datetime(2019, 7, 2, 9, 0),
        ))
        session.commit()

    SuggestionEngine(factory).gerar()
    _sug, evidencias = _sugestao_de(factory, "a.jpg")
    ano = next(e for e in evidencias if e.campo == "ano")
    assert "DIVERGE do EXIF (2019)" in ano.justificativa


def test_nao_classificadas_quebram_por_ano_e_mes(migrated_engine):
    """Sem categoria, evento ou lugar, o destino seria a pasta "2025" —
    um balde que não é revisável. Vai para o ramo de não classificadas,
    quebrado por ano e mês no formato do próprio acervo."""
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        fonte = Source(caminho="/fotos")
        session.add(fonte)
        session.flush()
        for i in range(3):
            session.add(_media(
                fonte.id, f"x{i}.jpg", "/fotos/2025_05_24",
                data=datetime(2025, 5, 24, 11, i),
            ))
        session.commit()

    SuggestionEngine(factory).gerar()
    sugestao, _ev = _sugestao_de(factory, "x0.jpg")
    assert sugestao.destino_sugerido == "Não classificadas/2025/mai.2025"


def test_mes_nao_invade_destino_que_ja_tem_nome(migrated_engine):
    """Havendo evento, o nível continua sendo o ano: "Teatro" atravessa o
    ano inteiro e não pode ser fatiado em doze pastas."""
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        fonte = Source(caminho="/fotos")
        session.add(fonte)
        session.flush()
        for i in range(3):
            session.add(_media(
                fonte.id, f"t{i}.jpg", "/fotos/2026/Teatro",
                data=datetime(2026, 6, 2, 20, i),
            ))
        session.commit()

    SuggestionEngine(factory).gerar()
    sugestao, _ev = _sugestao_de(factory, "t0.jpg")
    assert sugestao.destino_sugerido == "Eventos/2026/Teatro"


def test_coordenada_herdada_e_persistida_com_doador_e_delta(migrated_engine):
    """A herança precisa sobreviver ao fim da geração: sem coluna, a foto
    continua contando como "sem coordenada" em toda consulta, e a origem da
    estimativa não é recuperável depois."""
    factory = create_session_factory(migrated_engine)
    base = datetime(2024, 5, 4, 10, 0)
    with factory() as session:
        camera = Source(caminho="/fotos/Camera")
        telefone = Source(caminho="/fotos/iPhone")
        session.add_all([camera, telefone])
        session.flush()
        session.add(_media(camera.id, "cam.jpg", "/fotos/Camera", data=base,
                           make="Canon", model="EOS R5"))
        session.add(_media(telefone.id, "tel.jpg", "/fotos/iPhone",
                           data=base + timedelta(minutes=2),
                           gps=(43.95, 4.8083), make="Apple", model="iPhone 15"))
        session.commit()

    SuggestionEngine(factory, LocationResolver(FakeGeocoder())).gerar()

    with factory() as session:
        cam = session.scalar(select(MediaFile).where(MediaFile.nome == "cam.jpg"))
        tel = session.scalar(select(MediaFile).where(MediaFile.nome == "tel.jpg"))
        # A coordenada lida continua vazia — estimativa não vira medição.
        assert cam.gps_lat is None
        assert cam.gps_lat_estimado == 43.95
        assert cam.gps_estimado_de_id == tel.id
        assert cam.gps_estimado_delta_s == 120
        assert cam.coordenada == (43.95, 4.8083)
        assert cam.coordenada_estimada is True
        # A doadora não herda de ninguém.
        assert tel.gps_lat_estimado is None
        assert tel.coordenada_estimada is False


def test_location_id_resolvido_mesmo_para_sugestao_ja_decidida(ambiente):
    """Fase B' (D-052): `location_id` é resolvido cedo, para TODA foto com
    coordenada — não só para quem ainda vai ganhar sugestão nesta rodada.
    Antes desta fatia, uma foto com sugestão já decidida nunca passava por
    `_evidencias_geo` de novo, e um `location_id` que ficasse None (ex.:
    resolvida antes de o resolver existir) nunca era corrigido."""
    factory, engine = ambiente
    engine.gerar()
    repo = SuggestionRepository(factory)

    sugestao, _ = _sugestao_de(factory, "franca_0.jpg")
    repo.editar_destino(sugestao.id, "Meu/Destino/Especial")
    with factory() as session:
        media = session.scalar(
            select(MediaFile).where(MediaFile.nome == "franca_0.jpg")
        )
        assert media.location_id is not None  # a 1ª geração já resolveu
        media.location_id = None  # simula o gap: nunca foi resolvido
        session.commit()

    engine.gerar()

    with factory() as session:
        media = session.scalar(
            select(MediaFile).where(MediaFile.nome == "franca_0.jpg")
        )
        assert media.location_id is not None
        local = session.get(Location, media.location_id)
        assert local.pais == "França"


def test_estimativa_some_quando_a_foto_ganha_gps_proprio(migrated_engine):
    """Reprocessar um arquivo pode trazer o GPS que faltava. A estimativa
    antiga não pode sobreviver a isso."""
    factory = create_session_factory(migrated_engine)
    base = datetime(2024, 5, 4, 10, 0)
    with factory() as session:
        camera = Source(caminho="/fotos/Camera")
        telefone = Source(caminho="/fotos/iPhone")
        session.add_all([camera, telefone])
        session.flush()
        session.add(_media(camera.id, "cam.jpg", "/fotos/Camera", data=base,
                           make="Canon", model="EOS R5"))
        session.add(_media(telefone.id, "tel.jpg", "/fotos/iPhone",
                           data=base + timedelta(minutes=2),
                           gps=(43.95, 4.8083), make="Apple", model="iPhone 15"))
        session.commit()

    engine = SuggestionEngine(factory, LocationResolver(FakeGeocoder()))
    engine.gerar()
    with factory() as session:
        cam = session.scalar(select(MediaFile).where(MediaFile.nome == "cam.jpg"))
        assert cam.gps_lat_estimado is not None
        cam.gps_lat, cam.gps_lon = 43.96, 4.81   # reprocessado, agora com EXIF
        session.commit()

    engine.gerar()
    with factory() as session:
        cam = session.scalar(select(MediaFile).where(MediaFile.nome == "cam.jpg"))
        assert cam.gps_lat_estimado is None
        assert cam.gps_estimado_de_id is None
        assert cam.coordenada_estimada is False


def test_tz_estimado_de_gps_proprio(ambiente):
    """País vindo de GPS próprio grava tz_estimado direto em MediaFile —
    sem Evidence nova, sem entrada em docs/CONFIANCA.md (D-03)."""
    factory, engine = ambiente
    engine.gerar()

    with factory() as session:
        franca = session.scalar(
            select(MediaFile).where(MediaFile.nome == "franca_0.jpg")
        )
        assert franca.tz_estimado == TZ_POR_PAIS["França"]


def test_tz_estimado_de_pais_herdado(ambiente):
    """País só por herança temporal (sem GPS próprio, D-025) também grava
    tz_estimado — mesmo resultado do GPS próprio."""
    factory, engine = ambiente
    engine.gerar()

    with factory() as session:
        sem_gps = session.scalar(
            select(MediaFile).where(MediaFile.nome == "sem_gps.jpg")
        )
        assert sem_gps.gps_lat is None
        assert sem_gps.tz_estimado == TZ_POR_PAIS["França"]


def test_tz_estimado_none_sem_pais_conhecido(ambiente):
    """Sem nenhum país conhecido, tz_estimado fica None — nunca inventa,
    nunca lança erro (D-04)."""
    factory, engine = ambiente
    engine.gerar()

    with factory() as session:
        misteriosa = session.scalar(
            select(MediaFile).where(MediaFile.nome == "misteriosa.jpg")
        )
        assert misteriosa.tz_estimado is None


def test_tz_estimado_atualiza_ao_regenerar_sugestoes(migrated_engine):
    """Regenerar sugestões não pode deixar um tz_estimado obsoleto de uma
    rodada anterior — mesmo padrão de
    test_estimativa_some_quando_a_foto_ganha_gps_proprio, mas para
    tz_estimado: a foto perde o país que tinha (pasta renomeada) e a
    segunda gerar() precisa refletir isso, não preservar o valor velho."""
    factory = create_session_factory(migrated_engine)
    base = datetime(2024, 5, 4, 10, 0)
    with factory() as session:
        fonte = Source(caminho="/fotos")
        session.add(fonte)
        session.flush()
        session.add(_media(
            fonte.id, "toquio.jpg", "/fotos/Japão/Tóquio", data=base,
        ))
        session.commit()

    engine = SuggestionEngine(factory, LocationResolver(FakeGeocoder()))
    engine.gerar()
    with factory() as session:
        foto = session.scalar(select(MediaFile).where(MediaFile.nome == "toquio.jpg"))
        assert foto.tz_estimado == TZ_POR_PAIS["Japão"]
        foto.pasta = "/fotos/sem_pais_no_nome"
        foto.caminho = "/fotos/sem_pais_no_nome/toquio.jpg"
        session.commit()

    engine.gerar()
    with factory() as session:
        foto = session.scalar(select(MediaFile).where(MediaFile.nome == "toquio.jpg"))
        assert foto.tz_estimado is None


def test_tz_estimado_atualiza_mesmo_com_sugestao_decidida(migrated_engine):
    """CR-01: `_persistir_sugestao` (onde tz_estimado era calculado antes)
    é pulada para mídia com sugestão já decidida — mas tz_estimado precisa
    do MESMO padrão de recálculo incondicional de gps_lat_estimado
    (`_persistir_herancas`), então não pode congelar no valor da última
    rodada em que a sugestão ainda estava pendente."""
    factory = create_session_factory(migrated_engine)
    base = datetime(2024, 5, 4, 10, 0)
    with factory() as session:
        fonte = Source(caminho="/fotos")
        session.add(fonte)
        session.flush()
        session.add(_media(
            fonte.id, "camera.jpg", "/fotos/desorganizadas", data=base,
            gps=(43.95, 4.8083),
        ))
        session.commit()

    engine = SuggestionEngine(factory, LocationResolver(FakeGeocoder()))
    engine.gerar()
    with factory() as session:
        foto = session.scalar(select(MediaFile).where(MediaFile.nome == "camera.jpg"))
        assert foto.tz_estimado == TZ_POR_PAIS["França"]
        sugestao = session.scalar(
            select(Suggestion).where(Suggestion.media_id == foto.id)
        )
        sugestao.status = SuggestionStatus.APROVADA
        # GPS muda para fora da cobertura do FakeGeocoder (deixa de
        # resolver para qualquer país conhecido) — o país efetivo da foto
        # mudou, mesmo com a sugestão da câmera já decidida.
        foto.gps_lat, foto.gps_lon = 10.0, 10.0
        session.commit()

    engine.gerar()
    with factory() as session:
        foto = session.scalar(select(MediaFile).where(MediaFile.nome == "camera.jpg"))
        assert foto.tz_estimado is None
        # A decisão do usuário continua preservada — só o dado técnico
        # auxiliar (D-038) acompanha a mudança.
        sugestao = session.scalar(
            select(Suggestion).where(Suggestion.media_id == foto.id)
        )
        assert sugestao.status == SuggestionStatus.APROVADA


def test_captura_de_tela_sai_do_fluxo_de_viagem(migrated_engine):
    """Captura de tela feita durante a viagem não pertence à pasta da
    viagem. Vai para ramo próprio, por tipo e ano, com a justificativa
    dizendo o que a denunciou."""
    factory = create_session_factory(migrated_engine)
    base = datetime(2024, 5, 4, 10, 0)
    with factory() as session:
        fonte = Source(caminho="/fotos")
        session.add(fonte)
        session.flush()
        for i in range(4):
            session.add(_media(
                fonte.id, f"franca_{i}.jpg", "/fotos/Viagens/2024 - França",
                data=base + timedelta(days=i), gps=(43.95, 4.8083),
                make="Canon", model="EOS R5",
            ))
        # No meio da viagem, uma captura de tela do mapa.
        captura = _media(fonte.id, "Captura de Tela 2024-05-05 às 09.00.00.png",
                         "/fotos/Viagens/2024 - França",
                         data=base + timedelta(days=1))
        captura.extensao = "png"
        captura.largura, captura.altura = 2556, 1179
        session.add(captura)
        session.commit()

    SuggestionEngine(factory, LocationResolver(FakeGeocoder())).gerar()

    sugestao, _ = _sugestao_de(factory, "Captura de Tela 2024-05-05 às 09.00.00.png")
    assert sugestao.destino_sugerido.startswith("Não são fotos/Captura de tela")
    assert "2024" in sugestao.destino_sugerido
    vinculadas = {e.campo: e for e in sugestao.evidencias}
    assert "captura de tela" in vinculadas["tipo"].justificativa.lower() or \
           "resolução de uma tela" in vinculadas["tipo"].justificativa

    # E a foto de verdade da mesma viagem não foi arrastada junto.
    foto, _ = _sugestao_de(factory, "franca_0.jpg")
    assert foto.destino_sugerido.startswith("Viagens")


def test_foto_com_camera_nao_vai_para_o_ramo_de_nao_fotos(migrated_engine):
    """A regra de ouro: na dúvida é foto. Erro aqui derruba a confiança no
    catálogo inteiro."""
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        fonte = Source(caminho="/fotos")
        session.add(fonte)
        session.flush()
        # Nome que parece download, mas com câmera gravada no arquivo.
        session.add(_media(fonte.id, "image (2).jpg", "/fotos/Downloads",
                           data=datetime(2024, 5, 4, 10, 0),
                           make="Nikon", model="Z6"))
        session.commit()

    SuggestionEngine(factory, LocationResolver(FakeGeocoder())).gerar()

    sugestao, _ = _sugestao_de(factory, "image (2).jpg")
    assert not sugestao.destino_sugerido.startswith("Não são fotos")


def test_correcao_do_usuario_sobrevive_a_regeneracao(migrated_engine):
    """`tipo_imagem` é a opinião do detector e é reescrita a cada geração —
    tem de ser, porque um arquivo reprocessado pode ganhar EXIF. Se a
    correção do usuário morasse ali, a próxima passagem a desfaria em
    silêncio."""
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        fonte = Source(caminho="/fotos")
        session.add(fonte)
        session.flush()
        # Nome de captura de tela, mas é uma foto de verdade que o usuário
        # renomeou. O detector vai insistir que é captura.
        session.add(_media(fonte.id, "Screenshot da praia.png", "/fotos",
                           data=datetime(2024, 5, 4, 10, 0)))
        session.commit()

    engine = SuggestionEngine(factory, LocationResolver(FakeGeocoder()))
    engine.gerar()
    with factory() as session:
        media = session.scalar(select(MediaFile))
        assert media.tipo_imagem == "captura"
        assert media.tipo_provisorio is True
        media.tipo_confirmado = "foto"      # o usuário discorda
        session.commit()

    engine.gerar()   # regenera tudo

    with factory() as session:
        media = session.scalar(select(MediaFile))
        # O detector continua achando o que achava — e continua irrelevante.
        assert media.tipo_imagem == "captura"
        assert media.tipo_confirmado == "foto"
        assert media.tipo_efetivo == "foto"
        assert media.tipo_provisorio is False
        sugestao = session.scalar(select(Suggestion))
        assert not sugestao.destino_sugerido.startswith("Não são fotos")


def test_confirmar_como_nao_foto_manda_para_o_ramo_certo(migrated_engine):
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        fonte = Source(caminho="/fotos")
        session.add(fonte)
        session.flush()
        # O detector acha que é foto (tem câmera); o usuário sabe que é lixo.
        session.add(_media(fonte.id, "recibo.jpg", "/fotos",
                           data=datetime(2024, 5, 4, 10, 0),
                           make="Canon", model="EOS R5"))
        session.commit()

    engine = SuggestionEngine(factory, LocationResolver(FakeGeocoder()))
    engine.gerar()
    with factory() as session:
        media = session.scalar(select(MediaFile))
        assert media.tipo_imagem == "foto"
        media.tipo_confirmado = "baixada"
        session.commit()

    engine.gerar()

    with factory() as session:
        sugestao = session.scalar(select(Suggestion))
        assert sugestao.destino_sugerido.startswith("Não são fotos/Baixada")
        vinculadas = {e.campo: e for e in sugestao.evidencias}
        assert vinculadas["tipo"].origem == "usuario"
        assert "por você" in vinculadas["tipo"].justificativa


def test_miniatura_de_cache_doa_gps_mas_nao_vira_sugestao(migrated_engine):
    """A separação que salvou a revisão: 89% do acervo local de um usuário
    real eram miniaturas 540×360 do pacote do Apple Fotos, e cada uma virava
    uma sugestão de destino.

    Apagá-las custaria caro — elas carregam o GPS que o catálogo externo não
    reporta. Então elas doam e ficam de fora (invariante 8, D-024).
    """
    factory = create_session_factory(migrated_engine)
    base = datetime(2024, 5, 4, 10, 0)
    biblioteca = "/Users/x/Pictures/Fotos.photoslibrary/resources/derivatives"
    with factory() as session:
        fonte = Source(caminho="/Users/x/Pictures")
        session.add(fonte)
        session.flush()
        # A foto do usuário, de câmera, sem GPS nenhum.
        session.add(_media(
            fonte.id, "ACM_0001.jpg", "/Users/x/Pictures/2024",
            data=base, make="Canon", model="EOS R6",
        ))
        # A miniatura interna, com GPS, um minuto depois.
        mini = _media(
            fonte.id, "ABC_4_5005_c.jpeg", biblioteca,
            data=base + timedelta(minutes=1), gps=(43.95, 4.8083),
            make="Apple", model="iPhone 15",
        )
        mini.papel = MediaRole.SINAL
        session.add(mini)
        session.commit()

    engine = SuggestionEngine(factory, LocationResolver(FakeGeocoder()))
    resultado = engine.gerar()

    with factory() as session:
        foto = session.scalar(
            select(MediaFile).where(MediaFile.nome == "ACM_0001.jpg")
        )
        miniatura = session.scalar(
            select(MediaFile).where(MediaFile.nome == "ABC_4_5005_c.jpeg")
        )
        # A doação aconteceu: a foto do usuário ganhou lugar estimado.
        assert foto.gps_lat_estimado == 43.95
        assert foto.gps_estimado_de_id == miniatura.id
        # E a miniatura não entrou na fila de decisão de ninguém.
        sugestoes = session.scalars(select(Suggestion)).all()
        assert [s.media_id for s in sugestoes] == [foto.id]
    assert resultado["herancas_gps"] == 1


def test_sugestao_de_quem_deixou_de_ser_acervo_e_descartada(migrated_engine):
    """Rebaixar uma mídia a testemunha tem de levar a sugestão pendente
    dela junto — senão a fila continua pedindo decisão sobre miniatura.

    A decisão já tomada pelo usuário fica: aprovada não se desfaz por
    reclassificação nossa.
    """
    factory = create_session_factory(migrated_engine)
    base = datetime(2024, 5, 4, 10, 0)
    with factory() as session:
        fonte = Source(caminho="/fotos")
        session.add(fonte)
        session.flush()
        for nome in ("mini_pendente.jpg", "mini_aprovada.jpg"):
            session.add(_media(
                fonte.id, nome, "/fotos/Lib.photoslibrary/derivatives",
                data=base, gps=(43.95, 4.8083),
            ))
        session.add(_media(fonte.id, "real.jpg", "/fotos/2024", data=base))
        session.commit()

    engine = SuggestionEngine(factory, LocationResolver(FakeGeocoder()))
    engine.gerar()  # ainda sem papel: as três recebem sugestão

    with factory() as session:
        assert session.scalar(select(func.count(Suggestion.id))) == 3
        aprovada = session.scalar(select(Suggestion).join(MediaFile).where(
            MediaFile.nome == "mini_aprovada.jpg"
        ))
        aprovada.status = SuggestionStatus.APROVADA
        for m in session.scalars(select(MediaFile).where(
            MediaFile.pasta.like("%.photoslibrary%")
        )):
            m.papel = MediaRole.SINAL
        session.commit()

    resultado = engine.gerar()
    assert resultado["descartadas"] == 1

    with factory() as session:
        restantes = {
            nome: status
            for nome, status in session.execute(
                select(MediaFile.nome, Suggestion.status)
                .join(Suggestion, Suggestion.media_id == MediaFile.id)
            )
        }
    assert restantes == {
        "real.jpg": SuggestionStatus.PENDENTE,
        "mini_aprovada.jpg": SuggestionStatus.APROVADA,
    }


def test_heranca_distante_afirma_o_pais_e_cala_a_cidade(migrated_engine):
    """D-025: em três horas se troca de cidade, não de país.

    Antes a janela era uma só e esta foto não herdava nada. Agora ela herda
    o que a distância sustenta — e a justificativa diz o que ficou de fora,
    para o usuário não concluir que a cidade veio junto.
    """
    factory = create_session_factory(migrated_engine)
    base = datetime(2024, 5, 4, 10, 0)
    with factory() as session:
        camera = Source(caminho="/fotos/raw")
        telefone = Source(caminho="/fotos/DCIM")
        session.add_all([camera, telefone])
        session.flush()
        session.add(_media(
            camera.id, "distante.jpg", "/fotos/raw", data=base,
            make="Canon", model="EOS R6",
        ))
        session.add(_media(
            telefone.id, "tel.jpg", "/fotos/DCIM",
            data=base + timedelta(hours=3),
            gps=(43.95, 4.8083), make="Apple", model="iPhone 15",
        ))
        session.commit()

    engine = SuggestionEngine(factory, LocationResolver(FakeGeocoder()))
    engine.gerar()

    _, evidencias = _sugestao_de(factory, "distante.jpg")
    campos = {e.campo for e in evidencias if e.origem == "vizinhanca_temporal"}
    assert "pais" in campos
    assert "cidade" not in campos
    heranca = next(e for e in evidencias if e.origem == "vizinhanca_temporal")
    assert "não a cidade" in heranca.justificativa


def test_heranca_concordante_diz_que_foi_confirmada(migrated_engine):
    """D-074: com doadora dos dois lados perto uma da outra, a cidade
    herdada fica corroborada — e a justificativa precisa dizer isso, não só
    guardar o dado internamente. Sem bônus de score: mesma fórmula de
    sempre, só a frase muda."""
    factory = create_session_factory(migrated_engine)
    base = datetime(2024, 5, 4, 10, 0)
    with factory() as session:
        camera = Source(caminho="/fotos/raw")
        telefone = Source(caminho="/fotos/DCIM")
        session.add_all([camera, telefone])
        session.flush()
        session.add(_media(
            camera.id, "meio.jpg", "/fotos/raw", data=base,
            make="Canon", model="EOS R6",
        ))
        session.add(_media(
            telefone.id, "antes.jpg", "/fotos/DCIM",
            data=base - timedelta(minutes=3),
            gps=(43.9500, 4.8083), make="Apple", model="iPhone 15",
        ))
        session.add(_media(
            telefone.id, "depois.jpg", "/fotos/DCIM",
            data=base + timedelta(minutes=4),
            gps=(43.9520, 4.8083), make="Apple", model="iPhone 15",
        ))
        session.commit()

    engine = SuggestionEngine(factory, LocationResolver(FakeGeocoder()))
    engine.gerar()

    _, evidencias = _sugestao_de(factory, "meio.jpg")
    heranca = next(
        e for e in evidencias
        if e.origem == "vizinhanca_temporal" and e.campo == "cidade"
    )
    assert "confirmada por outra foto" in heranca.justificativa
    assert "herdado de 'antes.jpg'" in heranca.justificativa
    # Sem bônus: o score é o mesmo que uma âncora única a 3 min daria.
    assert heranca.score == round(0.75 * campos_confiaveis(
        timedelta(minutes=3)
    )[-1][1], 3)


# -- D-083: cidade da pasta confirmada no dataset vira lugar --------------

def _acervo(migrated_engine):
    return create_session_factory(migrated_engine)


def test_cidade_da_pasta_confirmada_vira_lugar_sem_coordenada_estimada(migrated_engine):
    """"Amsterdam 2016" sem GPS e sem doadora: a foto ganha um Location de
    fonte "pasta:" com o centroide, evidência de país/cidade com origem
    `pasta` e fuso — mas NADA em `gps_*_estimado`: esses campos alimentam
    o plano de escrita EXIF no original e um ponto com 15 km de dúvida
    não pode ir parar lá."""
    from fotoorganizer.geolocation.cidades import FONTE_PASTA
    from fotoorganizer.models import Evidence, Location

    factory = _acervo(migrated_engine)
    base = datetime(2016, 10, 15, 12, 0)
    with factory() as session:
        fonte = Source(caminho="/fotos")
        session.add(fonte)
        session.flush()
        session.add(_media(
            fonte.id, "canal.jpg", "/fotos/Amsterdam 2016/15 de outubro de 2016",
            data=base,
        ))
        # A subpasta nomeia outro lugar: a cidade da pasta-mãe não vale.
        session.add(_media(
            fonte.id, "quai.jpg",
            "/fotos/Paris 2016/Aquitânia - Quai Salvette, 7 de outubro de 2016",
            data=base - timedelta(days=8),
        ))
        session.commit()

    SuggestionEngine(factory, LocationResolver(FakeGeocoder())).gerar()

    with factory() as session:
        canal = session.scalar(select(MediaFile).where(MediaFile.nome == "canal.jpg"))
        assert canal.coordenada is None and not canal.coordenada_estimada
        assert canal.gps_lat_estimado is None and canal.gps_estimado_de_id is None
        local = session.get(Location, canal.location_id)
        assert local.fonte == FONTE_PASTA
        assert (local.cidade, local.pais) == ("Amsterdam", "Países Baixos")
        assert abs(local.lat - 52.37) < 0.05 and abs(local.lon - 4.89) < 0.05
        assert canal.tz_estimado == "Europe/Amsterdam"
        evidencias = {
            e.campo: e for e in session.scalars(
                select(Evidence).where(Evidence.media_id == canal.id)
            )
        }
        assert evidencias["cidade"].origem == "pasta"
        assert evidencias["cidade"].valor == "Amsterdam"
        assert "confirmada no dataset offline" in evidencias["cidade"].justificativa
        assert evidencias["pais"].valor == "Países Baixos"

        quai = session.scalar(select(MediaFile).where(MediaFile.nome == "quai.jpg"))
        assert quai.coordenada is None and quai.location_id is None


def test_doadora_real_vale_mais_que_a_cidade_da_pasta(migrated_engine):
    """Rodada 1 sem doadora: lugar pela pasta. Rodada 2 com uma foto de
    outra fonte a minutos de distância: a herança decide, e o Location de
    pasta não sobrevive em quem ganhou doadora."""
    from fotoorganizer.geolocation.cidades import FONTE_PASTA
    from fotoorganizer.models import Location

    factory = _acervo(migrated_engine)
    base = datetime(2016, 10, 15, 12, 0)
    with factory() as session:
        pasta, celular = Source(caminho="/fotos"), Source(caminho="/iphone")
        session.add_all([pasta, celular])
        session.flush()
        session.add(_media(
            pasta.id, "canal.jpg", "/fotos/Amsterdam 2016", data=base,
            make="Canon", model="R6",
        ))
        session.commit()
    engine = SuggestionEngine(factory, LocationResolver(FakeGeocoder()))
    engine.gerar()
    with factory() as session:
        canal = session.scalar(select(MediaFile).where(MediaFile.nome == "canal.jpg"))
        assert session.get(Location, canal.location_id).fonte == FONTE_PASTA
        celular = session.scalar(select(Source).where(Source.caminho == "/iphone"))
        session.add(_media(
            celular.id, "IMG_1.jpg", "/iphone", data=base + timedelta(minutes=3),
            gps=(43.95, 4.8083), make="Apple", model="iPhone",
        ))
        session.commit()

    engine.gerar()

    with factory() as session:
        canal = session.scalar(select(MediaFile).where(MediaFile.nome == "canal.jpg"))
        assert canal.gps_estimado_de_id is not None       # herdou da doadora
        assert abs(canal.gps_lat_estimado - 43.95) < 0.01  # não é Amsterdam
        assert session.get(Location, canal.location_id).fonte == "fake"


def test_pasta_que_deixa_de_confirmar_cidade_perde_o_lugar(migrated_engine):
    """Renomeada a pasta para um lugar que o dataset não conhece, a rodada
    seguinte tira o `location_id` — sem isso a foto ficaria apontando para
    Amsterdam sem coordenada nenhuma (achado da revisão)."""
    factory = _acervo(migrated_engine)
    base = datetime(2016, 10, 15, 12, 0)
    with factory() as session:
        fonte = Source(caminho="/fotos")
        session.add(fonte)
        session.flush()
        session.add(_media(fonte.id, "canal.jpg", "/fotos/Amsterdam 2016", data=base))
        session.commit()
    engine = SuggestionEngine(factory, LocationResolver(FakeGeocoder()))
    engine.gerar()
    with factory() as session:
        canal = session.scalar(select(MediaFile).where(MediaFile.nome == "canal.jpg"))
        assert canal.location_id is not None
        canal.pasta = "/fotos/Aquitânia - Quai Salvette"
        session.commit()

    engine.gerar()

    with factory() as session:
        canal = session.scalar(select(MediaFile).where(MediaFile.nome == "canal.jpg"))
        assert canal.location_id is None


def test_homonimas_no_mesmo_pais_ganham_locations_diferentes(migrated_engine):
    """"Trindade - GO" e "Trindade - PE" são duas cidades: a chave de cache
    leva o estado, senão a segunda pasta reusava o Location da primeira."""
    from fotoorganizer.models import Location

    factory = _acervo(migrated_engine)
    base = datetime(2019, 6, 1, 12, 0)
    with factory() as session:
        fonte = Source(caminho="/fotos")
        session.add(fonte)
        session.flush()
        session.add(_media(fonte.id, "go.jpg", "/fotos/Trindade - GO", data=base))
        session.add(_media(fonte.id, "pe.jpg", "/fotos/Trindade - PE",
                           data=base + timedelta(days=40)))
        session.commit()

    SuggestionEngine(factory, LocationResolver(FakeGeocoder())).gerar()

    with factory() as session:
        go = session.scalar(select(MediaFile).where(MediaFile.nome == "go.jpg"))
        pe = session.scalar(select(MediaFile).where(MediaFile.nome == "pe.jpg"))
        assert go.location_id != pe.location_id
        assert session.get(Location, go.location_id).regiao == "Goiás"
        assert session.get(Location, pe.location_id).regiao == "Pernambuco"


# -- D-084: uma base de tempo só ------------------------------------------

def test_foto_so_mtime_entra_na_linha_do_tempo_em_hora_de_parede(migrated_engine):
    """mtime é UTC no catálogo; data_capturada é hora de parede. Antes, uma
    foto só-mtime ficava 3 h deslocada da doadora (no Brasil) e perdia a
    cidade (janela de 10 min). Agora o mtime chega em hora de parede."""
    from zoneinfo import ZoneInfo

    from fotoorganizer.models import Evidence

    factory = create_session_factory(migrated_engine)
    parede = datetime(2016, 10, 15, 10, 0)              # doadora, hora de parede
    utc = datetime(2016, 10, 15, 13, 5)                  # 10:05 em São Paulo
    with factory() as session:
        camera, celular = Source(caminho="/canon"), Source(caminho="/iphone")
        session.add_all([camera, celular])
        session.flush()
        session.add(_media(camera.id, "sem_exif.jpg", "/canon", mtime=utc,
                           make="Canon", model="R6"))
        session.add(_media(celular.id, "IMG_1.jpg", "/iphone", data=parede,
                           gps=(43.95, 4.8083), make="Apple", model="iPhone"))
        session.commit()

    SuggestionEngine(
        factory, LocationResolver(FakeGeocoder()),
        tz_padrao=ZoneInfo("America/Sao_Paulo"),
    ).gerar()

    with factory() as session:
        foto = session.scalar(select(MediaFile).where(MediaFile.nome == "sem_exif.jpg"))
        assert foto.gps_estimado_de_id is not None
        assert foto.gps_estimado_delta_s == 5 * 60             # não 3 h 05
        cidade = session.scalar(select(Evidence).where(
            Evidence.media_id == foto.id, Evidence.campo == "cidade"
        ))
        assert cidade is not None and cidade.origem == "vizinhanca_temporal"
        assert "hora de uma delas é a do arquivo" in cidade.justificativa
        data = session.scalar(select(Evidence).where(
            Evidence.media_id == foto.id, Evidence.campo == "data"
        ))
        assert data.origem == "fs" and data.valor.startswith("2016-10-15T10:05")
        assert "fuso desta máquina" in data.justificativa


def test_data_no_nome_manda_na_linha_do_tempo_nao_o_mtime(migrated_engine):
    """`IMG-20150420-WA0001.jpg` copiado em 2024: a evidência de data já
    dizia 2015, mas a sessão ia parar em 2024 junto com a cópia. Agora as
    duas contam a mesma história — e a data só de dia não mede minutos
    até ninguém (fica fora da correlação)."""
    from fotoorganizer.models import Evidence

    factory = create_session_factory(migrated_engine)
    copia = datetime(2024, 1, 1, 12, 0)
    with factory() as session:
        fonte, celular = Source(caminho="/fotos"), Source(caminho="/iphone")
        session.add_all([fonte, celular])
        session.flush()
        session.add(_media(fonte.id, "IMG-20150420-WA0001.jpg", "/fotos/zap", mtime=copia))
        session.add(_media(fonte.id, "IMG-20150421-WA0002.jpg", "/fotos/zap",
                           mtime=copia + timedelta(minutes=1)))
        # Foto de 2024 com GPS a minutos da CÓPIA: antes, as do WhatsApp
        # herdavam dela; agora estão em 2015 e não herdam de ninguém.
        session.add(_media(celular.id, "IMG_9.jpg", "/iphone", data=copia + timedelta(minutes=2),
                           gps=(43.95, 4.8083), make="Apple", model="iPhone"))
        session.commit()

    engine = SuggestionEngine(factory, LocationResolver(FakeGeocoder()))
    engine.gerar()

    with factory() as session:
        zap = list(session.scalars(select(MediaFile).where(MediaFile.pasta == "/fotos/zap")))
        assert all(m.gps_estimado_de_id is None for m in zap)
        anos = {session.scalar(select(Evidence).where(
            Evidence.media_id == m.id, Evidence.campo == "data")).valor[:4] for m in zap}
        assert anos == {"2015"}
        midias = list(session.scalars(select(MediaFile)))
        sessoes, sessao_da_media = engine._montar_sessoes(session, midias, {})
        de_2015 = {id(sessao_da_media[m.id]) for m in zap}
        # A foto de 2024 pode nem formar sessão sozinha; o que importa é
        # que as do WhatsApp não estão com ela.
        de_2024 = sessao_da_media.get(next(m.id for m in midias if m.nome == "IMG_9.jpg"))
        assert len(de_2015) == 1 and (de_2024 is None or id(de_2024) not in de_2015)
        assert sessao_da_media[zap[0].id].draft.inicio.year == 2015
