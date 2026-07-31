#!/usr/bin/env python
"""Remove do catálogo testemunhas que deixaram de valer o espaço que ocupam.

Testemunha é o registro que não é acervo do usuário e existe para doar data,
GPS e correlação (ver MediaRole e o invariante 8 do CLAUDE.md). Duas famílias
delas deixaram de compensar:

- **Miniaturas internas do Apple Fotos** (`.photoslibrary/…/derivatives/`).
  Enquanto a janela da herança era de 10 minutos, elas eram as doadoras
  principais. Com a janela por campo (D-025), as referências do próprio Apple
  Fotos cobrem os mesmos momentos: medido no acervo real, remover as 45.822
  miniaturas custa **10 fotos** de 4.938 com lugar.
- **Arquivos de pasta de trabalho de programação** (`node_modules`,
  `Assets.xcassets`): nunca doaram nada — um ícone de app não tem data de
  captura nem GPS.

O invariante 8 continua valendo, e é por isso que este script NÃO toca em:

- **referências de catálogo externo** (`arquivo_ausente=1`): são o registro
  da foto em si, não um derivado dela, e doam 4.341 lugares;
- **acervo** (`papel='ACERVO'`), inclusive as linhas cujo arquivo sumiu do
  disco — para essas, o catálogo é o único registro que restou.

Uso:
    scripts/remover_testemunhas.py --dry-run          # só conta
    scripts/remover_testemunhas.py                    # remove, com cópia antes
    scripts/remover_testemunhas.py --catalogo ~/teste

A cópia de segurança é feita antes de qualquer escrita e o script para se ela
falhar. Para desfazer: troque o catálogo pela cópia, ou rode
`scan --reprocessar` — as miniaturas voltam a ser catalogadas se a fonte da
biblioteca ainda estiver ativa.
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

# Tabelas que apontam para media_files, na ordem em que precisam sair.
# `suggestion_evidence` é ponte e sai antes das duas pontas.
_DEPENDENTES = (
    "metadata_entries", "evidence", "suggestions", "duplicate_members",
    "operation_items", "media_tags", "face_occurrences",
)

_ALVO = """
    caminho like '%.photoslibrary%'
    or (papel = 'SINAL' and arquivo_ausente = 0
        and caminho not like '%.photoslibrary%')
"""


def _contar(con: sqlite3.Connection) -> dict[str, int]:
    def n(sql: str, *args) -> int:
        return con.execute(sql, args).fetchone()[0]

    return {
        "alvo": n(f"select count(*) from media_files where {_ALVO}"),
        "total": n("select count(*) from media_files"),
        "acervo": n("select count(*) from media_files where papel='ACERVO'"),
        "referencias": n(
            "select count(*) from media_files where arquivo_ausente=1"
        ),
        "metadados": n("select count(*) from metadata_entries"),
        "albuns": n(
            "select count(*) from metadata_entries "
            "where namespace='apple' and chave='album'"
        ),
        "com_lugar": n(
            "select count(*) from media_files "
            "where papel='ACERVO' and gps_lat_estimado is not null"
        ),
    }


def _copiar(db: Path) -> Path:
    carimbo = datetime.now(timezone.utc).astimezone().strftime("%Y%m%d-%H%M%S")
    destino = db.with_name(f"{db.stem}-antes-da-limpeza-{carimbo}.db")
    if shutil.which("sqlite3"):
        # .backup respeita transação em curso; cp de um WAL aberto pode
        # copiar um arquivo inconsistente.
        subprocess.run(
            ["sqlite3", str(db), f".backup '{destino}'"], check=True
        )
    else:
        shutil.copy2(db, destino)
    if not destino.is_file():
        raise SystemExit("não consegui copiar o catálogo — nada foi removido")
    return destino


def remover(con: sqlite3.Connection) -> None:
    con.execute("pragma foreign_keys = off")
    con.execute("begin")
    con.execute(
        f"create temp table alvo as select id from media_files where {_ALVO}"
    )
    # Quem herdou lugar de uma doadora que vai sumir perde a estimativa: sem
    # isto sobraria uma coordenada órfã, apontando para um id inexistente.
    con.execute(
        "update media_files set gps_lat_estimado=null, gps_lon_estimado=null,"
        " gps_estimado_de_id=null, gps_estimado_delta_s=null"
        " where gps_estimado_de_id in (select id from alvo)"
    )
    con.execute(
        "delete from suggestion_evidence where suggestion_id in"
        "   (select id from suggestions where media_id in (select id from alvo))"
        " or evidence_id in"
        "   (select id from evidence where media_id in (select id from alvo))"
    )
    for tabela in _DEPENDENTES:
        con.execute(
            f"delete from {tabela} where media_id in (select id from alvo)"
        )
    con.execute("delete from media_files where id in (select id from alvo)")
    con.commit()

    violacoes = con.execute("pragma foreign_key_check").fetchall()
    if violacoes:
        raise SystemExit(
            f"{len(violacoes)} referências órfãs após a remoção — "
            "restaure a cópia de segurança"
        )
    con.execute("vacuum")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--catalogo", type=Path, default=None)
    ap.add_argument("--dry-run", action="store_true",
                    help="conta o que sairia e não escreve nada")
    args = ap.parse_args()

    db = paths.default_db_path(args.catalogo)
    if not db.is_file():
        print(f"catálogo não encontrado: {db}")
        return 1

    con = sqlite3.connect(db)
    antes = _contar(con)
    mb = db.stat().st_size / 1048576
    print(f"catálogo: {db}  ({mb:.0f} MB)")
    print(f"  linhas             {antes['total']:>8}")
    print(f"  a remover          {antes['alvo']:>8}")
    print(f"  acervo (fica)      {antes['acervo']:>8}")
    print(f"  referências (fica) {antes['referencias']:>8}")
    print(f"  fotos com lugar    {antes['com_lugar']:>8}")

    if args.dry_run:
        print("\n--dry-run: nada foi alterado.")
        return 0
    if antes["alvo"] == 0:
        print("\nnada a remover.")
        return 0

    con.close()
    copia = _copiar(db)
    print(f"\ncópia de segurança: {copia.name}")

    con = sqlite3.connect(db)
    remover(con)
    depois = _contar(con)
    con.close()

    mb2 = db.stat().st_size / 1048576
    print(f"\nremovidas {antes['alvo']} testemunhas.")
    print(f"  linhas          {antes['total']:>8} → {depois['total']}")
    print(f"  acervo          {antes['acervo']:>8} → {depois['acervo']}")
    print(f"  referências     {antes['referencias']:>8} → {depois['referencias']}")
    print(f"  álbuns          {antes['albuns']:>8} → {depois['albuns']}")
    print(f"  fotos com lugar {antes['com_lugar']:>8} → {depois['com_lugar']}")
    print(f"  tamanho         {mb:>8.0f} MB → {mb2:.0f} MB")
    if depois["acervo"] != antes["acervo"]:
        print("\n  ATENÇÃO: o acervo mudou de tamanho — não deveria.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
