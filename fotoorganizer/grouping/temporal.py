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
