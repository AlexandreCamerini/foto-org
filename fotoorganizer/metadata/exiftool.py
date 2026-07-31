"""Extrator via exiftool, em processo persistente (`-stay_open`).

O extrator puro-Python vinha sendo tratado como teto, e não é. Num acervo
real, 2.949 CR3 ficaram sem `Make`/`Model`: o libraw entrega abertura, ISO e
obturador, mas não a câmera. Sem câmera não há correção de deriva de relógio
nem "outra origem" na herança de GPS — a lacuna se propaga para a
classificação inteira.

O exiftool lê 386 tags do mesmo arquivo, contra 8 do libraw.

Por que `-stay_open`: um `exiftool arquivo` por foto paga ~200 ms de partida
do Perl. Num scan de dezenas de milhares, isso é a diferença entre minutos e
horas. O processo sobe uma vez e recebe os argumentos pelo stdin.

Segurança (invariante 5): sem `shell=True`, argumentos em lista, caminho
resolvido e recusado se não for arquivo comum. Um caminho com `\n` quebraria
o protocolo do `-stay_open` — é rejeitado antes de chegar lá.

Nunca levanta exceção por arquivo: devolve `MediaMetadata` com `erro`
preenchido, e o scanner cataloga assim mesmo.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import threading
from datetime import datetime
from pathlib import Path

from fotoorganizer.metadata.base import MediaMetadata, MetadataExtractor
from fotoorganizer.metadata.purepython import PurePythonExtractor

log = logging.getLogger(__name__)

_FIM = "{ready}"
_TIMEOUT_S = 30.0

# Grupo do exiftool → namespace do catálogo. O que não estiver aqui fica de
# fora da base bruta: "File" repete o que o filesystem já disse, "ExifTool"
# fala do próprio exiftool, "Composite" é derivado e entraria como se fosse
# leitura do arquivo.
_GRUPOS = {
    "EXIF": "exif",
    "GPS": "gps",
    "IPTC": "iptc",
    "XMP": "xmp",
    "ICC_Profile": "icc",
    "QuickTime": "quicktime",
    "PNG": "png",
}

# `MakerNotes` fica FORA da base bruta de propósito (D-027). São ~259 campos
# por CR3 — modo de foco, posição do estabilizador, contador do obturador,
# temperatura do sensor — e somavam 969 mil linhas, 83% de todo o metadado de
# um acervo real, sem que nada ali ajude a decidir viagem, evento ou lugar.
#
# O que o bloco tem de aproveitável já é lido acima: `MakerNotes:LensType`
# entra em `lente` pela busca em `dados`, que enxerga o JSON inteiro e não
# depende deste mapa.
#
# Para reativar: devolva "MakerNotes": "makernotes" aqui e rode
# `scan --reprocessar`. O rótulo legível continua em ROTULOS_NAMESPACE.

# O exiftool devolve a orientação por extenso; o catálogo guarda o número da
# EXIF. Pedir `-n` global resolveria isto e estragaria todo o resto da base
# bruta, que existe para ser lida por gente.
_ORIENTACAO = {
    "Horizontal (normal)": 1,
    "Mirror horizontal": 2,
    "Rotate 180": 3,
    "Mirror vertical": 4,
    "Mirror horizontal and rotate 270 CW": 5,
    "Rotate 90 CW": 6,
    "Mirror horizontal and rotate 90 CW": 7,
    "Rotate 270 CW": 8,
}

_TAGS_OPACAS = frozenset({
    "ThumbnailImage", "PreviewImage", "JpgFromRaw", "OtherImage",
    "ThumbnailTIFF", "PhotoshopThumbnail", "DataDump", "Padding",
})

_FORMATOS_DE_DATA = ("%Y:%m:%d %H:%M:%S", "%Y:%m:%d %H:%M:%S%z")


def _data(valor: str | None) -> datetime | None:
    if not valor:
        return None
    # Sobras comuns: subsegundos ("2025:11:08 01:16:32.35") e fuso colado.
    limpo = str(valor).strip().split(".")[0].replace("Z", "+0000")
    for formato in _FORMATOS_DE_DATA:
        try:
            return datetime.strptime(limpo, formato).replace(tzinfo=None)
        except ValueError:
            continue
    return None


def _numero(valor) -> float | None:
    try:
        return float(str(valor).strip().lstrip("+"))
    except (TypeError, ValueError):
        return None


def _inteiro(valor) -> int | None:
    n = _numero(valor)
    return int(n) if n is not None else None


class ExifToolExtractor:
    """Fala com um processo exiftool vivo. Use como context manager ou
    chame `close()` — o processo não morre sozinho.

    Não é thread-safe por desenho; um lock serializa o acesso porque o
    protocolo do `-stay_open` é uma conversa única por stdin/stdout.
    """

    def __init__(
        self,
        binario: str | None = None,
        fallback: MetadataExtractor | None = None,
    ) -> None:
        self._binario = binario or shutil.which("exiftool") or "exiftool"
        self._fallback = fallback if fallback is not None else PurePythonExtractor()
        self._proc: subprocess.Popen | None = None
        self._lock = threading.Lock()

    # -- disponibilidade ----------------------------------------------------
    @staticmethod
    def disponivel(binario: str | None = None) -> bool:
        return shutil.which(binario or "exiftool") is not None

    def supported_extensions(self) -> set[str]:
        # O exiftool entende mais formatos do que o app aceita; a lista de
        # quem manda continua sendo a do fallback, para o scanner não passar
        # a descobrir arquivo que o resto do sistema não sabe tratar.
        return self._fallback.supported_extensions()

    # -- processo -----------------------------------------------------------
    def _garantir(self) -> subprocess.Popen:
        if self._proc is not None and self._proc.poll() is None:
            return self._proc
        self._proc = subprocess.Popen(
            [self._binario, "-stay_open", "True", "-@", "-"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True, encoding="utf-8", errors="replace",
            bufsize=1,
        )
        return self._proc

    def close(self) -> None:
        with self._lock:
            proc, self._proc = self._proc, None
        if proc is None or proc.poll() is not None:
            return
        try:
            proc.stdin.write("-stay_open\nFalse\n")
            proc.stdin.flush()
            proc.wait(timeout=5)
        except (OSError, ValueError, subprocess.TimeoutExpired):
            proc.kill()

    def __enter__(self) -> "ExifToolExtractor":
        return self

    def __exit__(self, *_) -> None:
        self.close()

    # -- leitura ------------------------------------------------------------
    def _conversar(self, caminho: Path) -> dict | None:
        """Uma rodada do protocolo. None quando o processo não colabora."""
        proc = self._garantir()
        argumentos = [
            "-j",                 # JSON
            "-G",                 # nome do grupo junto da chave
            "-c", "%+.8f",        # coordenada em grau decimal com sinal
            "-charset", "filename=utf8",
            str(caminho),
            "-execute",
        ]
        proc.stdin.write("\n".join(argumentos) + "\n")
        proc.stdin.flush()

        linhas: list[str] = []
        while True:
            linha = proc.stdout.readline()
            if not linha:                      # processo morreu
                self._proc = None
                return None
            if linha.strip() == _FIM:
                break
            linhas.append(linha)
        bruto = "".join(linhas).strip()
        if not bruto:
            return None
        try:
            dados = json.loads(bruto)
        except json.JSONDecodeError:
            return None
        return dados[0] if dados else None

    def extract(self, path: Path) -> MediaMetadata:
        caminho = Path(path)
        # Quebra de linha no nome romperia o protocolo do -stay_open, que é
        # delimitado por linha. Vai para o fallback em vez de arriscar.
        if "\n" in str(caminho) or "\r" in str(caminho):
            return self._fallback.extract(caminho)
        try:
            if not caminho.is_file():
                return MediaMetadata(erro="arquivo não encontrado")
        except OSError as exc:
            return MediaMetadata(erro=f"caminho inacessível: {exc}")

        try:
            with self._lock:
                dados = self._conversar(caminho)
        except (OSError, ValueError) as exc:
            log.warning("exiftool falhou em %s (%s) — usando fallback",
                        caminho.name, exc)
            self._proc = None
            return self._fallback.extract(caminho)

        if dados is None:
            log.warning("exiftool não respondeu por %s — usando fallback",
                        caminho.name)
            return self._fallback.extract(caminho)
        return self._converter(dados)

    # -- conversão ----------------------------------------------------------
    @staticmethod
    def _converter(dados: dict) -> MediaMetadata:
        def valor(*chaves: str):
            for chave in chaves:
                if dados.get(chave) not in (None, ""):
                    return dados[chave]
            return None

        meta = MediaMetadata()
        meta.data_capturada = _data(
            valor("EXIF:DateTimeOriginal", "EXIF:CreateDate",
                  "QuickTime:CreateDate", "XMP:DateCreated",
                  "EXIF:ModifyDate")
        )
        meta.make = valor("EXIF:Make", "XMP:Make")
        meta.model = valor("EXIF:Model", "XMP:Model")
        meta.lente = valor("EXIF:LensModel", "MakerNotes:LensType",
                           "XMP:Lens", "Composite:LensID")
        orientacao = valor("EXIF:Orientation")
        meta.orientacao = _ORIENTACAO.get(str(orientacao)) if orientacao else None
        meta.largura = _inteiro(valor("EXIF:ExifImageWidth", "EXIF:ImageWidth",
                                      "File:ImageWidth", "QuickTime:ImageWidth"))
        meta.altura = _inteiro(valor("EXIF:ExifImageHeight", "EXIF:ImageHeight",
                                     "File:ImageHeight", "QuickTime:ImageHeight"))
        # Composite já aplica o hemisfério (N/S, E/W); a tag crua é sempre
        # positiva e usá-la direto põe o Rio no hemisfério errado.
        meta.gps_lat = _numero(valor("Composite:GPSLatitude"))
        meta.gps_lon = _numero(valor("Composite:GPSLongitude"))

        for chave, bruto in dados.items():
            grupo, _, nome = chave.partition(":")
            namespace = _GRUPOS.get(grupo)
            if namespace is None or nome in _TAGS_OPACAS:
                continue
            if isinstance(bruto, (dict, list)):
                bruto = json.dumps(bruto, ensure_ascii=False)
            texto = str(bruto)
            # Binário embutido que o exiftool resume: nada a cruzar.
            if texto.startswith("(Binary data"):
                continue
            meta.extras.append((namespace, nome, texto[:2000]))
        return meta
