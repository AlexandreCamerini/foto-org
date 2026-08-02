"""Álbum de catálogo externo dando nome ao que o agrupamento já detectou.

Três níveis, do puro ao ponta a ponta: a escolha entre álbuns concorrentes
(`escolher_album`), o desempate pasta × álbum na cascata
(`classificar_sessao`) e a ligação real `MetadataEntry` → `Trip.nome` no
motor. A regra documentada está em `docs/AGRUPAMENTO.md`, seção 2c.
"""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import select

from fotoorganizer.classification import SuggestionEngine
from fotoorganizer.classification.confidence import SCORES_REFERENCIA
from fotoorganizer.database import create_session_factory
from fotoorganizer.geolocation import GeoResult, LocationResolver
from fotoorganizer.grouping.albuns import escolher_album
from fotoorganizer.grouping.classifier import (
    ORIGEM_ALBUM,
    DadosSessao,
    classificar_sessao,
)
from fotoorganizer.models import (
    Evidence,
    MediaFile,
    MetadataEntry,
    Source,
    Trip,
)


# -- 1. qual álbum, entre os que cobrem o período -------------------------
def test_o_aninhado_especifico_vence_a_prateleira_mais_frequente():
    """O caso de D-030, com os números do acervo real: "Férias" cobre mais
    fotos e diz menos. Sem o rebaixamento de prateleira, a viagem a
    Portugal se chamaria "Férias"."""
    escolhido = escolher_album({
        "Férias": 4352,
        "Portugal e Italia com as Meninas": 3729,
        "Family": 607,
    })
    assert escolhido == ("Portugal e Italia com as Meninas", 3729)


def test_o_album_do_acontecimento_inteiro_vence_o_aninhado_dentro_dele():
    assert escolher_album({
        "Dubai, Thai & Viet": 2019,
        "Nosso Casamento": 107,
    }) == ("Dubai, Thai & Viet", 2019)


def test_camera_e_app_nao_nomeiam_nem_quando_sao_maioria():
    """No acervo real a câmera tem 4.887 fotos e o mensageiro 1.450."""
    assert escolher_album(
        {"Canon EOS 5D Mark IV": 4887, "WhatsApp": 1450, "Jalapão": 947},
        cameras=frozenset({"canon eos 5d mark iv"}),
    ) == ("Jalapão", 947)


def test_punhado_de_fotos_nao_nomeia_o_conjunto():
    assert escolher_album({"Aiuruoca e Tiradentes": 94, "Tiradentes": 2}) == (
        "Aiuruoca e Tiradentes", 94
    )


def test_empate_de_contagem_e_deterministico():
    """"Empolga 2025" e "Empolga as 9 - 2025" têm 159 fotos cada no acervo.
    Sem desempate estável o rótulo mudaria a cada regeneração."""
    contagens = {"Empolga 2025": 159, "Empolga as 9 - 2025": 159}
    primeira = escolher_album(contagens)
    assert primeira == ("Empolga", 159)
    assert escolher_album(dict(reversed(list(contagens.items())))) == primeira


def test_a_data_sai_do_nome_como_ja_sai_da_pasta():
    assert escolher_album({"Peru - Julho de 2026": 1306})[0] == "Peru"


def test_album_que_e_so_data_nao_nomeia():
    assert escolher_album({"2019": 500}) is None


def test_sem_candidato_aproveitavel_devolve_nada():
    assert escolher_album({"WhatsApp": 900, "Instagram": 300}) is None


# -- 2. desempate pasta × álbum na cascata --------------------------------
def _sessao(pastas, *, dias=0, horas=0, pais=None, dist=None, albuns=()):
    return DadosSessao(
        pastas=tuple(pastas),
        duracao=timedelta(days=dias, hours=horas),
        pais_dominante=pais,
        dist_mediana_casa_km=dist,
        periodo_curto="Viagem de 02-11 a 11-11",
        albuns=tuple(albuns),
        fonte_dos_albuns="Apple Fotos",
    )


def test_pasta_informativa_vence_album():
    """"Quizomba" está escrito na pasta; o álbum não passa por cima."""
    decisao = classificar_sessao(_sessao(
        ["/fotos/2026/Quizomba"], horas=4,
        albuns=[("Jalapão", 947)],
    ))
    assert decisao.tipo == "evento"
    assert decisao.rotulo == "Quizomba"
    assert decisao.origem_do_rotulo == "pasta"


def test_pais_lido_da_pasta_tambem_vence_album():
    decisao = classificar_sessao(_sessao(
        ["/fotos/França/Provence"], dias=5,
        albuns=[("Jalapão", 947)],
    ))
    assert decisao.rotulo == "França"
    assert decisao.origem_do_rotulo == "pasta"


def test_pasta_tecnica_cede_para_album():
    """Pasta de data não nomeia nada; a sessão é viagem pelo deslocamento e
    hoje se chamaria "Brasil". O álbum dá o nome que o dono escreveu."""
    decisao = classificar_sessao(_sessao(
        ["/fotos/2021_11_02/[Originals]"], dias=9, pais="Brasil", dist=1100.0,
        albuns=[("Jalapão", 947), ("WhatsApp", 30)],
    ))
    assert decisao.tipo == "viagem"
    assert decisao.rotulo == "Jalapão"
    assert decisao.origem == "gps"            # o TIPO continua vindo do GPS
    assert decisao.origem_do_rotulo == ORIGEM_ALBUM
    assert "Jalapão" in decisao.justificativa
    assert "Apple Fotos" in decisao.justificativa
    assert "947 fotos" in decisao.justificativa


def test_periodo_sem_nome_nenhum_cede_para_album():
    decisao = classificar_sessao(_sessao(
        ["/fotos/DCIM"], dias=9, pais=None, dist=1100.0,
        albuns=[("Jalapão", 947)],
    ))
    assert decisao.rotulo == "Jalapão"


def test_sem_pasta_e_sem_album_aproveitavel_fica_com_o_fallback_de_hoje():
    """Nada é inventado: o rótulo continua sendo o que a cascata já dava."""
    decisao = classificar_sessao(_sessao(
        ["/fotos/DCIM"], dias=9, pais="Brasil", dist=1100.0,
        albuns=[("WhatsApp", 300), ("Canon EOS R6m2", 200)],
    ))
    assert decisao.rotulo == "Brasil"
    assert decisao.origem_do_rotulo == "gps"


def test_sessao_neutra_continua_sem_nome_mesmo_com_album():
    """D-030: álbum nomeia, não detecta. Uma sessão que a cascata não
    classificou não vira evento por existir um álbum no período."""
    decisao = classificar_sessao(_sessao(
        ["/fotos/2025_05_24"], horas=3,
        albuns=[("Joanna 4 Anos", 236)],
    ))
    assert decisao.tipo == "neutra"
    assert decisao.rotulo is None


# -- 3. ponta a ponta: MetadataEntry → Trip.nome --------------------------
class _FakeGeocoder:
    def resolve(self, lat, lon):
        return GeoResult("Brasil", "Tocantins", "Mateiros", "fake")


def _media(source_id, nome, pasta, data, gps=None, papel=None):
    media = MediaFile(
        source_id=source_id, caminho=f"{pasta}/{nome}", pasta=pasta,
        nome=nome, extensao="jpg", tamanho=100, data_capturada=data,
        gps_lat=gps[0] if gps else None, gps_lon=gps[1] if gps else None,
    )
    if papel is not None:
        media.papel = papel
        media.arquivo_ausente = True
    return media


@pytest.fixture()
def acervo_com_album(migrated_engine):
    """Uma viagem de 9 dias longe de casa, em pasta de data, ao lado de
    referências do Apple Fotos que carregam a nomeação — a forma exata do
    acervo real, onde 100% das marcações de álbum estão em registro sem
    arquivo local (D-028)."""
    from fotoorganizer.models import MediaRole

    factory = create_session_factory(migrated_engine)
    base = datetime(2021, 11, 2, 13, 0)
    with factory() as session:
        fonte = Source(caminho="/fotos")
        biblioteca = Source(caminho="/Photos.photoslibrary", tipo="APPLE_PHOTOS")
        session.add_all([fonte, biblioteca])
        session.flush()
        # Casa: 30 fotos no Rio, para a detecção de casa funcionar.
        for i in range(30):
            session.add(_media(
                fonte.id, f"casa_{i:02d}.jpg", "/fotos/2021_01_01",
                datetime(2021, 1, 1, 9, 0) + timedelta(minutes=i),
                gps=(-22.97, -43.19),
            ))
        # A viagem, em pasta que não nomeia nada.
        for i in range(12):
            session.add(_media(
                fonte.id, f"IMG_{i:04d}.jpg", "/fotos/2021_11_02/[Originals]",
                base + timedelta(hours=18 * i), gps=(-10.3, -46.5),
            ))
        # As referências do Apple Fotos, com o álbum.
        for i in range(6):
            ref = _media(
                biblioteca.id, f"ref_{i}.heic", "",
                base + timedelta(hours=30 * i), papel=MediaRole.SINAL,
            )
            session.add(ref)
            session.flush()
            for album in ("Jalapão", "WhatsApp"):
                session.add(MetadataEntry(
                    media_id=ref.id, namespace="apple", chave="album",
                    valor=album,
                ))
        session.commit()
    return factory


def test_album_do_apple_fotos_nomeia_a_viagem(acervo_com_album):
    """Sem a ligação, esta viagem se chamaria "Brasil" — o país que o
    geocoder devolve. O nome que o dono escreveu está no álbum."""
    SuggestionEngine(
        acervo_com_album, LocationResolver(_FakeGeocoder())
    ).gerar()
    with acervo_com_album() as session:
        nomes = [t.nome for t in session.scalars(select(Trip))]
    assert "Jalapão" in nomes


def test_a_evidencia_diz_de_onde_o_nome_veio(acervo_com_album):
    SuggestionEngine(
        acervo_com_album, LocationResolver(_FakeGeocoder())
    ).gerar()
    with acervo_com_album() as session:
        evidencias = [
            e for e in session.scalars(select(Evidence))
            if e.campo == "viagem"
        ]
    assert evidencias
    ev = evidencias[0]
    assert ev.valor == "Jalapão"
    assert ev.origem == ORIGEM_ALBUM
    assert "álbum 'Jalapão'" in ev.justificativa
    assert "Apple Fotos" in ev.justificativa
    # Abaixo de `pasta` (0.60): o vínculo é de contemporaneidade.
    assert ev.score == SCORES_REFERENCIA[ORIGEM_ALBUM] < SCORES_REFERENCIA["pasta"]
