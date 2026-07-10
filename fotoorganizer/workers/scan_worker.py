"""Varredura em QThread — a UI nunca bloqueia durante a indexação."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Signal

from fotoorganizer.scanner import CatalogScanner, ScanControl, ScanMetrics

_EMIT_EVERY = 20  # arquivos entre emissões de progresso


class ScanWorker(QThread):
    progresso = Signal(int, int, int, float)  # vistos, indexados, erros, arq/s
    terminado = Signal(str, int, int, int)    # status, indexados, pulados, erros

    def __init__(self, scanner: CatalogScanner, caminho: Path, parent=None) -> None:
        super().__init__(parent)
        self._scanner = scanner
        self._caminho = caminho
        self.control = ScanControl()

    def run(self) -> None:
        contador = 0

        def on_progress(metrics: ScanMetrics, _caminho: str) -> None:
            nonlocal contador
            contador += 1
            if contador % _EMIT_EVERY == 0:
                self.progresso.emit(
                    metrics.vistos, metrics.indexados, metrics.erros,
                    metrics.arquivos_por_segundo,
                )

        scan, metrics = self._scanner.scan_source(
            self._caminho, progress=on_progress, control=self.control
        )
        self.terminado.emit(
            scan.status.value, metrics.indexados, metrics.pulados, metrics.erros
        )
