"""Agrupamento temporal em viagens/sessões (portado e evoluído do v1).

Não usa o dia do calendário: uma lacuna longa sem fotos ("voltou pra casa")
é o que separa viagens — uma viagem pode durar semanas. Fotos sem data de
captura nem mtime ficam de fora (não dá para saber a que viagem pertencem).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

GAP_NOVA_VIAGEM = timedelta(days=3)


@dataclass(slots=True)
class ViagemDraft:
    inicio: datetime
    fim: datetime
    media_ids: list[int] = field(default_factory=list)

    @property
    def n_fotos(self) -> int:
        return len(self.media_ids)

    def periodo_legivel(self) -> str:
        inicio = self.inicio.strftime("%d/%m/%Y")
        fim = self.fim.strftime("%d/%m/%Y")
        return inicio if inicio == fim else f"{inicio} – {fim}"


def agrupar_viagens(
    itens: list[tuple[int, datetime]],
    gap: timedelta = GAP_NOVA_VIAGEM,
) -> list[ViagemDraft]:
    """`itens` = [(media_id, data_referencia)]. Devolve viagens ordenadas."""
    ordenados = sorted(itens, key=lambda par: par[1])
    viagens: list[ViagemDraft] = []
    atual: ViagemDraft | None = None

    for media_id, data in ordenados:
        if atual is not None and (data - atual.fim) > gap:
            viagens.append(atual)
            atual = None
        if atual is None:
            atual = ViagemDraft(inicio=data, fim=data)
        atual.media_ids.append(media_id)
        atual.fim = data

    if atual is not None:
        viagens.append(atual)
    return viagens


def dividir_por_transicao_casa(
    itens: list[tuple[int, datetime, bool | None]],
) -> list[list[tuple[int, datetime]]]:
    """Divide uma sessão nos pontos em que a linha do tempo passa por casa.

    Duas viagens com menos de GAP_NOVA_VIAGEM em casa no meio viravam uma
    sessão só — o gap temporal não vê [viagem A][2 dias em casa][viagem B].

    `itens` já ordenados por data; o terceiro campo é o estado GPS de cada
    foto: True (em casa), False (longe) ou None (sem GPS — herda o estado
    corrente). A transição só corta quando confirmada pela foto com GPS
    SEGUINTE no mesmo estado novo: uma foto isolada (GPS errado, escala
    rápida perto de casa) não divide uma viagem real.
    """
    n = len(itens)
    # Estado da foto com GPS mais próxima DEPOIS de cada posição.
    proximo_estado: list[bool | None] = [None] * n
    seguinte: bool | None = None
    for i in range(n - 1, -1, -1):
        proximo_estado[i] = seguinte
        if itens[i][2] is not None:
            seguinte = itens[i][2]

    segmentos: list[list[tuple[int, datetime]]] = []
    atual: list[tuple[int, datetime]] = []
    estado_corrente: bool | None = None

    for i, (media_id, data, estado) in enumerate(itens):
        if estado is not None and estado_corrente is None:
            estado_corrente = estado
        elif (estado is not None and estado != estado_corrente
                and proximo_estado[i] == estado):
            if atual:
                segmentos.append(atual)
            atual = []
            estado_corrente = estado
        atual.append((media_id, data))

    if atual:
        segmentos.append(atual)
    return segmentos
