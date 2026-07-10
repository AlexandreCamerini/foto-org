"""Stub seguro: nenhum rosto detectado, nenhuma dependência pesada.

A associação manual (PeopleRepository) funciona sem detector; um provider
local real (roadmap v2) implementará o mesmo Protocol.
"""

from __future__ import annotations

import math
from pathlib import Path

from fotoorganizer.faces.base import FaceDetection


class NullFaceProvider:
    @property
    def local(self) -> bool:
        return True

    def detectar(self, path: Path) -> list[FaceDetection]:
        return []

    def similaridade(self, a: list[float], b: list[float]) -> float:
        """Cosseno — pronto para quando houver embeddings reais."""
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norma = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
        return max(0.0, dot / norma) if norma else 0.0
