"""Contrato do reconhecimento facial (opcional, desativado por padrão).

Regras invioláveis (CLAUDE.md invariante 6 / docs/PRIVACIDADE.md):
processamento local, nenhuma busca de identidade na internet, embeddings
criptografados, limiar conservador, resultado é sempre SUGESTÃO — associar
um nome exige confirmação humana. Estados: detectado → possível →
confirmado/incorreto (models.FaceState).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True, slots=True)
class FaceDetection:
    # Caixa normalizada 0-1: (x, y, largura, altura).
    bbox: tuple[float, float, float, float]
    # Vetor de características para comparação local (será criptografado).
    embedding: list[float] | None
    modelo: str


class FaceRecognitionProvider(Protocol):
    @property
    def local(self) -> bool:
        ...

    def detectar(self, path: Path) -> list[FaceDetection]:
        """Detecta rostos (sem identificar ninguém). Lista vazia quando não
        há suporte ou não há rostos."""
        ...

    def similaridade(self, a: list[float], b: list[float]) -> float:
        """0-1 entre dois embeddings; quem decide se é 'possível pessoa'
        é o chamador, com limiar conservador."""
        ...
