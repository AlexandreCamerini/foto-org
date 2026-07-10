"""Varredura de diretórios: encontra fotos, extrai metadados e hashes."""

from __future__ import annotations

import hashlib
import io
import logging
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

    # exifread loga um warning("File format not recognized.") pra CADA
    # arquivo que não é TIFF/IFD clássico (todo CR3, por exemplo) — em vez
    # de exceção. Num scan com milhares de RAW isso inunda o log; a falha
    # em si já é tratada (ver `_gps_from_exifread`), então abafamos aqui.
    logging.getLogger("exifread").setLevel(logging.ERROR)

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


def _exifread_dms_to_decimal(values, ref: str) -> float:
    degrees, minutes, seconds = (float(v) for v in values)
    decimal = degrees + minutes / 60 + seconds / 3600
    if ref in ("S", "W"):
        decimal = -decimal
    return decimal


def _gps_from_exifread(path: Path) -> str | None:
    """Best-effort: exifread só entende contêineres RAW baseados em
    TIFF/IFD (DNG, NEF, ARW, ...). CR3 usa ISO-BMFF (mesma família do
    .mp4/.heic) e faz o parse falhar — por isso GPS de CR3 fica sempre
    `None` aqui (a data não depende disto, ver `_extract_raw`)."""
    try:
        with path.open("rb") as handle:
            tags = exifread.process_file(handle, details=False)
        lat, lat_ref = tags.get("GPS GPSLatitude"), tags.get("GPS GPSLatitudeRef")
        lon, lon_ref = tags.get("GPS GPSLongitude"), tags.get("GPS GPSLongitudeRef")
        if lat and lon and lat_ref and lon_ref:
            lat_dec = _exifread_dms_to_decimal(lat.values, str(lat_ref))
            lon_dec = _exifread_dms_to_decimal(lon.values, str(lon_ref))
            return f"{lat_dec:.6f},{lon_dec:.6f}"
    except Exception:
        pass
    return None


def _extract_raw(path: Path) -> tuple[datetime | None, str | None, str | None]:
    """Abre o RAW uma única vez com libraw pra tirar data + miniatura
    (evita reabrir arquivos de dezenas de MB duas vezes). A data vem do
    libraw (`raw.other.timestamp`) em vez de exifread porque libraw entende
    qualquer variante de RAW pelo mesmo código, inclusive CR3 — exifread só
    lê contêineres TIFF/IFD clássicos e falha silenciosamente no CR3."""
    data_exif: datetime | None = None
    hash_perceptual: str | None = None

    try:
        with rawpy.imread(str(path)) as raw:
            if raw.other.timestamp:
                data_exif = raw.other.timestamp
            if _HAS_IMAGEHASH:
                thumb = raw.extract_thumb()
                if thumb.format == rawpy.ThumbFormat.JPEG:
                    img = Image.open(io.BytesIO(thumb.data))
                    hash_perceptual = str(imagehash.phash(img))
                elif thumb.format == rawpy.ThumbFormat.BITMAP:
                    hash_perceptual = str(imagehash.phash(Image.fromarray(thumb.data)))
    except Exception:
        # Arquivo corrompido ou variante de RAW que o libraw não abre — a
        # foto ainda entra no catálogo (por md5), só sem data/hash de RAW.
        pass

    localizacao = _gps_from_exifread(path)
    return data_exif, localizacao, hash_perceptual


def scan_file(path: Path) -> ScannedPhoto:
    stat = path.stat()
    is_raw = path.suffix.lower() in RAW_EXTENSIONS

    if is_raw:
        data_exif, localizacao, hash_perceptual = _extract_raw(path)
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
