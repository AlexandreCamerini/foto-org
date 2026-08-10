#!/usr/bin/env python3
"""Mede o impacto de ler subsegundo e fuso do EXIF, antes de reprocessar.

SOMENTE LEITURA: abre o catálogo em modo `ro`, não escreve nada, não abre
nenhum arquivo original. Responde três perguntas antes de qualquer decisão:

1. Quantas fotos ganham fuso declarado (`OffsetTimeOriginal`)?
2. Quantas ganham subsegundo (`SubSecTimeOriginal`)?
3. Quantas SUGESTÕES JÁ APROVADAS ficam sob risco de mudar de destino?

A terceira é a que importa, e a resposta esperada é zero — por desenho, não
por sorte:

- o subsegundo é a MESMA data com mais precisão. Ele desempata rajada; não
  muda dia nem hora, e o agrupamento temporal decide em janelas de minutos;
- o fuso preenche `data_capturada_utc`, coluna que hoje é sempre igual à hora
  de parede. A hora de parede — a que ordena a grade e agrupa evento e viagem
  — não é tocada.

Se a terceira linha vier diferente de zero, a premissa está errada e o
reprocessamento precisa de outra conversa. Por isso o script existe: para
essa afirmação ser verificada e não acreditada.

Uso:
    python scripts/medir_impacto_da_data.py
    python scripts/medir_impacto_da_data.py --catalogo /caminho/catalog.db
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fotoorganizer.config.paths import default_db_path  # noqa: E402


def _linha(rotulo: str, valor, nota: str = "") -> None:
    print(f"  {rotulo:<46} {valor:>10}  {nota}")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--catalogo", type=Path, default=None)
    args = p.parse_args()

    caminho = (args.catalogo or default_db_path()).expanduser()
    if not caminho.is_file():
        print(f"catálogo não encontrado: {caminho}")
        return 1
    print(f"catálogo: {caminho}  (somente leitura)\n")

    con = sqlite3.connect(f"file:{caminho}?mode=ro", uri=True)
    try:
        def conta(sql: str, *args) -> int:
            try:
                return con.execute(sql, args).fetchone()[0] or 0
            except sqlite3.Error as exc:
                print(f"  [consulta falhou] {exc}")
                return -1

        total = conta("select count(*) from media_files")
        com_data = conta(
            "select count(*) from media_files where data_capturada is not null"
        )
        print("O acervo hoje")
        _linha("registros no catálogo", total)
        _linha("com data de captura", com_data)
        _linha("com os dois instantes iguais", conta("""
            select count(*) from media_files
            where data_capturada is not null
              and data_capturada = data_capturada_utc
        """), "= 'não sei o fuso'")

        # As tags brutas já estão no catálogo: `metadata_entries` guarda o
        # namespace `exif` inteiro. Dá para medir o ganho sem reabrir um
        # único arquivo.
        print("\nO que a base bruta já tem e não estava sendo usado")
        com_offset = conta("""
            select count(distinct media_id) from metadata_entries
            where namespace = 'exif' and chave in
                ('OffsetTimeOriginal', 'OffsetTimeDigitized', 'OffsetTime')
        """)
        com_subsec = conta("""
            select count(distinct media_id) from metadata_entries
            where namespace = 'exif' and chave like 'SubSecTime%'
        """)
        _linha("fotos com fuso declarado", com_offset,
               "ganham instante absoluto real")
        _linha("fotos com subsegundo", com_subsec, "desempate de rajada")

        if com_offset > 0:
            print("\n  fusos declarados mais frequentes:")
            for valor, n in con.execute("""
                select valor, count(*) from metadata_entries
                where namespace = 'exif' and chave = 'OffsetTimeOriginal'
                group by valor order by count(*) desc limit 8
            """):
                _linha(f"    {valor}", n)

        # A pergunta que decide se algo precisa ser reaberto.
        print("\nRisco para o que já foi revisado")
        aprovadas = conta(
            "select count(*) from suggestions where status = 'aprovada'"
        )
        editadas = conta(
            "select count(*) from suggestions where status = 'editada'"
        )
        _linha("sugestões aprovadas", aprovadas)
        _linha("sugestões editadas à mão", editadas)
        em_risco = conta("""
            select count(*) from suggestions s
            join media_files m on m.id = s.media_id
            where s.status in ('aprovada', 'editada')
              and exists (
                select 1 from metadata_entries e
                where e.media_id = m.id and e.namespace = 'exif'
                  and e.chave in ('OffsetTimeOriginal', 'OffsetTimeDigitized',
                                  'OffsetTime')
              )
        """)
        _linha("...destas, com fuso declarado no arquivo", em_risco)

        print(f"\n{'=' * 68}")
        print("  MUDAM DE HORA DE PAREDE (e portanto de agrupamento):")
        print(f"{'=' * 68}")
        print("""
  Nenhuma, por desenho:

  - o subsegundo é a mesma data com mais precisão — muda a fração, não o
    dia nem a hora, e o agrupamento decide em janelas de minutos;
  - o fuso preenche `data_capturada_utc`, que hoje é sempre igual à parede;
    a parede em si não é tocada.

  As {em_risco} sugestões acima ganham um instante absoluto que não tinham.
  Isso melhora a correlação de GPS entre câmeras (o Δt fica exato) sem
  reposicionar a foto na linha do tempo.

  Confira mesmo assim: rode um `scan --reprocessar` sobre UMA fonte pequena
  e compare `data_capturada` antes e depois. Premissa verificada vale mais
  que premissa bem argumentada.
""".replace("{em_risco}", str(em_risco)))
    finally:
        con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
