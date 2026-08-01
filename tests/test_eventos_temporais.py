"""Divisão de uma sessão em acontecimentos.

Os cenários são rotulados: cada um diz quantos blocos o dono reconheceria.
Mexer em PISO, TETO ou FATOR sem passar aqui é ajuste às cegas.
"""

from datetime import datetime, timedelta

import pytest

from fotoorganizer.grouping.eventos_temporais import (
    Momento,
    dividir_em_eventos,
    dividir_sessao,
)

BASE = datetime(2026, 5, 9, 8, 0)


def _fotos(offsets_min, lat=None, lon=None, inicio=BASE):
    """Fotos nos minutos dados, opcionalmente todas no mesmo lugar."""
    return [
        Momento(i, inicio + timedelta(minutes=m), lat, lon)
        for i, m in enumerate(offsets_min)
    ]


def _tamanhos(blocos):
    return [len(b) for b in blocos]


# -- o caso que motivou tudo -------------------------------------------------
def test_aniversario_de_manha_e_show_a_noite_sao_dois():
    """O caso do dono: mesmo dia, mesma cidade, mesma câmera. Nenhum
    metadado além do ritmo separa — e o ritmo separa."""
    manha = list(range(0, 90, 3))          # 30 fotos, uma a cada 3 min
    noite = list(range(780, 870, 3))       # 13h depois, mesmo ritmo
    blocos = dividir_em_eventos(_fotos(manha + noite))
    assert len(blocos) == 2
    assert _tamanhos(blocos) == [30, 30]


def test_viagem_continua_nao_e_partida_na_meia_noite():
    """O falso positivo que uma régua por dia de calendário produz: 8 dos 28
    dias alcançáveis do acervo real acusaram "dois blocos" que eram a mesma
    noite da viagem a Dubai."""
    # 22:00 às 02:00, disparando a cada 4 min, atravessando a meia-noite.
    noite = list(range(0, 240, 4))
    blocos = dividir_em_eventos(_fotos(noite, inicio=datetime(2025, 11, 10, 22, 0)))
    assert len(blocos) == 1


def test_pausa_de_almoco_nao_corta():
    """Uma hora parada no meio de um dia de turismo é pausa, não fronteira."""
    antes = list(range(0, 120, 10))
    depois = list(range(180, 300, 10))     # 70 min de intervalo
    assert len(dividir_em_eventos(_fotos(antes + depois))) == 1


def test_respiro_de_rajada_nao_vira_evento():
    """Ensaio dispara a cada poucos segundos; 40 min de intervalo é enorme
    em relação ao ritmo e ainda assim é a mesma sessão de fotos. É o que o
    PISO protege — sem ele, a razão pura cortaria aqui."""
    rajada = [i / 6 for i in range(0, 120)]      # a cada 10 s
    pausa = [40 + i / 6 for i in range(0, 120)]  # 40 min depois
    blocos = dividir_em_eventos([
        Momento(i, BASE + timedelta(minutes=m)) for i, m in enumerate(rajada + pausa)
    ])
    assert len(blocos) == 1


def test_ritmo_lento_ainda_tem_fronteira_pelo_teto():
    """Um dia de fotos esparsas — uma a cada 2 h — não pode esconder a
    fronteira seguinte. É o que o TETO protege."""
    esparsas = list(range(0, 480, 120))          # a cada 2 h
    depois = [480 + 600 + i for i in range(0, 30, 5)]   # 10 h de intervalo
    assert len(dividir_em_eventos(_fotos(esparsas + depois))) == 2


# -- deslocamento ------------------------------------------------------------
def test_mudar_de_lugar_corta_mesmo_com_as_fotos_coladas():
    """Deslocamento encerra o que estava acontecendo. Duas fotos a 5 min de
    distância e 20 km não são o mesmo acontecimento."""
    aqui = [Momento(i, BASE + timedelta(minutes=i), -22.95, -43.18)
            for i in range(5)]
    la = [Momento(10 + i, BASE + timedelta(minutes=5 + i), -22.80, -43.35)
          for i in range(5)]
    assert len(dividir_em_eventos(aqui + la)) == 2


def test_andar_pelo_bairro_nao_corta():
    """3 km separa bairros; não pode separar salões do mesmo casamento."""
    salao = [Momento(i, BASE + timedelta(minutes=i * 5), -22.9500, -43.1800)
             for i in range(6)]
    jardim = [Momento(10 + i, BASE + timedelta(minutes=35 + i * 5),
                      -22.9510, -43.1810) for i in range(6)]
    assert len(dividir_em_eventos(salao + jardim)) == 1


def test_coordenada_de_um_lado_so_nao_decide():
    """Só a 5D Mark IV grava GPS neste acervo (D-029): a maior parte das
    fotos não tem coordenada, e a régua não pode depender dela."""
    com = [Momento(0, BASE, -22.95, -43.18)]
    sem = [Momento(1, BASE + timedelta(minutes=5))]
    assert len(dividir_em_eventos(com + sem)) == 1


# -- bordas ------------------------------------------------------------------
@pytest.mark.parametrize("entrada,esperado", [([], []), ])
def test_vazio(entrada, esperado):
    assert dividir_em_eventos(entrada) == esperado


def test_uma_foto_e_um_bloco():
    assert dividir_em_eventos(_fotos([0])) == [[0]]


def test_ordem_de_entrada_nao_importa():
    embaralhado = _fotos([100, 0, 50, 780, 800])
    assert dividir_em_eventos(embaralhado) == dividir_em_eventos(
        sorted(embaralhado, key=lambda m: m.quando)
    )


def test_nenhum_bloco_sai_vazio():
    for blocos in (dividir_em_eventos(_fotos([0, 700, 1400, 2100]))):
        assert blocos


# -- viagem não se divide ----------------------------------------------------
def test_viagem_continua_sendo_uma_pasta_so():
    """O Pantanal, três dias, virou quatro blocos na primeira versão — uma
    saída por manhã e outra por tarde. Isso desfaz o commit 9670765: a viagem
    Tailândia–Vietnã já esteve partida em três destinos porque só 106 das
    2.405 fotos tinham GPS, e a forma da pasta acabava dependendo de qual
    foto por acaso gravou coordenada."""
    # Três dias de saídas, com noites entre elas.
    dia1 = list(range(0, 240, 10))
    dia2 = list(range(1440, 1680, 10))
    dia3 = list(range(2880, 3120, 10))
    fotos = _fotos(dia1 + dia2 + dia3)

    assert len(dividir_em_eventos(fotos)) == 3      # navegar: três saídas
    assert len(dividir_sessao(fotos, e_viagem=True)) == 1   # destino: uma pasta
    # E mesmo sem o rótulo de viagem: três dias atravessam noites, então é
    # estadia. O destino não depende de o classificador ter acertado o rótulo.
    assert len(dividir_sessao(fotos, e_viagem=False)) == 1


def test_viagem_sem_fotos_nao_inventa_bloco():
    assert dividir_sessao([], e_viagem=True) == []


def test_sessao_que_atravessa_noites_e_um_destino_so():
    """O Pantanal: 97 fotos de 18 a 20 de julho, rotuladas "evento" porque a
    duração de 1 dia e 23 h não alcança o limiar de viagem de 3 dias. A régua
    de ritmo partia em quatro saídas — e a forma da pasta não pode depender
    de uma fresta do classificador."""
    dia1 = list(range(0, 240, 10))
    dia2 = list(range(1440, 1680, 10))
    dia3 = list(range(2880, 3120, 10))
    fotos = _fotos(dia1 + dia2 + dia3)
    assert len(dividir_sessao(fotos, e_viagem=False)) == 1


def test_festa_que_vira_a_noite_ainda_e_uma_festa():
    """22h às 2h atravessa a meia-noite e cabe em 20 h corridas: continua
    sendo um acontecimento, e a régua de ritmo ainda vale dentro dele."""
    fotos = _fotos(list(range(0, 240, 5)), inicio=datetime(2026, 5, 9, 22, 0))
    assert len(dividir_sessao(fotos, e_viagem=False)) == 1
