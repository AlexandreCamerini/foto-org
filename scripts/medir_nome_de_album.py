#!/usr/bin/env python3
"""Mede o que a nomeação por álbum muda no acervo real.

O catálogo original é aberto SOMENTE LEITURA; a regeneração roda sobre uma
CÓPIA em pasta temporária, que é apagada no fim. Nenhum arquivo de foto é
tocado (invariante 1 do CLAUDE.md).

Três medições, porque as três respondem perguntas diferentes:

  1. GANHO HOJE — regenera as sugestões na cópia e compara os nomes de
     `trips`/`events` com os que o catálogo já tinha. É o número honesto de
     "quantas viagens/eventos ganharam nome melhor" agora.
  2. GANHO BLOQUEADO — o mesmo, mas contando os períodos que TÊM álbum
     aproveitável e não têm sessão nenhuma, porque as fotos que carregam a
     nomeação não são acervo alcançável (D-028: 44.661 registros do Apple
     Fotos sem arquivo local). Mede o que a ligação entrega no dia em que
     esses arquivos forem alcançados, sem prometer que ela entrega hoje.
  3. DESEMPATE — para cada período com mais de um álbum aprovado, mostra o
     escolhido e o que cada critério alternativo escolheria. É o dado que
     sustenta (ou derruba) a ordem de `escolher_album`.

Uso:
    .venv/bin/python scripts/medir_nome_de_album.py
    .venv/bin/python scripts/medir_nome_de_album.py --db <catalog.db>
    .venv/bin/python scripts/medir_nome_de_album.py --sem-regenerar
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
import tempfile
from collections import Counter
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fotoorganizer.config import paths  # noqa: E402
from fotoorganizer.grouping.albuns import (  # noqa: E402
    MIN_FOTOS_ALBUM,
    album_nomeia,
    cameras_do_catalogo,
    escolher_album,
)
from fotoorganizer.grouping.datas import separar_data  # noqa: E402
from fotoorganizer.grouping.eventos import extrair_evento  # noqa: E402
from fotoorganizer.grouping.temporal import agrupar_viagens  # noqa: E402


def _abrir(db: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{db}?immutable=1", uri=True)


def _grupos(con: sqlite3.Connection) -> dict[tuple[str, str], tuple[str, int]]:
    """{(tipo, período): (nome, fotos)} das viagens e eventos persistidos."""
    saida: dict[tuple[str, str], tuple[str, int]] = {}
    for tabela, tipo in (("trips", "viagem"), ("events", "evento")):
        for nome, inicio, fim, n in con.execute(
            f"select g.nome, g.inicio, g.fim, "
            f"(select count(*) from media_files m "
            f" where m.{'trip' if tipo == 'viagem' else 'event'}_id = g.id) "
            f"from {tabela} g"
        ):
            saida[(tipo, f"{inicio}→{fim}")] = (nome, n)
    return saida


def _albuns_por_media(con: sqlite3.Connection):
    por_media: dict[int, tuple[datetime, list[str]]] = {}
    for mid, quando, album in con.execute(
        "select m.id, coalesce(m.data_capturada, m.mtime), e.valor "
        "from metadata_entries e join media_files m on m.id = e.media_id "
        "where e.chave = 'album' "
        "  and coalesce(m.data_capturada, m.mtime) is not null "
        "  and e.valor is not null"
    ):
        entrada = por_media.setdefault(mid, (datetime.fromisoformat(quando), []))
        entrada[1].append(album)
    return por_media


def _cameras(con: sqlite3.Connection) -> frozenset[str]:
    return cameras_do_catalogo(
        con.execute(
            "select distinct make, model from media_files "
            "where model is not null"
        )
    )


# -- 1. ganho hoje ---------------------------------------------------------
def regenerar(origem: Path) -> dict[tuple[str, str], tuple[str, int]]:
    """Roda o motor sobre uma cópia e devolve os grupos resultantes."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from fotoorganizer.classification import SuggestionEngine
    from fotoorganizer.geolocation import LocationResolver
    from fotoorganizer.geolocation.offline import OfflineGeocoder

    with tempfile.TemporaryDirectory(prefix="medir-album-") as tmp:
        copia = Path(tmp) / "catalog.db"
        # `backup` e não cópia de arquivo: o catálogo roda em WAL, e copiar
        # só o .db deixaria de fora o que ainda está no journal.
        origem_con = sqlite3.connect(f"file:{origem}?mode=ro", uri=True)
        destino_con = sqlite3.connect(copia)
        with destino_con:
            origem_con.backup(destino_con)
        origem_con.close()
        destino_con.close()
        engine = create_engine(f"sqlite:///{copia}")
        SuggestionEngine(
            sessionmaker(engine), LocationResolver(OfflineGeocoder())
        ).gerar()
        engine.dispose()
        con = sqlite3.connect(copia)
        try:
            return _grupos(con)
        finally:
            con.close()


# -- 2 e 3. períodos de álbum ---------------------------------------------
def periodos(con: sqlite3.Connection):
    """Agrupa por lacuna temporal as fotos que carregam nomeação de álbum.

    Usa o MESMO gap do agrupamento de sessões (`agrupar_viagens`), para que
    cada período seja comparável a uma sessão que existiria se essas fotos
    fossem acervo alcançável.
    """
    por_media = _albuns_por_media(con)
    pastas = dict(con.execute(
        "select m.id, m.pasta from media_files m "
        "where exists (select 1 from metadata_entries e "
        "              where e.media_id = m.id and e.chave = 'album')"
    ))
    clusters = agrupar_viagens([(mid, v[0]) for mid, v in por_media.items()])
    for cluster in clusters:
        contagem: Counter = Counter()
        for mid in cluster.media_ids:
            for album in por_media[mid][1]:
                contagem[album] += 1
        nome_de_pasta = next(
            (n for mid in cluster.media_ids
             if (n := extrair_evento([pastas.get(mid) or ""])[0])),
            None,
        )
        yield cluster, contagem, nome_de_pasta


def _criterios(contagem: Counter, cameras: frozenset[str]) -> dict[str, str]:
    """O que cada critério alternativo escolheria, para comparação."""
    aprovados: dict[str, int] = {}
    for bruto, n in contagem.items():
        if n < MIN_FOTOS_ALBUM or not album_nomeia(bruto, cameras):
            continue
        nome = separar_data(bruto)[0].strip()
        if nome and album_nomeia(nome, cameras):
            aprovados[nome] = max(aprovados.get(nome, 0), n)
    if not aprovados:
        return {}
    escolhido = escolher_album(contagem, cameras)
    return {
        "regra": escolhido[0] if escolhido else "—",
        "mais frequente": max(aprovados, key=lambda k: (aprovados[k], -len(k))),
        "menos frequente": min(aprovados, key=lambda k: (aprovados[k], len(k))),
        "nome mais longo": max(aprovados, key=len),
        "_n": len(aprovados),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=paths.default_db_path())
    parser.add_argument("--sem-regenerar", action="store_true",
                        help="pula a medição 1 (que é a demorada)")
    args = parser.parse_args()

    con = _abrir(args.db)
    cameras = _cameras(con)
    antes = _grupos(con)

    print(f"catálogo: {args.db}")
    print(f"câmeras conhecidas: {len(cameras)}")
    total_album = con.execute(
        "select count(*) from metadata_entries where chave = 'album'"
    ).fetchone()[0]
    em_acervo = con.execute(
        "select count(distinct m.id) from media_files m "
        "join metadata_entries e on e.media_id = m.id and e.chave = 'album' "
        "where m.papel = 'ACERVO' and m.arquivo_ausente = 0"
    ).fetchone()[0]
    print(f"marcações de álbum: {total_album}; em foto organizável: {em_acervo}")

    # 1 ------------------------------------------------------------------
    if not args.sem_regenerar:
        print("\n== 1. ganho hoje (regeneração numa cópia) ==")
        depois = regenerar(args.db)
        mudaram = []
        for chave, (nome, n) in sorted(depois.items()):
            velho = antes.get(chave)
            if velho is not None and velho[0] != nome:
                mudaram.append((chave, velho[0], nome, n))
        print(f"grupos antes: {len(antes)}; depois: {len(depois)}; "
              f"com nome diferente: {len(mudaram)}")
        for (tipo, periodo), velho, novo, n in mudaram:
            print(f"  {tipo} {periodo} ({n} fotos): '{velho}' → '{novo}'")

    # 2 e 3 ---------------------------------------------------------------
    print("\n== 2/3. períodos com nomeação de álbum ==")
    com_candidato = 0
    com_disputa = 0
    so_album = 0
    fotos_cobertas = 0
    fotos_so_album = 0
    divergencias = []
    for cluster, contagem, nome_de_pasta in periodos(con):
        criterios = _criterios(contagem, cameras)
        if not criterios:
            continue
        com_candidato += 1
        fotos_cobertas += cluster.n_fotos
        if nome_de_pasta is None:
            so_album += 1
            fotos_so_album += cluster.n_fotos
        if criterios["_n"] > 1:
            com_disputa += 1
            print(f"\n  {cluster.inicio:%Y-%m-%d} → {cluster.fim:%Y-%m-%d} "
                  f"({cluster.n_fotos} fotos)")
            for rotulo in ("regra", "mais frequente", "menos frequente",
                           "nome mais longo"):
                print(f"      {rotulo:>16}: {criterios[rotulo]}")
            if criterios["regra"] != criterios["mais frequente"]:
                divergencias.append(
                    (f"{cluster.inicio:%Y-%m-%d}", criterios["mais frequente"],
                     criterios["regra"])
                )

    print(f"\n  períodos com álbum aproveitável: {com_candidato}")
    print(f"  deles, com mais de um candidato: {com_disputa}")
    print(f"  deles, SEM nome de pasta (só o álbum nomeia): {so_album}")
    print(f"  fotos nesses períodos: {fotos_cobertas} "
          f"(só o álbum nomeia: {fotos_so_album})")
    if divergencias:
        print("  onde a regra diverge de 'mais frequente':")
        for dia, freq, regra in divergencias:
            print(f"    {dia}: '{freq}' (frequência) → '{regra}' (regra)")
    con.close()


if __name__ == "__main__":
    main()
