#!/usr/bin/env python3
"""Mede quantas sessões do acervo real cairiam em "neutra" e chamariam o
advisor LLM — o achado 4 da revisão de `docs/PLANO_IA_E_PRODUTO.md`
(fase 5): o "zero de 63" citado ali (`:56`) é do catálogo de demonstração
sintético, nunca do acervo real. Este script mede o número de verdade.

SEM CHAMAR O ADVISOR DE VERDADE: nenhum dado sai da máquina (invariante 4,
e a instalação de dependência/credencial de API é Classe C — sempre espera
aprovação, não é decidida por medição). `CountingNullAdvisor` (abaixo)
implementa o mesmo `Protocol` de
`fotoorganizer/classification/advisor.py::ClassificationAdvisor` que
`NullAdvisor` já implementa — `classificar()` nunca faz I/O de rede, só
conta a chamada e devolve `None` ("sem opinião"), exatamente como
`NullAdvisor.classificar` já faz. `local=True` pelo mesmo motivo de
`NullAdvisor`. A única diferença é a contagem.

O catálogo original é aberto SOMENTE LEITURA; o motor roda sobre uma CÓPIA
em pasta temporária (via `sqlite3.Connection.backup`, mesmo padrão de
`scripts/medir_nome_de_album.py` — WAL exige `.backup`, não `cp`), apagada
no fim. Nenhum arquivo de foto é tocado (invariante 1).

Uso:
    .venv/bin/python scripts/medir_uso_do_advisor.py
    .venv/bin/python scripts/medir_uso_do_advisor.py --db <catalog.db>
    .venv/bin/python scripts/medir_uso_do_advisor.py --exportar-periodos clusters_neutra.json
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fotoorganizer.classification.advisor import AdvisorResult, ClusterInfo  # noqa: E402
from fotoorganizer.config import paths  # noqa: E402


@dataclass
class CountingNullAdvisor:
    """Mesma promessa de `NullAdvisor` — nenhum dado sai da máquina, nenhuma
    opinião — só que registra CADA chamada para medição. `classificar` não
    importa `anthropic`, não abre socket, não lê credencial nenhuma: é uma
    lista Python recebendo um dataclass já montado em memória pelo motor."""

    chamadas: list[ClusterInfo] = field(default_factory=list)

    @property
    def local(self) -> bool:
        return True

    def classificar(self, cluster: ClusterInfo) -> AdvisorResult | None:
        self.chamadas.append(cluster)
        return None


def _copiar_para_temp(origem: Path, destino: Path) -> None:
    origem_con = sqlite3.connect(f"file:{origem}?mode=ro", uri=True)
    destino_con = sqlite3.connect(destino)
    try:
        with destino_con:
            origem_con.backup(destino_con)
    finally:
        origem_con.close()
        destino_con.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=paths.default_db_path())
    parser.add_argument(
        "--exportar-periodos", type=Path, default=None,
        help="grava (início, fim, n_fotos) de TODAS as sessões neutra em "
             "JSON — só datas e contagem, sem pasta nem nome de arquivo. "
             "Existe para não precisar rodar a passada completa (~1h40) de "
             "novo só para pegar os períodos de uma comparação de modelos.",
    )
    args = parser.parse_args()

    if not args.db.is_file():
        raise SystemExit(f"catálogo não encontrado: {args.db}")

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from fotoorganizer.classification import SuggestionEngine
    from fotoorganizer.geolocation import LocationResolver
    from fotoorganizer.geolocation.offline import OfflineGeocoder

    advisor = CountingNullAdvisor()

    with tempfile.TemporaryDirectory(prefix="medir-advisor-") as tmp:
        copia = Path(tmp) / "catalog.db"
        _copiar_para_temp(args.db, copia)

        engine = create_engine(f"sqlite:///{copia}")
        motor = SuggestionEngine(
            sessionmaker(engine),
            LocationResolver(OfflineGeocoder()),
            advisor=advisor,
        )
        resultado = motor.gerar()
        engine.dispose()

    total_sessoes = resultado["viagens"] + resultado["eventos"] + len(advisor.chamadas)
    # ^ `gerar()` só devolve contagem de viagem/evento (engine.py:286-287);
    # sessões "neutra" não têm contador próprio no retorno — mas cada uma
    # passou por `_consultar_advisor` exatamente uma vez (engine.py:389-390),
    # então len(advisor.chamadas) É a contagem de sessões neutra.

    print(f"catálogo: {args.db}")
    print(f"sugestões geradas nesta passada: {resultado['sugestoes']}")
    print(f"sugestões preservadas (já decididas, fora da regeneração): "
          f"{resultado['preservadas']}")
    print()
    print(f"sessões viagem:  {resultado['viagens']}")
    print(f"sessões evento:  {resultado['eventos']}")
    print(f"sessões neutra:  {len(advisor.chamadas)}  "
          f"(= chamadas ao advisor, se ele estivesse ligado)")
    print(f"total de sessões: {total_sessoes}")
    if total_sessoes:
        pct = 100 * len(advisor.chamadas) / total_sessoes
        print(f"proporção neutra/total: {pct:.2f}%")

    if advisor.chamadas:
        fotos = [c.n_fotos for c in advisor.chamadas]
        print(f"\nfotos cobertas pelas sessões neutra: {sum(fotos)}")
        print(f"fotos por sessão neutra — min={min(fotos)} "
              f"média={sum(fotos)/len(fotos):.1f} max={max(fotos)}")
        # Amostra para conferência manual — até 10 sessões, período e
        # tamanho, sem nome de arquivo nem pasta (informação só entraria se
        # alguém abrisse o cluster de verdade; aqui é só para o dono
        # confirmar que os casos fazem sentido como "resíduo genuíno").
        print("\namostra de até 10 sessões neutra (período, n_fotos):")
        for cluster in advisor.chamadas[:10]:
            print(f"  {cluster.inicio:%Y-%m-%d} → {cluster.fim:%Y-%m-%d}: "
                  f"{cluster.n_fotos} fotos")

    if args.exportar_periodos:
        dados = [
            {
                "inicio": c.inicio.date().isoformat(),
                "fim": c.fim.date().isoformat(),
                "n_fotos": c.n_fotos,
            }
            for c in advisor.chamadas
        ]
        args.exportar_periodos.write_text(
            json.dumps(dados, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"\nperíodos das {len(dados)} sessões neutra exportados para "
              f"{args.exportar_periodos}")


if __name__ == "__main__":
    main()
