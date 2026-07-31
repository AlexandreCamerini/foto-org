#!/usr/bin/env python
"""Remove da base bruta um namespace inteiro de metadados.

A base bruta existe para o usuário inspecionar a foto dele e para o motor
cruzar sinais. Nem todo namespace serve às duas coisas: `makernotes` traz 259
campos por CR3 sobre o estado interno da câmera e não ajuda a decidir viagem,
evento ou lugar — eram 969 mil linhas, 83% de todo o metadado de um acervo
real (D-027).

Isto é poda, não perda: `scan --reprocessar` regrava tudo que o extrator
atual produzir. Se o namespace continuar fora de `_GRUPOS`, ele não volta —
que é justamente a intenção.

Uso:
    scripts/podar_metadados.py --dry-run
    scripts/podar_metadados.py --namespace makernotes
    scripts/podar_metadados.py --namespace makernotes --namespace quicktime

As colunas do catálogo (data, câmera, lente, GPS, dimensões) NÃO dependem da
base bruta: são preenchidas na leitura e ficam intactas.
"""

from __future__ import annotations

import argparse
import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fotoorganizer.config import paths  # noqa: E402

PADRAO = ("makernotes",)


def _peso(con: sqlite3.Connection) -> list[tuple[str, int, float]]:
    return [
        (ns, n, bytes_ / 1048576)
        for ns, n, bytes_ in con.execute(
            "select namespace, count(*),"
            "       sum(length(coalesce(chave,'')) + length(coalesce(valor,'')))"
            "  from metadata_entries group by namespace order by 3 desc"
        )
    ]


def _copiar(db: Path) -> Path:
    carimbo = datetime.now(timezone.utc).astimezone().strftime("%Y%m%d-%H%M%S")
    destino = db.with_name(f"{db.stem}-antes-da-poda-{carimbo}.db")
    if shutil.which("sqlite3"):
        subprocess.run(["sqlite3", str(db), f".backup '{destino}'"], check=True)
    else:
        shutil.copy2(db, destino)
    if not destino.is_file():
        raise SystemExit("não consegui copiar o catálogo — nada foi podado")
    return destino


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--catalogo", type=Path, default=None)
    ap.add_argument("--namespace", action="append", default=None,
                    help=f"pode repetir; padrão: {', '.join(PADRAO)}")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--sem-copia", action="store_true",
                    help="pula a cópia de segurança (para catálogo de teste)")
    args = ap.parse_args()

    alvos = tuple(args.namespace or PADRAO)
    db = paths.default_db_path(args.catalogo)
    if not db.is_file():
        print(f"catálogo não encontrado: {db}")
        return 1

    con = sqlite3.connect(db)
    mb = db.stat().st_size / 1048576
    print(f"catálogo: {db}  ({mb:.0f} MB)\n")
    print(f"  {'namespace':<14} {'linhas':>9} {'texto':>9}")
    total_linhas = 0
    for ns, n, peso in _peso(con):
        marca = "  ← poda" if ns in alvos else ""
        print(f"  {ns:<14} {n:>9} {peso:>7.1f} MB{marca}")
        if ns in alvos:
            total_linhas += n
    if total_linhas == 0:
        print("\nnada a podar.")
        return 0
    if args.dry_run:
        print(f"\n--dry-run: {total_linhas} linhas sairiam. Nada foi alterado.")
        return 0

    con.close()
    if not args.sem_copia:
        print(f"\ncópia de segurança: {_copiar(db).name}")

    con = sqlite3.connect(db)
    marcas = ",".join("?" * len(alvos))
    con.execute("begin")
    con.execute(
        f"delete from metadata_entries where namespace in ({marcas})", alvos
    )
    con.commit()
    con.execute("vacuum")
    restantes = con.execute("select count(*) from metadata_entries").fetchone()[0]
    integridade = con.execute("pragma integrity_check").fetchone()[0]
    con.close()

    mb2 = db.stat().st_size / 1048576
    print(f"\npodadas {total_linhas} linhas de {', '.join(alvos)}.")
    print(f"  metadados restantes {restantes}")
    print(f"  tamanho             {mb:.0f} MB → {mb2:.0f} MB")
    print(f"  integridade         {integridade}")
    return 0 if integridade == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
