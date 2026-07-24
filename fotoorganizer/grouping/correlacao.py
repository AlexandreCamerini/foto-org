"""Correlação temporal entre fontes: a informação mais correta disponível.

A câmera boa não grava GPS; o telefone grava. Quando as duas fotografam a
mesma cena com minutos de diferença, a foto da câmera pode HERDAR a
localização da foto do telefone — como evidência com origem, confiança
por Δt e justificativa legível, nunca como escrita no arquivo.

Dois problemas resolvidos aqui, ambos como funções puras:

1. Deriva de relógio: câmeras dedicadas vivem com o relógio errado (fuso
   não ajustado na viagem, minutos de atraso). Pares-âncora — a MESMA
   foto presente em duas fontes (mesmo hash rápido ou mesmo phash) —
   revelam o desvio: a mediana de (hora na fonte de referência − hora na
   câmera) por câmera corrige a linha do tempo antes do cruzamento.

2. Herança de GPS: para cada foto sem GPS, a foto COM GPS de outra
   origem (fonte ou câmera diferente) mais próxima na linha do tempo
   corrigida doa suas coordenadas, dentro de uma janela de tolerância.
"""

from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass
from datetime import datetime, timedelta
from statistics import median

JANELA_HERANCA = timedelta(minutes=10)
# Δt até este limite: confiança cheia da origem; acima, decai até a borda.
_JANELA_CURTA = timedelta(minutes=2)
# Âncoras com desvios muito espalhados indicam pareamento ruim — descarta.
_DISPERSAO_MAX = timedelta(minutes=3)
_MIN_ANCORAS = 2


@dataclass(frozen=True, slots=True)
class FotoRef:
    """Projeção mínima de uma foto para correlação (independente do ORM)."""

    media_id: int
    source_id: int
    quando: datetime
    camera: tuple[str | None, str | None] = (None, None)
    lat: float | None = None
    lon: float | None = None
    hash_rapido: str | None = None
    hash_perceptual: str | None = None

    @property
    def tem_gps(self) -> bool:
        return self.lat is not None and self.lon is not None


@dataclass(frozen=True, slots=True)
class Heranca:
    media_id: int
    doador_id: int
    lat: float
    lon: float
    delta: timedelta
    score_fator: float  # 1.0 na janela curta, decaindo até a borda


def estimar_offsets(
    fotos: list[FotoRef],
) -> dict[tuple[str | None, str | None], timedelta]:
    """Deriva de relógio por câmera, via pares-âncora entre fontes.

    Âncora = mesma foto em duas fontes (hash rápido igual, ou phash igual
    quando o export foi recomprimido). A fonte que conhece GPS é tratada
    como referência de relógio (Google/Apple normalizam a hora real).
    Devolve {câmera: offset} tal que `quando + offset` aproxima a linha
    do tempo da referência. Câmeras sem âncoras suficientes ou com
    desvios dispersos ficam de fora (offset implícito zero).
    """
    por_conteudo: dict[str, list[FotoRef]] = {}
    for foto in fotos:
        for chave in (foto.hash_rapido, foto.hash_perceptual):
            if chave:
                por_conteudo.setdefault(chave, []).append(foto)

    desvios: dict[tuple[str | None, str | None], list[timedelta]] = {}
    vistos: set[tuple[int, int]] = set()
    for grupo in por_conteudo.values():
        if len(grupo) < 2:
            continue
        for a in grupo:
            for b in grupo:
                if a.media_id >= b.media_id or a.source_id == b.source_id:
                    continue
                if (a.media_id, b.media_id) in vistos:
                    continue
                vistos.add((a.media_id, b.media_id))
                # Referência = quem tem GPS (catálogo de telefone);
                # câmera = quem não tem.
                if a.tem_gps == b.tem_gps:
                    continue
                referencia, camera = (a, b) if a.tem_gps else (b, a)
                if camera.camera == (None, None):
                    continue
                desvios.setdefault(camera.camera, []).append(
                    referencia.quando - camera.quando
                )

    offsets: dict[tuple[str | None, str | None], timedelta] = {}
    for camera, lista in desvios.items():
        if len(lista) < _MIN_ANCORAS:
            continue
        segundos = sorted(d.total_seconds() for d in lista)
        med = median(segundos)
        # Dispersão (mediana dos desvios absolutos em torno da mediana).
        mad = median(abs(s - med) for s in segundos)
        if mad > _DISPERSAO_MAX.total_seconds():
            continue
        offsets[camera] = timedelta(seconds=med)
    return offsets


def herdar_gps(
    fotos: list[FotoRef],
    offsets: dict[tuple[str | None, str | None], timedelta] | None = None,
    janela: timedelta = JANELA_HERANCA,
) -> list[Heranca]:
    """Para cada foto sem GPS, herda a localização da foto com GPS de
    OUTRA origem (fonte ou câmera diferente) mais próxima na linha do
    tempo corrigida, dentro da janela."""
    offsets = offsets or {}

    def corrigida(foto: FotoRef) -> datetime:
        return foto.quando + offsets.get(foto.camera, timedelta())

    doadores = sorted(
        (foto for foto in fotos if foto.tem_gps),
        key=corrigida,
    )
    if not doadores:
        return []
    tempos = [corrigida(d) for d in doadores]

    herancas: list[Heranca] = []
    for foto in fotos:
        if foto.tem_gps:
            continue
        alvo = corrigida(foto)
        i = bisect_left(tempos, alvo)
        melhor: tuple[timedelta, FotoRef] | None = None
        for j in (i - 1, i):
            if 0 <= j < len(doadores):
                doador = doadores[j]
                # Outra origem: fonte diferente OU câmera diferente —
                # duas fotos da mesma câmera na mesma fonte já vivem na
                # mesma linha do tempo e não acrescentam informação.
                if (doador.source_id == foto.source_id
                        and doador.camera == foto.camera):
                    continue
                delta = abs(tempos[j] - alvo)
                if melhor is None or delta < melhor[0]:
                    melhor = (delta, doador)
        if melhor is None:
            continue
        delta, doador = melhor
        if delta > janela:
            continue
        if delta <= _JANELA_CURTA:
            fator = 1.0
        else:
            # Decai linearmente de 1.0 (janela curta) a 0.6 (borda).
            resto = (delta - _JANELA_CURTA) / (janela - _JANELA_CURTA)
            fator = 1.0 - 0.4 * resto
        herancas.append(Heranca(
            media_id=foto.media_id, doador_id=doador.media_id,
            lat=doador.lat, lon=doador.lon, delta=delta,
            score_fator=round(fator, 3),
        ))
    return herancas
