"""Classificador de sessões — a cascata determinística como função pura.

Separado do motor para ser testável cenário a cenário e comparável entre
variantes de configuração (scripts/avaliar_agrupamento.py). A decisão é
tomada só com os dados da sessão; coleta de GPS/geocoding fica no motor.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import timedelta

from fotoorganizer.grouping.albuns import escolher_album
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
    # Nomeações de álbum de catálogo externo que cobrem o período da sessão:
    # {nome do álbum: fotos daquele período nele}. Só NOMEIA (D-030) — o
    # tipo da sessão é decidido sem olhar para cá.
    albuns: tuple[tuple[str, int], ...] = ()
    # De onde vieram esses álbuns, para a justificativa citar ("Apple Fotos").
    fonte_dos_albuns: str = "catálogo externo"
    # Câmeras conhecidas do acervo, normalizadas — `album_nomeia` precisa
    # delas para descartar álbum que é nome de aparelho.
    cameras: frozenset[str] = frozenset()
    # O que cada NOME de pasta significa: lugar, ocasião, pessoa ou ruído
    # (`fotoorganizer/classification/lexico.py`). Vazio quando o léxico está
    # desligado — e aí a cascata decide exatamente como decidia antes.
    tipos_de_nome: tuple[tuple[str, str], ...] = ()

    def tipo_do_nome(self, nome: str) -> str | None:
        for chave, tipo in self.tipos_de_nome:
            if chave == nome:
                return tipo
        return None


@dataclass(frozen=True, slots=True)
class Decisao:
    tipo: str                       # viagem | evento | neutra
    rotulo: str | None
    origem: str
    justificativa: str
    # Origem só do RÓTULO. Separada de `origem` porque as duas podem
    # divergir: a sessão pode ser viagem pelo GPS (`geocoding_offline`) e o
    # nome vir do álbum (`album_externo`). A categoria continua citando
    # `origem`; a evidência de viagem/evento, cujo valor É o rótulo, cita
    # esta.
    origem_do_rotulo: str = ""
    # True quando o rótulo é um segmento de pasta escrito pelo dono. É o
    # que dá a pasta a prioridade sobre o álbum (docs/AGRUPAMENTO.md, 2c).
    rotulo_de_pasta: bool = False

    def __post_init__(self) -> None:
        if not self.origem_do_rotulo:
            object.__setattr__(self, "origem_do_rotulo", self.origem)


NEUTRA = Decisao("neutra", None, "agrupamento", "")

# Origem das evidências cujo valor é um nome de álbum de catálogo externo.
ORIGEM_ALBUM = "album_externo"


def classificar_sessao(
    dados: DadosSessao,
    config: ConfigClassificacao = ConfigClassificacao(),
) -> Decisao:
    """Tipo e nome da sessão. O tipo sai da cascata determinística; o nome
    pode ser melhorado por álbum de catálogo externo, nunca o tipo."""
    return _nomear_por_album(_cascata(dados, config), dados)


def _nomear_por_album(decisao: Decisao, dados: DadosSessao) -> Decisao:
    """Álbum entra como NOME, e só onde não há nome do dono (D-030).

    Três limites, nesta ordem:

    - **Não cria acontecimento.** Sessão neutra continua neutra: nomear o
      que a cascata não classificou seria detectar evento por álbum, que é
      exatamente o que D-030 proíbe (os álbuns se aninham — a mesma foto
      em três deles no mesmo dia).
    - **Pasta ganha.** Quando o rótulo já é um segmento de pasta, o álbum
      não entra. A pasta é uma decisão de arrumação única por foto e já
      testada nos 17 cenários de `scripts/avaliar_agrupamento.py`; o álbum
      é múltiplo por foto e precisou de um desempate inventado.
    - **Só substitui nome derivado.** O que o álbum troca é país
      geocodificado ("Brasil") ou período ("Viagem de 08-07 a 11-07") —
      rótulos que descrevem quando e onde, não o quê.
    """
    if decisao.tipo == "neutra" or decisao.rotulo_de_pasta or not dados.albuns:
        return decisao
    escolhido = escolher_album(dict(dados.albuns), dados.cameras)
    if escolhido is None:
        return decisao
    nome, fotos = escolhido
    if nome == decisao.rotulo:
        return decisao
    justificativa = (
        f"{decisao.justificativa}; nome do álbum '{nome}' "
        f"({dados.fonte_dos_albuns}), que cobre {fotos} fotos deste período"
    ).lstrip("; ")
    return Decisao(
        tipo=decisao.tipo, rotulo=nome, origem=decisao.origem,
        justificativa=justificativa, origem_do_rotulo=ORIGEM_ALBUM,
    )


def _cascata(
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
        # O rótulo aqui é derivado (país geocodificado, pernas ou
        # período): mesmo quando a REGRA veio da pasta, o NOME não veio —
        # é justamente onde o álbum pode entrar.
        return Decisao("viagem", rotulo, origem, justificativa,
                       rotulo_de_pasta=False)

    # 1. Pasta de categoria "Viagens" no caminho.
    for pasta in dados.pastas:
        for segmento in pasta.split("/"):
            if _normalizar(segmento) in _PASTAS_VIAGEM:
                return viagem("pasta", f"pasta '{segmento}' no caminho")

    # 2. Palavra-chave de evento na pasta (Serena 15 Anos, Casamento…).
    evento, de_keyword = extrair_evento(list(dados.pastas))
    if evento and de_keyword:
        return Decisao("evento", evento, "pasta",
                       f"pasta '{evento}' indica um evento",
                       rotulo_de_pasta=True)

    # 3. Países reconhecidos no nome das pastas.
    #
    # Uma pasta pode listar a viagem inteira ("Dubai, Thai & Viet"), e
    # essa lista vale mais que as pernas deduzidas do GPS: a cobertura de
    # coordenada é irregular (nessa viagem, 106 fotos de 2.405 tinham
    # GPS, nenhuma nos Emirados), enquanto o nome que o dono escreveu
    # cobre a viagem toda.
    # Detecta com a tabela canônica, mas NOMEIA com as palavras do dono:
    # "Dubai, Thai & Viet" diz o mesmo que "Emirados Árabes Unidos –
    # Tailândia – Vietnã" em menos da metade do comprimento, e é como ele
    # já chama a viagem. Os países reconhecidos ficam na justificativa.
    for pasta in dados.pastas:
        for segmento in reversed([s for s in pasta.split("/") if s]):
            paises = identificar_paises(segmento)
            if len(paises) >= 2:
                return Decisao(
                    "viagem", segmento.strip(), "pasta",
                    f"pasta '{segmento}' lista {len(paises)} destinos: "
                    f"{', '.join(paises)}",
                    rotulo_de_pasta=True,
                )
    for pasta in dados.pastas:
        hierarquia = extrair_hierarquia_da_pasta(pasta)
        if hierarquia.pais:
            # O país foi LIDO da pasta — é palavra do dono, não dedução do
            # GPS, então o álbum não passa por cima dele.
            decisao = viagem(
                "pasta",
                f"país reconhecido na pasta ('{hierarquia.segmento_pais}')",
                pais=hierarquia.pais,
            )
            return replace(decisao, rotulo_de_pasta=True)

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

    # 6. Nome de álbum + sessão curta = evento nomeado (Quizomba) — a menos
    #    que o nome seja um LUGAR, e aí é viagem nomeada pelo lugar.
    #
    #    A cascata sabe medir duração e distância; não tem como saber que
    #    "Pantanal" é destino de viagem e "Quizomba" é festa. Sem o léxico,
    #    a regra caía sempre em evento — foi o que mandou Pantanal (1d23h) e
    #    Visconde de Mauá (18 fotos, 0h) para Eventos no acervo do dono. Com
    #    o léxico desligado, `tipo_do_nome` devolve None e nada muda.
    if evento and dados.duracao <= config.duracao_max_evento:
        if dados.tipo_do_nome(evento) == "lugar":
            return Decisao(
                "viagem", evento, "lexico",
                f"'{evento}' é um lugar, não um acontecimento",
                rotulo_de_pasta=True,
            )
        return Decisao(
            "evento", evento, "pasta",
            f"pasta '{evento}' nomeia uma sessão de "
            f"{max(dados.duracao.days, 1)} dia(s)",
            rotulo_de_pasta=True,
        )

    # 7. Sem veredito — um cluster de horas NUNCA vira viagem sozinho.
    return NEUTRA
