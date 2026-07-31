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
"""

from __future__ import annotations

import re

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
