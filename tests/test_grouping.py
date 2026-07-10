from datetime import datetime, timedelta

from fotoorganizer.grouping import agrupar_viagens


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
