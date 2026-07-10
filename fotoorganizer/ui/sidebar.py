"""Sidebar: fontes cadastradas, estatísticas e progresso da varredura."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from fotoorganizer.repositories import MediaRepository

TODAS_AS_FONTES = -1


class Sidebar(QWidget):
    adicionar_pasta = Signal()
    fonte_selecionada = Signal(object)  # source_id: int | None
    pausar_scan = Signal()
    continuar_scan = Signal()
    cancelar_scan = Signal()

    def __init__(self, repo: MediaRepository, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("painelLateral")
        self._repo = repo

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 8)
        layout.setSpacing(4)

        layout.addWidget(QLabel("FONTES", objectName="tituloPainel"))

        self._lista = QListWidget()
        self._lista.setFrameShape(QListWidget.Shape.NoFrame)
        self._lista.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._lista.setTextElideMode(Qt.TextElideMode.ElideMiddle)
        self._lista.currentItemChanged.connect(self._on_selecao)
        layout.addWidget(self._lista, stretch=1)

        self._btn_adicionar = QPushButton("Adicionar pasta…")
        self._btn_adicionar.clicked.connect(self.adicionar_pasta.emit)
        botao_row = QHBoxLayout()
        botao_row.setContentsMargins(12, 4, 12, 4)
        botao_row.addWidget(self._btn_adicionar)
        layout.addLayout(botao_row)

        # Progresso do scan (aparece só durante varredura)
        self._scan_box = QWidget()
        scan_layout = QVBoxLayout(self._scan_box)
        scan_layout.setContentsMargins(12, 4, 12, 4)
        scan_layout.setSpacing(4)
        self._scan_label = QLabel("", objectName="textoSecundario")
        self._scan_label.setWordWrap(True)
        scan_layout.addWidget(self._scan_label)
        botoes = QHBoxLayout()
        self._btn_pausar = QPushButton("Pausar")
        self._btn_pausar.clicked.connect(self._on_pausar)
        self._btn_cancelar = QPushButton("Cancelar")
        self._btn_cancelar.clicked.connect(self.cancelar_scan.emit)
        botoes.addWidget(self._btn_pausar)
        botoes.addWidget(self._btn_cancelar)
        scan_layout.addLayout(botoes)
        self._scan_box.hide()
        self._pausado = False
        layout.addWidget(self._scan_box)

        self._stats = QLabel("", objectName="textoSecundario")
        self._stats.setContentsMargins(12, 4, 12, 0)
        layout.addWidget(self._stats)

        self.recarregar()

    # -- dados -----------------------------------------------------------
    def recarregar(self) -> None:
        atual = self.fonte_atual()
        self._lista.blockSignals(True)
        self._lista.clear()

        stats = self._repo.estatisticas()
        item_todas = QListWidgetItem(f"Todas as fotos  ({stats['total']})")
        item_todas.setData(Qt.ItemDataRole.UserRole, TODAS_AS_FONTES)
        self._lista.addItem(item_todas)

        selecionar = item_todas
        for source, contagem in self._repo.fontes_com_contagem():
            rotulo = source.apelido or source.caminho
            sufixo = "" if source.disponivel else "  ⚠ indisponível"
            item = QListWidgetItem(f"{rotulo}  ({contagem}){sufixo}")
            item.setData(Qt.ItemDataRole.UserRole, source.id)
            item.setToolTip(source.caminho)
            self._lista.addItem(item)
            if source.id == atual:
                selecionar = item

        self._lista.setCurrentItem(selecionar)
        self._lista.blockSignals(False)

        erros = f" · {stats['erros']} erros" if stats["erros"] else ""
        self._stats.setText(f"{stats['total']} fotos · {stats['fontes']} fontes{erros}")

    def fonte_atual(self) -> int | None:
        item = self._lista.currentItem()
        if item is None:
            return None
        valor = item.data(Qt.ItemDataRole.UserRole)
        return None if valor == TODAS_AS_FONTES else valor

    def _on_selecao(self, *_args) -> None:
        self.fonte_selecionada.emit(self.fonte_atual())

    # -- scan ------------------------------------------------------------
    def scan_iniciado(self, caminho: str) -> None:
        self._btn_adicionar.setEnabled(False)
        self._pausado = False
        self._btn_pausar.setText("Pausar")
        self._scan_label.setText(f"Varrendo {caminho}…")
        self._scan_box.show()

    def scan_progresso(self, vistos: int, indexados: int, erros: int,
                       aps: float) -> None:
        erros_txt = f" · {erros} erros" if erros else ""
        self._scan_label.setText(
            f"{vistos} vistos · {indexados} indexados{erros_txt} · {aps:.0f} arq/s"
        )

    def scan_terminado(self) -> None:
        self._btn_adicionar.setEnabled(True)
        self._scan_box.hide()
        self.recarregar()

    def _on_pausar(self) -> None:
        if self._pausado:
            self._pausado = False
            self._btn_pausar.setText("Pausar")
            self.continuar_scan.emit()
        else:
            self._pausado = True
            self._btn_pausar.setText("Continuar")
            self.pausar_scan.emit()
