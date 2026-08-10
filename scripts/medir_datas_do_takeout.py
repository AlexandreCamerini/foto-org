#!/usr/bin/env python3
"""Mede o que muda no catálogo ao corrigir a data do Google Takeout.

SOMENTE LEITURA: abre o catálogo em modo `ro`, não escreve nada, não toca em
arquivo original. Serve para decidir — com número na mão — se vale reimportar
o Takeout depois da correção do fuso.

O defeito: `datetime.fromtimestamp(epoch)` sem fuso gravava a hora de parede
no fuso da MÁQUINA que rodou a importação. Como o epoch do Takeout é o
instante absoluto, a hora certa é a de UTC — e a diferença é o offset local
vigente NAQUELE instante, horário de verão incluído. Por isso o deslocamento
não é uma constante: varia por foto, e o script mede foto a foto.

Como o epoch é recuperado: a data gravada é `fromtimestamp(epoch)`, então
interpretá-la de volta como hora local devolve o mesmo epoch. A inversa só é
ambígua na hora que o relógio repete ao sair do horário de verão; essas caem
em `ambiguas` e não entram na conta.

Uso:
    python scripts/medir_datas_do_takeout.py
    python scripts/medir_datas_do_takeout.py --catalogo /caminho/catalog.db
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fotoorganizer.config.paths import default_db_path  # noqa: E402


def _abrir(caminho: Path) -> sqlite3.Connection:
    con = sqlite3.connect(f"file:{caminho}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def _corrigir(gravada: datetime) -> tuple[datetime | None, float | None]:
    """(data correta, horas de deslocamento). `None` se a inversa for ambígua."""
    try:
        epoch = gravada.timestamp()
    except (OverflowError, OSError, ValueError):
        return None, None
    # `fold=1` é a segunda ocorrência da hora repetida na saída do horário de
    # verão. Se os dois folds dão epochs diferentes, a hora é ambígua e não dá
    # para afirmar de qual instante ela veio.
    if gravada.replace(fold=1).timestamp() != epoch:
        return None, None
    correta = datetime.fromtimestamp(epoch, tz=timezone.utc).replace(tzinfo=None)
    return correta, (correta - gravada).total_seconds() / 3600


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--catalogo", type=Path, default=None)
    p.add_argument("--exemplos", type=int, default=5)
    args = p.parse_args()

    caminho = (args.catalogo or default_db_path()).expanduser()
    if not caminho.is_file():
        print(f"catálogo não encontrado: {caminho}")
        return 1
    print(f"catálogo: {caminho}  (somente leitura)\n")

    con = _abrir(caminho)
    try:
        fontes = con.execute(
            "select id, apelido, caminho from sources where tipo = 'google_takeout'"
        ).fetchall()
        if not fontes:
            print("Nenhuma fonte do tipo google_takeout no catálogo.")
            print("Nada a corrigir — a correção só afeta importações do Takeout.")
            return 0

        for f in fontes:
            print(f"fonte #{f['id']}  {f['apelido']}  ({f['caminho']})")
        ids = ",".join(str(f["id"]) for f in fontes)

        linhas = con.execute(f"""
            select id, nome, data_capturada, data_capturada_utc,
                   trip_id, event_id
            from media_files
            where source_id in ({ids})
        """).fetchall()

        total = len(linhas)
        sem_data = mudam = iguais = ambiguas = 0
        em_grupo = 0
        deslocamentos: Counter = Counter()
        exemplos: list[tuple] = []

        for linha in linhas:
            bruto = linha["data_capturada"]
            if not bruto:
                sem_data += 1
                continue
            try:
                gravada = datetime.fromisoformat(bruto)
            except ValueError:
                sem_data += 1
                continue
            correta, horas = _corrigir(gravada)
            if correta is None:
                ambiguas += 1
                continue
            if correta == gravada:
                iguais += 1
                continue
            mudam += 1
            deslocamentos[horas] += 1
            if linha["trip_id"] or linha["event_id"]:
                em_grupo += 1
            if len(exemplos) < args.exemplos:
                exemplos.append((linha["nome"], gravada, correta))

        print(f"\n{'=' * 66}")
        print(f"  itens do Takeout no catálogo{total:>36}")
        print(f"  sem data gravada{sem_data:>48}")
        print(f"  data já correta{iguais:>49}")
        print(f"  hora ambígua (saída do horário de verão){ambiguas:>24}")
        print(f"  MUDAM de data{mudam:>51}")
        print(f"{'=' * 66}")

        if not mudam:
            print("\nNada muda. Reimportar o Takeout é seguro e sem efeito"
                  " sobre datas.")
            return 0

        print("\n  deslocamento (horas somadas à data atual):")
        for horas, n in sorted(deslocamentos.items()):
            sinal = "+" if horas > 0 else ""
            print(f"    {sinal}{horas:>5.1f} h  →  {n:>7} fotos")

        print(f"\n  destas, já agrupadas em viagem ou evento: {em_grupo}")
        if em_grupo:
            print("    ^ estas podem trocar de grupo quando a data mudar:")
            print("      o agrupamento temporal decide por proximidade, e um")
            print("      deslocamento de horas atravessa a virada do dia.")

        print("\n  exemplos:")
        for nome, antes, depois in exemplos:
            print(f"    {nome[:34]:<34} {antes}  →  {depois}")

        print("\nNada foi alterado. Para aplicar, reimporte a fonte do Takeout")
        print("com o código corrigido — a importação é idempotente (upsert).")
    finally:
        con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
