"""Contrato dos provedores de análise visual (componente substituível).

Dois modos previstos: local/privado (padrão) e serviço externo opcional.
Um provider externo (ex.: Claude Vision) implementará este mesmo Protocol;
o envio exige opt-in explícito, indicação visual na UI e lista dos
arquivos a enviar — regras em docs/PRIVACIDADE.md. Rótulos visuais nunca
afirmam cidade/vila específica (só cena: praia, montanha, urbano…).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True, slots=True)
class VisionResult:
    # Rótulos de cena com score 0-1 (ex.: {"praia": 0.9, "externo": 0.8}).
    rotulos: dict[str, float] = field(default_factory=dict)
    tem_pessoas: bool | None = None
    qualidade_baixa: bool | None = None
    # captura_de_tela | documento | fotografia
    tipo: str | None = None
    # Identificação do provedor que analisou (auditoria).
    fonte: str = ""


class VisionProvider(Protocol):
    @property
    def local(self) -> bool:
        """True quando nenhum dado sai da máquina."""
        ...

    def analisar(self, path: Path) -> VisionResult | None:
        """Analisa uma imagem. None quando não há análise disponível."""
        ...
