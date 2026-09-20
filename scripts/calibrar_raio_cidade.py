"""Mede o raio honesto de "a foto está em algum ponto desta cidade".

Para cada pasta cujas fotos têm GPS PRÓPRIO e cujo nome é uma cidade
confirmada no dataset offline (`geolocation/cidades.lugar_da_pasta`), mede
a distância entre o centroide da cidade e a coordenada média das fotos.
O raio que cobre 100% dessas distâncias é `RAIO_CIDADE_M` (D-083).

Somente leitura no catálogo. Uso:
    .venv/bin/python scripts/calibrar_raio_cidade.py [--catalogo caminho.db]
"""

from __future__ import annotations

import argparse
import math
import os
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fotoorganizer.geolocation.cidades import RAIO_CIDADE_M, lugar_da_pasta  # noqa: E402

_CATALOGO = os.path.expanduser(
    "~/Library/Application Support/FotoOrganizer/catalog.db"
)


def _km(lat1, lon1, lat2, lon2) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalogo", default=_CATALOGO)
    args = ap.parse_args()
    con = sqlite3.connect(f"file:{args.catalogo}?mode=ro", uri=True)
    linhas = []
    for pasta, n, lat, lon in con.execute(
        "select pasta, count(*), avg(gps_lat), avg(gps_lon) from media_files "
        "where gps_lat is not null group by 1"
    ):
        lugar = lugar_da_pasta(pasta)
        if lugar is None:
            continue
        linhas.append((_km(lat, lon, lugar.cidade.lat, lugar.cidade.lon), n, lugar.cidade.nome,
                       lugar.cidade.pais, lugar.cidade.populacao, pasta[-50:]))
    if not linhas:
        print("nenhuma pasta com GPS próprio nomeia cidade conhecida")
        return 0
    linhas.sort()
    print(f"{'km':>7} {'fotos':>5}  cidade / país / hab. / pasta")
    for km, n, cidade, pais, pop, pasta in linhas:
        print(f"{km:7.1f} {n:5d}  {cidade} / {pais} / {pop} / …{pasta}")
    dist = [l[0] for l in linhas]
    fotos = sum(l[1] for l in linhas)
    cobertas = sum(l[1] for l in linhas if l[0] * 1000 <= RAIO_CIDADE_M)
    print(f"\npastas={len(linhas)} fotos={fotos} máx={max(dist):.1f} km "
          f"mediana={sorted(dist)[len(dist)//2]:.1f} km")
    print(f"RAIO_CIDADE_M={RAIO_CIDADE_M/1000:.0f} km cobre "
          f"{cobertas}/{fotos} fotos ({100*cobertas/fotos:.1f}%)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
