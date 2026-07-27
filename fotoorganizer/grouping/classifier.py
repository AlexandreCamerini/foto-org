"""Classificador de sessões — a cascata determinística como função pura.

Separado do motor para ser testável cenário a cenário e comparável entre
variantes de configuração (scripts/avaliar_agrupamento.py). A decisão é
tomada só com os dados da sessão; coleta de GPS/geocoding fica no motor.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from fotoorganizer.grouping.eventos import extrair_evento
from fotoorganizer.geolocation import extrair_hierarquia_da_pasta
from fotoorganizer.geolocation.folder_names import _normalizar
from fotoorganizer.geolocation.paises import identificar_paises

_PASTAS_VIAGEM = {"viagens", "viagem"}


@dataclass(frozen=True, slots=True)
class ConfigClassificacao:
    # Estadia mínima para GPS geocodificado virar viagem (regra 5).
    duracao_min_viagem: timedelta = timedelta(days=3)
    # Duração máxima para nome de álbum virar evento (regra 6).
    duracao_max_evento: timedelta = timedelta(days=2)
    # Distância mediana até casa que caracteriza deslocamento (regra 4).
    dist_viagem_km: float = 100.0
    # Raio em torno da casa para o corte de sessões por transição
    # casa↔fora (viagens coladas com < GAP_NOVA_VIAGEM em casa no meio).
    raio_casa_km: float = 50.0
    # Regra 5 só vale quando a casa é desconhecida: com casa conhecida, a
    # regra 4 (distância) é quem decide — senão férias EM CASA virariam
    # "viagem" só por durarem dias com GPS.
    estadia_exige_casa_desconhecida: bool = True


@dataclass(frozen=True, slots=True)
class DadosSessao:
    pastas: tuple[str, ...]
    duracao: timedelta
    pais_dominante: str | None      # via geocoding dos membros com GPS
    dist_mediana_casa_km: float | None  # None = sem casa conhecida ou sem GPS
    periodo_curto: str              # rótulo de fallback ("Viagem de dd-mm…")
    # Países da sessão em ordem cronológica de chegada (só os relevantes) —
    # ≥ 2 entradas indicam viagem multi-país (Dubai → Tailândia → Vietnã).
    paises_no_tempo: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Decisao:
    tipo: str                       # viagem | evento | neutra
    rotulo: str | None
    origem: str
    justificativa: str


NEUTRA = Decisao("neutra", None, "agrupamento", "")


def classificar_sessao(
    dados: DadosSessao,
    config: ConfigClassificacao = ConfigClassificacao(),
) -> Decisao:
    def viagem(origem: str, justificativa: str, pais: str | None = None) -> Decisao:
        if pais:
            rotulo = pais
        elif len(dados.paises_no_tempo) >= 2:
            # Multi-país: as pernas em ordem cronológica nomeiam a viagem.
            rotulo = " – ".join(dados.paises_no_tempo)
        else:
            rotulo = dados.pais_dominante or dados.periodo_curto
        return Decisao("viagem", rotulo, origem, justificativa)

    # 1. Pasta de categoria "Viagens" no caminho.
    for pasta in dados.pastas:
        for segmento in pasta.split("/"):
            if _normalizar(segmento) in _PASTAS_VIAGEM:
                return viagem("pasta", f"pasta '{segmento}' no caminho")

    # 2. Palavra-chave de evento na pasta (Serena 15 Anos, Casamento…).
    evento, de_keyword = extrair_evento(list(dados.pastas))
    if evento and de_keyword:
        return Decisao("evento", evento, "pasta",
                       f"pasta '{evento}' indica um evento")

    # 3. Países reconhecidos no nome das pastas.
    #
    # Uma pasta pode listar a viagem inteira ("Dubai, Thai & Viet"), e
    # essa lista vale mais que as pernas deduzidas do GPS: a cobertura de
    # coordenada é irregular (nessa viagem, 106 fotos de 2.405 tinham
    # GPS, nenhuma nos Emirados), enquanto o nome que o dono escreveu
    # cobre a viagem toda.
    for pasta in dados.pastas:
        for segmento in reversed([s for s in pasta.split("/") if s]):
            paises = identificar_paises(segmento)
            if len(paises) >= 2:
                return Decisao(
                    "viagem", " – ".join(paises), "pasta",
                    f"pasta '{segmento}' lista {len(paises)} destinos",
                )
    for pasta in dados.pastas:
        hierarquia = extrair_hierarquia_da_pasta(pasta)
        if hierarquia.pais:
            return viagem(
                "pasta",
                f"país reconhecido na pasta ('{hierarquia.segmento_pais}')",
                pais=hierarquia.pais,
            )

    # 4. Deslocamento: longe de casa.
    if (dados.dist_mediana_casa_km is not None
            and dados.dist_mediana_casa_km > config.dist_viagem_km):
        return viagem(
            "gps", f"fotos a ~{dados.dist_mediana_casa_km:.0f} km de casa"
        )

    # 5. Estadia geocodificada: país conhecido e vários dias.
    if (dados.pais_dominante
            and dados.duracao >= config.duracao_min_viagem
            and (not config.estadia_exige_casa_desconhecida
                 or dados.dist_mediana_casa_km is None)):
        return viagem(
            "geocoding_offline",
            f"fotos com GPS em {dados.pais_dominante} ao longo de "
            f"{dados.duracao.days + 1} dias",
        )

    # 6. Nome de álbum + sessão curta = evento nomeado (Quizomba).
    if evento and dados.duracao <= config.duracao_max_evento:
        return Decisao(
            "evento", evento, "pasta",
            f"pasta '{evento}' nomeia uma sessão de "
            f"{max(dados.duracao.days, 1)} dia(s)",
        )

    # 7. Sem veredito — um cluster de horas NUNCA vira viagem sozinho.
    return NEUTRA
