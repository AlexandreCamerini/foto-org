"""Hash perceptual (phash 64-bit) + BK-tree para busca por similaridade.

O BK-tree evita comparação O(n²): consultas por distância de Hamming ≤ d
visitam só os ramos que podem conter vizinhos. Suficiente para dezenas de
milhares de fotos sem dependência extra.
"""

from __future__ import annotations

import io
import logging
from pathlib import Path

from PIL import Image

from fotoorganizer.metadata.purepython import RAW_EXTENSIONS, _HAS_RAW

log = logging.getLogger(__name__)


def distancia_hamming(a: int, b: int) -> int:
    return (a ^ b).bit_count()


class BKTree:
    __slots__ = ("_raiz",)

    def __init__(self) -> None:
        # nó = [valor, payload, {distância: nó_filho}]
        self._raiz: list | None = None

    def inserir(self, valor: int, payload) -> None:
        if self._raiz is None:
            self._raiz = [valor, [payload], {}]
            return
        no = self._raiz
        while True:
            d = distancia_hamming(valor, no[0])
            if d == 0:
                no[1].append(payload)
                return
            filho = no[2].get(d)
            if filho is None:
                no[2][d] = [valor, [payload], {}]
                return
            no = filho

    def buscar(self, valor: int, max_dist: int) -> list[tuple[int, int, list]]:
        """[(distância, valor, payloads)] com distância ≤ max_dist."""
        if self._raiz is None:
            return []
        resultados = []
        pilha = [self._raiz]
        while pilha:
            no = pilha.pop()
            d = distancia_hamming(valor, no[0])
            if d <= max_dist:
                resultados.append((d, no[0], no[1]))
            for dist_filho, filho in no[2].items():
                if d - max_dist <= dist_filho <= d + max_dist:
                    pilha.append(filho)
        return resultados


def calcular_phash(original: Path, thumb: Path | None = None) -> str | None:
    """phash em hex. Usa a miniatura em cache quando existir (o phash reduz
    para 32×32 de qualquer forma — o resultado é o mesmo, a leitura é menor).
    RAW abre pela miniatura embutida via libraw. None se indecodificável."""
    import imagehash

    fontes: list[Path] = [p for p in (thumb, original) if p is not None]
    for fonte in fontes:
        try:
            img = _abrir(fonte if fonte != original else original)
            if img is None:
                continue
            with img:
                return str(imagehash.phash(img))
        except Exception as exc:
            log.debug("phash falhou para %s: %s", fonte, exc)
    return None


def _abrir(path: Path) -> Image.Image | None:
    if path.suffix.lower() in RAW_EXTENSIONS:
        if not _HAS_RAW:  # pragma: no cover
            return None
        import rawpy

        with rawpy.imread(str(path)) as raw:
            thumb = raw.extract_thumb()
            if thumb.format == rawpy.ThumbFormat.JPEG:
                return Image.open(io.BytesIO(thumb.data))
            if thumb.format == rawpy.ThumbFormat.BITMAP:
                return Image.fromarray(thumb.data)
        return None
    return Image.open(path)
