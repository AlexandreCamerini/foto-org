#!/usr/bin/env python3
"""Diagnostica por que a leitura de uma fonte externa traz menos do que deveria.

SOMENTE LEITURA: abre o `.lrcat` com `immutable=1`, a biblioteca do Fotos pelo
osxphotos e a pasta do Takeout sem escrever nada, sem tocar em original e sem
rede. Não altera o catálogo do Foto Organizer — nem o abre.

Existe porque "não funcionava bem" precisa virar número antes de virar
correção. Cada checagem abaixo corresponde a um defeito identificado por
leitura do código em 2026-08-10; o script diz se ele afeta ESTE acervo e
quanto.

Uso:
    python scripts/diagnosticar_fontes.py --lrcat ~/Pictures/Lightroom/Cat.lrcat
    python scripts/diagnosticar_fontes.py --apple
    python scripts/diagnosticar_fontes.py --takeout ~/Downloads/Takeout
    python scripts/diagnosticar_fontes.py --lrcat ... --apple --takeout ...
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path


def _titulo(texto: str) -> None:
    print(f"\n{'=' * 70}\n{texto}\n{'=' * 70}")


def _linha(rotulo: str, valor, nota: str = "") -> None:
    print(f"  {rotulo:<44} {valor:>10}  {nota}")


# --------------------------------------------------------------------------
# Lightroom
# --------------------------------------------------------------------------
def diagnosticar_lrcat(caminho: Path) -> None:
    _titulo(f"Lightroom · {caminho.name}")
    if not caminho.is_file():
        print(f"  catálogo não encontrado: {caminho}")
        return
    try:
        con = sqlite3.connect(f"file:{caminho}?immutable=1", uri=True)
    except sqlite3.Error as exc:
        print(f"  não consegui abrir: {exc}")
        return

    def conta(sql: str) -> int:
        try:
            return con.execute(sql).fetchone()[0] or 0
        except sqlite3.Error as exc:
            print(f"  [consulta falhou] {exc}")
            return -1

    try:
        total_img = conta("select count(*) from Adobe_images")
        total_arq = conta("select count(*) from AgLibraryFile")
        _linha("Adobe_images (linhas)", total_img)
        _linha("AgLibraryFile (arquivos distintos)", total_arq,
               "diferença = cópias virtuais" if total_img > total_arq else "")

        # --- Defeito 1: concatenação SQL com NULL apaga o caminho inteiro.
        # `a || b` em SQL é NULL se QUALQUER parte for NULL. A consulta atual
        # monta o caminho com 5 concatenações; um NULL em qualquer uma delas
        # devolve NULL e a referência perde a única pista de LUGAR que tinha.
        _titulo_sub = "\n  -- caminho montado por concatenação --"
        print(_titulo_sub)
        perdidas = conta("""
            select count(*)
            from Adobe_images i
            join AgLibraryFile f        on f.id_local  = i.rootFile
            join AgLibraryFolder fo     on fo.id_local = f.folder
            join AgLibraryRootFolder rf on rf.id_local = fo.rootFolder
            where rf.absolutePath is null or fo.pathFromRoot is null
               or f.baseName is null or f.extension is null
        """)
        _linha("linhas com algum campo NULL", perdidas,
               "<-- PERDEM O CAMINHO INTEIRO" if perdidas > 0 else "ok")
        for campo, sql in (
            ("rf.absolutePath", "rf.absolutePath is null"),
            ("fo.pathFromRoot", "fo.pathFromRoot is null"),
            ("f.baseName", "f.baseName is null"),
            ("f.extension", "f.extension is null"),
        ):
            n = conta(f"""
                select count(*) from Adobe_images i
                join AgLibraryFile f        on f.id_local  = i.rootFile
                join AgLibraryFolder fo     on fo.id_local = f.folder
                join AgLibraryRootFolder rf on rf.id_local = fo.rootFolder
                where {sql}
            """)
            if n:
                _linha(f"  ...destes, {campo} nulo", n)

        # --- Defeito 2: o INNER JOIN descarta imagem sem pasta/raiz.
        print("\n  -- cobertura do join --")
        com_join = conta("""
            select count(*)
            from Adobe_images i
            join AgLibraryFile f        on f.id_local  = i.rootFile
            join AgLibraryFolder fo     on fo.id_local = f.folder
            join AgLibraryRootFolder rf on rf.id_local = fo.rootFolder
        """)
        _linha("linhas que sobrevivem ao join", com_join)
        if total_img > 0 and com_join >= 0:
            _linha("perdidas pelo join", total_img - com_join,
                   "<-- SOMEM DA IMPORTAÇÃO" if total_img > com_join else "ok")

        # --- Defeito 3: identidade por arquivo, não por imagem.
        print("\n  -- identidade (referencia = f.id_global) --")
        dups = conta("""
            select count(*) from (
                select f.id_global
                from Adobe_images i
                join AgLibraryFile f on f.id_local = i.rootFile
                group by f.id_global having count(*) > 1
            )
        """)
        _linha("id_global repetido (cópias virtuais)", dups,
               "<-- uma sobrescreve a outra" if dups > 0 else "ok")

        # --- Volume: o que responde "de que disco veio?" com o disco fora.
        print("\n  -- volumes --")
        try:
            for nome, n in con.execute("""
                select rf.absolutePath, count(*)
                from Adobe_images i
                join AgLibraryFile f        on f.id_local  = i.rootFile
                join AgLibraryFolder fo     on fo.id_local = f.folder
                join AgLibraryRootFolder rf on rf.id_local = fo.rootFolder
                group by rf.absolutePath order by count(*) desc limit 10
            """):
                _linha(f"  {str(nome)[:40]}", n)
        except sqlite3.Error as exc:
            print(f"  [volumes] {exc}")

        # --- Curadoria: o que se perde se o .lrcat não for lido.
        print("\n  -- curadoria no .lrcat --")
        _linha("com nota >= 4", conta(
            "select count(*) from Adobe_images where rating >= 4"))
        _linha("com pick > 0 (sinalizada)", conta(
            "select count(*) from Adobe_images where pick > 0"))
        _linha("com pick < 0 (rejeitada)", conta(
            "select count(*) from Adobe_images where pick < 0"),
            "hoje tratadas como 'não favorito', indistintas de sem nota")
        _linha("em alguma coleção", conta(
            "select count(distinct image) from AgLibraryCollectionimage"))
        _linha("com palavra-chave", conta(
            "select count(distinct image) from AgLibraryKeywordImage"))
        _linha("com GPS", conta(
            "select count(*) from AgHarvestedExifMetadata "
            "where gpsLatitude is not null"))
    finally:
        con.close()


# --------------------------------------------------------------------------
# Apple Fotos
# --------------------------------------------------------------------------
def diagnosticar_apple(biblioteca: Path | None) -> None:
    _titulo("Apple Fotos")
    try:
        import osxphotos
    except ImportError:
        print("  osxphotos não instalado — 'pip install fotoorganizer[apple]'")
        return
    alvo = str(biblioteca) if biblioteca else None
    try:
        db = osxphotos.PhotosDB(alvo) if alvo else osxphotos.PhotosDB()
    except Exception as exc:
        print(f"  não consegui abrir a biblioteca: {exc}")
        print("  (Acesso Total ao Disco é concedido ao APP que roda o script)")
        return

    # `movies=False` é o que o provider usa hoje. As duas contagens medem
    # exatamente o que esse filtro descarta.
    so_fotos = db.photos(movies=False)
    com_video = db.photos(movies=True)
    _linha("fotos (movies=False, o que o app lê hoje)", len(so_fotos))
    _linha("fotos + vídeos (movies=True)", len(com_video))
    _linha("descartados pelo filtro de vídeo", len(com_video) - len(so_fotos),
           "<-- doadores de GPS e metade das Live Photos")

    sem_arquivo = sem_uuid = com_gps = com_kw = com_pessoa = 0
    com_tz = burst = live = 0
    kws: Counter = Counter()
    for p in com_video:
        if not getattr(p, "path", None):
            sem_arquivo += 1
        if not getattr(p, "uuid", None):
            sem_uuid += 1
        if getattr(p, "location", None) and p.location[0] is not None:
            com_gps += 1
        ks = getattr(p, "keywords", None) or ()
        if ks:
            com_kw += 1
            kws.update(ks)
        if getattr(p, "persons", None):
            com_pessoa += 1
        d = getattr(p, "date", None)
        if d is not None and d.tzinfo is not None:
            com_tz += 1
        if getattr(p, "burst", False):
            burst += 1
        if getattr(p, "live_photo", False):
            live += 1

    print("\n  -- o que a biblioteca oferece --")
    _linha("sem original local (só iCloud)", sem_arquivo, "entram como SINAL")
    _linha("sem uuid (descartados)", sem_uuid)
    _linha("com GPS", com_gps, "doadores da correlação")
    _linha("com fuso por foto", com_tz, "única fonte de fuso medido")
    _linha("em rajada", burst)
    _linha("Live Photo", live, "o vídeo tem GPS quando a foto não tem")

    print("\n  -- o que o app NÃO lê hoje --")
    _linha("com palavra-chave", com_kw,
           "<-- IGNORADAS: o provider não lê photo.keywords")
    _linha("com pessoa nomeada", com_pessoa, "lidas ✓")
    if kws:
        print("     palavras-chave mais frequentes:")
        for k, n in kws.most_common(10):
            print(f"       {n:>7}  {k}")


# --------------------------------------------------------------------------
# Google Takeout
# --------------------------------------------------------------------------
_EXTS_LIDAS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".tif", ".tiff",
               ".bmp", ".heic", ".heif"}
_EXTS_VIDEO = {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".3gp", ".webm"}


def diagnosticar_takeout(raiz: Path) -> None:
    _titulo(f"Google Takeout · {raiz}")
    if not raiz.is_dir():
        print(f"  pasta não encontrada: {raiz}")
        return

    lidas = video = outros = 0
    sem_sidecar = com_gps = com_data = 0
    for arq in raiz.rglob("*"):
        if not arq.is_file():
            continue
        ext = arq.suffix.lower()
        if ext == ".json":
            continue
        if ext in _EXTS_LIDAS:
            lidas += 1
        elif ext in _EXTS_VIDEO:
            video += 1
            continue
        else:
            outros += 1
            continue

        sc = None
        for cand in (arq.with_name(arq.name + ".json"),
                     arq.with_name(arq.name + ".supplemental-metadata.json")):
            if cand.is_file():
                sc = cand
                break
        if sc is None:
            sem_sidecar += 1
            continue
        try:
            d = json.loads(sc.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        geo = d.get("geoData") or d.get("geoDataExif") or {}
        if geo.get("latitude") and geo.get("longitude"):
            com_gps += 1
        if (d.get("photoTakenTime") or {}).get("timestamp"):
            com_data += 1

    _linha("imagens lidas hoje", lidas)
    _linha("vídeos IGNORADOS", video,
           "<-- carregam GPS e não são lidos")
    _linha("outros arquivos", outros)
    print()
    _linha("imagens sem sidecar JSON encontrado", sem_sidecar,
           "<-- perdem data e GPS" if sem_sidecar else "ok")
    _linha("com GPS no sidecar", com_gps, "doadores da correlação")
    _linha("com photoTakenTime", com_data,
           "epoch UTC = instante absoluto exato")
    print("\n  Nota: o epoch do Takeout é o instante ABSOLUTO da captura —")
    print("  a informação de fuso mais confiável que esta fonte tem. Hoje ele")
    print("  é convertido com o fuso DESTA MÁQUINA e o absoluto é descartado.")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--lrcat", type=Path, help="caminho do arquivo .lrcat")
    p.add_argument("--apple", action="store_true",
                   help="diagnostica a biblioteca do Apple Fotos")
    p.add_argument("--biblioteca", type=Path,
                   help="biblioteca do Fotos (padrão: a do sistema)")
    p.add_argument("--takeout", type=Path, help="pasta raiz do Takeout")
    args = p.parse_args()

    if not (args.lrcat or args.apple or args.takeout):
        p.print_help()
        return 2
    if args.lrcat:
        diagnosticar_lrcat(args.lrcat.expanduser())
    if args.apple:
        diagnosticar_apple(args.biblioteca.expanduser()
                           if args.biblioteca else None)
    if args.takeout:
        diagnosticar_takeout(args.takeout.expanduser())
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
