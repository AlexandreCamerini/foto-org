"""Importação de catálogo externo em QThread — a UI nunca bloqueia."""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from fotoorganizer.sources import (
    ExternalCatalogImporter,
    ExternalCatalogProvider,
    ImportMetrics,
)

_EMIT_EVERY = 20


class ImportWorker(QThread):
    progresso = Signal(int, int, int)  # vistos, importados, erros
    # importados, pulados, erros, erro_fatal ("" quando ok)
    terminado = Signal(int, int, int, str)

    def __init__(self, importer: ExternalCatalogImporter,
                 provider: ExternalCatalogProvider, parent=None) -> None:
        super().__init__(parent)
        self._importer = importer
        self._provider = provider

    def run(self) -> None:
        contador = 0

        def on_progress(metrics: ImportMetrics, _caminho: str) -> None:
            nonlocal contador
            contador += 1
            if contador % _EMIT_EVERY == 0:
                self.progresso.emit(
                    metrics.vistos, metrics.importados, metrics.erros
                )

        try:
            metrics = self._importer.importar(
                self._provider, progress=on_progress
            )
        except Exception as exc:
            # Biblioteca inacessível (permissão), pasta inválida etc. —
            # a mensagem chega à UI, nada derruba o app.
            self.terminado.emit(0, 0, 0, str(exc))
            return
        self.terminado.emit(
            metrics.importados, metrics.pulados, metrics.erros, ""
        )
