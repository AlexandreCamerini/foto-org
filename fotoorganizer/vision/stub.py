"""Stub seguro: nenhuma análise, nenhum dado sai da máquina.

Mantém o resto da aplicação desacoplado até existir um modelo local
(roadmap v2). O motor de sugestões já trata a ausência de rótulos visuais.
"""

from __future__ import annotations

from pathlib import Path

from fotoorganizer.vision.base import VisionResult


class NullVisionProvider:
    @property
    def local(self) -> bool:
        return True

    def analisar(self, path: Path) -> VisionResult | None:
        return None
