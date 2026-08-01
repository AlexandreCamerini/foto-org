#!/usr/bin/env python3
"""Calibra o raio de incerteza do lugar herdado contra o acervo real.

SOMENTE LEITURA: abre o catálogo em modo `ro`, não escreve nada, não toca em
nenhum arquivo original. Serve para provar (ou derrubar) as constantes de
`raio_incerteza()` em `fotoorganizer/grouping/correlacao.py`.

O truque da medição: a herança de GPS acontece quando uma foto SEM
coordenada pega a da foto mais próxima no tempo, de OUTRA origem, que tem
coordenada. Para essa foto não dá para saber o erro — é justamente o que não
se conhece. Mas o acervo tem milhares de fotos COM GPS próprio: tratando uma
delas como se fosse herdeira, e aplicando a mesma regra de escolha
(`herdar_gps`) para achar a doadora hipotética, dá para comparar a distância
REAL entre as duas com o raio que a fórmula proporia para aquele Δt.

A cobertura é reportada de três formas, porque as três respondem perguntas
diferentes e uma só esconderia o resto:

  bruta     — fração de pares cobertos, cada par pesando igual;
  ponderada — cada banda de Δt pesa quanto ela pesa no acervo de verdade
              (as herdeiras reais estão concentradas em 30 min–12 h);
  por dia   — cada dia de fotografia pesa igual, para que uma viagem com
              300 pares não decida a constante sozinha.

Uso:
    .venv/bin/python scripts/calibrar_raio_incerteza.py
    .venv/bin/python scripts/calibrar_raio_incerteza.py --grade
    .venv/bin/python scripts/calibrar_raio_incerteza.py --db <catalog.db>

Resultado documentado em docs/LOCAL_ESTIMADO.md.
"""

from __future__ import annotations

import argparse
import math
import random
import sqlite3
import statistics
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fotoorganizer.config import paths  # noqa: E402
from fotoorganizer.grouping.correlacao import (  # noqa: E402
    JANELA_HERANCA,
    RAIO_PISO_M,
    RAIO_TETO_M,
    VELOCIDADE_PLAUSIVEL_MS,
    raio_incerteza,
)

RAIO_TERRA_M = 6_371_008.8

# As bandas em que a medição é lida. Não são limiares de nada — só a régua
# que deixa ver a forma da curva sem afogar o olho em 2 mil linhas.
BANDAS: tuple[tuple[str, float, float], ...] = (
    ("<=1min", 0, 60),
    ("1-10min", 60, 600),
    ("10-30min", 600, 1800),
    ("30min-2h", 1800, 7200),
    ("2-6h", 7200, 21600),
    ("6-12h", 21600, 43200),
)


@dataclass(frozen=True, slots=True)
class Par:
    """Uma herança hipotética: as duas fotos têm GPS próprio, então a
    distância entre elas é medida, não estimada."""

    delta_s: float
    distancia_m: float
    dia: date


def haversine(a: tuple[float, float], b: tuple[float, float]) -> float:
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = (math.sin((la2 - la1) / 2) ** 2
         + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2)
    return 2 * RAIO_TERRA_M * math.asin(min(1.0, math.sqrt(h)))


def ler_fotos_com_gps(db: Path) -> list[tuple[float, int, float, float]]:
    """(instante, origem, lat, lon) de toda foto com GPS PRÓPRIO e data."""
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        linhas = con.execute(
            "select data_capturada, source_id, gps_lat, gps_lon"
            "  from media_files"
            " where gps_lat is not null and data_capturada is not null"
        ).fetchall()
    finally:
        con.close()
    return sorted(
        (datetime.fromisoformat(q).timestamp(), src, lat, lon)
        for q, src, lat, lon in linhas
    )


def pesos_do_acervo(db: Path) -> dict[str, int]:
    """Quantas herdeiras REAIS caem em cada banda de Δt.

    Sem isto a média trataria a banda de 1 minuto (277 fotos) igual à de
    30 min–2 h (5.905) e a conta diria mais sobre a régua que sobre o acervo.
    """
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        deltas = [
            d for (d,) in con.execute(
                "select gps_estimado_delta_s from media_files"
                " where gps_lat is null and gps_lat_estimado is not null"
                "   and gps_estimado_delta_s is not null"
            )
        ]
    finally:
        con.close()
    pesos = {nome: 0 for nome, _, _ in BANDAS}
    for d in deltas:
        for nome, lo, hi in BANDAS:
            if (lo < d <= hi) or (lo == 0 and d <= hi):
                pesos[nome] += 1
                break
    return pesos


def montar_pares(
    fotos: list[tuple[float, int, float, float]],
    janela_s: float,
) -> list[Par]:
    """A mesma regra de escolha de `herdar_gps`, sobre fotos que já têm GPS.

    Para cada foto, a de OUTRA origem mais próxima no tempo dentro da janela
    — indo para os dois lados e parando no primeiro candidato de cada lado,
    porque a lista está ordenada e o primeiro que serve é o mais próximo.
    """
    tempos = [f[0] for f in fotos]
    pares: list[Par] = []
    for i, (t, origem, lat, lon) in enumerate(fotos):
        melhor: tuple[float, int] | None = None
        for passo in (-1, 1):
            j = i + passo
            while 0 <= j < len(fotos):
                delta = abs(tempos[j] - t)
                if delta > janela_s:
                    break
                if fotos[j][1] != origem:
                    if melhor is None or delta < melhor[0]:
                        melhor = (delta, j)
                    break
                j += passo
        if melhor is None:
            continue
        delta, j = melhor
        pares.append(Par(
            delta_s=delta,
            distancia_m=haversine((lat, lon), (fotos[j][2], fotos[j][3])),
            dia=datetime.fromtimestamp(t).date(),
        ))
    return pares


def _cobre(par: Par) -> bool:
    """O raio proposto pela fórmula em vigor conteria a distância real?"""
    return par.distancia_m <= raio_incerteza(timedelta(seconds=par.delta_s))


def _por_banda(pares: list[Par]) -> dict[str, list[Par]]:
    saida: dict[str, list[Par]] = {nome: [] for nome, _, _ in BANDAS}
    for par in pares:
        for nome, lo, hi in BANDAS:
            if (lo < par.delta_s <= hi) or (lo == 0 and par.delta_s <= hi):
                saida[nome].append(par)
                break
    return saida


def coberturas(
    pares: list[Par], pesos: dict[str, int], fn=raio_incerteza
) -> tuple[float, float, float]:
    """(bruta, ponderada pelo acervo, por dia)."""
    def cobre(par: Par) -> bool:
        return par.distancia_m <= fn(timedelta(seconds=par.delta_s))

    bruta = sum(1 for p in pares if cobre(p)) / len(pares)

    soma = peso_total = 0.0
    for nome, sub in _por_banda(pares).items():
        if not sub or not pesos.get(nome):
            continue
        soma += (sum(1 for p in sub if cobre(p)) / len(sub)) * pesos[nome]
        peso_total += pesos[nome]
    ponderada = soma / peso_total if peso_total else 0.0

    por_dia: dict[date, list[bool]] = defaultdict(list)
    for par in pares:
        por_dia[par.dia].append(cobre(par))
    media_dia = statistics.mean(sum(v) / len(v) for v in por_dia.values())
    return bruta, ponderada, media_dia


def _percentil(valores: list[float], q: float) -> float:
    ordenado = sorted(valores)
    return ordenado[min(len(ordenado) - 1, int(q * len(ordenado)))]


def bootstrap_por_dia(
    pares: list[Par], repeticoes: int = 400, semente: int = 20260801
) -> tuple[float, float, float]:
    """(p5, mediana, p95) da cobertura reamostrando DIAS, não pares.

    Reamostrar par a par mentiria: pares do mesmo dia não são independentes
    — é o mesmo trajeto contado muitas vezes. A pergunta que interessa é se
    a cobertura sobrevive a ter fotografado outros dias.
    """
    rng = random.Random(semente)
    por_dia: dict[date, list[Par]] = defaultdict(list)
    for par in pares:
        por_dia[par.dia].append(par)
    dias = sorted(por_dia)

    amostras = []
    for _ in range(repeticoes):
        taxas = [
            sum(1 for p in por_dia[dia] if _cobre(p)) / len(por_dia[dia])
            for dia in rng.choices(dias, k=len(dias))
        ]
        amostras.append(statistics.mean(taxas))
    amostras.sort()
    return (_percentil(amostras, 0.05), statistics.median(amostras),
            _percentil(amostras, 0.95))


def relatorio(pares: list[Par], pesos: dict[str, int]) -> None:
    print(f"pares medidos: {len(pares)}  "
          f"dias de fotografia: {len({p.dia for p in pares})}")
    print(f"fórmula: min({RAIO_TETO_M / 1000:.0f} km, "
          f"max({RAIO_PISO_M:.0f} m, {VELOCIDADE_PLAUSIVEL_MS} m/s × Δt))")
    print()
    cab = f"{'banda':<10}{'n':>6}{'dias':>6}{'p50 real':>11}{'p90 real':>11}"
    print(cab + f"{'raio no fim':>13}{'cobertura':>11}")
    for nome, _, hi in BANDAS:
        sub = _por_banda(pares)[nome]
        if not sub:
            continue
        ds = [p.distancia_m for p in sub]
        cob = sum(1 for p in sub if _cobre(p)) / len(sub)
        print(f"{nome:<10}{len(sub):>6}{len({p.dia for p in sub}):>6}"
              f"{statistics.median(ds) / 1000:>10.1f}k"
              f"{_percentil(ds, 0.90) / 1000:>10.1f}k"
              f"{raio_incerteza(timedelta(seconds=hi)) / 1000:>12.1f}k"
              f"{cob:>11.1%}")

    bruta, ponderada, por_dia = coberturas(pares, pesos)
    print()
    print(f"cobertura bruta ............ {bruta:.1%}")
    print(f"cobertura ponderada ........ {ponderada:.1%}"
          f"   (pesos do acervo: {pesos})")
    print(f"cobertura por dia .......... {por_dia:.1%}")
    p5, med, p95 = bootstrap_por_dia(pares)
    print(f"bootstrap por dia .......... p5={p5:.1%} "
          f"mediana={med:.1%} p95={p95:.1%}")

    piores = sorted(pares, key=lambda p: p.distancia_m
                    - raio_incerteza(timedelta(seconds=p.delta_s)))[::-1][:5]
    print("\nos piores descobertos (distância real − raio proposto):")
    for p in piores:
        raio = raio_incerteza(timedelta(seconds=p.delta_s))
        print(f"  {p.dia}  Δt={p.delta_s / 60:>7.1f} min"
              f"  real={p.distancia_m / 1000:>7.1f} km"
              f"  raio={raio / 1000:>6.1f} km")
    dias_ruins = Counter(p.dia for p in pares if not _cobre(p))
    print(f"  descobertos concentrados em {len(dias_ruins)} dias: "
          f"{dias_ruins.most_common(5)}")


def grade(pares: list[Par], pesos: dict[str, int]) -> None:
    """Sensibilidade: o que acontece com a cobertura ao mexer nas constantes.

    Uma constante escolhida sem esta tabela é chute com cara de medição.
    """
    print(f"\n{'V m/s':>7}{'teto km':>9}{'bruta':>9}{'pond':>9}{'por-dia':>9}")
    for v in (4.0, 5.0, 6.0, 7.0, 8.0):
        for teto_km in (40, 45, 50, 60, 80):
            def fn(delta, v=v, teto=teto_km * 1000.0):
                s = abs(delta.total_seconds())
                return min(teto, max(RAIO_PISO_M, v * s))
            b, p, d = coberturas(pares, pesos, fn)
            marca = "  <= mira 90%" if p >= 0.90 else ""
            print(f"{v:>7.1f}{teto_km:>9}{b:>9.1%}{p:>9.1%}{d:>9.1%}{marca}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", type=Path, default=paths.default_db_path())
    ap.add_argument("--grade", action="store_true",
                    help="tabela de sensibilidade das constantes")
    args = ap.parse_args()

    if not args.db.exists():
        print(f"catálogo não encontrado: {args.db}", file=sys.stderr)
        return 1

    fotos = ler_fotos_com_gps(args.db)
    print(f"fotos com GPS próprio: {len(fotos)}")
    pares = montar_pares(fotos, JANELA_HERANCA.total_seconds())
    if not pares:
        print("nenhum par de origens diferentes dentro da janela — "
              "sem o que calibrar neste catálogo.", file=sys.stderr)
        return 1
    pesos = pesos_do_acervo(args.db)
    relatorio(pares, pesos)
    if args.grade:
        grade(pares, pesos)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
