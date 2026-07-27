from datetime import datetime, timedelta

from fotoorganizer.grouping import agrupar_viagens, dividir_por_transicao_casa


def _dias(n: int) -> datetime:
    return datetime(2024, 5, 1) + timedelta(days=n)


def test_lacuna_separa_viagens():
    itens = [
        (1, _dias(0)), (2, _dias(1)), (3, _dias(2)),   # viagem 1
        (4, _dias(10)), (5, _dias(11)),                # viagem 2 (gap 8d)
        (6, _dias(30)),                                # viagem 3 (gap 19d)
    ]
    viagens = agrupar_viagens(itens)
    assert [v.media_ids for v in viagens] == [[1, 2, 3], [4, 5], [6]]


def test_viagem_longa_nao_quebra_por_dia():
    # 14 dias seguidos de fotos = UMA viagem (não uma por dia do calendário).
    itens = [(i, _dias(i)) for i in range(14)]
    viagens = agrupar_viagens(itens)
    assert len(viagens) == 1
    assert viagens[0].n_fotos == 14
    assert viagens[0].periodo_legivel() == "01/05/2024 – 14/05/2024"


def test_ordem_de_entrada_nao_importa():
    itens = [(2, _dias(1)), (1, _dias(0)), (3, _dias(20))]
    viagens = agrupar_viagens(itens)
    assert [v.media_ids for v in viagens] == [[1, 2], [3]]


def test_dia_unico_tem_periodo_simples():
    viagens = agrupar_viagens([(1, _dias(0)), (2, _dias(0))])
    assert viagens[0].periodo_legivel() == "01/05/2024"


# -- divisão por transição casa↔fora ----------------------------------------
FORA, CASA, SEM_GPS = False, True, None


def test_viagens_coladas_separadas_ao_passar_por_casa():
    # [viagem A][2 dias em casa][viagem B] — gap temporal nunca > 3 dias.
    itens = [
        (1, _dias(0), FORA), (2, _dias(1), FORA),
        (3, _dias(2), CASA), (4, _dias(3), CASA),
        (5, _dias(4), FORA), (6, _dias(5), FORA),
    ]
    segmentos = dividir_por_transicao_casa(itens)
    assert [[m for m, _ in seg] for seg in segmentos] == [[1, 2], [3, 4], [5, 6]]


def test_foto_isolada_em_casa_nao_corta_viagem_real():
    # Um único frame "em casa" no meio (GPS errado/escala) não confirma.
    itens = [
        (1, _dias(0), FORA), (2, _dias(1), FORA),
        (3, _dias(2), CASA),
        (4, _dias(3), FORA), (5, _dias(4), FORA),
    ]
    segmentos = dividir_por_transicao_casa(itens)
    assert len(segmentos) == 1


def test_fotos_sem_gps_herdam_o_segmento_corrente():
    itens = [
        (1, _dias(0), FORA), (2, _dias(1), SEM_GPS),
        (3, _dias(2), CASA), (4, _dias(3), CASA), (5, _dias(4), SEM_GPS),
    ]
    segmentos = dividir_por_transicao_casa(itens)
    assert [[m for m, _ in seg] for seg in segmentos] == [[1, 2], [3, 4, 5]]


def test_sessao_sem_gps_nenhum_fica_inteira():
    itens = [(1, _dias(0), SEM_GPS), (2, _dias(1), SEM_GPS)]
    segmentos = dividir_por_transicao_casa(itens)
    assert len(segmentos) == 1


def test_pasta_que_lista_destinos_nomeia_a_viagem_inteira():
    """A cobertura de GPS é irregular; o nome que o dono escreveu não é.

    Caso real: 2.405 fotos em "Dubai, Thai & Viet", das quais só 106 com
    coordenada — e nenhuma nos Emirados. A viagem saía como
    "Tailândia – Vietnã", perdendo um país inteiro.
    """
    from datetime import timedelta

    from fotoorganizer.grouping.classifier import DadosSessao, classificar_sessao

    decisao = classificar_sessao(DadosSessao(
        pastas=("/Users/x/Pictures/Dubai, Thai & Viet",),
        duracao=timedelta(days=20),
        pais_dominante="Tailândia",
        dist_mediana_casa_km=None,
        periodo_curto="Viagem de 01-11 a 21-11",
        paises_no_tempo=("Tailândia", "Vietnã"),
    ))
    assert decisao.tipo == "viagem"
    assert decisao.rotulo == "Emirados Árabes Unidos – Tailândia – Vietnã"
    assert decisao.origem == "pasta"
    assert "lista 3 destinos" in decisao.justificativa
