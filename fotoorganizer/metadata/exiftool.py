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
import re
import shutil
import subprocess
import threading
from datetime import datetime, timedelta
from pathlib import Path

from fotoorganizer.metadata.base import (
    MediaMetadata,
    MetadataExtractor,
    data_plausivel,
)
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
    # Curadoria que veio do arquivo `.xmp` ao lado, não de dentro da foto.
    # Namespace próprio para a pergunta "de onde veio?" continuar tendo
    # resposta: nota escrita pelo Aftershoot num sidecar e nota gravada
    # dentro do JPEG são fatos diferentes, com confiança diferente.
    "XMPSidecar": "xmp_sidecar",
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

_FORMATOS_DE_DATA = (
    "%Y:%m:%d %H:%M:%S", "%Y:%m:%d %H:%M:%S%z",
    # XMP (Lightroom/Photoshop) escreve ISO-8601; IPTC IIM grava só a data.
    "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S%z",
    "%Y:%m:%d", "%Y-%m-%d",
)


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


def _offset(bruto: str | None) -> timedelta | None:
    """`OffsetTimeOriginal` ("+02:00", "-03:00") → deslocamento do fuso.

    É o fuso da captura DECLARADO pela câmera — não estimado, não inferido.
    Estava sendo capturado e ignorado em 1.527 fotos do acervo
    (`docs/INVENTARIO_DE_SINAIS.md`), enquanto `grouping/correlacao.py`
    gastava estatística para adivinhar a deriva entre relógios.

    "+00:00" é aceito como fato: a foto foi tirada em Greenwich (ou Lisboa no
    inverno). O catálogo não consegue distinguir isso de "fuso desconhecido"
    depois de gravado — as duas colunas ficam iguais nos dois casos — e essa
    limitação já está declarada em `models/catalog.py`. Descartar o valor aqui
    não resolveria nada e perderia a informação de quem realmente estava lá.
    """
    if not bruto:
        return None
    texto = str(bruto).strip()
    m = re.fullmatch(r"([+-])(\d{2}):?(\d{2})", texto)
    if not m:
        return None
    sinal, horas, minutos = m.group(1), int(m.group(2)), int(m.group(3))
    if horas > 14 or minutos > 59:
        return None
    delta = timedelta(hours=horas, minutes=minutos)
    return -delta if sinal == "-" else delta


# Tags de data do arquivo original. Quando o sidecar traz data, TODAS estas
# saem: misturar a data que o editor gravou com o fuso que a câmera gravou
# produz um instante que não existiu. É a mesma regra do Immich, e o motivo
# é o mesmo.
_TAGS_DE_DATA_DO_ORIGINAL = (
    "EXIF:DateTimeOriginal", "EXIF:CreateDate", "EXIF:ModifyDate",
    "Composite:SubSecDateTimeOriginal", "Composite:SubSecCreateDate",
    "QuickTime:CreateDate", "IPTC:DateCreated",
    "EXIF:OffsetTimeOriginal", "EXIF:OffsetTimeDigitized", "EXIF:OffsetTime",
)

# Chaves de data que o sidecar pode trazer, na ordem em que o XMP as declara.
_TAGS_DE_DATA_DO_SIDECAR = (
    "XMP:DateTimeOriginal", "XMP:DateCreated", "XMP:CreateDate",
)


def _sidecar_de(caminho: Path) -> Path | None:
    """O `.xmp` irmão, nos dois padrões que os editores usam.

    605 destes existem no acervo e 599 carregam curadoria
    (`docs/INVENTARIO_DE_SINAIS.md`) — nota, rótulo de cor e palavras-chave
    hierárquicas escritas pelo Aftershoot. Nenhum era lido: o scanner enxerga
    arquivo de imagem, e o `.xmp` fica ao lado sem nunca ser abrido junto.

    `foto.jpg.xmp` é o padrão do Adobe; `foto.xmp` o do darktable e de parte
    do fluxo do Lightroom. O primeiro que existir vence — procurar os dois e
    fundir arriscaria juntar curadoria de dois editores diferentes.
    """
    candidatos = (
        caminho.with_name(caminho.name + ".xmp"),
        caminho.with_suffix(".xmp"),
    )
    for candidato in candidatos:
        try:
            if candidato.is_file():
                return candidato
        except OSError:
            continue
    return None


def _fundir_sidecar(original: dict, sidecar: dict) -> dict:
    """Tags do arquivo + tags do `.xmp`, com o sidecar vencendo.

    O sidecar é mais novo por construção: ele existe porque alguém editou a
    foto depois de ela sair da câmera, e não pôde (ou não quis) reescrever o
    original. Onde os dois falam, quem fala por último tem razão.

    A exceção que exige cuidado é a data. Se o sidecar declara QUALQUER data,
    todas as datas do original saem junto — inclusive o offset de fuso. Casar
    a data que o editor gravou com o fuso que a câmera gravou produziria um
    instante que nunca existiu, e o erro seria invisível: as duas colunas
    continuariam preenchidas e plausíveis.

    As tags do sidecar entram na base bruta com grupo `XMPSidecar`, que o mapa
    de namespaces manda para `xmp_sidecar` — sem isso, uma nota escrita pelo
    Aftershoot ficaria indistinguível de uma escrita dentro do arquivo, e a
    pergunta "de onde veio?" perderia a resposta.
    """
    fundido = dict(original)
    tem_data = any(sidecar.get(t) for t in _TAGS_DE_DATA_DO_SIDECAR)
    if tem_data:
        for tag in _TAGS_DE_DATA_DO_ORIGINAL:
            fundido.pop(tag, None)
    for chave, valor in sidecar.items():
        grupo, _, nome = chave.partition(":")
        if grupo in ("SourceFile", "ExifTool", "File"):
            continue
        fundido[f"XMPSidecar:{nome}"] = valor
        # O sidecar também responde pelas chaves XMP normais: é assim que a
        # precedência chega em `_converter` sem ele precisar saber que existe
        # um arquivo ao lado.
        if grupo == "XMP":
            fundido[chave] = valor
    return fundido


# Os quatro formatos de palavra-chave, em ordem de precedência. Os dois
# primeiros carregam HIERARQUIA ("Viagens|2019|Patagônia"); os dois últimos
# são lista plana. A ordem é a mesma do Immich, e por um motivo verificável:
# quem escreve hierarquia escreve a lista plana junto, como redundância para
# programas que não entendem hierarquia — então a hierarquia é o registro
# completo e a lista plana é a versão degradada dele.
_TAGS_DE_PALAVRA_CHAVE = (
    "XMPSidecar:TagsList", "XMP:TagsList",
    "XMPSidecar:HierarchicalSubject", "XMP:HierarchicalSubject",
    "XMPSidecar:Subject", "XMP:Subject",
    "IPTC:Keywords",
)


def _palavras_chave(dados: dict) -> tuple[str, ...]:
    """Palavras-chave dos quatro formatos, unificadas e sem repetição.

    A unificação é o ponto, não a leitura. O acervo tem catálogo do Lightroom
    importado como fonte E os `.xmp` que o mesmo fluxo gravou no disco: o
    mesmo "Selected" chega pelos dois caminhos. Somar os dois contaria duas
    vezes a mesma afirmação de uma pessoa só, e confiança somada indevidamente
    é o defeito que docs/CONFIANCA.md existe para impedir.

    Cada nível da hierarquia entra separado além do caminho inteiro:
    "Viagens|2019|Patagônia" também vale como "Patagônia", que é o termo que a
    classificação procura. O caminho completo fica porque é o que responde
    "onde isto estava organizado?".
    """
    vistas: dict[str, None] = {}
    for tag in _TAGS_DE_PALAVRA_CHAVE:
        bruto = dados.get(tag)
        if not bruto:
            continue
        itens = bruto if isinstance(bruto, list) else [bruto]
        for item in itens:
            texto = str(item).strip()
            if not texto:
                continue
            vistas.setdefault(texto, None)
            if "|" in texto:
                for parte in texto.split("|"):
                    parte = parte.strip()
                    if parte:
                        vistas.setdefault(parte, None)
    return tuple(vistas)


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

        # A única espera potencialmente infinita do scan inteiro: se o
        # exiftool emudecer diante de um arquivo, este readline não tem fim
        # e a fila congela em RODANDO. O vigia mata o processo no teto; o
        # readline devolve EOF, o chamador recebe None e o fallback
        # puro-Python responde pelo arquivo.
        vigia = threading.Timer(_TIMEOUT_S, proc.kill)
        vigia.start()
        try:
            linhas: list[str] = []
            while True:
                linha = proc.stdout.readline()
                if not linha:                      # processo morreu
                    self._proc = None
                    return None
                if linha.strip() == _FIM:
                    break
                linhas.append(linha)
        finally:
            vigia.cancel()
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

        sidecar = _sidecar_de(caminho)
        if sidecar is not None:
            try:
                with self._lock:
                    do_sidecar = self._conversar(sidecar)
            except (OSError, ValueError) as exc:
                log.warning("exiftool falhou no sidecar %s (%s) — ignorado",
                            sidecar.name, exc)
                self._proc, do_sidecar = None, None
            if do_sidecar:
                dados = _fundir_sidecar(dados, do_sidecar)
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
        # Ordem de precedência da hora de PAREDE. As duas primeiras carregam
        # subsegundo e são as mesmas datas das seguintes com mais precisão —
        # 1.524 fotos do acervo têm `SubSecTimeOriginal` e ele estava sendo
        # descartado (`docs/INVENTARIO_DE_SINAIS.md`). Subsegundo não muda o
        # dia nem a hora: ele desempata rajada, onde seis fotos dividem o
        # mesmo segundo e a ordem entre elas era arbitrária.
        #
        # IPTC:DateCreated é a data em que a foto foi FEITA (padrão IIM) e
        # costuma sobreviver à edição que apaga o EXIF. Entra antes do
        # ModifyDate, que fala da edição, não do clique.
        #
        # `Composite:GPSDateTime` NÃO entra nesta lista, apesar de ser a data
        # mais confiável do arquivo (vem do satélite, imune a relógio errado):
        # ela é UTC, e esta coluna é hora de parede. Colocá-la aqui repetiria
        # exatamente o defeito que o Takeout tinha — gravar um instante
        # absoluto na coluna da hora local e deslocar a foto pelo tamanho do
        # fuso. Ela entra abaixo, no lado certo.
        quando = _data(
            valor("Composite:SubSecDateTimeOriginal", "EXIF:DateTimeOriginal",
                  "Composite:SubSecCreateDate", "EXIF:CreateDate",
                  "QuickTime:CreateDate", "XMP:DateCreated",
                  "IPTC:DateCreated", "EXIF:ModifyDate")
        )
        # Data impossível não entra na coluna; o valor bruto segue nos extras.
        meta.data_capturada = quando if data_plausivel(quando) else None

        # O instante absoluto, quando o arquivo DECLARA o fuso da captura.
        # Sem isto, `data_capturada_utc` era sempre igual à parede — a forma
        # de dizer "não sei o fuso" — mesmo nas 1.527 fotos que sabiam.
        #
        # `-` porque o offset diz quanto o relógio local está À FRENTE de UTC:
        # 14h em +02:00 são 12h UTC.
        offset = _offset(valor("EXIF:OffsetTimeOriginal",
                               "EXIF:OffsetTimeDigitized", "EXIF:OffsetTime"))
        if meta.data_capturada is not None and offset is not None:
            meta.data_capturada_utc = meta.data_capturada - offset
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
        meta.palavras_chave = _palavras_chave(dados)

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
