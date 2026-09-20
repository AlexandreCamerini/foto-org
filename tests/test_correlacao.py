"""Correlação temporal entre fontes: deriva de relógio e herança de GPS."""

from datetime import datetime, timedelta

import pytest

from fotoorganizer.grouping import (
    RAIO_PISO_M,
    RAIO_TETO_M,
    VELOCIDADE_PLAUSIVEL_MS,
    FotoRef,
    estimar_offsets,
    frase_do_raio,
    herdar_gps,
    raio_incerteza,
)
from fotoorganizer.grouping.correlacao import campos_confiaveis

CANON = ("Canon", "EOS R6")
IPHONE = ("Apple", "iPhone 15 Pro")
T0 = datetime(2025, 11, 1, 10, 0, 0)


def _canon(mid, segundos, **kw):
    return FotoRef(media_id=mid, source_id=1, camera=CANON,
                   quando=T0 + timedelta(seconds=segundos), **kw)


def _iphone(mid, segundos, lat=25.2, lon=55.3, **kw):
    return FotoRef(media_id=mid, source_id=2, camera=IPHONE,
                   quando=T0 + timedelta(seconds=segundos),
                   lat=lat, lon=lon, **kw)


def _de(herancas, media_id):
    """A herança de uma foto específica. Toda foto sem GPS tenta herdar, e
    o retorno traz todas — filtrar deixa a asserção falar de uma só."""
    return next((h for h in herancas if h.media_id == media_id), None)


# -- herança de GPS ----------------------------------------------------------
def test_heranca_do_doador_mais_proximo():
    fotos = [
        _canon(1, 0),                       # sem GPS
        _iphone(2, -42),                    # doadora 42s antes
        # 3h depois: longe demais NO TEMPO para opinar sobre cidade/região
        # (D-074) — só existe para provar que o mais próximo vence, não
        # para testar concordância.
        _iphone(3, 10800, lat=25.9, lon=55.9),
    ]
    h = _de(herdar_gps(fotos), 1)
    assert h.doador_id == 2
    assert h.lat == 25.2
    assert h.delta == timedelta(seconds=42)
    # 42s sustenta até a cidade, com confiança cheia (janela curta).
    assert h.granularidade == "cidade"
    assert h.fator_de("cidade") == 1.0
    assert h.concordancia == ()   # outro lado longe demais no tempo p/ testar


def test_fora_da_janela_da_cidade_ainda_herda_o_pais():
    """11 minutos não dizem em que cidade você estava; dizem em que país.

    Antes de D-025 a janela era uma só, de 10 min, e esta foto não herdava
    nada — o limite da cidade jogava fora a informação de país, que é segura
    por muito mais tempo.
    """
    h = _de(herdar_gps([_canon(1, 0), _iphone(2, 11 * 60)]), 1)
    assert h is not None
    assert h.granularidade == "regiao"
    assert h.fator_de("cidade") is None
    assert h.fator_de("pais") is not None


def test_janela_de_pais_vai_alem_da_janela_de_regiao():
    """13 h não dizem em que região você estava; ainda dizem em que país
    (D-085, estende D-025: país passa de 12 h para 48 h)."""
    h = _de(herdar_gps([_canon(1, 0), _iphone(2, 13 * 3600)]), 1)
    assert h is not None
    assert h.granularidade == "pais"
    assert h.fator_de("regiao") is None
    assert h.fator_de("pais") is not None


def test_47h_ainda_herda_pais_49h_nao_herda_mais_nada():
    h = _de(herdar_gps([_canon(1, 0), _iphone(2, 47 * 3600)]), 1)
    assert h is not None and h.fator_de("pais") is not None
    assert _de(herdar_gps([_canon(1, 0), _iphone(2, 49 * 3600)]), 1) is None


def test_longe_demais_para_qualquer_campo():
    assert _de(herdar_gps([_canon(1, 0), _iphone(2, 49 * 3600)]), 1) is None


def test_confianca_decai_com_delta():
    fotos = [_canon(1, 0), _iphone(2, 6 * 60)]  # 6 min: meio da rampa
    h = _de(herdar_gps(fotos), 1)
    assert 0.7 < h.fator_de("cidade") < 0.9
    # O país mal sente 6 minutos dentro da janela de 48 h (D-085).
    assert h.fator_de("pais") > 0.99


def test_mesma_camera_na_mesma_fonte_nao_doa():
    # Duas fotos da MESMA câmera/fonte: uma com GPS não doa pra outra
    # (não é outra origem de informação).
    fotos = [
        _canon(1, 0),
        FotoRef(media_id=2, source_id=1, camera=CANON,
                quando=T0 + timedelta(seconds=30), lat=1.0, lon=2.0),
    ]
    assert herdar_gps(fotos) == []


def test_doadora_de_outra_fonte_mesmo_sem_camera():
    # Takeout sem make/model ainda doa (fonte diferente).
    fotos = [
        _canon(1, 0),
        FotoRef(media_id=2, source_id=3, camera=(None, None),
                quando=T0 + timedelta(seconds=60), lat=9.0, lon=8.0),
    ]
    (h,) = herdar_gps(fotos)
    assert h.doador_id == 2


# -- regra 1: câmera com receptor GPS confirmado (D-029/D-086) ---------------
_5D_IV = ("Canon", "Canon EOS 5D Mark IV")


def test_mesma_camera_doa_quando_tem_receptor_confirmado():
    # Mesma câmera/fonte, mas a 5D Mark IV tem receptor GPS embutido
    # confirmado (D-029) — a exceção da regra 1 se aplica só a ela.
    fotos = [
        FotoRef(media_id=1, source_id=1, camera=_5D_IV, quando=T0),
        FotoRef(media_id=2, source_id=1, camera=_5D_IV,
                quando=T0 + timedelta(minutes=30), lat=1.0, lon=2.0),
    ]
    (h,) = herdar_gps(fotos)
    assert h.doador_id == 2
    assert h.mesma_camera is True


def test_mesma_camera_confiavel_nao_muda_camera_sem_receptor_confirmado():
    # A exceção não vira "toda Canon doa pra si mesma" — só a câmera medida.
    outra_canon = ("Canon", "Canon EOS R6m2")
    fotos = [
        FotoRef(media_id=1, source_id=1, camera=outra_canon, quando=T0),
        FotoRef(media_id=2, source_id=1, camera=outra_canon,
                quando=T0 + timedelta(minutes=30), lat=1.0, lon=2.0),
    ]
    assert herdar_gps(fotos) == []


def test_doacao_same_camera_cai_para_confianca_baixa():
    # Δt curto (2min, dentro da janela curta) normalmente dá fator 1.0; a
    # penalidade de mecanismo (D-086) derruba mesmo esse caso melhor para
    # baixo do piso de média (score 0.75*fator < 0.5 — ver
    # classification/confidence.py). `Heranca.campos` é capado em país
    # (achado da 3ª rodada de revisão: sem isso, `granularidade` mentia
    # "cidade" mesmo quando só país é oferecido).
    fotos = [
        FotoRef(media_id=1, source_id=1, camera=_5D_IV, quando=T0),
        FotoRef(media_id=2, source_id=1, camera=_5D_IV,
                quando=T0 + timedelta(minutes=2), lat=1.0, lon=2.0),
    ]
    (h,) = herdar_gps(fotos)
    assert h.granularidade == "pais"
    assert h.fator_de("cidade") is None
    assert h.fator_de("regiao") is None
    assert h.fator_de("pais") == 0.6  # 1.0 (janela curta) × 0.6 (mecanismo)


def test_doacao_de_outra_fonte_nao_leva_a_penalidade_de_mesma_camera():
    # A penalidade só se aplica à doação same-câmera; a mesma câmera
    # recebendo de OUTRA fonte segue com a confiança normal.
    fotos = [
        FotoRef(media_id=1, source_id=1, camera=_5D_IV, quando=T0),
        FotoRef(media_id=2, source_id=2, camera=_5D_IV,
                quando=T0 + timedelta(minutes=2), lat=1.0, lon=2.0),
    ]
    (h,) = herdar_gps(fotos)
    assert h.mesma_camera is False
    assert h.fator_de("cidade") == 1.0


def test_cross_source_vence_mesma_camera_mesmo_mais_longe():
    # Doadora same-câmera a 2min (mais perto) E doadora de outra fonte a
    # 5min (mais longe, mas medida) — a de outra fonte tem que vencer:
    # mecanismo sem amostra é fallback, nunca desloca uma doadora válida.
    fotos = [
        FotoRef(media_id=1, source_id=1, camera=_5D_IV, quando=T0),
        FotoRef(media_id=2, source_id=1, camera=_5D_IV,
                quando=T0 + timedelta(minutes=2), lat=1.0, lon=2.0),
        FotoRef(media_id=3, source_id=2, camera=IPHONE,
                quando=T0 + timedelta(minutes=5), lat=9.0, lon=9.0),
    ]
    (h,) = herdar_gps(fotos)
    assert h.doador_id == 3
    assert h.mesma_camera is False
    # Fator normal da rampa a 5min (sem a penalidade de mecanismo).
    assert h.fator_de("cidade") == pytest.approx(0.85, abs=0.005)


def test_cross_source_vence_mesma_camera_em_lados_opostos():
    # Mesmo problema do teste acima, mas com as duas doadoras em lados
    # OPOSTOS do tempo (same-câmera antes, cross-source depois) — achado
    # da segunda rodada de revisão: preferir cross-source só DENTRO do
    # mesmo lado não bastava, porque a escolha final comparava os dois
    # lados só por Δt cru. Repro real: media 98028 perdia uma oferta de
    # região que tinha antes desta fatia.
    fotos = [
        FotoRef(media_id=2, source_id=1, camera=_5D_IV,
                quando=T0 - timedelta(minutes=2), lat=1.0, lon=2.0),
        FotoRef(media_id=1, source_id=1, camera=_5D_IV, quando=T0),
        FotoRef(media_id=3, source_id=2, camera=IPHONE,
                quando=T0 + timedelta(minutes=5), lat=9.0, lon=9.0),
    ]
    (h,) = herdar_gps(fotos)
    assert h.doador_id == 3
    assert h.mesma_camera is False


def test_desempate_vale_entre_lados_opostos_nao_so_dentro_do_mesmo_lado():
    # Achado da 2ª rodada de revisão sobre D-087: reverter só o desempate
    # CROSS-LADO (voltar a decidir por Δt cru entre os dois lados) deixava
    # a suíte verde — faltava um teste cobrindo exatamente essa linha. É
    # a forma geométrica exata de D-032: doadora de catálogo (não
    # confiável) 5 min ANTES, doadora de pasta (confiável) 5 min DEPOIS —
    # empatadas em Δt, mas em lados opostos da órfã.
    fotos = [
        FotoRef(media_id=1, source_id=1, camera=(None, None), quando=T0),
        FotoRef(media_id=2, source_id=2, camera=(None, None),
                quando=T0 - timedelta(minutes=5), lat=1.0, lon=2.0,
                gps_direto_do_arquivo=False),
        FotoRef(media_id=3, source_id=3, camera=("Canon", "EOS R6"),
                quando=T0 + timedelta(minutes=5), lat=9.0, lon=9.0,
                gps_direto_do_arquivo=True),
    ]
    (h,) = herdar_gps(fotos)
    assert h.doador_id == 3   # pasta vence mesmo estando do outro lado


def test_mesma_camera_so_entra_sem_doadora_de_outra_origem_no_lado():
    # Mesmo cenário, mas sem a doadora de outra fonte: aí o fallback vale.
    fotos = [
        FotoRef(media_id=1, source_id=1, camera=_5D_IV, quando=T0),
        FotoRef(media_id=2, source_id=1, camera=_5D_IV,
                quando=T0 + timedelta(minutes=2), lat=1.0, lon=2.0),
    ]
    (h,) = herdar_gps(fotos)
    assert h.doador_id == 2
    assert h.mesma_camera is True


def test_testemunha_same_camera_nao_concede_confirmada():
    # Achado da 3ª rodada de revisão: doadora cross-source (medida) de um
    # lado, testemunha same-câmera (sem amostra) do outro lado, as duas
    # geometricamente próximas — a testemunha NÃO pode conceder
    # "confirmada" a uma herança medida. A corroboração de D-074 foi
    # calibrada para doadora de outra origem, não para mecanismo.
    fotos = [
        FotoRef(media_id=1, source_id=1, camera=_5D_IV, quando=T0),
        FotoRef(media_id=2, source_id=2, camera=IPHONE,
                quando=T0 - timedelta(minutes=3),
                lat=25.2000, lon=55.3000),
        FotoRef(media_id=3, source_id=1, camera=_5D_IV,
                quando=T0 + timedelta(minutes=4),
                lat=25.2020, lon=55.3000),   # perto — concordaria, se testado
    ]
    (h,) = herdar_gps(fotos)
    assert h.doador_id == 2          # cross-source vence, como sempre
    assert h.mesma_camera is False
    assert h.concordancia == ()      # testemunha same-câmera não conta
    assert h.doador_concordante_id is None


def test_campos_confiaveis_mesma_camera_penaliza_todos_os_campos():
    # Comparado com tolerância (não `round(f*0.6,3)` sobre o fator já
    # arredondado — a dupla rolagem de arredondamento diverge do valor
    # real em boa parte da rampa, dando falso positivo de invariante).
    for minutos in (2, 6, 30, 90, 300, 1000, 2000):
        delta = timedelta(minutes=minutos)
        normal = dict(campos_confiaveis(delta))
        mesma_cam = dict(campos_confiaveis(delta, mesma_camera=True))
        assert set(normal) == set(mesma_cam)
        for campo, fator in normal.items():
            assert mesma_cam[campo] == pytest.approx(fator * 0.6, abs=0.002)


# -- deriva de relógio --------------------------------------------------------
def _ancoras_camera_3h_atrasada():
    """Mesma foto em 2 fontes: câmera marca 3h a menos que a referência."""
    fotos = []
    for i in range(3):
        fotos.append(FotoRef(
            media_id=10 + i, source_id=1, camera=CANON,
            quando=T0 + timedelta(minutes=i), hash_perceptual=f"ph{i}",
        ))
        fotos.append(FotoRef(
            media_id=20 + i, source_id=2, camera=(None, None),
            quando=T0 + timedelta(hours=3, minutes=i, seconds=5),
            lat=25.2, lon=55.3, hash_perceptual=f"ph{i}",
        ))
    return fotos


def test_offset_estimado_pelas_ancoras():
    offsets = estimar_offsets(_ancoras_camera_3h_atrasada())
    assert CANON in offsets
    assert abs(offsets[CANON] - timedelta(hours=3, seconds=5)) \
        < timedelta(seconds=1)


def test_offset_corrige_a_heranca():
    fotos = _ancoras_camera_3h_atrasada()
    # Foto nova da Canon sem cópia no Takeout: às 10:30 no relógio da
    # câmera = 13:30 reais; doadora do iPhone às 13:31 real.
    fotos.append(_canon(1, 30 * 60))
    fotos.append(FotoRef(
        media_id=2, source_id=2, camera=(None, None),
        quando=T0 + timedelta(hours=3, minutes=31), lat=13.75, lon=100.5,
    ))
    offsets = estimar_offsets(fotos)
    herancas = {h.media_id: h for h in herdar_gps(fotos, offsets)}
    assert 1 in herancas
    assert herancas[1].lat == 13.75
    # A cidade só sobrevive por causa da correção: sem ela, as 3h de deriva
    # jogam a foto para fora da janela de cidade e sobra o país (D-025).
    assert herancas[1].granularidade == "cidade"
    sem_offset = {h.media_id: h for h in herdar_gps(fotos)}
    assert sem_offset[1].fator_de("cidade") is None


def test_ancoras_dispersas_sao_descartadas():
    fotos = []
    deltas = [0, 50 * 60, 200 * 60]  # desvios incoerentes entre si
    for i, d in enumerate(deltas):
        fotos.append(FotoRef(
            media_id=10 + i, source_id=1, camera=CANON,
            quando=T0 + timedelta(minutes=i), hash_rapido=f"x{i}",
        ))
        fotos.append(FotoRef(
            media_id=20 + i, source_id=2, camera=(None, None),
            quando=T0 + timedelta(minutes=i, seconds=d),
            lat=1.0, lon=1.0, hash_rapido=f"x{i}",
        ))
    assert estimar_offsets(fotos) == {}


def test_ancora_unica_nao_basta():
    fotos = _ancoras_camera_3h_atrasada()[:2]  # só 1 par
    assert estimar_offsets(fotos) == {}


def test_procura_alem_dos_dois_vizinhos_imediatos():
    """Os vizinhos mais próximos COM GPS são da mesma origem da foto.

    Só doador de outra origem acrescenta informação, e a versão anterior
    olhava apenas os dois vizinhos imediatos: quando os dois eram da mesma
    origem, ela desistia sem nunca alcançar o terceiro. Num acervo real isso
    barrou 27.117 candidatos — a biblioteca do Apple Fotos é uma fonte só,
    e uma referência sem GPS fica cercada de referências com GPS.
    """
    fotos = [
        _canon(1, 0),                                  # quem precisa herdar
        _canon(2, -5, lat=1.0, lon=1.0),               # tem GPS, MESMA origem
        _canon(3, 5, lat=2.0, lon=2.0),                # idem, do outro lado
        _iphone(4, 30, lat=25.2, lon=55.3),            # a única que serve
    ]
    h = _de(herdar_gps(fotos), 1)
    assert h.doador_id == 4
    assert (h.lat, h.lon) == (25.2, 55.3)
    assert h.delta == timedelta(seconds=30)


def test_a_busca_para_na_borda_da_janela():
    """Varrer além da janela maior seria trabalho jogado fora — nenhum campo
    sobrevive a essa distância (janela de país, a maior: 48 h, D-085)."""
    fotos = [_canon(1, 0)]
    # Irmãs com GPS da MESMA origem cercando a foto, para forçar a varredura.
    fotos += [_canon(10 + i, 3600 * i, lat=1.0, lon=1.0) for i in range(1, 49)]
    fotos.append(_iphone(99, 49 * 3600))   # doadora válida, mas a 49 h
    assert _de(herdar_gps(fotos), 1) is None


def test_o_mais_proximo_vence_mesmo_vindo_do_outro_lado():
    fotos = [
        _canon(1, 0),
        _canon(2, -20),
        _iphone(3, -100, lat=10.0, lon=10.0),   # atrás, mais longe
        _iphone(4, 40, lat=20.0, lon=20.0),     # à frente, mais perto
    ]
    h = _de(herdar_gps(fotos), 1)
    assert h.doador_id == 4 and h.lat == 20.0


# -- desempate em Δt igual (D-032: doadora suspeita, catálogo externo) -------
def test_desempate_prefere_gps_direto_do_arquivo():
    """Repro do caso real de D-032: duas doadoras no MESMO instante (Δt=0),
    uma de catálogo externo (coordenada pode ter sido atribuída no app, não
    medida) e outra de pasta (EXIF do próprio arquivo). A de pasta é
    colocada DEPOIS na lista de propósito — sem o desempate, a ordem
    incidental da consulta decidiria; com ele, pasta sempre vence."""
    fotos = [
        FotoRef(media_id=1, source_id=1, camera=(None, None), quando=T0),
        FotoRef(media_id=2, source_id=2, camera=(None, None), quando=T0,
                lat=-22.9657, lon=-43.1892, gps_direto_do_arquivo=False),
        FotoRef(media_id=3, source_id=3, camera=("Canon", "EOS R6"),
                quando=T0, lat=-22.3301, lon=-44.6185,
                gps_direto_do_arquivo=True),
    ]
    (h,) = herdar_gps(fotos)
    assert h.doador_id == 3
    assert (h.lat, h.lon) == (-22.3301, -44.6185)


def test_desempate_so_atua_quando_ha_desacordo_real():
    """Sem desempate necessário (só uma candidata, ou candidatas de mesmo
    tipo de fonte), o comportamento é o de sempre — o mais próximo vence,
    sem preferência artificial por `gps_direto_do_arquivo`."""
    fotos = [
        _canon(1, 0),
        _iphone(2, 5, lat=1.0, lon=1.0),   # só uma candidata neste lado
    ]
    h = _de(herdar_gps(fotos), 1)
    assert h.doador_id == 2   # continua herdando normalmente


def test_desempate_nao_muda_quando_as_duas_ja_concordam():
    """Duas doadoras no mesmo instante que JÁ concordam geograficamente —
    o desempate não tem o que resolver (não é o caso de D-032); qualquer
    uma serve, e o resultado é determinístico pela mesma regra (primeira
    com `gps_direto_do_arquivo`, se houver)."""
    fotos = [
        FotoRef(media_id=1, source_id=1, camera=(None, None), quando=T0),
        FotoRef(media_id=2, source_id=2, camera=(None, None), quando=T0,
                lat=25.2000, lon=55.3000, gps_direto_do_arquivo=False),
        FotoRef(media_id=3, source_id=3, camera=("Canon", "EOS R6"),
                quando=T0, lat=25.2001, lon=55.3000,
                gps_direto_do_arquivo=True),
    ]
    (h,) = herdar_gps(fotos)
    assert h.doador_id == 3   # a de pasta ainda é a escolhida, por desenho


def test_desempate_prefere_hora_confiavel_sobre_fonte_confiavel():
    """Achado da 1ª rodada de revisão: a versão inicial do desempate
    olhava só `gps_direto_do_arquivo` e podia trocar uma doadora com hora
    de EXIF por uma de pasta com hora de MTIME — pior troca que a que a
    fatia existe para evitar, porque `hora_incerta` penaliza TODOS os
    campos da herança, não só a origem do GPS. Hora confiável tem que
    vencer fonte confiável quando os dois estão em jogo.

    Coordenadas sintéticas de propósito (não as de D-032/Penedo): no
    caso real as duas candidatas têm hora igualmente confiável e é
    `gps_direto_do_arquivo` quem decide (ver teste de ponta a ponta em
    test_suggestion_engine.py) — usar coordenadas reais aqui sugeriria
    que este é o resultado do caso real, quando é só a demonstração
    isolada do critério de hora. A 2ª rodada de revisão notou que, em
    desacordo geográfico genuíno com hora em conflito, a fatia prefere
    a doadora de hora confiável mesmo que fique geograficamente errada
    (0 ocorrências no catálogo real — ver D-087, "Limitação conhecida")."""
    fotos = [
        FotoRef(media_id=1, source_id=1, camera=(None, None), quando=T0),
        FotoRef(media_id=2, source_id=2, camera=(None, None), quando=T0,
                lat=1.0, lon=2.0, gps_direto_do_arquivo=False),
        FotoRef(media_id=3, source_id=3, camera=("Canon", "EOS R6"),
                quando=T0, lat=9.0, lon=9.0,
                gps_direto_do_arquivo=True, hora_do_arquivo=True),
    ]
    (h,) = herdar_gps(fotos)
    assert h.doador_id == 2          # hora confiável vence, mesmo sendo catálogo
    assert h.hora_incerta is False   # nada de penalidade de hora incerta aqui


def test_desempate_ignora_hora_da_doadora_quando_a_orfa_ja_e_incerta():
    """Achado da 2ª rodada de revisão: se a ÓRFÃ já tem hora incerta,
    `hora_incerta` final é `True` de qualquer jeito (`foto.hora_do_arquivo
    or doador.hora_do_arquivo`) — priorizar a hora da doadora não muda
    esse resultado, só rebaixaria `gps_direto_do_arquivo` de graça.
    Confiança de fonte volta a decidir.

    Fixture invertida de propósito (achado da 3ª rodada de revisão: a
    primeira versão deste teste não discriminava — a doadora de pasta já
    vencia nos dois critérios, então passava com a chave antiga também).
    Aqui é a de CATÁLOGO que tem hora confiável e a de PASTA que não —
    só a chave nova (que ignora a hora da doadora quando a órfã já está
    perdida) escolhe a de pasta; a antiga escolheria a de catálogo só
    por causa da hora dela, mesmo sem ganho nenhum em `hora_incerta`."""
    fotos = [
        FotoRef(media_id=1, source_id=1, camera=(None, None), quando=T0,
                hora_do_arquivo=True),
        FotoRef(media_id=2, source_id=2, camera=(None, None), quando=T0,
                lat=1.0, lon=2.0, gps_direto_do_arquivo=False,
                hora_do_arquivo=False),
        FotoRef(media_id=3, source_id=3, camera=("Canon", "EOS R6"),
                quando=T0, lat=9.0, lon=9.0, gps_direto_do_arquivo=True,
                hora_do_arquivo=True),
    ]
    (h,) = herdar_gps(fotos)
    assert h.doador_id == 3          # fonte confiável decide, hora já era perdida
    assert h.hora_incerta is True    # a órfã já garantia isso
    assert h.hora_incerta is True    # a órfã já garantia isso, com ou sem a doadora


# -- duas âncoras: concordância e discordância (D-074) -----------------------
def test_duas_ancoras_concordantes_confirmam_sem_inflar_score():
    """Doadora dos dois lados, coordenadas próximas: os círculos de
    incerteza se sobrepõem — a granularidade fica corroborada, mas o fator
    de confiança continua sendo o de sempre (mesmo Δt, sem bônus inventado).
    O ganho é reportar QUE houve concordância, não inflar o score.
    """
    fotos = [
        _canon(1, 0),
        _iphone(2, -180, lat=25.2000, lon=55.3000),   # antes, 3 min
        _iphone(3, 240, lat=25.2020, lon=55.3000),    # depois, 4 min — perto
    ]
    h = _de(herdar_gps(fotos), 1)
    assert h.doador_id == 2                      # o mais próximo continua vencendo
    assert h.delta == timedelta(seconds=180)
    assert set(h.concordancia) == {"cidade", "regiao"}
    assert h.doador_concordante_id == 3
    assert "pais" not in h.concordancia           # país nunca ganha bônus (D-074)
    # Sem bônus de fator: o score é idêntico ao de uma âncora única no mesmo Δt.
    assert h.campos == campos_confiaveis(timedelta(seconds=180))
    # O raio já é o do lado mais próximo — mais apertado que o do lado que
    # perdeu, sem precisar de fórmula geométrica nova (ver Heranca.raio_m).
    assert h.raio_m == raio_incerteza(timedelta(seconds=180))
    assert h.raio_m < raio_incerteza(timedelta(seconds=240))


def test_duas_ancoras_discordantes_nao_herdam_a_granularidade_em_disputa():
    """Doadoras dos dois lados, mas longe uma da outra: os círculos de
    incerteza não se tocam. Não é 'fica com a mais próxima mesmo assim' — é
    sinal de trânsito, e nenhuma das duas fica confiável para cidade/região.
    País sobrevive porque nunca passa por este teste (D-074)."""
    fotos = [
        _canon(1, 0),
        _iphone(2, -180, lat=25.2, lon=55.3),   # antes, 3 min
        _iphone(3, 240, lat=25.9, lon=55.9),    # depois, 4 min — longe (~100 km)
    ]
    h = _de(herdar_gps(fotos), 1)
    assert h.doador_id == 2                       # continua sendo o mais próximo
    assert h.fator_de("cidade") is None
    assert h.fator_de("regiao") is None
    assert h.fator_de("pais") is not None
    assert h.concordancia == ()


def test_lado_distante_demais_no_tempo_nao_opina_sobre_o_campo_mais_fino():
    """O lado fora da janela de um campo simplesmente não opina sobre ele:
    cidade sobrevive sem teste (o outro lado está longe demais NO TEMPO
    para valer como segunda opinião); só região, que o Δt do lado distante
    ainda alcança, é de fato confrontada — e cai."""
    fotos = [
        _canon(1, 0),
        _iphone(2, -180, lat=25.2, lon=55.3),      # antes, 3 min: dentro da cidade
        _iphone(3, 3000, lat=27.0, lon=57.0),      # depois, 50 min: só região, longe
    ]
    h = _de(herdar_gps(fotos), 1)
    assert h.fator_de("cidade") is not None        # não testada (outro fora da janela)
    assert "cidade" not in h.concordancia
    assert h.fator_de("regiao") is None             # testada e discordante
    assert h.fator_de("pais") is not None


def test_pais_nunca_ganha_bonus_de_concordancia():
    """Duas doadoras a centenas de km uma da outra são obviamente do mesmo
    país — mas `raio_incerteza` é calibrado para deslocamento de PESSOA
    (teto 50 km), não para o tamanho de um país. Testar concordância de
    país com esse raio quebraria o caso óbvio; por isso país nunca entra
    no teste (D-074), a distância real não importa."""
    fotos = [
        _canon(1, 0),
        _iphone(2, -5 * 3600, lat=25.2, lon=55.3),   # antes, 5 h
        _iphone(3, 6 * 3600, lat=28.0, lon=58.0),    # depois, 6 h — ~380 km
    ]
    h = _de(herdar_gps(fotos), 1)
    assert h.fator_de("cidade") is None      # Δt já não sustenta cidade nem sozinho
    assert h.fator_de("regiao") is None
    assert h.fator_de("pais") is not None
    assert h.concordancia == ()
    assert h.fator_de("pais") == campos_confiaveis(timedelta(hours=5))[0][1]


def test_ancora_unica_sem_concordancia_por_padrao():
    """Sem doadora do outro lado, `concordancia` fica vazia — o
    comportamento de sempre, sem regressão."""
    h = _de(herdar_gps([_canon(1, 0), _iphone(2, -42)]), 1)
    assert h.concordancia == ()
    assert h.doador_concordante_id is None


def test_hora_incerta_em_qualquer_lado_desativa_o_teste_de_concordancia():
    """Achado da revisão por sub-agente: a primeira versão só desligava o
    teste geométrico quando a hora incerta estava no lado DESCARTADO —
    deixava passar foto ou doador escolhido com hora incerta, produzindo
    uma justificativa que diria "pode ser coincidência" e "confirmada" na
    mesma frase (`classification/engine.py`). Hora incerta em QUALQUER um
    dos três lados (foto, doador escolhido, doador do outro lado) precisa
    desligar o teste — mesmo com coordenadas idênticas dos dois lados."""
    perto_antes = dict(mid=2, segundos=-180, lat=25.2000, lon=55.3000)
    perto_depois = dict(mid=3, segundos=240, lat=25.2020, lon=55.3000)

    # Hora incerta na FOTO que herda.
    h = _de(herdar_gps([
        _canon(1, 0, hora_do_arquivo=True),
        _iphone(**perto_antes), _iphone(**perto_depois),
    ]), 1)
    assert h.concordancia == ()

    # Hora incerta no doador ESCOLHIDO (o mais próximo, id 2).
    h2 = _de(herdar_gps([
        _canon(1, 0),
        _iphone(**{**perto_antes, "hora_do_arquivo": True}),
        _iphone(**perto_depois),
    ]), 1)
    assert h2.concordancia == ()

    # Hora incerta no OUTRO lado (o descartado, id 3) — já coberto pela
    # implementação original, reafirmado aqui junto dos outros dois casos.
    h3 = _de(herdar_gps([
        _canon(1, 0),
        _iphone(**perto_antes),
        _iphone(**{**perto_depois, "hora_do_arquivo": True}),
    ]), 1)
    assert h3.concordancia == ()


def test_hora_vinda_do_arquivo_vale_menos():
    """`mtime` costuma ser a hora da cópia, não a do disparo: a vizinhança
    pode ser coincidência de quando os arquivos foram parar no disco."""
    certa = _de(herdar_gps([_canon(1, 0), _iphone(2, 30)]), 1)
    incerta = _de(herdar_gps(
        [_canon(1, 0, hora_do_arquivo=True), _iphone(2, 30)]
    ), 1)

    assert certa.hora_incerta is False
    assert incerta.hora_incerta is True
    assert incerta.fator_de("cidade") < certa.fator_de("cidade")
    # A herança continua acontecendo — vale menos, não vale zero.
    assert incerta.doador_id == 2

    # Basta um dos dois lados ser incerto.
    pelo_doador = _de(herdar_gps(
        [_canon(1, 0), _iphone(2, 30, hora_do_arquivo=True)]
    ), 1)
    assert pelo_doador.hora_incerta is True


# -- raio de incerteza (docs/LOCAL_ESTIMADO.md) -------------------------------
def test_raio_nunca_vira_ponto():
    """Δt zero não é certeza: a coordenada da doadora tem o erro do receptor.

    Um raio zero desenharia a estimativa igual a uma medição — exatamente a
    mentira que o círculo existe para desfazer.
    """
    assert raio_incerteza(timedelta(0)) == RAIO_PISO_M
    assert raio_incerteza(timedelta(seconds=1)) == RAIO_PISO_M


def test_raio_cresce_com_a_velocidade_plausivel():
    v = VELOCIDADE_PLAUSIVEL_MS
    assert raio_incerteza(timedelta(minutes=10)) == 600 * v
    assert raio_incerteza(timedelta(hours=1)) == 3600 * v


def test_raio_para_de_crescer_no_teto():
    """A distância à doadora satura no acervo medido; o raio satura junto.

    Sem teto, 12 h de crescimento linear já dariam 259 km — um círculo
    que cobre tudo e não informa nada. O teto não depende da largura da
    janela de país (48 h, D-085): é função direta de Δt, e já satura bem
    antes de qualquer janela de campo.
    """
    assert raio_incerteza(timedelta(hours=12)) == RAIO_TETO_M
    assert raio_incerteza(timedelta(hours=20)) == RAIO_TETO_M
    assert RAIO_TETO_M < 12 * 3600 * VELOCIDADE_PLAUSIVEL_MS


def test_raio_ignora_o_sinal_do_delta():
    """Doadora antes ou depois erra igual — `herdar_gps` já entrega |Δt|,
    mas a função pura não pode devolver raio negativo se receber."""
    assert raio_incerteza(timedelta(minutes=-7)) == raio_incerteza(
        timedelta(minutes=7)
    )


def test_raio_nunca_encolhe_com_o_tempo():
    minutos = [0, 1, 2, 5, 10, 30, 60, 120, 360, 720]
    raios = [raio_incerteza(timedelta(minutes=m)) for m in minutos]
    assert raios == sorted(raios)
    assert raios[0] == RAIO_PISO_M and raios[-1] == RAIO_TETO_M


def test_raio_por_granularidade_bate_com_a_escala_do_campo():
    """D-025 em metros: a cidade cabe em quilômetros, a região em dezenas.

    Se estes números saírem da escala do nome do campo, o círculo passou a
    dizer uma coisa e a justificativa outra.
    """
    assert raio_incerteza(timedelta(minutes=10)) == 3_600      # cidade
    assert raio_incerteza(timedelta(hours=2)) == 43_200        # região
    assert raio_incerteza(timedelta(hours=12)) == 50_000       # país (teto)


def test_heranca_carrega_o_proprio_raio():
    h = _de(herdar_gps([_canon(1, 0), _iphone(2, 5 * 60)]), 1)
    assert h.delta == timedelta(minutes=5)
    assert h.raio_m == raio_incerteza(timedelta(minutes=5))
    # 5 min de câmera para telefone: raio de 1,8 km, escala de bairro.
    assert h.raio_m == 1_800


# -- a frase que explica o círculo -------------------------------------------
def test_frase_do_raio_cita_a_doadora_o_tempo_e_o_tamanho():
    """A resposta ao clique no círculo, pronta no Python.

    Se a UI tivesse de montá-la, precisaria da velocidade, do piso e do teto
    em TypeScript — e no dia da recalibração as constantes divergiriam sem
    ninguém perceber (docs/LOCAL_ESTIMADO.md).
    """
    frase = frase_do_raio(timedelta(minutes=12), "IMG_9100.jpg")
    assert "IMG_9100.jpg" in frase
    assert "12 min" in frase
    assert "4,3 km" in frase
    assert "22 km/h" in frase   # a velocidade, derivada da constante em m/s


def test_frase_no_piso_fala_do_receptor_e_nao_de_deslocamento():
    """A Δt zero o círculo não é 'até onde ela andou' — é o erro do GPS de
    quem emprestou. Dizer 'a 0 s de distância, isso dá 15 m de dúvida' seria
    explicar o tamanho pelo motivo errado."""
    frase = frase_do_raio(timedelta(0), "IMG_9100.jpg")
    assert "15 m" in frase
    assert "receptor" in frase
    assert "km/h" not in frase


def test_frase_no_teto_diz_que_o_raio_parou_de_crescer():
    """No teto a velocidade deixa de explicar o tamanho — o platô medido
    explica (D-032). A frase precisa mudar junto com o regime da fórmula."""
    frase = frase_do_raio(timedelta(hours=11), "IMG_9100.jpg")
    assert "50 km" in frase
    assert "para de crescer" in frase
    assert "11 h" in frase


def test_frase_sem_nome_da_doadora_nao_deixa_buraco():
    """Doadora fora de alcance ou apagada do catálogo não pode virar
    'herdado de None' na tela."""
    frase = frase_do_raio(timedelta(minutes=12))
    assert "None" not in frase
    assert "de outra foto" in frase


def test_frase_acompanha_o_raio_quando_a_constante_mudar():
    """Amarra a frase à função, não a um número escrito à mão: mudar
    VELOCIDADE_PLAUSIVEL_MS tem de mudar as duas juntas."""
    for minutos in (3, 12, 45, 200):
        delta = timedelta(minutes=minutos)
        raio = raio_incerteza(delta)
        alvo = (f"{round(raio)} m" if raio < 1000
                else f"{raio / 1000:.1f}".rstrip("0").rstrip(".")
                .replace(".", ",") + " km")
        assert alvo in frase_do_raio(delta, "x.jpg"), (minutos, raio)
