"""Avalia variantes do modelo de agrupamento contra cenários rotulados.

Uso: .venv/bin/python scripts/avaliar_agrupamento.py

Cada cenário descreve uma sessão real típica (pastas, duração, GPS) e o
tipo esperado. As variantes mudam limiares/regras da cascata; a melhor
vira a ConfigClassificacao padrão. Resultados documentados em
docs/AGRUPAMENTO.md.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fotoorganizer.grouping.classifier import (
    ConfigClassificacao,
    DadosSessao,
    classificar_sessao,
)


@dataclass(frozen=True)
class Cenario:
    nome: str
    dados: DadosSessao
    esperado: str  # viagem | evento | neutra


def _sessao(pastas, horas=0, dias=0, pais=None, dist=None):
    return DadosSessao(
        pastas=tuple(pastas),
        duracao=timedelta(days=dias, hours=horas),
        pais_dominante=pais,
        dist_mediana_casa_km=dist,
        periodo_curto="Viagem de 01-01 a 05-01",
    )


CENARIOS = [
    # — casos reais do catálogo do usuário —
    Cenario("aniversário 15 anos, 5h",
            _sessao(["/Users/a/Pictures/2026/Serena 15 Anos"], horas=5),
            "evento"),
    Cenario("álbum nomeado (Quizomba), 4h",
            _sessao(["/Users/a/Pictures/2026/Quizomba"], horas=4),
            "evento"),
    Cenario("pasta técnica de data, 2h",
            _sessao(["/Users/a/Pictures/2025_05_24/[Originals]"], horas=2),
            "neutra"),
    # — viagens —
    Cenario("pasta Viagens/, 1 dia",
            _sessao(["/fotos/Viagens/Praia"], dias=1), "viagem"),
    Cenario("país na pasta, 2h",
            _sessao(["/fotos/Japão/Tóquio"], horas=2), "viagem"),
    Cenario("GPS 450km de casa, 1 dia",
            _sessao(["/fotos/DCIM"], dias=1, pais="Brasil", dist=450.0),
            "viagem"),
    Cenario("estadia 5 dias, GPS, casa DESCONHECIDA",
            _sessao(["/fotos/exports"], dias=5, pais="França", dist=None),
            "viagem"),
    Cenario("fim de semana 300km de casa",
            _sessao(["/fotos/DCIM"], dias=2, pais="Brasil", dist=300.0),
            "viagem"),
    # — armadilhas: NÃO são viagens —
    Cenario("festa de 4h com GPS em casa",
            _sessao(["/fotos/DCIM"], horas=4, pais="Brasil", dist=3.0),
            "neutra"),
    Cenario("férias EM CASA: 6 dias de GPS a 2km",
            _sessao(["/fotos/DCIM"], dias=6, pais="Brasil", dist=2.0),
            "neutra"),
    Cenario("casamento de fim de semana (keyword)",
            _sessao(["/fotos/Casamento de João e Maria"], dias=2),
            "evento"),
    Cenario("Natal (keyword), 2 dias",
            _sessao(["/fotos/2025/Natal 2025"], dias=2), "evento"),
    Cenario("formatura, 3h",
            _sessao(["/fotos/Formatura da Bia"], horas=3), "evento"),
    Cenario("álbum longo (obra da casa, 10 dias)",
            _sessao(["/fotos/Obra da casa"], dias=10), "neutra"),
    Cenario("home dir + data: nada nomeável",
            _sessao(["/Users/acamerini/Pictures/2025_05_24"], horas=3),
            "neutra"),
    Cenario("sessão de horas, GPS país sem casa",
            _sessao(["/fotos/DCIM"], horas=6, pais="Brasil", dist=None),
            "neutra"),
]

VARIANTES = {
    "A: v4 original (estadia≥3d, sem exigir casa desconhecida)":
        ConfigClassificacao(estadia_exige_casa_desconhecida=False),
    "B: estadia≥2d (pega fins de semana)":
        ConfigClassificacao(duracao_min_viagem=timedelta(days=2),
                            estadia_exige_casa_desconhecida=False),
    "C: álbum vira evento sem limite de duração":
        ConfigClassificacao(duracao_max_evento=timedelta(days=9999),
                            estadia_exige_casa_desconhecida=False),
    "D: estadia só com casa desconhecida (proposta)":
        ConfigClassificacao(),
    "E: D + estadia≥2d":
        ConfigClassificacao(duracao_min_viagem=timedelta(days=2)),
}


def avaliar() -> dict[str, int]:
    placares = {}
    for nome_variante, config in VARIANTES.items():
        acertos = 0
        erros = []
        for cenario in CENARIOS:
            decisao = classificar_sessao(cenario.dados, config)
            if decisao.tipo == cenario.esperado:
                acertos += 1
            else:
                erros.append(
                    f"    ✗ {cenario.nome}: esperado={cenario.esperado} "
                    f"obtido={decisao.tipo}"
                )
        placares[nome_variante] = acertos
        print(f"{acertos:2d}/{len(CENARIOS)}  {nome_variante}")
        for erro in erros:
            print(erro)
    return placares


if __name__ == "__main__":
    print(f"{len(CENARIOS)} cenários rotulados × {len(VARIANTES)} variantes\n")
    placares = avaliar()
    melhor = max(placares, key=placares.get)
    print(f"\nMELHOR: {melhor} ({placares[melhor]}/{len(CENARIOS)})")
