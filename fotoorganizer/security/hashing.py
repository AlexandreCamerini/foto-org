"""Hash rápido (assinatura amostrada) e hash criptográfico completo.

A assinatura rápida é O(1) por arquivo (tamanho + primeiros/últimos 64 KiB
via xxh3) — suficiente para detectar mudança e apontar candidatos a
duplicata. Igualdade de conteúdo só é afirmada com SHA-256 completo, que é
calculado sob demanda (duplicatas nível "exato" e verificação de cópias).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import xxhash

_SAMPLE = 64 * 1024
_CHUNK = 256 * 1024


def quick_signature(path: Path) -> str:
    size = path.stat().st_size
    h = xxhash.xxh3_64()
    h.update(size.to_bytes(8, "little"))
    with path.open("rb") as fh:
        h.update(fh.read(_SAMPLE))
        if size > 2 * _SAMPLE:
            fh.seek(size - _SAMPLE)
            h.update(fh.read(_SAMPLE))
    return f"xxh3:{h.hexdigest()}"


def sha256_full(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(_CHUNK):
            h.update(chunk)
    return f"sha256:{h.hexdigest()}"
