"""Cache de miniaturas em disco, chaveado por conteúdo (hash rápido).

Chave por conteúdo: duas cópias do mesmo arquivo compartilham a miniatura,
e um arquivo alterado ganha chave nova (o hash rápido muda) — sem
invalidação manual. Arquivos ficam em <cache>/thumbs/aa/<chave>.jpg.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from fotoorganizer.thumbnails.generator import THUMB_SIZE, generate_thumbnail


class ThumbnailCache:
    def __init__(self, cache_dir: Path, size: int = THUMB_SIZE) -> None:
        self._root = cache_dir / "thumbs"
        self._size = size

    def path_for_key(self, chave: str) -> Path:
        chave = chave.replace(":", "_")
        return self._root / chave[:2] / f"{chave}.jpg"

    def get(self, chave: str) -> Path | None:
        path = self.path_for_key(chave)
        return path if path.is_file() else None

    def get_or_generate(self, chave: str, original: Path) -> Path | None:
        """Devolve a miniatura do cache, gerando na primeira vez.
        None se a imagem não puder ser decodificada."""
        path = self.path_for_key(chave)
        if path.is_file():
            return path
        if generate_thumbnail(original, path, self._size):
            return path
        return None

    def tamanho_bytes(self) -> int:
        if not self._root.is_dir():
            return 0
        return sum(f.stat().st_size for f in self._root.rglob("*.jpg"))

    def limpar(self) -> None:
        if self._root.is_dir():
            shutil.rmtree(self._root)
