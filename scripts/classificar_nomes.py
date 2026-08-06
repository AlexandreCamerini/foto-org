#!/usr/bin/env python
"""Classifica os nomes de pasta e álbum do acervo: lugar, ocasião, pessoa ou ruído.

Por que existe: a cascata determinística sabe medir duração e distância, e
não tem como saber que "Pantanal" é um lugar aonde se viaja e "Quizomba" é
uma festa. Medido no acervo real, a regra 6 de `docs/AGRUPAMENTO.md` mandou
Pantanal (1d23h) e Visconde de Mauá (18 fotos) para Eventos — os dois são
destino de viagem.

**Privacidade (invariante 4).** Sai da máquina apenas a lista de PALAVRAS —
nunca imagem, caminho completo, data, coordenada ou contagem. O `--listar`
mostra exatamente o que sairia, sem enviar nada. Enviar exige
`--enviar` E `[privacidade] servicos_externos = true` no config.

O que já foi classificado nunca é reenviado, e correção manual do dono
(`--corrigir`) nunca é sobrescrita pela máquina.

Uso:
    scripts/classificar_nomes.py --listar         # o que sairia, sem enviar
    scripts/classificar_nomes.py --enviar         # classifica o que falta
    scripts/classificar_nomes.py --mostrar        # o que já está classificado
    scripts/classificar_nomes.py --corrigir "Pantanal=lugar"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from fotoorganizer.classification.lexico import (  # noqa: E402
    CATEGORIAS,
    LexicoClaude,
)
from fotoorganizer.config.settings import load_settings  # noqa: E402
from fotoorganizer.database.engine import (  # noqa: E402
    create_db_engine,
    create_session_factory,
)
from fotoorganizer.grouping.datas import separar_data  # noqa: E402
from fotoorganizer.grouping.eventos import extrair_evento, nome_de_album  # noqa: E402
from fotoorganizer.models import MediaFile, MetadataEntry  # noqa: E402
from fotoorganizer.repositories.lexico import LexicoRepository  # noqa: E402


def nomes_do_acervo(factory) -> set[str]:
    """Os nomes que a cascata realmente usa.

    Passa cada pasta por `extrair_evento` de propósito: é ele que tira a
    data ("Pantanal Jul.2023" → "Pantanal"), e a regra 6 decide com o nome
    já limpo. Classificar o segmento cru produziria um léxico que nunca
    casa com nada.

    Além do nome extraído, entra cada NÍVEL nomeável do caminho: a cascata
    consulta o léxico da folha à raiz ("Pantanal/Dia 2" pergunta pelos
    dois), e um nível que nunca foi oferecido à classificação é um nível
    em que o léxico nunca terá opinião. `nome_de_album` corta o técnico —
    sem ele voltaria o ruído dos 12.665 fragmentos.
    """
    nomes: set[str] = set()
    with factory() as session:
        # Só o acervo. Testemunha não vira sessão e não é nomeada — e as
        # pastas dela são fragmentos hexadecimais dos derivados
        # (".lrdata/0/000C", "derivatives/F"). Sem este filtro o acervo do
        # dono oferecia 12.665 "nomes" em vez da centena real.
        for (pasta,) in session.execute(
            select(MediaFile.pasta)
            .where(MediaFile.pasta != "", MediaFile.organizavel)
            .distinct()
        ):
            nome, _ = extrair_evento([pasta])
            if nome:
                nomes.add(nome)
            for segmento in pasta.split("/"):
                nivel, _data = separar_data(segmento)
                nivel = (nivel or "").strip()
                if nivel and nome_de_album(nivel):
                    nomes.add(nivel)
        for (album,) in session.execute(
            select(MetadataEntry.valor)
            .where(MetadataEntry.chave == "album")
            .distinct()
        ):
            if album:
                nomes.add(album)
    return nomes


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--catalogo", type=Path, default=None)
    ap.add_argument("--listar", action="store_true",
                    help="mostra o que sairia da máquina; não envia nada")
    ap.add_argument("--enviar", action="store_true",
                    help="classifica o que falta (exige servicos_externos)")
    ap.add_argument("--mostrar", action="store_true",
                    help="mostra o que já está classificado")
    ap.add_argument("--corrigir", metavar="NOME=CATEGORIA", action="append",
                    default=[], help="corrige à mão; nunca é sobrescrito")
    args = ap.parse_args()

    # `load_settings` e não `Settings()`: o construtor devolve os defaults e
    # ignora o config.toml — o opt-in de privacidade mora lá.
    settings = load_settings()
    if args.catalogo:
        from dataclasses import replace
        settings = replace(settings, data_dir=args.catalogo)
    factory = create_session_factory(create_db_engine(settings.db_path))
    repo = LexicoRepository(factory)

    if args.corrigir:
        pares = {}
        for item in args.corrigir:
            nome, _, categoria = item.partition("=")
            if categoria not in CATEGORIAS:
                print(f"categoria inválida: {categoria!r} "
                      f"(use uma de {', '.join(CATEGORIAS)})")
                return 1
            pares[nome] = categoria
        print(f"corrigidos {repo.salvar(pares, origem='manual')} nome(s).")
        return 0

    if args.mostrar:
        conhecidos = repo.conhecidos()
        print(f"{len(conhecidos)} nome(s) classificado(s):")
        for nome, categoria in sorted(conhecidos.items(), key=lambda kv: kv[1]):
            print(f"  {categoria:9} {nome}")
        return 0

    nomes = nomes_do_acervo(factory)
    faltam = repo.faltantes(nomes)
    print(f"catálogo: {settings.db_path}")
    print(f"  nomes distintos:  {len(nomes):>5}")
    print(f"  já classificados: {len(nomes) - len(faltam):>5}")
    print(f"  a classificar:    {len(faltam):>5}")

    if not faltam:
        print("\nnada a fazer.")
        return 0

    if not args.enviar:
        print("\nO que sairia da máquina (só isto — nenhuma imagem, data ou "
              "coordenada):")
        for nome in faltam:
            print(f"  {nome}")
        print("\nsem --enviar: nada foi enviado.")
        return 0

    if not settings.privacidade.servicos_externos:
        print("\nRecusado: [privacidade] servicos_externos = false.")
        print("Ligue no config.toml antes de enviar qualquer palavra.")
        return 1

    print(f"\nenviando {len(faltam)} nome(s)…")
    categorias = LexicoClaude().classificar(faltam)
    if not categorias:
        print("nenhuma classificação obtida (ver log).")
        return 1
    print(f"gravados {repo.salvar(categorias)} nome(s).")
    for nome, categoria in sorted(categorias.items(), key=lambda kv: kv[1]):
        print(f"  {categoria:9} {nome}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
