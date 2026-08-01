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

**Viagem não se divide.** Um evento acontece dentro de um dia; uma viagem
contém dias. Aplicar esta régua a uma viagem produz uma saída por manhã e
outra por tarde — foi o que aconteceu com o Pantanal, três dias que viraram
quatro blocos —, e isso desfaz a decisão do commit 9670765: a viagem
Tailândia–Vietnã já esteve partida em três destinos porque só 106 das 2.405
fotos tinham GPS, e a forma da pasta acabava dependendo de qual foto por
acaso gravou coordenada.

Dentro de uma viagem os blocos servem para navegar — ver o dia 2 separado do
dia 3 na tela — nunca para virar pasta. Por isso `dividir_sessao` recebe o
tipo: quem chama precisa dizer o que está dividindo.
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
# Além disto, a sessão não é um acontecimento: é uma estadia com noites no
# meio, e vira um destino só. Medido em horas corridas, não em dias de
# calendário — uma festa das 22h às 02h atravessa a meia-noite e continua
# sendo uma festa.
#
# É o que segura o caso do Pantanal: 97 fotos ao longo de 18 a 20 de julho,
# que a régua de ritmo partia em quatro saídas. O motor o classificou como
# "evento" porque a duração — 1 dia e 23 h — não alcança o limiar de viagem
# de 3 dias, e essa fresta não pode determinar a forma da pasta.
DURACAO_MAX_ACONTECIMENTO = timedelta(hours=20)
# Quantos intervalos ANTERIORES definem "o ritmo local". A janela olha só para
# trás de propósito: a fronteira é o intervalo que destoa do que aquelas fotos
# vinham fazendo, e uma janela simétrica enxerga o bloco seguinte e se
# contamina com ele — num cenário de fotos esparsas seguidas de uma rajada,
# ela concluía que 2 h entre fotos era anomalia e cortava quatro vezes.
JANELA = 12
# Bloco menor que isto não é acontecimento: são fotos de teste, um ajuste de
# luz, uma câmera ligada cedo. Absorve no vizinho mais próximo no tempo.
#
# A Serena 15 Anos tinha cinco fotos às 17:25 e a festa das 19:28 às 22:47.
# A régua separava — tecnicamente certo, duas horas de intervalo — e o dono
# não reconhece cinco fotos como um evento da vida dele. O custo é engolir um
# acontecimento pequeno de verdade; o erro é barato porque ele fica visível
# junto do grande, e não numa pasta que ninguém procura.
MIN_FOTOS_EVENTO = 10


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


def dividir_sessao(
    momentos: list[Momento], e_viagem: bool
) -> list[list[int]]:
    """A divisão que vale para destino.

    Um bloco só quando a sessão é viagem, ou quando ela atravessa noites —
    aí é estadia, não acontecimento, mesmo que o classificador a tenha
    rotulado de evento por não alcançar o limiar de duração.

    `dividir_em_eventos` continua disponível para navegação: ver o dia 2
    separado do dia 3 na tela é útil e não vira pasta.
    """
    if not momentos:
        return []
    ordenados = sorted(momentos, key=lambda m: m.quando)
    atravessa_noites = (
        ordenados[-1].quando - ordenados[0].quando
    ) > DURACAO_MAX_ACONTECIMENTO
    if e_viagem or atravessa_noites:
        return [[m.media_id for m in ordenados]]
    return dividir_em_eventos(ordenados)


def dividir_em_eventos(momentos: list[Momento]) -> list[list[int]]:
    """Blocos de `media_id`, na ordem do tempo. Nunca devolve bloco vazio.

    Não aplique a uma viagem — use `dividir_sessao`.
    """
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
    return _absorver_pequenos(blocos)


def _absorver_pequenos(blocos: list[list[int]]) -> list[list[int]]:
    """Junta blocos abaixo do mínimo ao vizinho, preservando a ordem.

    Um bloco só, por menor que seja, fica: se a sessão inteira tem três
    fotos, elas são o acontecimento.
    """
    if len(blocos) <= 1:
        return blocos
    resultado: list[list[int]] = []
    for bloco in blocos:
        if resultado and len(bloco) < MIN_FOTOS_EVENTO:
            resultado[-1].extend(bloco)
        else:
            resultado.append(bloco)
    # O primeiro bloco pode ter ficado pequeno sem ninguém antes dele.
    if len(resultado) > 1 and len(resultado[0]) < MIN_FOTOS_EVENTO:
        resultado[1][:0] = resultado[0]
        resultado.pop(0)
    return resultado
