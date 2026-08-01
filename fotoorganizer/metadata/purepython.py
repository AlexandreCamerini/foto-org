"""Extrator puro-Python: Pillow (+pillow-heif) para formatos comuns,
libraw/rawpy + exifread para RAW.

Lógica portada do protótipo v1 (validada em fotos reais):
- DateTimeOriginal mora na sub-IFD Exif, não na IFD0 (`get_ifd`); DateTime
  da IFD0 é fallback menos confiável.
- Em RAW, a data vem do libraw (`raw.other.timestamp`), que entende todas
  as variantes inclusive CR3 (ISO-BMFF); exifread só serve para GPS em
  contêineres TIFF/IFD clássicos e falha silenciosamente no CR3.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from PIL import ExifTags, Image, IptcImagePlugin

from fotoorganizer.metadata.base import MediaMetadata, data_plausivel

log = logging.getLogger(__name__)

try:
    import pillow_heif

    pillow_heif.register_heif_opener()
    _HAS_HEIF = True
except ImportError:  # pragma: no cover
    _HAS_HEIF = False

try:
    import exifread
    import rawpy

    # exifread avisa "File format not recognized" para cada CR3 — inundaria
    # o log num scan grande; a falha já é tratada por arquivo.
    logging.getLogger("exifread").setLevel(logging.ERROR)
    _HAS_RAW = True
except ImportError:  # pragma: no cover
    _HAS_RAW = False

PILLOW_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".bmp", ".gif"}
HEIF_EXTENSIONS = {".heic", ".heif", ".hif"}
RAW_EXTENSIONS = {".dng", ".cr2", ".cr3", ".nef", ".arw", ".raf", ".orf", ".rw2"}

_EXIF_DATE_FORMAT = "%Y:%m:%d %H:%M:%S"


# libraw devolve a rotação no vocabulário do dcraw; o catálogo guarda o da
# EXIF. -1 significa "não sei" e vira None em vez de "sem rotação".
_FLIP_PARA_ORIENTACAO = {0: 1, 3: 3, 5: 8, 6: 6}

# Tags que ocupam espaço e não dizem nada legível: miniatura embutida,
# perfil de cor, bloco proprietário do fabricante. Ficam de fora da base
# bruta — o objetivo é ter o que dá para cruzar, não o arquivo de novo.
_TAGS_OPACAS = frozenset({
    "MakerNote", "UserComment", "ICCProfile", "InterColorProfile",
    "ThumbnailData", "PrintImageMatching", "XMLPacket", "ExifTool",
    "JPEGThumbnail", "TIFFThumbnail", "ImageResources", "Padding",
})
_VALOR_MAX = 500


def _valor_legivel(valor: object) -> str | None:
    """Texto curto que representa a tag, ou None quando não vale guardar.

    Blobs binários e listas gigantes entram como ruído: inflam a base e
    ninguém cruza por eles. O corte é por tamanho, não por adivinhação de
    tipo — uma tag desconhecida e curta continua entrando.
    """
    if valor is None:
        return None
    if isinstance(valor, bytes):
        return None
    texto = str(valor).strip()
    if not texto or len(texto) > _VALOR_MAX:
        return None
    return texto


def _coletar(destino: list, namespace: str, itens) -> None:
    """Acumula (namespace, chave, valor) descartando o ilegível."""
    for chave, valor in itens:
        nome = str(chave)
        if nome in _TAGS_OPACAS:
            continue
        texto = _valor_legivel(valor)
        if texto is not None:
            destino.append((namespace, nome, texto))


# IPTC/IIM por (registro, campo). Só os que um DAM usa — o padrão tem
# dezenas, e despejar todos enche metadata_entries de ruído.
_IPTC_CAMPOS: dict[tuple[int, int], str] = {
    (2, 5): "ObjectName",          # título
    (2, 25): "Keywords",           # repetível
    (2, 55): "DateCreated",
    (2, 60): "TimeCreated",
    (2, 80): "By-line",            # autor
    (2, 85): "By-lineTitle",
    (2, 90): "City",
    (2, 92): "Sub-location",
    (2, 95): "Province-State",
    (2, 101): "Country-PrimaryLocationName",
    (2, 105): "Headline",
    (2, 110): "Credit",
    (2, 115): "Source",
    (2, 116): "CopyrightNotice",
    (2, 120): "Caption-Abstract",
}


def _achatar_xmp(no, prefixo: str = ""):
    """XMP vem como árvore; metadata_entries é chave-valor.

    Achata para chaves pontuadas ("dc.creator", "photoshop.City"), que é
    como o resto do mundo escreve caminho de XMP.
    """
    if isinstance(no, dict):
        for chave, valor in no.items():
            nome = f"{prefixo}.{chave}" if prefixo else str(chave)
            yield from _achatar_xmp(valor, nome)
    elif isinstance(no, (list, tuple)):
        # Lista repetível (dc:subject, por exemplo): junta, não indexa —
        # índice em chave não sobrevive a reprocessamento.
        planos = [v for v in no if isinstance(v, (str, int, float))]
        if planos:
            yield prefixo, "; ".join(str(v) for v in planos)
        for item in no:
            if isinstance(item, (dict, list, tuple)):
                yield from _achatar_xmp(item, prefixo)
    elif no is not None:
        yield prefixo, no


try:  # Pillow só analisa XMP com defusedxml — XML não confiável exige parser seguro.
    import defusedxml  # noqa: F401

    _HAS_XMP = True
except ImportError:  # pragma: no cover — depende do ambiente
    _HAS_XMP = False
    log.info(
        "XMP indisponível: instale 'defusedxml' para ler palavras-chave, "
        "direitos e legenda de arquivos editados. IPTC e EXIF seguem normais."
    )


def _coletar_xmp(destino: list, img) -> None:
    """XMP: onde vivem palavras-chave, direitos e legenda em arquivo editado."""
    if not _HAS_XMP:
        # Sem o parser seguro, o Pillow avisa por arquivo — em 500 mil fotos
        # isso é meio milhão de linhas de log dizendo a mesma coisa.
        return
    try:
        xmp = img.getxmp()
    except Exception:  # noqa: BLE001 — arquivo ruim não derruba o scan
        return
    if not xmp:
        return
    # A raiz é sempre xmpmeta > RDF > Description; ela não informa nada.
    raiz = xmp.get("xmpmeta", xmp)
    _coletar(destino, "xmp", _achatar_xmp(raiz))


def _coletar_iptc(destino: list, img) -> None:
    """IPTC/IIM: o padrão que as agências e o Photoshop ainda escrevem."""
    try:
        info = IptcImagePlugin.getiptcinfo(img)
    except Exception:  # noqa: BLE001
        return
    if not info:
        return
    itens = []
    for chave, valor in info.items():
        nome = _IPTC_CAMPOS.get(chave)
        if nome is None:
            continue
        if isinstance(valor, (list, tuple)):
            texto = "; ".join(
                v.decode("utf-8", "replace") if isinstance(v, bytes) else str(v)
                for v in valor
            )
        elif isinstance(valor, bytes):
            texto = valor.decode("utf-8", "replace")
        else:
            texto = str(valor)
        itens.append((nome, texto))
    _coletar(destino, "iptc", itens)


def _plausivel(quando: datetime | None) -> datetime | None:
    """Filtra data impossível, mantendo o bruto nos extras (base.py)."""
    return quando if data_plausivel(quando) else None


def _parse_exif_date(raw: object) -> datetime | None:
    try:
        return datetime.strptime(str(raw), _EXIF_DATE_FORMAT)
    except (ValueError, TypeError):
        return None


def _dms_to_decimal(dms, ref: str) -> float:
    degrees, minutes, seconds = (float(part) for part in dms)
    decimal = degrees + minutes / 60 + seconds / 3600
    if ref in ("S", "W"):
        decimal = -decimal
    return decimal


class PurePythonExtractor:
    def supported_extensions(self) -> set[str]:
        exts = set(PILLOW_EXTENSIONS)
        if _HAS_HEIF:
            exts |= HEIF_EXTENSIONS
        if _HAS_RAW:
            exts |= RAW_EXTENSIONS
        return exts

    def extract(self, path: Path) -> MediaMetadata:
        if path.suffix.lower() in RAW_EXTENSIONS:
            return self._extract_raw(path)
        return self._extract_pillow(path)

    def _extract_pillow(self, path: Path) -> MediaMetadata:
        meta = MediaMetadata()
        try:
            with Image.open(path) as img:
                meta.largura, meta.altura = img.size
                # XMP e IPTC vêm ANTES do short-circuit do EXIF: arquivo
                # editado no Lightroom pode ter palavras-chave e direitos
                # sem trazer EXIF nenhum, e sair daqui cedo perdia os dois.
                _coletar_xmp(meta.extras, img)
                _coletar_iptc(meta.extras, img)
                exif = img.getexif()
                if not exif:
                    return meta

                make = exif.get(ExifTags.Base.Make)
                model = exif.get(ExifTags.Base.Model)
                meta.make = str(make).strip() if make else None
                meta.model = str(model).strip() if model else None
                orientacao = exif.get(ExifTags.Base.Orientation)
                meta.orientacao = int(orientacao) if orientacao else None

                sub = exif.get_ifd(ExifTags.IFD.Exif)
                raw_date = sub.get(ExifTags.Base.DateTimeOriginal) or exif.get(
                    ExifTags.Base.DateTime
                )
                if raw_date:
                    meta.data_capturada = _plausivel(_parse_exif_date(raw_date))
                    if meta.data_capturada is None:
                        meta.extras.append(("exif", "data_invalida", str(raw_date)))
                lente = sub.get(ExifTags.Base.LensModel)
                meta.lente = str(lente).strip() if lente else None

                # Base bruta: tudo que o arquivo diz, não só os campos que a
                # cascata consome hoje. É o substrato das correlações que
                # ainda não foram escritas.
                _coletar(meta.extras, "exif", (
                    (ExifTags.TAGS.get(k, k), v) for k, v in exif.items()
                ))
                _coletar(meta.extras, "exif", (
                    (ExifTags.TAGS.get(k, k), v) for k, v in sub.items()
                ))

                gps_ifd = exif.get_ifd(ExifTags.IFD.GPSInfo)
                if gps_ifd:
                    _coletar(meta.extras, "gps", (
                        (ExifTags.GPSTAGS.get(k, k), v)
                        for k, v in gps_ifd.items()
                    ))
                    lat = gps_ifd.get(2)
                    lat_ref = gps_ifd.get(1)
                    lon = gps_ifd.get(4)
                    lon_ref = gps_ifd.get(3)
                    if lat and lon and lat_ref and lon_ref:
                        try:
                            meta.gps_lat = _dms_to_decimal(lat, str(lat_ref))
                            meta.gps_lon = _dms_to_decimal(lon, str(lon_ref))
                        except (ValueError, TypeError, ZeroDivisionError):
                            meta.extras.append(("exif", "gps_invalido", str(gps_ifd)))
        except Exception as exc:  # arquivo corrompido/ilegível: catalogar mesmo assim
            meta.erro = f"{type(exc).__name__}: {exc}"
        return meta

    def _extract_raw(self, path: Path) -> MediaMetadata:
        meta = MediaMetadata()
        if not _HAS_RAW:  # pragma: no cover
            meta.erro = "suporte RAW indisponível (rawpy/exifread não instalados)"
            return meta
        try:
            with rawpy.imread(str(path)) as raw:
                if raw.other.timestamp:
                    meta.data_capturada = _plausivel(raw.other.timestamp)
                sizes = raw.sizes
                meta.largura, meta.altura = sizes.width, sizes.height
                # libraw lê lente e rotação de qualquer RAW, inclusive CR3,
                # onde o exifread não entra. Medido em 300 fotos reais do
                # acervo: 65% delas ficavam sem lente e sem orientação, e
                # todas eram RAW.
                modelo_lente = getattr(raw.lens, "model", "") or ""
                meta.lente = modelo_lente.strip() or None
                meta.orientacao = _FLIP_PARA_ORIENTACAO.get(sizes.flip)
                # No CR3 o libraw é a única fonte: o exifread não abre
                # ISO-BMFF. Exposição, ISO e distância focal só existem aqui.
                outros = raw.other
                _coletar(meta.extras, "libraw", (
                    ("iso", getattr(outros, "iso_speed", None)),
                    ("abertura", getattr(outros, "aperture", None)),
                    ("obturador", getattr(outros, "shutter_speed", None)),
                    ("distancia_focal", getattr(outros, "focal_length", None)),
                    ("artista", getattr(outros, "artist", None)),
                    ("ordem_disparo", getattr(outros, "shot_order", None)),
                    ("lente_min_focal", getattr(raw.lens, "min_focal", None)),
                    ("lente_max_focal", getattr(raw.lens, "max_focal", None)),
                    ("flip", sizes.flip),
                ))
        except Exception as exc:
            meta.erro = f"{type(exc).__name__}: {exc}"

        # GPS/câmera best-effort via exifread (só contêineres TIFF/IFD).
        # CR3 é ISO-BMFF: o exifread falha sempre — pular economiza uma
        # segunda leitura do arquivo (~25 MB) por foto. O preço é make/model
        # em branco no CR3: o libraw não expõe o fabricante, e inferi-lo da
        # lente seria adivinhação disfarçada de evidência.
        if path.suffix.lower() == ".cr3":
            return meta
        try:
            with path.open("rb") as fh:
                tags = exifread.process_file(fh, details=False)
            _coletar(meta.extras, "exif", tags.items())
            make, model = tags.get("Image Make"), tags.get("Image Model")
            meta.make = str(make).strip() if make else None
            meta.model = str(model).strip() if model else None
            lat, lat_ref = tags.get("GPS GPSLatitude"), tags.get("GPS GPSLatitudeRef")
            lon, lon_ref = tags.get("GPS GPSLongitude"), tags.get("GPS GPSLongitudeRef")
            if lat and lon and lat_ref and lon_ref:
                meta.gps_lat = _dms_to_decimal(lat.values, str(lat_ref))
                meta.gps_lon = _dms_to_decimal(lon.values, str(lon_ref))
        except Exception:
            pass
        return meta
