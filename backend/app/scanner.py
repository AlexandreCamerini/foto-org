"""Varredura de diretórios: encontra fotos, extrai metadados e hashes."""

from __future__ import annotations

import hashlib
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
    # formato padrão de foto do iPhone (a maioria das fotos reais de um Mac).
    import pillow_heif

    pillow_heif.register_heif_opener()
    _HAS_HEIF = True
except ImportError:
    _HAS_HEIF = False

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".gif", ".webp"}
if _HAS_HEIF:
    IMAGE_EXTENSIONS |= {".heic", ".heif"}

_TAG_NAMES = {v: k for k, v in ExifTags.TAGS.items()}
_DATE_TAG = _TAG_NAMES.get("DateTimeOriginal") or _TAG_NAMES.get("DateTime")
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

            if _DATE_TAG and _DATE_TAG in exif:
                raw = exif[_DATE_TAG]
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


def scan_file(path: Path) -> ScannedPhoto:
    stat = path.stat()
    data_exif, localizacao = _extract_exif(path)

    return ScannedPhoto(
        caminho_original=str(path.resolve()),
        nome_arquivo=path.name,
        tamanho_bytes=stat.st_size,
        hash_md5=_md5_of_file(path),
        hash_perceptual=_perceptual_hash(path),
        data_exif=data_exif,
        localizacao_exif=localizacao,
        data_arquivo=datetime.fromtimestamp(stat.st_mtime),
        pasta_fonte=str(path.parent.resolve()),
    )


def scan_directories(directories: list[str]) -> list[ScannedPhoto]:
    return [scan_file(path) for path in iter_image_files(directories)]
