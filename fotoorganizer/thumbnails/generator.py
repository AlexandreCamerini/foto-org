"""Geração de miniaturas — read-only sobre o original, saída só no cache.

RAW usa a miniatura JPEG embutida via libraw (portado do legado); os demais
formatos abrem no Pillow (HEIC/HEIF registrados por pillow_heif no import
de fotoorganizer.metadata). Orientação EXIF é aplicada na miniatura.
"""

from __future__ import annotations

import io
import logging
from pathlib import Path

from PIL import Image, ImageOps

from fotoorganizer.metadata.purepython import RAW_EXTENSIONS, _HAS_RAW

if _HAS_RAW:  # pragma: no branch
    import rawpy

log = logging.getLogger(__name__)

THUMB_SIZE = 320
_JPEG_QUALITY = 82


def _open_source(path: Path) -> Image.Image | None:
    if path.suffix.lower() in RAW_EXTENSIONS:
        if not _HAS_RAW:  # pragma: no cover
            return None
        with rawpy.imread(str(path)) as raw:
            thumb = raw.extract_thumb()
            if thumb.format == rawpy.ThumbFormat.JPEG:
                return Image.open(io.BytesIO(thumb.data))
            if thumb.format == rawpy.ThumbFormat.BITMAP:
                return Image.fromarray(thumb.data)
        return None
    return Image.open(path)


def generate_thumbnail(source: Path, destino: Path, size: int = THUMB_SIZE) -> bool:
    """Gera a miniatura em `destino`. False (sem exceção) se a imagem não
    puder ser decodificada — o placeholder da UI cobre esses casos."""
    try:
        img = _open_source(source)
        if img is None:
            return False
        with img:
            img = ImageOps.exif_transpose(img)
            img.thumbnail((size, size))
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            destino.parent.mkdir(parents=True, exist_ok=True)
            tmp = destino.with_suffix(".tmp")
            img.save(tmp, "JPEG", quality=_JPEG_QUALITY)
            tmp.replace(destino)
        return True
    except Exception as exc:
        log.debug("thumbnail falhou para %s: %s", source, exc)
        return False
