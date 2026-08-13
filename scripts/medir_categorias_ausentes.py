#!/usr/bin/env python3
"""Mede, entre as sessões "neutra" do acervo real, que fração concentra
padrão de nome de WhatsApp ou de captura de tela — a hipótese registrada em
D-053 (`docs/DECISOES.md`): parte dos 39,10% de sessões "neutra" (D-047)
pode não ser falta de evidência para Viagens/Família/Eventos, mas conteúdo
que genuinamente não é nenhuma das três.

SEM CHAMAR O ADVISOR DE VERDADE: mesmo padrão de
`scripts/medir_uso_do_advisor.py` — `CountingNullAdvisor` nunca faz I/O de
rede, `local=True` pelo mesmo motivo do `NullAdvisor` do motor. Este script
INSTRUMENTA `SuggestionEngine._consultar_advisor` por monkeypatch A PARTIR
DAQUI, em tempo de execução — nenhum arquivo de `fotoorganizer/**` é
editado — para capturar a lista COMPLETA de membros de cada sessão
"neutra". O `ClusterInfo` que o advisor recebe carrega só 8 nomes de
exemplo (`engine.py:562`, `membros[:8]`), insuficiente para medir
proporção dentro da sessão.

O catálogo original é aberto SOMENTE LEITURA; o motor roda sobre uma CÓPIA
em pasta temporária (`sqlite3.Connection.backup`, mesmo padrão de
`scripts/medir_nome_de_album.py`), apagada no fim. Nenhum arquivo de foto
é tocado (invariante 1).

Sinais medidos, por conservadorismo (a pesquisa de D-053 já registrou que
detectar screenshot só por resolução é ruidoso — comunidade do Immich
relatou falso positivo):
- padrão de nome do WhatsApp (`IMG-YYYYMMDD-WAxxxx`) — formato fixo do
  exportador do próprio app, não é heurística frágil;
- nome começando com "Screenshot"/"Captura de Tela" — carimbo do SO,
  conservador (não pega quem renomeou o arquivo);
- PNG sem câmera (make/model nulos) — sinal mais fraco, reportado à parte.

Uso:
    .venv/bin/python scripts/medir_categorias_ausentes.py
    .venv/bin/python scripts/medir_categorias_ausentes.py --db <catalog.db>
    .venv/bin/python scripts/medir_categorias_ausentes.py --exportar-amostra amostra.json
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fotoorganizer.config import paths  # noqa: E402

# IMG-20230101-WA0001.jpg / VID-20230101-WA0001.mp4 — formato fixo do
# exportador do WhatsApp, documentado e estável entre versões do app.
_PADRAO_WHATSAPP = re.compile(r"^(IMG|VID)-\d{8}-WA\d+", re.IGNORECASE)
# Carimbo que o próprio SO grava em captura de tela — conservador: não
# pega quem renomeou o arquivo depois.
_PADRAO_SCREENSHOT_NOME = re.compile(
    r"^(screenshot|screen shot|captura de tela|captura_de_tela)",
    re.IGNORECASE,
)
_LIMIAR_DOMINANCIA = 0.8  # sessão "é isso" quando >=80% dos membros batem


def _copiar_para_temp(origem: Path, destino: Path) -> None:
    origem_con = sqlite3.connect(f"file:{origem}?mode=ro", uri=True)
    destino_con = sqlite3.connect(destino)
    try:
        with destino_con:
            origem_con.backup(destino_con)
    finally:
        origem_con.close()
        destino_con.close()


@dataclass
class _SessaoCapturada:
    inicio: object
    fim: object
    n_fotos: int
    nomes: list[str]
    extensoes: list[str]
    cameras: list[tuple[str | None, str | None]]

    def pct_whatsapp(self) -> float:
        return sum(1 for n in self.nomes if _PADRAO_WHATSAPP.match(n)) / len(self.nomes)

    def pct_screenshot_nome(self) -> float:
        return sum(
            1 for n in self.nomes if _PADRAO_SCREENSHOT_NOME.match(n)
        ) / len(self.nomes)

    def pct_png_sem_camera(self) -> float:
        return sum(
            1 for n, ext, cam in zip(self.nomes, self.extensoes, self.cameras)
            if ext.lower() == "png" and cam == (None, None)
        ) / len(self.nomes)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=paths.default_db_path())
    parser.add_argument(
        "--exportar-amostra", type=Path, default=None,
        help="grava (período, n_fotos, %% whatsapp, %% screenshot-por-nome, "
             "%% png-sem-câmera) de todas as sessões neutra em JSON — sem "
             "nome de arquivo individual.",
    )
    args = parser.parse_args()

    if not args.db.is_file():
        raise SystemExit(f"catálogo não encontrado: {args.db}")

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from fotoorganizer.classification import SuggestionEngine
    from fotoorganizer.classification.advisor import AdvisorResult, ClusterInfo
    from fotoorganizer.geolocation import LocationResolver
    from fotoorganizer.geolocation.offline import OfflineGeocoder

    @dataclass
    class CountingNullAdvisor:
        chamadas: list[ClusterInfo] = field(default_factory=list)

        @property
        def local(self) -> bool:
            return True

        def classificar(self, cluster: ClusterInfo) -> AdvisorResult | None:
            self.chamadas.append(cluster)
            return None

    capturadas: list[_SessaoCapturada] = []
    original = SuggestionEngine._consultar_advisor

    def _instrumentado(self, sessao, membros):
        capturadas.append(_SessaoCapturada(
            inicio=sessao.draft.inicio,
            fim=sessao.draft.fim,
            n_fotos=sessao.draft.n_fotos,
            nomes=[m.nome for m in membros],
            extensoes=[m.extensao for m in membros],
            cameras=[(m.make, m.model) for m in membros],
        ))
        return original(self, sessao, membros)

    SuggestionEngine._consultar_advisor = _instrumentado
    try:
        advisor = CountingNullAdvisor()
        with tempfile.TemporaryDirectory(prefix="medir-categorias-") as tmp:
            copia = Path(tmp) / "catalog.db"
            _copiar_para_temp(args.db, copia)

            engine = create_engine(f"sqlite:///{copia}")
            motor = SuggestionEngine(
                sessionmaker(engine),
                LocationResolver(OfflineGeocoder()),
                advisor=advisor,
            )
            motor.gerar()
            engine.dispose()
    finally:
        SuggestionEngine._consultar_advisor = original

    print(f"catálogo: {args.db}")
    print(f"sessões neutra: {len(capturadas)}")
    if not capturadas:
        return

    dominadas_wa = [s for s in capturadas if s.pct_whatsapp() >= _LIMIAR_DOMINANCIA]
    dominadas_ss = [
        s for s in capturadas if s.pct_screenshot_nome() >= _LIMIAR_DOMINANCIA
    ]
    dominadas_png = [
        s for s in capturadas if s.pct_png_sem_camera() >= _LIMIAR_DOMINANCIA
    ]
    total = len(capturadas)

    print(f"\nsessões neutra dominadas (>={_LIMIAR_DOMINANCIA:.0%} dos membros) "
          f"por padrão de nome do WhatsApp: {len(dominadas_wa)} "
          f"({100 * len(dominadas_wa) / total:.1f}%)")
    print(f"sessões neutra dominadas por nome de captura de tela: "
          f"{len(dominadas_ss)} ({100 * len(dominadas_ss) / total:.1f}%)")
    print(f"sessões neutra dominadas por PNG sem câmera (sinal mais fraco, "
          f"ruidoso conforme pesquisa de D-053): {len(dominadas_png)} "
          f"({100 * len(dominadas_png) / total:.1f}%)")

    cobertas = {id(s) for s in dominadas_wa} | {id(s) for s in dominadas_ss}
    fotos_cobertas = sum(s.n_fotos for s in capturadas if id(s) in cobertas)
    fotos_neutra_total = sum(s.n_fotos for s in capturadas)
    pct_fotos = 100 * fotos_cobertas / fotos_neutra_total if fotos_neutra_total else 0.0
    print(f"\nfotos em sessão neutra explicadas por WhatsApp OU nome de "
          f"screenshot (sinais fortes, sem sobrepor): {fotos_cobertas}/"
          f"{fotos_neutra_total} ({pct_fotos:.1f}% das fotos em sessão neutra)")

    print("\namostra de até 10 sessões neutra dominadas por sinal forte "
          "(período, n_fotos, sinal):")
    mostradas = 0
    for s in capturadas:
        if id(s) not in cobertas or mostradas >= 10:
            continue
        sinal = "whatsapp" if s.pct_whatsapp() >= _LIMIAR_DOMINANCIA else "screenshot"
        print(f"  {s.inicio:%Y-%m-%d} → {s.fim:%Y-%m-%d}: {s.n_fotos} fotos "
              f"({sinal})")
        mostradas += 1

    if args.exportar_amostra:
        dados = [
            {
                "inicio": s.inicio.date().isoformat(),
                "fim": s.fim.date().isoformat(),
                "n_fotos": s.n_fotos,
                "pct_whatsapp": round(s.pct_whatsapp(), 3),
                "pct_screenshot_nome": round(s.pct_screenshot_nome(), 3),
                "pct_png_sem_camera": round(s.pct_png_sem_camera(), 3),
            }
            for s in capturadas
        ]
        args.exportar_amostra.write_text(
            json.dumps(dados, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"\namostra completa exportada para {args.exportar_amostra}")


if __name__ == "__main__":
    main()
