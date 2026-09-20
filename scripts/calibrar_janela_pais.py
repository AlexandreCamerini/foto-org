#!/usr/bin/env python3
"""Calibra o alargamento da janela de país da herança de GPS (D-025) contra
o acervo real.

SOMENTE LEITURA: abre o catálogo em `mode=ro`, não escreve nada, não toca em
nenhum arquivo original.

D-025 fixou a janela de país em 12 h porque era a maior sustentada pelos
dados de então. Esta calibração responde duas perguntas separadas para um
alargamento candidato (24 h, 48 h...), na mesma técnica de doadora
hipotética de `calibrar_raio_incerteza.py` (D-032/D-074):

  cobertura — quantas fotos hoje SEM lugar nenhum ganhariam um país dentro
              da janela nova (rodando `herdar_gps` de verdade sobre o
              acervo real, só alargando o campo "pais");
  acurácia  — para os pares NOVOS que a janela alargada passaria a aceitar
              (Δt entre a janela antiga e a nova), quantos por cento o país
              da doadora mais próxima bate com o país real da herdeira —
              medido em fotos que JÁ TÊM GPS próprio dos dois lados, onde
              dá para saber a resposta certa.

D-025 já registrou por que a janela de país não passa pelo teste de
concordância de D-074 (raio_incerteza não é calibrado para escala de país):
esta medição não tenta consertar isso — mede acurácia por geocodificação
direta, não por distância.

Uso:
    .venv/bin/python scripts/calibrar_janela_pais.py
    .venv/bin/python scripts/calibrar_janela_pais.py --janelas 24 48 72
    .venv/bin/python scripts/calibrar_janela_pais.py --db <catalog.db>

Resultado documentado em docs/DECISOES.md (D-085, se aprovado).
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fotoorganizer.config import paths  # noqa: E402
from fotoorganizer.geolocation.offline import OfflineGeocoder  # noqa: E402
from fotoorganizer.grouping import correlacao  # noqa: E402
from fotoorganizer.grouping.correlacao import (  # noqa: E402
    FotoRef,
    estimar_offsets,
    herdar_gps,
)
from fotoorganizer.grouping.datas import fuso_da_maquina, quando_da_foto  # noqa: E402

_DB_PADRAO = paths.default_db_path()
# O valor de JANELAS_POR_CAMPO["pais"] ANTES desta calibração decidir
# nada — fixo em 12h de propósito, não importado de `correlacao.py`,
# para continuar servindo de linha de base mesmo depois que o valor
# real mudar (D-085 já subiu para 48h).
_JANELA_BASELINE = timedelta(hours=12)


def _linhas(db: Path) -> list[tuple]:
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        return con.execute(
            "select id, source_id, make, model, gps_lat, gps_lon,"
            "       data_capturada, mtime, nome, hash_rapido, hash_perceptual"
            "  from media_files"
        ).fetchall()
    finally:
        con.close()


def _refs(linhas: list[tuple], tz) -> list[FotoRef]:
    """Uma FotoRef por linha com `quando` resolvido (D-084) — a MESMA
    cascata que o motor usa, precisão de segundo só. Traz `hash_rapido`/
    `hash_perceptual` para `estimar_offsets` poder achar par-âncora de
    verdade, como `engine._correlacionar` faz — sem eles a deriva de
    relógio nunca seria estimada, mesmo que o acervo tivesse âncora."""
    refs = []
    for id_, src, make, model, lat, lon, dc, mt, nome, hr, hp in linhas:
        dc = datetime.fromisoformat(dc) if dc else None
        mt = datetime.fromisoformat(mt) if mt else None
        q = quando_da_foto(dc, nome, mt, tz_padrao=tz)
        if q is None or q.precisao != "segundo":
            continue
        refs.append(FotoRef(
            media_id=id_, source_id=src, quando=q.instante,
            camera=(make, model), lat=lat, lon=lon,
            hash_rapido=hr, hash_perceptual=hp,
            hora_do_arquivo=q.hora_incerta,
        ))
    return refs


def _com_janela_pais(janela: timedelta):
    """Context manager: `JANELAS_POR_CAMPO`/`JANELA_HERANCA` do módulo real
    com o campo "pais" alargado — as mesmas funções de produção
    (`campos_confiaveis`, `herdar_gps`) leem a constante do módulo."""
    class _Patch:
        def __enter__(self) -> "_Patch":
            self._antes = correlacao.JANELAS_POR_CAMPO, correlacao.JANELA_HERANCA
            novas = tuple(
                (campo, janela if campo == "pais" else j)
                for campo, j in correlacao.JANELAS_POR_CAMPO
            )
            correlacao.JANELAS_POR_CAMPO = novas
            correlacao.JANELA_HERANCA = max(j for _, j in novas)
            return self

        def __exit__(self, *_exc):
            correlacao.JANELAS_POR_CAMPO, correlacao.JANELA_HERANCA = self._antes
    return _Patch()


def cobertura(refs: list[FotoRef], offsets, janela: timedelta) -> set[int]:
    """Ids que ganham campo "pais" na herança, com esta janela."""
    with _com_janela_pais(janela):
        herancas = herdar_gps(refs, offsets, janela=correlacao.JANELA_HERANCA)
    return {h.media_id for h in herancas if any(c == "pais" for c, _ in h.campos)}


def pares_hipoteticos(
    refs: list[FotoRef], offsets, janela_de: timedelta, janela_ate: timedelta,
) -> list[tuple[int, int, float, date]]:
    """(id_herdeira, id_doadora, delta_s, dia) — UM par por candidata, a
    doadora ÚNICA que `herdar_gps` escolheria (a mais próxima entre os
    DOIS lados, dentro de `janela_ate`), reportado só quando esse Δt cai
    ALÉM de `janela_de` — ou seja: candidatas cuja doadora real já está
    coberta pela janela antiga (`janela_de`) não entram aqui, porque para
    elas a janela nova não muda nada; só entram as que a janela nova
    passa a alcançar.

    Buscar cada lado e ficar só com o vencedor (não os dois) é o que
    `herdar_gps.procurar` + `min(achados, ...)` fazem de verdade — um par
    por lado, como a primeira versão deste script fazia, conta a mesma
    foto duas vezes e infla a amostra com o lado que o motor nunca usaria.
    """
    def corrigida(f: FotoRef) -> datetime:
        return f.quando + offsets.get(f.camera, timedelta())

    com_gps = sorted((f for f in refs if f.tem_gps), key=corrigida)
    tempos = [corrigida(f) for f in com_gps]
    pares = []
    for i, foto in enumerate(com_gps):
        alvo = tempos[i]
        melhor: tuple[timedelta, int] | None = None
        for passo in (-1, 1):
            j = i + passo
            while 0 <= j < len(com_gps):
                delta = abs(tempos[j] - alvo)
                if delta > janela_ate:
                    break
                if foto.outra_origem(com_gps[j]):
                    if melhor is None or delta < melhor[0]:
                        melhor = (delta, j)
                    break
                j += passo
        if melhor is None:
            continue
        delta, j = melhor
        if delta > janela_de:
            pares.append((foto.media_id, com_gps[j].media_id,
                         delta.total_seconds(), alvo.date()))
    return pares


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", type=Path, default=_DB_PADRAO)
    ap.add_argument("--janelas", type=int, nargs="+", default=[24, 48])
    args = ap.parse_args()

    linhas = _linhas(args.db)
    tz = fuso_da_maquina()
    refs = _refs(linhas, tz)
    por_id = {r.media_id: r for r in refs}
    offsets = estimar_offsets(refs)

    print(f"fotos com quando resolvido: {len(refs)} "
          f"(com GPS próprio: {sum(1 for r in refs if r.tem_gps)})")

    base = cobertura(refs, offsets, _JANELA_BASELINE)
    print(f"\ncobertura atual (janela 12h, campo país): {len(base)} fotos")

    geocoder = OfflineGeocoder()
    cache_pais: dict[tuple[float, float], str | None] = {}

    def pais_de(lat: float, lon: float) -> str | None:
        chave = (round(lat, 3), round(lon, 3))
        if chave not in cache_pais:
            r = geocoder.resolve(lat, lon)
            cache_pais[chave] = r.pais if r else None
        return cache_pais[chave]

    def medir_faixa(de: timedelta, ate: timedelta) -> None:
        """Acurácia de país (bruta e por dia) para quem a janela `ate`
        alcançaria a mais sobre a janela `de` — a doadora ÚNICA que
        `herdar_gps` escolheria para cada candidata."""
        faixa = f"{int(de.total_seconds()/3600)}-{int(ate.total_seconds()/3600)}h"
        pares = pares_hipoteticos(refs, offsets, de, ate)
        if not pares:
            print(f"  acurácia (faixa {faixa}, um par por candidata — a "
                  f"doadora que herdar_gps escolheria): sem pares medíveis")
            return
        acertos = erros = sem_pais = 0
        distrib_erro: Counter[tuple[str | None, str | None]] = Counter()
        por_dia: dict[date, list[bool]] = {}
        for id_h, id_d, _delta_s, dia in pares:
            h, d = por_id[id_h], por_id[id_d]
            assert h.lat is not None and h.lon is not None
            assert d.lat is not None and d.lon is not None
            pais_h, pais_d = pais_de(h.lat, h.lon), pais_de(d.lat, d.lon)
            if pais_h is None or pais_d is None:
                sem_pais += 1
                continue
            ok = pais_h == pais_d
            acertos += ok
            erros += not ok
            por_dia.setdefault(dia, []).append(ok)
            if not ok:
                distrib_erro[(pais_h, pais_d)] += 1
        total = acertos + erros
        dias_com_erro = sum(1 for v in por_dia.values() if not all(v))
        media_por_dia = (
            sum(sum(v) / len(v) for v in por_dia.values()) / len(por_dia)
            if por_dia else 0.0
        )
        print(f"  acurácia (faixa {faixa}, um par por candidata): "
              f"{acertos}/{total}" + (f" = {100*acertos/total:.1f}%" if total else "")
              + f" ({sem_pais} sem geocodificação)")
        print(f"  por dia: {media_por_dia*100:.1f}% "
              f"(erro em {dias_com_erro} de {len(por_dia)} dias de viagem)")
        if distrib_erro:
            print("  erros mais comuns (real → doadora dizia):")
            for (real, dito), n in distrib_erro.most_common(8):
                print(f"    {n:4d}  {real} → {dito}")

    print("\n== janela atual (0-12h) — linha de base ==")
    medir_faixa(timedelta(0), _JANELA_BASELINE)

    anterior = _JANELA_BASELINE
    for horas in sorted(args.janelas):
        nova = timedelta(hours=horas)
        cobre = cobertura(refs, offsets, nova)
        ganho = cobre - base
        print(f"\n== janela {horas}h ==")
        print(f"  cobertura: {len(cobre)} fotos (+{len(ganho)} sobre as 12h atuais)")
        medir_faixa(anterior, nova)
        anterior = nova

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
