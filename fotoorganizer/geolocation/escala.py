"""Quantos metros vale um grau — a ponte entre o raio e o desenho.

O raio de incerteza sai de `grouping/correlacao.py` em METROS; o mapa
desenha em GRAUS de latitude/longitude. Alguém tem de converter, e esse
alguém é o Python: um grau de longitude vale 111 km no equador e 79 km no
Rio, e uma constante única chutada do outro lado da API desenharia o
círculo com o tamanho errado exatamente onde o acervo está.

Aproximação local (série de Taylor da elipsoide WGS84), válida para as
escalas deste mapa — dezenas de quilômetros em torno de um ponto. Não
serve para navegação; serve para dizer de que tamanho é o círculo.
"""

from __future__ import annotations

import math

__all__ = ["metros_por_grau"]


def metros_por_grau(lat: float) -> tuple[float, float]:
    """(metros por grau de latitude, metros por grau de longitude) em `lat`.

    O valor da longitude encolhe com o cosseno da latitude; o da latitude
    quase não muda. Devolver os dois separados é o que permite ao mapa
    desenhar um círculo redondo em vez de uma elipse achatada.
    """
    phi = math.radians(lat)
    por_lat = (111_132.92
               - 559.82 * math.cos(2 * phi)
               + 1.175 * math.cos(4 * phi)
               - 0.0023 * math.cos(6 * phi))
    por_lon = (111_412.84 * math.cos(phi)
               - 93.5 * math.cos(3 * phi)
               + 0.118 * math.cos(5 * phi))
    # Nos polos o grau de longitude tende a zero e dividir por ele explodiria
    # o desenho. Nenhuma foto deste acervo está lá, mas o mapa não pode
    # quebrar por causa de uma que esteja.
    return por_lat, max(por_lon, 1.0)
