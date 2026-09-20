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


def _sessao(pastas, horas=0, dias=0, pais=None, dist=None, pernas=()):
    return DadosSessao(
        pastas=tuple(pastas),
        duracao=timedelta(days=dias, hours=horas),
        pais_dominante=pais,
        dist_mediana_casa_km=dist,
        periodo_curto="Viagem de 01-01 a 05-01",
        paises_no_tempo=tuple(pernas),
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
    # D-073: pasta cronológica (mês por extenso + dia, ano na pasta-mãe)
    # virava "nome de álbum" e a regra 6 promovia a evento falso — achado
    # 5 de D-069, 3.220 fotos reais do acervo.
    Cenario("pasta cronológica 'mês dia' sem ano, 2h",
            _sessao(["/Users/a/Pictures/2009/novembro 30"], horas=2),
            "neutra"),
    Cenario("pasta cronológica 'dia de mês de ano' por extenso, 2h",
            _sessao(["/Users/a/Pictures/2016/29 de outubro de 2016"], horas=2),
            "neutra"),
    # — viagens —
    Cenario("pasta Viagens/, 1 dia",
            _sessao(["/fotos/Viagens/Praia"], dias=1), "viagem"),
    Cenario("país na pasta, 2h",
            _sessao(["/fotos/Japão/Tóquio"], horas=2), "viagem"),
    # D-082: pasta que lista destinos com hífen, ano ou conector — 8.690
    # fotos reais em "Não classificadas" porque o reconhecedor exigia o
    # segmento inteiro igual ao nome do país.
    Cenario("pasta 'Peru-Bolivia-Chile', 20 dias",
            _sessao(["/Volumes/photo/Portfolio/Viagens Antigas/Peru-Bolivia-Chile"],
                    dias=20), "viagem"),
    Cenario("pasta 'Italia e Franca 2013', 12 dias",
            _sessao(["/Volumes/photo/Portfolio/Viagens Antigas/Italia e Franca 2013"],
                    dias=12), "viagem"),
    Cenario("pasta 'Chile e Atacama Abr.18', 7 dias",
            _sessao(["/Volumes/photo/Portfolio/Chile e Atacama Abr.18/[Developed]"],
                    dias=7), "viagem"),
    Cenario("pasta 'Carnaval 2016 - Portugal e Espanha', 6 dias",
            _sessao(["/Volumes/photo/Portfolio/Fotos Organizadas/Carnaval 2016 - Portugal e Espanha"],
                    dias=6), "viagem"),
    # Guardas: homônimo de país não vira viagem — bairro com sigla de
    # estado, aniversário com nome de país, abreviação solta.
    Cenario("estádio em Guadalupe, RJ (bairro homônimo de país), 3h",
            _sessao(["/Volumes/photo/Portfolio/Fotos Organizadas/"
                     "Estádio Nilton Santos - Guadalupe, RJ, 18 de agosto de 2016"],
                    horas=3, pais="Brasil", dist=12.0), "evento"),
    Cenario("pasta 'Guadalupe - RJ', 3h",
            _sessao(["/fotos/Guadalupe - RJ"], horas=3, pais="Brasil", dist=12.0),
            "evento"),
    Cenario("aniversário 'Georgia 15 Anos', 5h",
            _sessao(["/fotos/Georgia 15 Anos"], horas=5), "evento"),
    Cenario("pasta 'Serra - ES' (abreviação de Serra Leoa), 4h",
            _sessao(["/fotos/Serra - ES"], horas=4, pais="Brasil", dist=8.0),
            "evento"),
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
    # — multi-país (caso real: Dubai, Thai & Viet, 21 dias) —
    Cenario("viagem multi-país, 21 dias, 9000km de casa",
            _sessao(["/fotos/DCIM"], dias=21, pais="Tailândia", dist=9000.0,
                    pernas=("Emirados Árabes", "Tailândia", "Vietnã")),
            "viagem"),
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
