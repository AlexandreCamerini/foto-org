#!/usr/bin/env python3
"""Mede o tamanho do empilhamento de capturas irmãs (RAW+JPEG do mesmo
clique) no acervo real — a medição que D-042 (`docs/DECISOES.md`) registra
como pré-requisito antes de reavaliar esse item do §7.1 da fase 14
(`docs/prompts/fase-14-photoprism-e-sintese.md`).

Somente leitura: o catálogo é aberto com `mode=ro` via URI SQLite, nenhuma
escrita acontece. Não precisa de pixel nem de volume montado — a medição é
inteiramente sobre metadados já indexados (`data_capturada`, `make`,
`model`, `extensao`), coerente com a nota de D-042 ("roda sobre o catálogo
atual, somente leitura").

Critério: linhas de `papel='ACERVO'` que compartilham a MESMA
`(source_id, data_capturada, make, model)` mas têm `extensao` diferente —
mesma câmera, mesmo instante, formatos diferentes é o sinal de "duas
codificações do mesmo disparo" (D-042). Falso positivo possível: duas
fotos de verdade tiradas no mesmo segundo pela mesma câmera (rajada com
resolução de tempo de 1s no metadado) — o script reporta os pares de
extensão encontrados para quem for revisar poder distinguir esse caso de
um RAW+JPEG genuíno.

Uso:
    .venv/bin/python scripts/medir_capturas_irmas.py
    .venv/bin/python scripts/medir_capturas_irmas.py --db <catalog.db>
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fotoorganizer.config import paths  # noqa: E402


def _abrir(db: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{db}?immutable=1", uri=True)


def _grupos_com_extensao_divergente(con: sqlite3.Connection):
    """(source_id, data_capturada, make, model) com mais de uma extensão
    entre as fotos do acervo (papel='ACERVO') que compartilham os quatro.

    `data_capturada is not null` e `(make is not null or model is not
    null)` seguem o critério do D-042 ao pé da letra: "mesma data_capturada
    e a mesma câmera" — sem os dois, não há como afirmar "mesmo disparo".
    """
    return con.execute(
        """
        select source_id, data_capturada, make, model,
               group_concat(distinct extensao) as extensoes,
               count(*) as n_arquivos
          from media_files
         where papel = 'ACERVO'
           and data_capturada is not null
           and (make is not null or model is not null)
         group by source_id, data_capturada, make, model
        having count(distinct extensao) > 1
        """
    ).fetchall()


def _fontes(con: sqlite3.Connection) -> dict[int, str]:
    return {
        sid: (apelido or caminho)
        for sid, apelido, caminho in con.execute(
            "select id, apelido, caminho from sources"
        )
    }


def _total_acervo(con: sqlite3.Connection) -> int:
    return con.execute(
        "select count(*) from media_files where papel = 'ACERVO'"
    ).fetchone()[0]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=paths.default_db_path())
    args = parser.parse_args()

    if not args.db.is_file():
        raise SystemExit(f"catálogo não encontrado: {args.db}")

    con = _abrir(args.db)
    try:
        total_acervo = _total_acervo(con)
        fontes = _fontes(con)
        grupos = _grupos_com_extensao_divergente(con)

        print(f"catálogo: {args.db}")
        print(f"total em papel='ACERVO': {total_acervo}")
        print()

        if not grupos:
            print("nenhum grupo com mesma data_capturada + mesma câmera + "
                  "extensão divergente — empilhamento de capturas irmãs "
                  "não é problema mensurável neste acervo hoje.")
            return

        n_grupos = len(grupos)
        n_fotos = sum(n for *_resto, n in grupos)
        pares_extensao: Counter[str] = Counter()
        por_fonte: Counter[str] = Counter()
        fotos_por_fonte: Counter[str] = Counter()

        for source_id, _data, _make, _model, extensoes, n in grupos:
            par = "+".join(sorted(extensoes.split(",")))
            pares_extensao[par] += 1
            nome_fonte = fontes.get(source_id, f"fonte #{source_id}")
            por_fonte[nome_fonte] += 1
            fotos_por_fonte[nome_fonte] += n

        print(f"grupos candidatos a captura irmã: {n_grupos}")
        print(f"fotos envolvidas: {n_fotos} "
              f"({100 * n_fotos / total_acervo:.2f}% do acervo organizável)")

        print("\ncombinações de extensão encontradas (grupos):")
        for par, n in pares_extensao.most_common():
            print(f"  {par}: {n}")

        print("\npor fonte (grupos / fotos envolvidas):")
        for nome_fonte, n in por_fonte.most_common():
            print(f"  {nome_fonte}: {n} grupos / {fotos_por_fonte[nome_fonte]} fotos")
    finally:
        con.close()


if __name__ == "__main__":
    main()
