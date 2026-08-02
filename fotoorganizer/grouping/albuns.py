"""Que álbum de catálogo externo nomeia um conjunto de fotos — e qual não.

Álbum é a coisa mais próxima de uma resposta pronta que existe: o dono já
disse "estas fotos são a viagem a Portugal". Mas a lista real mistura três
coisas com a mesma cara:

    Portugal e Italia com as Meninas   3.729   viagem — nomeia
    Canon EOS 5D Mark IV               4.887   câmera — não nomeia
    WhatsApp                           1.441   app    — não nomeia

O maior álbum de um acervo real era o nome de uma câmera, e o mais próximo no
tempo da foto média era "WhatsApp". Herdar sem filtrar batizaria os eventos do
dono com o nome do aparelho e do mensageiro.

Os dois casos ruins têm marca própria:

- **Câmera** se reconhece por dois caminhos, e são necessários os dois. O
  catálogo conhece as câmeras cujas fotos estão ao alcance, e um filtro que
  aprende do acervo não envelhece quando o dono compra outra. Mas a câmera
  antiga, cujas fotos foram para o disco na gaveta, não está lá: num acervo
  real o maior álbum era "Canon EOS 5D Mark IV" e o catálogo alcançável só
  conhecia quatro modelos, nenhum deles esse. Daí a marca também entrar por
  vocabulário.
- **App e serviço** compartilham vocabulário com o detector de tipo de
  imagem (`grouping/origens.py`), que precisa dos mesmos nomes para saber que
  a foto foi recebida ou baixada.

Sobrando os álbuns que nomeiam, ainda falta escolher UM: os álbuns se
aninham (D-030) e a mesma foto está em "Férias", em "Portugal e Italia com
as Meninas" e em "Family" ao mesmo tempo. `escolher_album` é esse desempate
— documentado em `docs/AGRUPAMENTO.md`, seção 2c.
"""

from __future__ import annotations

import re
from collections.abc import Mapping

from fotoorganizer.grouping.datas import separar_data
from fotoorganizer.grouping.origens import (
    PASTAS_BAIXADA,
    PASTAS_CAPTURA,
    PASTAS_RECEBIDA,
)
from fotoorganizer.geolocation.folder_names import _normalizar

# Serviços e aparelhos que dão nome a álbum automático e não a acontecimento.
# O que é mensageiro, captura ou download vem do detector de tipo — os mesmos
# nomes, um vocabulário só.
_APPS = frozenset(
    {"instagram", "twitter", "x", "facebook", "flickr", "tiktok", "snapchat",
     "linkedin", "pinterest", "dropbox", "icloud", "email", "e-mail",
     "airdrop", "drone", "gopro", "print", "prints", "recentes", "recents",
     "favoritos", "favorites", "importados", "imported", "sem titulo",
     "untitled", "novo album", "new album"}
    | {_normalizar(p) for p in PASTAS_RECEBIDA}
    | {_normalizar(p) for p in PASTAS_CAPTURA}
    | {_normalizar(p) for p in PASTAS_BAIXADA}
)

# "Salvo do Flickr", "GoPro Album", "Fotos do WhatsApp": o serviço aparece
# dentro de uma frase curta de arrumação.
_RE_SERVICO = re.compile(
    r"\b(" + "|".join(sorted(map(re.escape, _APPS))) + r")\b"
)

# Marcas e linhas de equipamento. Existem porque a câmera que gerou o álbum
# pode não estar no catálogo alcançável — ver o comentário do módulo. É lista
# de MARCA, não de modelo: modelo novo sai sozinho ("Canon EOS R7").
_MARCAS = (
    "canon", "nikon", "sony", "fujifilm", "fuji", "olympus", "panasonic",
    "lumix", "leica", "pentax", "sigma", "hasselblad", "phase one",
    "iphone", "ipad", "ipod", "pixel", "galaxy", "xiaomi", "motorola",
    "eos", "nikkor", "alpha", "dji", "mavic", "insta360",
)
_RE_MARCA = re.compile(r"\b(" + "|".join(_MARCAS) + r")\b")

_MIN_CARACTERES = 3


def _e_camera(norm: str, cameras: frozenset[str]) -> bool:
    """O nome é (ou contém) equipamento, conhecido do acervo ou pela marca."""
    if norm in cameras:
        return True
    # "Fotos da Canon EOS R6m2" — a câmera aparece dentro da frase.
    if any(cam and cam in norm for cam in cameras if len(cam) >= 8):
        return True
    return bool(_RE_MARCA.search(norm))


def album_nomeia(nome: str, cameras: frozenset[str] = frozenset()) -> bool:
    """True quando o álbum nomeia um acontecimento.

    `cameras` vem do catálogo (make/model já vistos), normalizadas.
    """
    norm = _normalizar(nome or "")
    if len(norm) < _MIN_CARACTERES:
        return False
    if norm in _APPS or _RE_SERVICO.search(norm):
        return False
    if _e_camera(norm, cameras):
        return False
    # Só dígitos e pontuação ("2019", "01") descreve quando, não o quê — e a
    # data já é tratada em outro lugar da cascata.
    return bool(re.search(r"[a-z]", norm))


# Prateleiras: nomes de álbum que dizem em que gaveta a foto foi guardada,
# não o que aconteceu. É o equivalente, no catálogo externo, das pastas
# contêiner de `grouping/eventos.py` ("Portfolio", "Acervo", "Diversos").
#
# Diferença deliberada: pasta contêiner é REJEITADA, prateleira é apenas
# REBAIXADA. O motivo é medido — no acervo real nenhum período tem só
# prateleira como candidata ("Férias" e "Family" sempre aparecem ao lado de
# "Portugal e Italia com as Meninas"), então rejeitar e rebaixar dão o mesmo
# resultado hoje; rebaixar é a ação menor e preserva o único sinal que
# sobraria num acervo onde o dono só usou a gaveta.
_PRATELEIRAS = frozenset({
    "ferias", "vacation", "vacations", "holiday", "holidays",
    "familia", "family", "viagens", "viagem", "trips", "trip", "travel",
    "eventos", "events", "momentos", "moments", "memories", "lembrancas",
    "melhores", "best of", "selecao", "selection", "geral", "general",
    "diversos", "misc", "casa", "home", "trabalho", "work", "album",
    "albuns", "albums", "fotos", "photos", "pictures", "imagens",
})

# Fotos mínimas para um álbum nomear um período. Mesmo número e mesma razão
# de `_MIN_FOTOS_PERNA` no motor: um punhado de fotos não nomeia o conjunto
# (uma escala de aeroporto não nomeia a viagem; duas fotos marcadas
# "Tiradentes" não renomeiam os seis dias de "Aiuruoca e Tiradentes").
MIN_FOTOS_ALBUM = 3


def _e_prateleira(nome: str) -> bool:
    return _normalizar(nome) in _PRATELEIRAS


def escolher_album(
    contagens: Mapping[str, int],
    cameras: frozenset[str] = frozenset(),
    minimo: int = MIN_FOTOS_ALBUM,
) -> tuple[str, int] | None:
    """O álbum que nomeia um período, entre os que o cobrem.

    `contagens` = {nome do álbum: fotos daquele período nele}. Devolve
    (nome já sem a data, fotos que o sustentam) ou None quando nenhum
    candidato sobrevive aos filtros.

    A ordem do desempate, e por que cada critério existe:

    1. **Não-prateleira antes de prateleira.** Sem isto o acervo real
       escolheria "Férias" (4.352 fotos) em vez de "Portugal e Italia com as
       Meninas" (3.729) — mais frequente e menos informativo, exatamente o
       aninhamento que D-030 descreve.
    2. **Mais fotos primeiro.** É o que separa o álbum do acontecimento
       inteiro do álbum aninhado dentro dele ("Dubai, Thai & Viet" com 2.019
       contra "Nosso Casamento" com 107 no mesmo período).
    3. **Nome mais curto, depois ordem alfabética.** Só desempate — dois
       álbuns com a mesma contagem existem no acervo ("Empolga 2025" e
       "Empolga as 9 - 2025", 159 cada) e a escolha precisa ser a mesma em
       toda regeneração, ou o rótulo dança sozinho entre execuções.

    A data sai do nome (`separar_data`), como já acontece com o nome de
    pasta: "Peru - Julho de 2026" nomeia "Peru", e o ano do destino continua
    vindo do EXIF.
    """
    candidatos: list[tuple[bool, int, int, str]] = []
    for bruto, fotos in contagens.items():
        if fotos < minimo or not album_nomeia(bruto, cameras):
            continue
        nome, _data = separar_data(bruto)
        nome = nome.strip()
        # Sobrou só a data ("2019") — não nomeia nada, e a data já é
        # evidência à parte.
        if not nome or not album_nomeia(nome, cameras):
            continue
        candidatos.append((_e_prateleira(nome), -fotos, len(nome), nome))
    if not candidatos:
        return None
    _prateleira, negativo, _tam, nome = min(candidatos)
    return nome, -negativo


def cameras_do_catalogo(pares) -> frozenset[str]:
    """Normaliza (make, model) do catálogo para comparar com nome de álbum.

    Guarda o modelo sozinho e a marca junto com ele: o dono escreve tanto
    "EOS R6m2" quanto "Canon EOS R6m2".
    """
    nomes: set[str] = set()
    for make, model in pares:
        if model:
            nomes.add(_normalizar(model))
            if make:
                nomes.add(_normalizar(f"{make} {model}"))
    return frozenset(n for n in nomes if len(n) >= _MIN_CARACTERES)
