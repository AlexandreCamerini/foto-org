"""Barra de filtros da biblioteca: busca, extensão, ano e ordenação."""

from __future__ import annotations

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLineEdit, QWidget

from fotoorganizer.repositories import MediaFilters, MediaRepository

_DEBOUNCE_MS = 300

ORDENACAO_OPCOES = [
    ("Mais recentes", "data_desc"),
    ("Mais antigas", "data_asc"),
    ("Nome", "nome"),
    ("Maiores", "tamanho_desc"),
]


class FilterBar(QWidget):
    filtros_alterados = Signal()

    def __init__(self, repo: MediaRepository, parent=None) -> None:
        super().__init__(parent)
        self._repo = repo
        self._source_id: int | None = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 4)
        layout.setSpacing(8)

        self._busca = QLineEdit()
        self._busca.setPlaceholderText("Buscar por nome ou caminho…")
        self._busca.setClearButtonEnabled(True)
        layout.addWidget(self._busca, stretch=1)

        self._ano = QComboBox()
        self._extensao = QComboBox()
        self._ordenacao = QComboBox()
        for rotulo, _valor in ORDENACAO_OPCOES:
            self._ordenacao.addItem(rotulo)
        layout.addWidget(self._ano)
        layout.addWidget(self._extensao)
        layout.addWidget(self._ordenacao)

        self._debounce = QTimer(self, singleShot=True, interval=_DEBOUNCE_MS)
        self._debounce.timeout.connect(self.filtros_alterados.emit)
        self._busca.textChanged.connect(lambda _t: self._debounce.start())
        self._ano.currentIndexChanged.connect(lambda _i: self.filtros_alterados.emit())
        self._extensao.currentIndexChanged.connect(
            lambda _i: self.filtros_alterados.emit()
        )
        self._ordenacao.currentIndexChanged.connect(
            lambda _i: self.filtros_alterados.emit()
        )

        self.recarregar_opcoes()

    def recarregar_opcoes(self) -> None:
        """Repovoa anos/extensões do catálogo preservando a seleção."""
        for combo, valores, todos in (
            (self._ano, [str(a) for a in self._repo.anos()], "Qualquer data"),
            (self._extensao, self._repo.extensoes(), "Todos os tipos"),
        ):
            atual = combo.currentText()
            combo.blockSignals(True)
            combo.clear()
            combo.addItem(todos)
            for valor in valores:
                combo.addItem(valor)
            idx = combo.findText(atual)
            combo.setCurrentIndex(idx if idx >= 0 else 0)
            combo.blockSignals(False)

    def set_source_id(self, source_id: int | None) -> None:
        self._source_id = source_id

    def filtros(self) -> MediaFilters:
        return MediaFilters(
            busca=self._busca.text().strip() or None,
            extensao=(
                self._extensao.currentText()
                if self._extensao.currentIndex() > 0 else None
            ),
            ano=int(self._ano.currentText()) if self._ano.currentIndex() > 0 else None,
            source_id=self._source_id,
            ordenacao=ORDENACAO_OPCOES[self._ordenacao.currentIndex()][1],
        )
