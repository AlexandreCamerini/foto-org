#!/usr/bin/env python3
"""Mede quantas fotos mudam de categoria se "organizável" passar a exigir
que a fonte esteja montada.

O funil promete que cada degrau é subconjunto do anterior (conhecidas →
alcançáveis → organizáveis). "Alcançáveis" olha `Source.disponivel`;
"organizáveis" não olha — vem de `MediaFile.organizavel` (papel=acervo e
arquivo presente). Uma fonte na gaveta produz fotos ditas organizáveis que
não abrem, e no limite quebra a monotonicidade do funil.

O catálogo é copiado com `.backup` e as contagens rodam sobre a CÓPIA, que é
apagada no fim. Nenhum arquivo do acervo é tocado (invariante 1).

Uso:
    .venv/bin/python scripts/medir_alcance_do_organizavel.py
    .venv/bin/python scripts/medir_alcance_do_organizavel.py --db <catalog.db>
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fotoorganizer.config import paths  # noqa: E402

# O filtro de acervo, exatamente como `MediaFile.organizavel` o define. O
# enum é gravado pelo NOME ("ACERVO"), não pelo valor — `Enum(..., native_enum
# =False)` do SQLAlchemy.
ORGANIZAVEL = "m.papel = 'ACERVO' AND m.arquivo_ausente = 0"


def _copiar(origem: Path, destino: Path) -> None:
    """`.backup` em vez de `cp`: com WAL ativo, copiar o arquivo solto pega
    um estado sem as páginas do -wal."""
    with sqlite3.connect(f"file:{origem}?mode=ro", uri=True) as src:
        with sqlite3.connect(destino) as dst:
            src.backup(dst)


def _n(con: sqlite3.Connection, sql: str, *args) -> int:
    return con.execute(sql, args).fetchone()[0]


def medir(con: sqlite3.Connection) -> None:
    con.row_factory = sqlite3.Row

    registros = _n(con, "SELECT count(*) FROM media_files")
    organizaveis = _n(
        con, f"SELECT count(*) FROM media_files m WHERE {ORGANIZAVEL}"
    )
    off = _n(con, f"""
        SELECT count(*) FROM media_files m JOIN sources s ON s.id = m.source_id
        WHERE {ORGANIZAVEL} AND s.disponivel = 0
    """)

    print("== catálogo ==")
    print(f"registros                         {registros:>9,}")
    print(f"organizáveis (definição de hoje)  {organizaveis:>9,}")
    print(f"  em fonte indisponível           {off:>9,}"
          f"   ({off / max(organizaveis, 1):.1%})")
    print(f"organizáveis se exigir fonte      {organizaveis - off:>9,}")

    print("\n== por fonte ==")
    for linha in con.execute(f"""
        SELECT s.id, s.apelido, s.caminho, s.disponivel,
               count(m.id) FILTER (WHERE {ORGANIZAVEL}) AS organizaveis,
               count(m.id) AS registros
        FROM sources s LEFT JOIN media_files m ON m.source_id = s.id
        GROUP BY s.id ORDER BY organizaveis DESC
    """):
        marca = "✓" if linha["disponivel"] else "✗"
        nome = linha["apelido"] or Path(linha["caminho"]).name
        print(f"  {marca} {nome[:34]:<34} "
              f"organizáveis {linha['organizaveis']:>8,}"
              f"   registros {linha['registros']:>8,}")

    # Duas contas que o funil precisa e o SQL sozinho não dá barato (sem
    # índice por caminho, o EXISTS cruzado varre 197 mil × 26 mil):
    #
    #  - GÊMEA ALCANÇÁVEL: a mesma foto conhecida por duas fontes, uma na
    #    gaveta e outra montada. Descontar a linha da fonte off tiraria da
    #    conta uma foto que ABRE por outro caminho — o mesmo erro que
    #    `levantar()` já corrigiu para os alcançáveis (2.620 fotos).
    #  - UNIDADE: "alcançáveis" conta FOTO (caminho distinto) e
    #    "organizáveis" conta REGISTRO. Se dois registros de acervo apontam
    #    para o mesmo caminho, o terceiro degrau infla sem que nada esteja
    #    errado em nenhum dos dois — e o funil pode deixar de afunilar por
    #    isso, não por indisponibilidade.
    caminhos_alcancaveis: set[str] = set()
    acervo_off: list[str] = []
    acervo_todos: list[str] = []
    for pasta, nome, ausente, papel, disponivel in con.execute("""
        SELECT m.pasta, m.nome, m.arquivo_ausente, m.papel, s.disponivel
        FROM media_files m JOIN sources s ON s.id = m.source_id
    """):
        chave = f"{pasta}/{nome}".casefold()
        if not ausente and disponivel:
            caminhos_alcancaveis.add(chave)
        if papel == "ACERVO" and not ausente:
            acervo_todos.append(chave)
            if not disponivel:
                acervo_off.append(chave)

    gemeas = sum(1 for c in acervo_off if c in caminhos_alcancaveis)
    print(f"\ndestas, com gêmea alcançável por outra fonte: {gemeas:,}")
    print(f"organizáveis contando FOTO e não registro: "
          f"{len(set(acervo_todos)):,} "
          f"(registros: {len(acervo_todos):,})")

    print("\n== o que a mudança tiraria de cada tela ==")
    for rotulo, extra in (
        ("grade (Biblioteca, filtro Organizáveis)", ""),
        ("panorama: sem data", " AND m.data_capturada IS NULL"),
        ("panorama: sem coordenada",
         " AND m.gps_lat IS NULL AND m.gps_lat_estimado IS NULL"),
        ("revisão: com sugestão", """
            AND EXISTS (SELECT 1 FROM suggestions g WHERE g.media_id = m.id)"""),
    ):
        n = _n(con, f"""
            SELECT count(*) FROM media_files m
            JOIN sources s ON s.id = m.source_id
            WHERE {ORGANIZAVEL} AND s.disponivel = 0 {extra}
        """)
        print(f"  {rotulo:<42} {n:>8,}")

    aprovadas = _n(con, """
        SELECT count(*) FROM suggestions g
        JOIN media_files m ON m.id = g.media_id
        JOIN sources s ON s.id = m.source_id
        WHERE g.status IN ('APROVADA', 'EDITADA') AND s.disponivel = 0
    """)
    total_aprovadas = _n(con, """
        SELECT count(*) FROM suggestions WHERE status IN ('APROVADA', 'EDITADA')
    """)
    print(f"\nsugestões aprovadas/editadas em fonte indisponível: "
          f"{aprovadas:,} de {total_aprovadas:,}"
          " (o que o planner tentaria copiar de um disco na gaveta)")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--db", type=Path, default=paths.default_db_path())
    args = p.parse_args()
    if not args.db.exists():
        raise SystemExit(f"catálogo não encontrado: {args.db}")

    with tempfile.TemporaryDirectory(prefix="medir-alcance-") as tmp:
        copia = Path(tmp) / "catalog.db"
        _copiar(args.db, copia)
        with sqlite3.connect(f"file:{copia}?mode=ro", uri=True) as con:
            medir(con)


if __name__ == "__main__":
    main()
