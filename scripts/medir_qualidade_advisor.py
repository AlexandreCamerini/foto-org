#!/usr/bin/env python3
"""Compara Haiku 4.5 × Opus 5 no advisor de classificação, sobre clusters
REAIS do acervo — a comparação pedida na revisão de
`docs/PLANO_IA_E_PRODUTO.md` (decisão 1 do gate), depois de D-047 mostrar
que sessões "neutra" são 39% do total, não resíduo, e D-048 mostrar um
primeiro sinal (n=5) de que Haiku inventa onde Opus recusa.

ATENÇÃO — este script ENVIA metadado real do acervo (nomes de pasta, até 8
nomes de arquivo por cluster, datas, lugares já geocodificados — nunca a
imagem) para a API da Anthropic, DUAS vezes por cluster (uma por modelo).
É a ação que `docs/prompts/00-protocolo.md` classifica como Classe C —
sempre espera aprovação explícita, mesmo em teste. Só rode isto depois de
confirmação explícita do dono, escopo (quantos clusters) combinado, e com
`ANTHROPIC_API_KEY` no ambiente — e rode você mesmo, no seu terminal: esta
sessão não manuseia a credencial (ver D-048).

Reusa `fotoorganizer.classification.advisor.ClaudeAdvisor` (mesma classe que
o produto usaria) — nenhuma lógica de chamada nova, só o comparador.

Os períodos dos clusters vêm de um JSON exportado por
`scripts/medir_uso_do_advisor.py --exportar-periodos <arquivo>` (períodos
reais das sessões "neutra" do catálogo, sem precisar rodar de novo a
passada completa de ~1h40 do motor). Cada cluster é reconstruído por SQL a
partir do período.

Saída: relatório EXECUTIVO — contagem agregada de concordância/discordância
por padrão, não um dump de N blocos. Use `--detalhe` para imprimir todos os
clusters (útil para conferência manual, não para leitura corrida).

Uso:
    ANTHROPIC_API_KEY=... .venv/bin/python scripts/medir_qualidade_advisor.py \\
        --periodos clusters_neutra_104.json
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sqlite3
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fotoorganizer.classification.advisor import (  # noqa: E402
    AdvisorResult,
    ClaudeAdvisor,
    ClusterInfo,
)
from fotoorganizer.config import paths  # noqa: E402

MODELOS = {
    "opus-5": "claude-opus-5",
    "haiku-4.5": "claude-haiku-4-5-20251001",
}

# Amostra pequena de fallback (as mesmas 5 de D-048), só para --periodos
# não ser obrigatório num teste rápido.
CLUSTERS_AMOSTRA_PADRAO = [
    {"inicio": "2001-02-22", "fim": "2001-02-25", "n_fotos": 30},
    {"inicio": "2002-04-13", "fim": "2002-04-16", "n_fotos": 33},
    {"inicio": "2005-01-01", "fim": "2005-01-01", "n_fotos": 4},
    {"inicio": "2006-12-31", "fim": "2007-01-04", "n_fotos": 90},
    {"inicio": "2007-01-27", "fim": "2007-02-03", "n_fotos": 149},
]


def _abrir(db: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{db}?immutable=1", uri=True)


def _reconstruir_cluster(con: sqlite3.Connection, inicio: str, fim: str) -> ClusterInfo:
    """Aproxima o ClusterInfo que o motor real montaria para este período —
    mesma consulta de campos que `_consultar_advisor` usa
    (`engine.py:560-569`), reconstruída por período em vez de reaproveitar
    o agrupamento interno do motor (que exigiria rodar `gerar()` de novo)."""
    linhas = con.execute(
        """
        select m.pasta, m.nome, l.pais, l.cidade
          from media_files m
          left join locations l on l.id = m.location_id
         where m.papel = 'ACERVO'
           and date(m.data_capturada) between ? and ?
         order by m.data_capturada
        """,
        (inicio, fim),
    ).fetchall()
    pastas = tuple(sorted({p for p, *_ in linhas if p}))
    exemplos = tuple(nome for _, nome, *_ in linhas[:8])
    lugares = tuple(sorted({
        f"{cidade}, {pais}" if cidade and pais else (pais or cidade)
        for _, _, pais, cidade in linhas
        if pais or cidade
    }))
    return ClusterInfo(
        pastas=pastas,
        exemplos_arquivos=exemplos,
        inicio=dt.datetime.fromisoformat(inicio),
        fim=dt.datetime.fromisoformat(fim),
        n_fotos=len(linhas),
        lugares=lugares,
    )


@dataclass
class Comparacao:
    cluster: ClusterInfo
    opus: AdvisorResult | None
    haiku: AdvisorResult | None

    @property
    def padrao(self) -> str:
        """`classificar()` quase sempre devolve um `AdvisorResult` de
        verdade, mesmo quando o modelo não tem confiança — a recusa vira
        `categoria=None` DENTRO do objeto (`advisor.py:97`: "devolva
        categoria e evento nulos"), não o objeto inteiro sendo `None`
        (isso só acontece em erro de API/parse, `advisor.py` mais abaixo).
        Comparar `self.opus is None` aqui seria o bug que gerou a primeira
        versão deste relatório — sempre zero nas três categorias que
        dependiam disso. O sinal certo de "recusou" é `.categoria is None`.
        """
        op_recusou = self.opus is None or self.opus.categoria is None
        ha_recusou = self.haiku is None or self.haiku.categoria is None
        if op_recusou and ha_recusou:
            return "concordam_null"
        if not op_recusou and not ha_recusou:
            if (self.opus.categoria, self.opus.evento) == (
                self.haiku.categoria, self.haiku.evento
            ):
                return "concordam_afirmam"
            return "discordam_entre_si"
        if op_recusou and not ha_recusou:
            return "haiku_afirma_opus_recusa"
        return "opus_afirma_haiku_recusa"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=paths.default_db_path())
    parser.add_argument(
        "--periodos", type=Path, default=None,
        help="JSON de scripts/medir_uso_do_advisor.py --exportar-periodos. "
             "Sem isto, usa a amostra fixa de 5 (mesma de D-048).",
    )
    parser.add_argument(
        "--limite", type=int, default=None,
        help="compara só os N primeiros períodos do arquivo (para um teste "
             "parcial antes de rodar tudo).",
    )
    parser.add_argument(
        "--detalhe", action="store_true",
        help="imprime cada cluster individualmente, além do resumo.",
    )
    args = parser.parse_args()

    if args.periodos:
        periodos = json.loads(args.periodos.read_text(encoding="utf-8"))
    else:
        periodos = CLUSTERS_AMOSTRA_PADRAO
    if args.limite:
        periodos = periodos[: args.limite]

    con = _abrir(args.db)
    clusters = [_reconstruir_cluster(con, p["inicio"], p["fim"]) for p in periodos]
    con.close()

    advisor_opus = ClaudeAdvisor(model=MODELOS["opus-5"])
    advisor_haiku = ClaudeAdvisor(model=MODELOS["haiku-4.5"])

    comparacoes: list[Comparacao] = []
    for i, cluster in enumerate(clusters, 1):
        print(f"[{i}/{len(clusters)}] {cluster.inicio:%Y-%m-%d} → {cluster.fim:%Y-%m-%d} "
              f"({cluster.n_fotos} fotos)...", file=sys.stderr)
        op = advisor_opus.classificar(cluster)
        ha = advisor_haiku.classificar(cluster)
        comparacoes.append(Comparacao(cluster, op, ha))

    # -- relatório executivo -------------------------------------------------
    padroes = Counter(c.padrao for c in comparacoes)
    total = len(comparacoes)

    print(f"\n{'='*70}")
    print(f"RELATÓRIO — {total} clusters comparados (Opus 5 × Haiku 4.5)")
    print(f"{'='*70}\n")

    concordancia = padroes["concordam_null"] + padroes["concordam_afirmam"]
    discordancia = total - concordancia
    print(f"Concordância: {concordancia}/{total} ({100*concordancia/total:.1f}%)")
    print(f"  — ambos recusam (null/null): {padroes['concordam_null']}")
    print(f"  — ambos afirmam a MESMA categoria/evento: {padroes['concordam_afirmam']}")
    print(f"Discordância: {discordancia}/{total} ({100*discordancia/total:.1f}%)")
    print(f"  — Haiku afirma, Opus recusa: {padroes['haiku_afirma_opus_recusa']}"
          f"  ← padrão de risco (D-048: Haiku inventa onde Opus se abstém)")
    print(f"  — Opus afirma, Haiku recusa: {padroes['opus_afirma_haiku_recusa']}")
    print(f"  — os dois afirmam, mas discordam entre si: {padroes['discordam_entre_si']}")

    # Distribuição de categoria quando cada modelo afirma algo, para ver se
    # convergem no TIPO de resposta mesmo quando divergem no caso a caso.
    for nome, advisor_key in (("Opus 5", "opus"), ("Haiku 4.5", "haiku")):
        cats = Counter(
            getattr(c, advisor_key).categoria
            for c in comparacoes
            if getattr(c, advisor_key) is not None
        )
        if cats:
            print(f"\nCategorias que {nome} afirmou (entre os que respondeu algo):")
            for cat, n in cats.most_common():
                print(f"  {cat}: {n}")

    # Amostra do padrão de risco — até 5 exemplos, não os N inteiros.
    risco = [c for c in comparacoes if c.padrao == "haiku_afirma_opus_recusa"]
    if risco:
        print(f"\nAmostra de 'Haiku afirma, Opus recusa' ({len(risco)} no total, "
              f"mostrando até 5):")
        for c in risco[:5]:
            print(f"\n  {c.cluster.inicio:%Y-%m-%d} → {c.cluster.fim:%Y-%m-%d} "
                  f"({c.cluster.n_fotos} fotos)")
            print(f"    pastas: {c.cluster.pastas[:3]}"
                  f"{' ...' if len(c.cluster.pastas) > 3 else ''}")
            print(f"    Haiku: {c.haiku.categoria}/{c.haiku.evento!r} — "
                  f"{c.haiku.justificativa}")

    if args.detalhe:
        print(f"\n{'='*70}\nDETALHE — todos os {total} clusters\n{'='*70}")
        for i, c in enumerate(comparacoes, 1):
            print(f"\n[{i}] {c.cluster.inicio:%Y-%m-%d} → {c.cluster.fim:%Y-%m-%d} "
                  f"({c.cluster.n_fotos} fotos) — {c.padrao}")
            print(f"    pastas: {c.cluster.pastas}")
            if c.opus:
                print(f"    Opus:  {c.opus.categoria}/{c.opus.evento!r} — {c.opus.justificativa}")
            else:
                print("    Opus:  null")
            if c.haiku:
                print(f"    Haiku: {c.haiku.categoria}/{c.haiku.evento!r} — {c.haiku.justificativa}")
            else:
                print("    Haiku: null")


if __name__ == "__main__":
    main()
