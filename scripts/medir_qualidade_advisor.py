#!/usr/bin/env python3
"""Compara dois modelos no advisor de classificação, sobre clusters REAIS
do acervo — a comparação pedida na revisão de `docs/PLANO_IA_E_PRODUTO.md`
(decisão 1 do gate), depois de D-047 mostrar que sessões "neutra" são 39%
do total, não resíduo, e D-048/D-049 mostrar que Haiku 4.5 inventa
categoria onde Opus 5 recusa, em pelo menos 19/31 discordâncias (n=104).

Generalizado para qualquer par de `MODELOS` (era hardcoded a Opus×Haiku;
a comparação original continua sendo o default, sem mudança de
comportamento se você não passar `--modelo-a`/`--modelo-b`). Motivo:
Sonnet 5 nunca entrou na medição — só Opus 5 e Haiku 4.5 foram testados.

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

    # Repetir a comparação original (Opus 5 × Haiku 4.5) é o default —
    # nada muda em relação ao script anterior a este ajuste.

    # Comparar Opus 5 × Sonnet 5 (decisão 1, opção Sonnet):
    ANTHROPIC_API_KEY=... .venv/bin/python scripts/medir_qualidade_advisor.py \\
        --periodos clusters_neutra_104.json --modelo-a opus-5 --modelo-b sonnet-5
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
    "sonnet-5": "claude-sonnet-5",
}
NOMES_LEGIVEIS = {
    "opus-5": "Opus 5",
    "haiku-4.5": "Haiku 4.5",
    "sonnet-5": "Sonnet 5",
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
    a: AdvisorResult | None
    b: AdvisorResult | None

    @property
    def padrao(self) -> str:
        """`classificar()` quase sempre devolve um `AdvisorResult` de
        verdade, mesmo quando o modelo não tem confiança — a recusa vira
        `categoria=None` DENTRO do objeto (`advisor.py:97`: "devolva
        categoria e evento nulos"), não o objeto inteiro sendo `None`
        (isso só acontece em erro de API/parse, `advisor.py` mais abaixo).
        Comparar `self.a is None` aqui seria o bug que gerou a primeira
        versão deste relatório — sempre zero nas três categorias que
        dependiam disso. O sinal certo de "recusou" é `.categoria is None`.
        """
        a_recusou = self.a is None or self.a.categoria is None
        b_recusou = self.b is None or self.b.categoria is None
        if a_recusou and b_recusou:
            return "concordam_null"
        if not a_recusou and not b_recusou:
            if (self.a.categoria, self.a.evento) == (self.b.categoria, self.b.evento):
                return "concordam_afirmam"
            return "discordam_entre_si"
        if a_recusou and not b_recusou:
            return "b_afirma_a_recusa"
        return "a_afirma_b_recusa"


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
    parser.add_argument(
        "--modelo-a", choices=sorted(MODELOS), default="opus-5",
        help="primeiro modelo da comparação (default: opus-5, igual a "
             "D-048/D-049 — não muda a comparação histórica por padrão).",
    )
    parser.add_argument(
        "--modelo-b", choices=sorted(MODELOS), default="haiku-4.5",
        help="segundo modelo da comparação (default: haiku-4.5).",
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

    nome_a, nome_b = NOMES_LEGIVEIS[args.modelo_a], NOMES_LEGIVEIS[args.modelo_b]
    advisor_a = ClaudeAdvisor(model=MODELOS[args.modelo_a])
    advisor_b = ClaudeAdvisor(model=MODELOS[args.modelo_b])

    comparacoes: list[Comparacao] = []
    for i, cluster in enumerate(clusters, 1):
        print(f"[{i}/{len(clusters)}] {cluster.inicio:%Y-%m-%d} → {cluster.fim:%Y-%m-%d} "
              f"({cluster.n_fotos} fotos)...", file=sys.stderr)
        ra = advisor_a.classificar(cluster)
        rb = advisor_b.classificar(cluster)
        comparacoes.append(Comparacao(cluster, ra, rb))

    # -- relatório executivo -------------------------------------------------
    padroes = Counter(c.padrao for c in comparacoes)
    total = len(comparacoes)

    print(f"\n{'='*70}")
    print(f"RELATÓRIO — {total} clusters comparados ({nome_a} × {nome_b})")
    print(f"{'='*70}\n")

    concordancia = padroes["concordam_null"] + padroes["concordam_afirmam"]
    discordancia = total - concordancia
    print(f"Concordância: {concordancia}/{total} ({100*concordancia/total:.1f}%)")
    print(f"  — ambos recusam (null/null): {padroes['concordam_null']}")
    print(f"  — ambos afirmam a MESMA categoria/evento: {padroes['concordam_afirmam']}")
    print(f"Discordância: {discordancia}/{total} ({100*discordancia/total:.1f}%)")
    print(f"  — {nome_b} afirma, {nome_a} recusa: {padroes['b_afirma_a_recusa']}"
          f"  ← padrão de risco (D-048/D-049: modelo mais barato inventa "
          f"onde o mais caro se abstém)")
    print(f"  — {nome_a} afirma, {nome_b} recusa: {padroes['a_afirma_b_recusa']}")
    print(f"  — os dois afirmam, mas discordam entre si: {padroes['discordam_entre_si']}")

    # Distribuição de categoria quando cada modelo afirma algo, para ver se
    # convergem no TIPO de resposta mesmo quando divergem no caso a caso.
    for nome, campo in ((nome_a, "a"), (nome_b, "b")):
        cats = Counter(
            getattr(c, campo).categoria
            for c in comparacoes
            if getattr(c, campo) is not None
        )
        if cats:
            print(f"\nCategorias que {nome} afirmou (entre os que respondeu algo):")
            for cat, n in cats.most_common():
                print(f"  {cat}: {n}")

    # Amostra do padrão de risco — até 5 exemplos, não os N inteiros.
    risco = [c for c in comparacoes if c.padrao == "b_afirma_a_recusa"]
    if risco:
        print(f"\nAmostra de '{nome_b} afirma, {nome_a} recusa' ({len(risco)} no "
              f"total, mostrando até 5):")
        for c in risco[:5]:
            print(f"\n  {c.cluster.inicio:%Y-%m-%d} → {c.cluster.fim:%Y-%m-%d} "
                  f"({c.cluster.n_fotos} fotos)")
            print(f"    pastas: {c.cluster.pastas[:3]}"
                  f"{' ...' if len(c.cluster.pastas) > 3 else ''}")
            print(f"    {nome_b}: {c.b.categoria}/{c.b.evento!r} — "
                  f"{c.b.justificativa}")

    if args.detalhe:
        print(f"\n{'='*70}\nDETALHE — todos os {total} clusters\n{'='*70}")
        for i, c in enumerate(comparacoes, 1):
            print(f"\n[{i}] {c.cluster.inicio:%Y-%m-%d} → {c.cluster.fim:%Y-%m-%d} "
                  f"({c.cluster.n_fotos} fotos) — {c.padrao}")
            print(f"    pastas: {c.cluster.pastas}")
            if c.a:
                print(f"    {nome_a}:  {c.a.categoria}/{c.a.evento!r} — {c.a.justificativa}")
            else:
                print(f"    {nome_a}:  null")
            if c.b:
                print(f"    {nome_b}: {c.b.categoria}/{c.b.evento!r} — {c.b.justificativa}")
            else:
                print(f"    {nome_b}: null")


if __name__ == "__main__":
    main()
