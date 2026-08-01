"""Dividir uma sessão em acontecimentos — o nível que faltava.

O agrupamento tem um nível só: `agrupar_viagens` corta onde passam 3 dias sem
foto. Isso encontra a viagem e nunca encontra o evento, então dois
acontecimentos no mesmo dia são sempre uma sessão só. Foi o que o dono
apontou: aniversário de manhã e show à noite viram um.

A régua **não** é um intervalo fixo. Duas medições do acervo real mostram por
que ela não pode ser:

- Um limiar de 4 h aplicado por dia de calendário partiu a viagem a Dubai na
  meia-noite: 8 dos 28 dias alcançáveis acusaram falso positivo, com blocos
  `22:41–23:59` e `01:53–06:57` que são a mesma noite.
- O ritmo de disparo varia por ordem de grandeza entre contextos. Um ensaio
  dispara a cada poucos segundos; um dia de turismo, a cada dezenas de
  minutos. O mesmo intervalo de 40 min é pausa num caso e fronteira no outro.

Então a fronteira é **relativa ao ritmo local**: corta onde o intervalo
destoa do que aquelas fotos vinham fazendo. Com piso e teto, porque razão
pura erra nos extremos — sem piso, uma rajada faz qualquer respiro virar
evento; sem teto, um dia inteiro parado esconde a fronteira seguinte.

Deslocamento corta independente do tempo: mudar de lugar encerra o que estava
acontecendo, e é o sinal mais forte quando existe. Neste acervo ele existe
para poucas fotos (só a 5D Mark IV grava GPS, ver D-029), então a régua não
pode depender dele.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from statistics import median

# Abaixo disto é pausa dentro do mesmo acontecimento: almoço, troca de lente,
# caminhada até o próximo ponto. Nenhum ritmo justifica cortar aqui.
#
# 90 min e não 45: num dia disparando a cada 10 min, uma parada de 70 min é
# sete vezes o ritmo e ainda assim é almoço, não acontecimento novo. O custo é
# não separar dois eventos colados — raro, e o erro barato é esse, porque
# juntar demais o dono desfaz com um clique e separar demais espalha a foto
# por pastas que ele não reconhece.
PISO = timedelta(minutes=90)
# Acima disto é sempre fronteira, por mais espaçado que o ritmo venha sendo.
TETO = timedelta(hours=8)
# Quantas vezes o intervalo típico local precisa ser excedido para virar corte.
FATOR = 6.0
# Deslocamento que encerra um acontecimento mesmo com as fotos coladas no
# tempo. 3 km separa bairros sem separar salões do mesmo casamento.
DESLOCAMENTO_KM = 3.0
# Quantos intervalos ANTERIORES definem "o ritmo local". A janela olha só para
# trás de propósito: a fronteira é o intervalo que destoa do que aquelas fotos
# vinham fazendo, e uma janela simétrica enxerga o bloco seguinte e se
# contamina com ele — num cenário de fotos esparsas seguidas de uma rajada,
# ela concluía que 2 h entre fotos era anomalia e cortava quatro vezes.
JANELA = 12


@dataclass(frozen=True, slots=True)
class Momento:
    media_id: int
    quando: datetime
    lat: float | None = None
    lon: float | None = None

    @property
    def tem_lugar(self) -> bool:
        return self.lat is not None and self.lon is not None


def _km(a: Momento, b: Momento) -> float | None:
    """Distância aproximada. Sem coordenada dos dois lados, None."""
    if not (a.tem_lugar and b.tem_lugar):
        return None
    dlat = math.radians(b.lat - a.lat)
    dlon = math.radians(b.lon - a.lon)
    lat_media = math.radians((a.lat + b.lat) / 2)
    return 6371.0 * math.hypot(dlat, dlon * math.cos(lat_media))


def _ritmo_local(intervalos: list[timedelta], i: int) -> timedelta | None:
    """O intervalo típico ANTES da posição `i`, ou None sem história.

    Sem história não há do que destoar: o primeiro intervalo de uma sessão só
    corta pelo teto ou por deslocamento.
    """
    anteriores = intervalos[max(0, i - JANELA):i]
    return median(anteriores) if anteriores else None


def dividir_em_eventos(momentos: list[Momento]) -> list[list[int]]:
    """Blocos de `media_id`, na ordem do tempo. Nunca devolve bloco vazio."""
    if not momentos:
        return []
    ordenados = sorted(momentos, key=lambda m: m.quando)
    if len(ordenados) == 1:
        return [[ordenados[0].media_id]]

    intervalos = [
        ordenados[i].quando - ordenados[i - 1].quando
        for i in range(1, len(ordenados))
    ]

    blocos: list[list[int]] = [[ordenados[0].media_id]]
    for i, intervalo in enumerate(intervalos):
        anterior, atual = ordenados[i], ordenados[i + 1]
        distancia = _km(anterior, atual)

        if distancia is not None and distancia >= DESLOCAMENTO_KM:
            corta = True
        elif intervalo >= TETO:
            corta = True
        elif intervalo < PISO:
            corta = False
        else:
            ritmo = _ritmo_local(intervalos, i)
            corta = ritmo is not None and intervalo > ritmo * FATOR

        if corta:
            blocos.append([])
        blocos[-1].append(atual.media_id)
    return blocos
