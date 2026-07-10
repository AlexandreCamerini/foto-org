"""Janela principal: sidebar | grade | inspetor + barra de status.

No M0 os painéis são placeholders com estado vazio; a grade virtualizada
chega no M2 (docs/ROADMAP.md).
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QLabel,
    QMainWindow,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from fotoorganizer import __version__


def _panel(object_name: str, title: str, empty_text: str) -> QWidget:
    panel = QWidget(objectName=object_name)
    layout = QVBoxLayout(panel)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(4)

    header = QLabel(title.upper(), objectName="tituloPainel")
    layout.addWidget(header)

    empty = QLabel(empty_text, objectName="textoSecundario")
    empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
    empty.setWordWrap(True)
    layout.addWidget(empty, stretch=1)
    return panel


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Foto Organizer")
        self.resize(1280, 800)

        self.sidebar = _panel(
            "painelLateral", "Fontes",
            "Nenhuma fonte cadastrada.\nAdicione uma pasta de fotos para começar.",
        )
        self.grid_area = _panel(
            "areaGrade", "Biblioteca",
            "A grade de miniaturas aparece aqui\napós a primeira varredura.",
        )
        self.inspector = _panel(
            "painelInspetor", "Inspetor",
            "Selecione uma foto para ver\nmetadados, sugestões e evidências.",
        )

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.addWidget(self.sidebar)
        self.splitter.addWidget(self.grid_area)
        self.splitter.addWidget(self.inspector)
        self.splitter.setSizes([240, 760, 280])
        self.splitter.setCollapsible(1, False)
        self.setCentralWidget(self.splitter)

        self.statusBar().showMessage(f"Pronto — catálogo local, v{__version__}")

        # ⌘1 / ⌘3 alternam sidebar e inspetor (DIRECAO_DE_ARTE.md).
        QShortcut(QKeySequence("Ctrl+1"), self, activated=self._toggle_sidebar)
        QShortcut(QKeySequence("Ctrl+3"), self, activated=self._toggle_inspector)

    def _toggle_sidebar(self) -> None:
        # isHidden() reflete o estado explícito mesmo antes do primeiro show().
        self.sidebar.setVisible(self.sidebar.isHidden())

    def _toggle_inspector(self) -> None:
        self.inspector.setVisible(self.inspector.isHidden())
