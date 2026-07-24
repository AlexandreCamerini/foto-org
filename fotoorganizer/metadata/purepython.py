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

from PIL import ExifTags, Image

from fotoorganizer.metadata.base import MediaMetadata

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
                    meta.data_capturada = _parse_exif_date(raw_date)
                    if meta.data_capturada is None:
                        meta.extras.append(("exif", "data_invalida", str(raw_date)))
                lente = sub.get(ExifTags.Base.LensModel)
                meta.lente = str(lente).strip() if lente else None

                gps_ifd = exif.get_ifd(ExifTags.IFD.GPSInfo)
                if gps_ifd:
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
                    meta.data_capturada = raw.other.timestamp
                sizes = raw.sizes
                meta.largura, meta.altura = sizes.width, sizes.height
        except Exception as exc:
            meta.erro = f"{type(exc).__name__}: {exc}"

        # GPS/câmera best-effort via exifread (só contêineres TIFF/IFD).
        # CR3 é ISO-BMFF: o exifread falha sempre — pular economiza uma
        # segunda leitura do arquivo (~25 MB) por foto.
        if path.suffix.lower() == ".cr3":
            return meta
        try:
            with path.open("rb") as fh:
                tags = exifread.process_file(fh, details=False)
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
