#!/usr/bin/env python
"""Rebaixa a fonte de sinal o que está marcado como acervo e não é.

O acervo é a foto do dono. O catálogo real acumulou três famílias que não
são, e que entraram porque a varredura desceu por onde não devia:

- **Smart Previews do Lightroom** (`… Smart Previews.lrdata/`): 14.755 DNG
  de pré-visualização, 100% ilegíveis (`LibRawFileUnsupportedError`, porque
  não são RAW de verdade). Eram 57% de tudo que o app dizia ser
  organizável, e são os mesmos 14.755 do contador de erros do rodapé.
- **Cache de aplicativo** (`…/Cache/…`, na prática o CapCut): 1.840
  texturas de efeito, sem GPS, sem câmera.
- **Saída do próprio app** (a pasta de destino de um plano de cópia): 143
  arquivos com o mesmo `hash_rapido` dos originais. O resultado do app
  virou entrada do app.

**Nada é removido** — só `papel` muda de `ACERVO` para `SINAL`
(invariante 8 do CLAUDE.md e D-024). O registro sai da grade, da revisão e
do plano de cópia, e continua no banco doando data, GPS e correlação. Isso
importa aqui: os Smart Previews carregam 1.113 coordenadas. Hoje elas são
inertes (a herança de D-025 casa por tempo, e esses registros não têm
data), mas apagá-las seria destruir sinal que não se recupera.

O portão para o futuro é outro arquivo: `fotoorganizer/scanner/discovery.py`
(`.lrdata` em `SUFIXOS_DE_PACOTE`, `cache` em `PASTAS_DE_CODIGO`). Sem ele,
a próxima varredura desfaz este rebaixamento — foi o que aconteceu com
`remover_testemunhas.py`, cuja poda de 45.822 miniaturas foi revertida pela
varredura seguinte da home (D-035).

Uso:
    scripts/rebaixar_nao_acervo.py                 # só conta, não escreve
    scripts/rebaixar_nao_acervo.py --aplicar       # cópia de segurança + UPDATE
    scripts/rebaixar_nao_acervo.py --catalogo ~/x

Para desfazer: troque o catálogo pela cópia de segurança que o `--aplicar`
grava ao lado, ou rode o UPDATE inverso — os ids afetados vão para
`rebaixados-<carimbo>.txt`, na mesma pasta.
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

# Cada família com o predicado que a identifica no catálogo. A ordem é a de
# exibição; os predicados são exclusivos entre si na prática, mas o UPDATE
# usa o OR de todos, então sobreposição não contaria duas vezes.
FAMILIAS: tuple[tuple[str, str], ...] = (
    ("Smart Previews do Lightroom", "caminho like '%.lrdata/%'"),
    ("cache de aplicativo", "caminho like '%/Cache/%' or caminho like '%/Caches/%'"),
    ("saída do próprio app", "caminho like '%FotoOrganizer-Teste%'"),
)

_ALVO = " or ".join(f"({p})" for _, p in FAMILIAS)


def _contar(con: sqlite3.Connection) -> dict[str, int]:
    def n(sql: str) -> int:
        return con.execute(sql).fetchone()[0]

    return {
        "acervo": n("select count(*) from media_files where papel='ACERVO'"),
        "sinal": n("select count(*) from media_files where papel='SINAL'"),
        "total": n("select count(*) from media_files"),
        "alvo": n(
            f"select count(*) from media_files where papel='ACERVO' and ({_ALVO})"
        ),
        "erros": n(
            "select count(*) from media_files "
            "where papel='ACERVO' and erro_leitura is not null"
        ),
    }


def _copiar(db: Path) -> Path:
    carimbo = datetime.now(timezone.utc).astimezone().strftime("%Y%m%d-%H%M%S")
    destino = db.with_name(f"{db.stem}-antes-do-rebaixamento-{carimbo}.db")
    if shutil.which("sqlite3"):
        # .backup respeita transação em curso; copiar um WAL aberto com cp
        # pode gravar um arquivo inconsistente.
        subprocess.run(["sqlite3", str(db), f".backup '{destino}'"], check=True)
    else:
        shutil.copy2(db, destino)
    if not destino.is_file():
        raise SystemExit("não consegui copiar o catálogo — nada foi alterado")
    return destino


def _scans_orfaos(con: sqlite3.Connection) -> list[tuple]:
    """Varreduras que dizem estar rodando e não têm processo por trás.

    Ninguém as fecha: o app só escreve `finalizado_em` no fim do job, e um
    encerramento abrupto deixa a linha em RODANDO para sempre. O efeito
    visível é a UI achar que há trabalho em andamento.
    """
    return con.execute(
        "select id, source_id, iniciado_em, arquivos_indexados "
        "from scan_sessions where status='RODANDO' order by id"
    ).fetchall()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--catalogo", type=Path, default=None)
    ap.add_argument("--aplicar", action="store_true",
                    help="escreve; sem isto o script só conta")
    args = ap.parse_args()

    db = paths.default_db_path(args.catalogo)
    if not db.is_file():
        print(f"catálogo não encontrado: {db}")
        return 1

    con = sqlite3.connect(db)
    antes = _contar(con)
    print(f"catálogo: {db}")
    print(f"  registros          {antes['total']:>8,}")
    print(f"  acervo             {antes['acervo']:>8,}")
    print(f"  sinal              {antes['sinal']:>8,}")
    print()
    print("a rebaixar (acervo → sinal), por família:")
    for rotulo, pred in FAMILIAS:
        n = con.execute(
            f"select count(*) from media_files where papel='ACERVO' and ({pred})"
        ).fetchone()[0]
        print(f"  {n:>8,}  {rotulo}")
    print(f"  {antes['alvo']:>8,}  TOTAL")
    print(f"\n  acervo depois:     {antes['acervo'] - antes['alvo']:>8,}")

    orfaos = _scans_orfaos(con)
    if orfaos:
        print("\nvarreduras presas em RODANDO (serão fechadas):")
        for sid, source_id, inicio, indexados in orfaos:
            print(f"  scan {sid} · fonte {source_id} · desde {inicio} "
                  f"· {indexados:,} indexados")

    if not args.aplicar:
        print("\nsem --aplicar: nada foi alterado.")
        return 0
    if antes["alvo"] == 0 and not orfaos:
        print("\nnada a fazer.")
        return 0

    con.close()
    copia = _copiar(db)
    print(f"\ncópia de segurança: {copia.name}")

    con = sqlite3.connect(db)
    ids = [r[0] for r in con.execute(
        f"select id from media_files where papel='ACERVO' and ({_ALVO})"
    )]
    if ids:
        lista = db.with_name(f"rebaixados-{copia.stem.split('-')[-1]}.txt")
        lista.write_text("\n".join(map(str, ids)), encoding="utf-8")
        print(f"ids afetados:       {lista.name}")

    con.execute("begin")
    con.execute(
        f"update media_files set papel='SINAL' where papel='ACERVO' and ({_ALVO})"
    )
    for sid, *_ in orfaos:
        # PAUSADO, não CONCLUIDO nem ERRO: a varredura tem checkpoint e
        # parou sem falhar — dizer "concluído" mentiria sobre o que foi
        # visto, e "erro" inventaria uma falha que não houve. É o mesmo
        # estado das outras quatro varreduras pausadas do catálogo, e o
        # único do enum que descreve "parou e dá para retomar".
        con.execute(
            "update scan_sessions set status='PAUSADO', finalizado_em=? "
            "where id=?",
            (datetime.now().replace(microsecond=0).isoformat(sep=" "), sid),
        )
    con.commit()

    violacoes = con.execute("pragma foreign_key_check").fetchall()
    if violacoes:
        raise SystemExit(
            f"{len(violacoes)} referências órfãs — restaure a cópia de segurança"
        )

    depois = _contar(con)
    con.close()
    print()
    print(f"  acervo   {antes['acervo']:>8,} → {depois['acervo']:,}")
    print(f"  sinal    {antes['sinal']:>8,} → {depois['sinal']:,}")
    print(f"  erros    {antes['erros']:>8,} → {depois['erros']:,}")
    if depois["total"] != antes["total"]:
        print("\n  ATENÇÃO: o total mudou — nenhuma linha deveria ter saído.")
        return 1
    print(f"  registros {antes['total']:>7,} → {depois['total']:,}  (nenhum removido)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
