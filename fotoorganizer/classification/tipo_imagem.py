"""Foto de câmera ou imagem que só passou pelo disco?

Um acervo pessoal real não é feito só de fotos: tem captura de tela, imagem
recebida no WhatsApp, banner baixado do navegador, figurinha. Elas entopem a
grade, poluem o agrupamento temporal e inflam qualquer contagem — e ninguém
quer organizá-las por viagem.

Aqui não entra modelo. Os sinais são determinísticos e verificáveis, e cada
um vira evidência com origem e justificativa como qualquer outra inferência
do motor. O detector NÃO decide sozinho: devolve o veredito com score, e o
usuário revisa como revisa tudo.

Regra de ouro do módulo: na dúvida, é foto. Marcar foto legítima como lixo
custa mais caro que deixar um screenshot passar — o usuário perde confiança
no catálogo inteiro.
"""

from __future__ import annotations

import re

from fotoorganizer.metadata.camera import nome_da_camera
from fotoorganizer.grouping.origens import (
    PASTAS_BAIXADA,
    PASTAS_CAPTURA,
    PASTAS_RECEBIDA,
)
from fotoorganizer.geolocation.folder_names import _normalizar
from dataclasses import dataclass

# Tipos. `foto` é o padrão e o que o resto do motor organiza por viagem.
FOTO = "foto"
CAPTURA = "captura"      # captura de tela
RECEBIDA = "recebida"    # WhatsApp, Telegram, mensageria
BAIXADA = "baixada"      # navegador, download

TIPOS = (FOTO, CAPTURA, RECEBIDA, BAIXADA)

ROTULOS = {
    FOTO: "foto",
    CAPTURA: "captura de tela",
    RECEBIDA: "recebida em mensageiro",
    BAIXADA: "baixada da web",
}


@dataclass(frozen=True, slots=True)
class Veredito:
    tipo: str
    score: float
    justificativa: str

    @property
    def e_foto(self) -> bool:
        return self.tipo == FOTO


# -- sinais ------------------------------------------------------------------

# WhatsApp nomeia o que exporta: IMG-20240504-WA0012.jpg, VID-...-WA...
_RE_WHATSAPP = re.compile(r"^(IMG|VID|AUD|PTT)-\d{8}-WA\d+", re.I)
# E o que o app do desktop salva: "WhatsApp Image 2024-05-04 at 10.30.00.jpeg"
_RE_WHATSAPP_DESKTOP = re.compile(r"^WhatsApp (Image|Video)\b", re.I)
# Telegram: photo_2024-05-04_10-30-00.jpg
_RE_TELEGRAM = re.compile(r"^photo_\d{4}-\d{2}-\d{2}_", re.I)
# Captura de tela em pt-BR, en e a variante antiga do macOS.
_RE_CAPTURA = re.compile(
    r"^(captura de (tela|ecr[ãa])|screenshot|screen shot|simulator screen shot)",
    re.I,
)
# Nome que só um download produz: "image (3).png", "unnamed.jpg", "download.jpeg"
_RE_BAIXADA = re.compile(
    r"^(image|imagem|unnamed|download|untitled|sem[-_ ]t[ií]tulo)"
    r"[\s_-]*(\(\d+\))?$",
    re.I,
)

_PASTAS_RECEBIDA = PASTAS_RECEBIDA
_PASTAS_BAIXADA = PASTAS_BAIXADA
_PASTAS_CAPTURA = PASTAS_CAPTURA

# Resoluções de tela comuns (Apple e monitores), nas duas orientações. Uma
# imagem com EXATAMENTE a dimensão de uma tela é captura com folga.
_TELAS = {
    (2556, 1179), (2796, 1290), (2532, 1170), (2778, 1284), (2436, 1125),
    (2688, 1242), (1792, 828), (2340, 1080), (2400, 1080),
    (2048, 1536), (2224, 1668), (2388, 1668), (2732, 2048),
    (2880, 1800), (3024, 1964), (3456, 2234), (2560, 1600), (3072, 1920),
    (1920, 1080), (2560, 1440), (3840, 2160), (1366, 768), (1440, 900),
}
_TELAS = _TELAS | {(a, l) for l, a in _TELAS}

# Piso de resolução abaixo do qual "sem câmera" sugere recompressão de
# mensageiro. Deliberadamente BAIXO: uma compacta de 1999 tirava 1024×768
# (0,78 MP) e JPEG antigo perde EXIF ao ser copiado — marcar a foto de
# infância de alguém como lixo custa a confiança no catálogo inteiro. O
# WhatsApp comprime bem abaixo disto quando o arquivo é pequeno; nos casos
# em que não comprime, o nome ou a pasta denunciam antes de chegar aqui.
_MP_MINIMO = 480_000  # ≈ 800×600


def _tem_assinatura_de_camera(make, model, lente, exposicao) -> bool:
    """Câmera grava quem ela é. App de mensagem e navegador não."""
    return any(v for v in (make, model, lente, exposicao))


def classificar(
    *,
    nome: str,
    pasta: str,
    extensao: str,
    largura: int | None = None,
    altura: int | None = None,
    make: str | None = None,
    model: str | None = None,
    lente: str | None = None,
    exposicao: str | None = None,
    tem_gps: bool = False,
) -> Veredito:
    """Decide o tipo por sinais de arquivo, sem abrir a imagem.

    A ordem importa: sinais fortes e específicos (nome de convenção, pasta
    dedicada, resolução exata de tela) vêm antes dos fracos e genéricos
    (ausência de EXIF), porque um sinal fraco sozinho nunca deve condenar.
    """
    base = nome.rsplit(".", 1)[0]
    # NFKD+ascii, não só lower(): o Finder/APFS grava pasta acentuada em NFD
    # (marcador combinante intercalado entre letras), que não bate como
    # substring nem contra a forma acentuada nem contra a sem-acento — mesma
    # causa raiz do D-070 em grouping/datas.py.
    pasta_baixa = _normalizar(pasta)
    tem_camera = _tem_assinatura_de_camera(make, model, lente, exposicao)

    # GPS é atestado de origem: nenhum app de mensagem devolve coordenada.
    # Vence qualquer heurística de nome — é o caso da foto que você tirou e
    # mandou para si mesmo, que continua sendo sua foto.
    if tem_gps:
        return Veredito(FOTO, 0.95, "tem coordenada GPS gravada no arquivo")

    # 1) Nome por convenção — o sinal mais específico que existe.
    if _RE_WHATSAPP.match(base) or _RE_WHATSAPP_DESKTOP.match(base):
        return Veredito(RECEBIDA, 0.95,
                        f"nome no padrão do WhatsApp ('{nome}')")
    if _RE_TELEGRAM.match(base):
        return Veredito(RECEBIDA, 0.90,
                        f"nome no padrão do Telegram ('{nome}')")
    if _RE_CAPTURA.match(base):
        return Veredito(CAPTURA, 0.95,
                        f"nome no padrão de captura de tela ('{nome}')")

    # 2) Pasta dedicada.
    for marca in _PASTAS_RECEBIDA:
        if _normalizar(marca) in pasta_baixa:
            return Veredito(RECEBIDA, 0.85,
                            f"está numa pasta de mensageiro ('{marca}')")
    for marca in _PASTAS_CAPTURA:
        if _normalizar(marca) in pasta_baixa:
            return Veredito(CAPTURA, 0.85,
                            f"está numa pasta de capturas ('{marca}')")

    # 3) Resolução exata de tela, sem assinatura de câmera.
    if (largura, altura) in _TELAS and not tem_camera:
        return Veredito(
            CAPTURA, 0.85,
            f"tem exatamente a resolução de uma tela ({largura}×{altura}) "
            "e nenhum dado de câmera",
        )

    # 4) Download: pasta OU nome genérico, sem câmera.
    if not tem_camera:
        if any(_normalizar(m) in pasta_baixa for m in _PASTAS_BAIXADA):
            return Veredito(BAIXADA, 0.80,
                            "está na pasta de downloads e não tem dado de câmera")
        if _RE_BAIXADA.match(base):
            return Veredito(BAIXADA, 0.70,
                            f"nome genérico de download ('{nome}') sem dado de câmera")

    # 5) PNG sem câmera. Foto de câmera praticamente nunca é PNG — mas é
    #    sinal fraco sozinho, então não passa de média.
    if extensao.lower().lstrip(".") == "png" and not tem_camera:
        return Veredito(CAPTURA, 0.55,
                        "é PNG e não tem nenhum dado de câmera")

    # 6) Sem nada que identifique câmera. O sinal mais fraco de todos, e o
    #    que mais erra: RAW antigo e arquivo já reprocessado caem aqui. Só
    #    marca como "recebida" se ADEMAIS perdeu tudo — é a assinatura de
    #    quem foi recomprimido por um app de mensagem.
    if not tem_camera and largura and altura and largura * altura < _MP_MINIMO:
        return Veredito(
            RECEBIDA, 0.55,
            f"sem dado de câmera e em resolução muito baixa ({largura}×{altura}), "
            "como o que aplicativo de mensagem recomprime",
        )

    if not tem_camera:
        return Veredito(FOTO, 0.50, "sem dado de câmera, mas nada indica o contrário")
    return Veredito(
        FOTO, 0.90,
        f"tem dado de câmera gravado ({nome_da_camera(make, model)})",
    )
