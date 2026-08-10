#!/usr/bin/env python3
"""Confere se o catálogo ainda descreve os arquivos que existem no disco.

SOMENTE LEITURA: abre o catálogo em modo `ro` e os arquivos para leitura.
Nada é escrito, movido ou apagado — o script relata, quem decide é você.

É a rede de segurança do invariante 3 ("verificar hash antes e depois de cada
cópia"): ela protege o momento da cópia, e nada até aqui protegia o intervalo
entre as cópias. Três perguntas, em ordem de gravidade:

1. **Conteúdo mudou sem o filesystem avisar.** Mesmo tamanho, mesmo mtime, e
   hash diferente. É o caso que ninguém percebe: o scanner pula o arquivo
   justamente porque tamanho e mtime batem, então a divergência nunca
   apareceria sozinha. Causas reais: bit rot em disco antigo, sincronização
   que sobrescreveu, cópia interrompida.

2. **Registro sem arquivo.** Já coberto em produção por `arquivo_offline` e
   `scanner/reconciliacao.py`; aqui entra para fechar a conta e para pegar o
   que a reconciliação ainda não visitou.

3. **Arquivo sem registro.** Está dentro de uma fonte conhecida e o catálogo
   não sabe dele — um scan resolve, e o script diz quantos são para você
   decidir se vale.

O padrão é amostrar, não varrer: recalcular a assinatura de 100 mil arquivos
lê cada um deles. `--tudo` faz a varredura completa quando você quiser pagar
o preço.

Uso:
    python scripts/verificar_integridade.py
    python scripts/verificar_integridade.py --amostra 5000
    python scripts/verificar_integridade.py --tudo --fonte 3
"""

from __future__ import annotations

import argparse
import random
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fotoorganizer.config.paths import default_db_path  # noqa: E402
from fotoorganizer.security.hashing import quick_signature  # noqa: E402


def _linha(rotulo: str, valor, nota: str = "") -> None:
    print(f"  {rotulo:<44} {valor:>10}  {nota}")


def _titulo(texto: str) -> None:
    print(f"\n{'=' * 72}\n{texto}\n{'=' * 72}")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--catalogo", type=Path, default=None)
    p.add_argument("--fonte", type=int, default=None,
                   help="limita a uma fonte (id)")
    p.add_argument("--amostra", type=int, default=2000,
                   help="quantos arquivos conferir (padrão 2000)")
    p.add_argument("--tudo", action="store_true",
                   help="confere todos — lê o acervo inteiro do disco")
    p.add_argument("--semente", type=int, default=20260810,
                   help="semente da amostra, para a rodada ser repetível")
    args = p.parse_args()

    caminho = (args.catalogo or default_db_path()).expanduser()
    if not caminho.is_file():
        print(f"catálogo não encontrado: {caminho}")
        return 1
    print(f"catálogo: {caminho}  (somente leitura)")

    con = sqlite3.connect(f"file:{caminho}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        filtro = "and m.source_id = ?" if args.fonte else ""
        params = (args.fonte,) if args.fonte else ()

        # Só o que tem arquivo local de verdade: referência de nuvem não tem
        # o que conferir, e testemunha idem.
        linhas = con.execute(f"""
            select m.id, m.caminho, m.tamanho, m.hash_rapido, m.arquivo_offline
            from media_files m
            where m.arquivo_ausente = 0 and m.hash_rapido is not null {filtro}
        """, params).fetchall()

        total = len(linhas)
        alvo = linhas
        if not args.tudo and total > args.amostra:
            alvo = random.Random(args.semente).sample(linhas, args.amostra)

        _titulo("1. O conteúdo mudou sem o filesystem avisar?")
        print(f"  conferindo {len(alvo)} de {total} registros com arquivo"
              f"{' (amostra)' if len(alvo) < total else ''}\n")

        divergentes: list[tuple[str, str, str]] = []
        sumidos: list[str] = []
        ilegiveis: list[tuple[str, str]] = []
        conferidos = 0
        for linha in alvo:
            arquivo = Path(linha["caminho"])
            try:
                if not arquivo.is_file():
                    sumidos.append(linha["caminho"])
                    continue
                atual = quick_signature(arquivo)
            except OSError as exc:
                ilegiveis.append((linha["caminho"], str(exc)))
                continue
            conferidos += 1
            if atual != linha["hash_rapido"]:
                divergentes.append((linha["caminho"], linha["hash_rapido"], atual))

        _linha("conferidos", conferidos)
        _linha("CONTEÚDO DIVERGENTE", len(divergentes),
               "<-- o arquivo mudou" if divergentes else "nenhum")
        _linha("sumidos do disco", len(sumidos),
               "esperado se o volume está fora" if sumidos else "")
        _linha("ilegíveis (permissão, I/O)", len(ilegiveis))

        if divergentes:
            print("\n  Os arquivos abaixo não são mais o que o catálogo diz:")
            for caminho_arq, antes, agora in divergentes[:20]:
                print(f"    {caminho_arq}")
                print(f"      catálogo: {antes}")
                print(f"      disco:    {agora}")
            if len(divergentes) > 20:
                print(f"    … e mais {len(divergentes) - 20}.")
            print("\n  O que fazer: `scan --reprocessar` sobre a fonte devolve")
            print("  o catálogo à realidade. Se você NÃO editou esses arquivos,")
            print("  isto é corrupção silenciosa — confira o backup antes.")

        if ilegiveis:
            print("\n  Ilegíveis:")
            for caminho_arq, erro in ilegiveis[:10]:
                print(f"    {caminho_arq} — {erro}")

        _titulo("2. Registro sem arquivo")
        marcados = con.execute(f"""
            select count(*) from media_files m
            where m.arquivo_offline = 1 and m.arquivo_ausente = 0 {filtro}
        """, params).fetchone()[0]
        _linha("já marcados como offline", marcados,
               "o app sabe; reconciliacao.py cuida")
        _linha("sumidos e ainda NÃO marcados", len(sumidos),
               "<-- o próximo scan marca" if sumidos else "")

        _titulo("3. Arquivo no disco sem registro")
        print("  Comparar disco × catálogo por fonte exige varrer as pastas —")
        print("  é o que o scan faz. Aqui fica só a conta que o catálogo sabe:\n")
        for fonte in con.execute("""
            select s.id, s.apelido, s.caminho, s.disponivel,
                   count(m.id) as registros
            from sources s left join media_files m on m.source_id = s.id
            group by s.id order by count(m.id) desc
        """):
            estado = "" if fonte["disponivel"] else "  (fora de alcance)"
            _linha(f"{fonte['apelido'] or fonte['caminho']}",
                   fonte["registros"], estado)
        print("\n  Rode `scan` na fonte para descobrir o que está no disco e")
        print("  não está aqui — o scan é incremental e pula o que não mudou.")
    finally:
        con.close()
    print()
    return 2 if divergentes else 0


if __name__ == "__main__":
    sys.exit(main())
