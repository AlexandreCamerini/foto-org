"""Geradores de arquivos de teste sintéticos (nunca fotos reais no repo)."""

from __future__ import annotations

from pathlib import Path

from PIL import ExifTags, Image, TiffImagePlugin


def _dms(value: float) -> tuple:
    degrees = int(value)
    minutes = int((value - degrees) * 60)
    seconds = round(((value - degrees) * 60 - minutes) * 60, 4)
    return (
        TiffImagePlugin.IFDRational(degrees),
        TiffImagePlugin.IFDRational(minutes),
        TiffImagePlugin.IFDRational(seconds),
    )


def make_jpeg(
    path: Path,
    *,
    seed: int = 0,
    data_exif: str | None = "2024:05:04 10:30:00",
    gps: tuple[float, float] | None = None,
    make: str | None = "TestMake",
    model: str | None = "TestModel",
    lente: str | None = None,
    orientacao: int | None = None,
    size: tuple[int, int] = (64, 48),
) -> Path:
    color = ((seed * 37) % 256, (seed * 73) % 256, (seed * 151) % 256)
    img = Image.new("RGB", size, color)
    exif = Image.Exif()
    if make:
        exif[ExifTags.Base.Make] = make
    if model:
        exif[ExifTags.Base.Model] = model
    if orientacao:
        exif[ExifTags.Base.Orientation] = orientacao

    sub_ifd: dict = {}
    if data_exif:
        sub_ifd[ExifTags.Base.DateTimeOriginal] = data_exif
    if lente:
        sub_ifd[ExifTags.Base.LensModel] = lente
    if sub_ifd:
        exif[0x8769] = sub_ifd

    if gps:
        lat, lon = gps
        exif[0x8825] = {
            1: "N" if lat >= 0 else "S",
            2: _dms(abs(lat)),
            3: "E" if lon >= 0 else "W",
            4: _dms(abs(lon)),
        }

    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, exif=exif)
    return path


def make_png(path: Path, size: tuple[int, int] = (32, 32)) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, "blue").save(path)
    return path


def make_corrupt_jpeg(path: Path) -> Path:
    """Cabeçalho JPEG válido seguido de lixo — abre e falha no decode."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00lixo" * 100)
    return path
