"""Varredura de diretórios: encontra fotos, extrai metadados e hashes."""

from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PIL import ExifTags, Image
from PIL.ExifTags import GPSTAGS

try:
    import imagehash

    _HAS_IMAGEHASH = True
except ImportError:  # imagehash é opcional só pra similaridade visual
    _HAS_IMAGEHASH = False

try:
    # Registra o HEIC/HEIF no Pillow — sem isto, `Image.open` não abre o
    # formato padrão de foto do iPhone (a maioria das fotos reais de um Mac),
    # nem o .HIF do Samsung (mesmo contêiner HEIF por baixo).
    import pillow_heif

    pillow_heif.register_heif_opener()
    _HAS_HEIF = True
except ImportError:
    _HAS_HEIF = False

try:
    # RAW (DNG, CR2, NEF, ARW, ...) não abre no Pillow — rawpy (via libraw)
    # extrai a miniatura JPEG embutida pro hash perceptual, exifread lê os
    # metadados (Pillow também não entende a estrutura EXIF de RAW cru).
    import exifread
    import rawpy

    _HAS_RAW = True
except ImportError:
    _HAS_RAW = False

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".gif", ".webp"}
if _HAS_HEIF:
    IMAGE_EXTENSIONS |= {".heic", ".heif", ".hif"}

RAW_EXTENSIONS = {".dng", ".cr2", ".cr3", ".nef", ".arw", ".raf", ".orf", ".rw2"}
if _HAS_RAW:
    IMAGE_EXTENSIONS |= RAW_EXTENSIONS

_TAG_NAMES = {v: k for k, v in ExifTags.TAGS.items()}
# DateTimeOriginal (data em que a foto foi tirada) mora na sub-IFD "Exif",
# não na IFD0 top-level que `img.getexif()` devolve direto — por isso
# precisa de `get_ifd(_EXIF_IFD_TAG)`. `DateTime` (data de modificação do
# arquivo, menos confiável) fica na IFD0 e serve de fallback.
_DATE_ORIGINAL_TAG = _TAG_NAMES.get("DateTimeOriginal")
_DATE_TAG = _TAG_NAMES.get("DateTime")
_EXIF_IFD_TAG = _TAG_NAMES.get("ExifOffset")
_GPS_TAG = _TAG_NAMES.get("GPSInfo")


@dataclass
class ScannedPhoto:
    caminho_original: str
    nome_arquivo: str
    tamanho_bytes: int
    hash_md5: str
    hash_perceptual: str | None
    data_exif: datetime | None
    localizacao_exif: str | None
    data_arquivo: datetime
    pasta_fonte: str


def iter_image_files(directories: list[str]):
    for directory in directories:
        base = Path(directory).expanduser()
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
                yield path


def _md5_of_file(path: Path) -> str:
    hasher = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _perceptual_hash(path: Path) -> str | None:
    if not _HAS_IMAGEHASH:
        return None
    try:
        with Image.open(path) as img:
            return str(imagehash.phash(img))
    except Exception:
        # Arquivo corrompido/formato não suportado pelo Pillow — a foto ainda
        # entra no catálogo (por md5), só sem comparação de similaridade visual.
        return None


def _dms_to_decimal(dms, ref: str) -> float:
    degrees, minutes, seconds = (float(part) for part in dms)
    decimal = degrees + minutes / 60 + seconds / 3600
    if ref in ("S", "W"):
        decimal = -decimal
    return decimal


def _extract_exif(path: Path) -> tuple[datetime | None, str | None]:
    """Devolve (data tirada, "lat,lon" da localização) — qualquer um pode vir
    `None` se a imagem não tiver aquele metadado (a maioria não tem GPS)."""
    data_exif: datetime | None = None
    localizacao: str | None = None

    try:
        with Image.open(path) as img:
            exif = img.getexif()
            if not exif:
                return None, None

            exif_ifd = exif.get_ifd(_EXIF_IFD_TAG) if _EXIF_IFD_TAG and hasattr(exif, "get_ifd") else {}
            raw = None
            if _DATE_ORIGINAL_TAG and _DATE_ORIGINAL_TAG in exif_ifd:
                raw = exif_ifd[_DATE_ORIGINAL_TAG]
            elif _DATE_TAG and _DATE_TAG in exif:
                raw = exif[_DATE_TAG]
            if raw:
                try:
                    data_exif = datetime.strptime(raw, "%Y:%m:%d %H:%M:%S")
                except (ValueError, TypeError):
                    data_exif = None

            if _GPS_TAG:
                gps_ifd = exif.get_ifd(_GPS_TAG) if hasattr(exif, "get_ifd") else None
                if gps_ifd:
                    gps = {GPSTAGS.get(tag, tag): value for tag, value in gps_ifd.items()}
                    lat = gps.get("GPSLatitude")
                    lat_ref = gps.get("GPSLatitudeRef")
                    lon = gps.get("GPSLongitude")
                    lon_ref = gps.get("GPSLongitudeRef")
                    if lat and lon and lat_ref and lon_ref:
                        lat_dec = _dms_to_decimal(lat, lat_ref)
                        lon_dec = _dms_to_decimal(lon, lon_ref)
                        localizacao = f"{lat_dec:.6f},{lon_dec:.6f}"
    except Exception:
        pass

    return data_exif, localizacao


def _perceptual_hash_raw(path: Path) -> str | None:
    if not (_HAS_IMAGEHASH and _HAS_RAW):
        return None
    try:
        with rawpy.imread(str(path)) as raw:
            thumb = raw.extract_thumb()
        if thumb.format == rawpy.ThumbFormat.JPEG:
            img = Image.open(io.BytesIO(thumb.data))
        elif thumb.format == rawpy.ThumbFormat.BITMAP:
            img = Image.fromarray(thumb.data)
        else:
            return None
        return str(imagehash.phash(img))
    except Exception:
        # Sem miniatura embutida, ou libraw não reconhece a variante do RAW —
        # a foto ainda entra no catálogo (por md5), só sem hash perceptual.
        return None


def _exifread_dms_to_decimal(values, ref: str) -> float:
    degrees, minutes, seconds = (float(v) for v in values)
    decimal = degrees + minutes / 60 + seconds / 3600
    if ref in ("S", "W"):
        decimal = -decimal
    return decimal


def _extract_exif_raw(path: Path) -> tuple[datetime | None, str | None]:
    """Mesma ideia de `_extract_exif`, mas via exifread — Pillow não entende
    a estrutura de metadados de arquivos RAW cru."""
    data_exif: datetime | None = None
    localizacao: str | None = None

    try:
        with path.open("rb") as handle:
            tags = exifread.process_file(handle, details=False)

        raw_date = tags.get("EXIF DateTimeOriginal") or tags.get("Image DateTime")
        if raw_date:
            try:
                data_exif = datetime.strptime(str(raw_date), "%Y:%m:%d %H:%M:%S")
            except (ValueError, TypeError):
                data_exif = None

        lat, lat_ref = tags.get("GPS GPSLatitude"), tags.get("GPS GPSLatitudeRef")
        lon, lon_ref = tags.get("GPS GPSLongitude"), tags.get("GPS GPSLongitudeRef")
        if lat and lon and lat_ref and lon_ref:
            lat_dec = _exifread_dms_to_decimal(lat.values, str(lat_ref))
            lon_dec = _exifread_dms_to_decimal(lon.values, str(lon_ref))
            localizacao = f"{lat_dec:.6f},{lon_dec:.6f}"
    except Exception:
        pass

    return data_exif, localizacao


def scan_file(path: Path) -> ScannedPhoto:
    stat = path.stat()
    is_raw = path.suffix.lower() in RAW_EXTENSIONS

    if is_raw:
        data_exif, localizacao = _extract_exif_raw(path)
        hash_perceptual = _perceptual_hash_raw(path)
    else:
        data_exif, localizacao = _extract_exif(path)
        hash_perceptual = _perceptual_hash(path)

    return ScannedPhoto(
        caminho_original=str(path.resolve()),
        nome_arquivo=path.name,
        tamanho_bytes=stat.st_size,
        hash_md5=_md5_of_file(path),
        hash_perceptual=hash_perceptual,
        data_exif=data_exif,
        localizacao_exif=localizacao,
        data_arquivo=datetime.fromtimestamp(stat.st_mtime),
        pasta_fonte=str(path.parent.resolve()),
    )


def scan_directories(directories: list[str]) -> list[ScannedPhoto]:
    return [scan_file(path) for path in iter_image_files(directories)]
