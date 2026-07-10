"""Inspetor: detalhes da foto selecionada (somente leitura no M2)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFormLayout,
    QFrame,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from fotoorganizer.models import MediaFile


def _campo() -> QLabel:
    label = QLabel("—")
    label.setWordWrap(True)
    label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return label


def _tamanho_legivel(n: int) -> str:
    for unidade in ("B", "KB", "MB", "GB"):
        if n < 1024 or unidade == "GB":
            return f"{n:.1f} {unidade}" if unidade != "B" else f"{n} B"
        n /= 1024
    return f"{n} B"


class Inspector(QScrollArea):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("painelInspetor")
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)

        corpo = QWidget(objectName="painelInspetor")
        layout = QVBoxLayout(corpo)
        layout.setContentsMargins(0, 0, 0, 12)
        layout.setSpacing(8)

        layout.addWidget(QLabel("INSPETOR", objectName="tituloPainel"))

        self._preview = QLabel()
        self._preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview.setMinimumHeight(180)
        layout.addWidget(self._preview)

        self._vazio = QLabel(
            "Selecione uma foto para ver\nmetadados, sugestões e evidências.",
            objectName="textoSecundario",
        )
        self._vazio.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._vazio)

        self._form_widget = QWidget()
        form = QFormLayout(self._form_widget)
        form.setContentsMargins(12, 0, 12, 0)
        form.setVerticalSpacing(6)
        self._nome = _campo()
        self._caminho = _campo()
        self._tamanho = _campo()
        self._data = _campo()
        self._modificado = _campo()
        self._camera = _campo()
        self._lente = _campo()
        self._dimensoes = _campo()
        self._gps = _campo()
        self._hash = _campo()
        self._erro = _campo()
        for rotulo, campo in [
            ("Nome", self._nome), ("Caminho", self._caminho),
            ("Tamanho", self._tamanho), ("Capturada", self._data),
            ("Modificado", self._modificado), ("Câmera", self._camera),
            ("Lente", self._lente), ("Dimensões", self._dimensoes),
            ("GPS", self._gps), ("Hash", self._hash), ("Erro", self._erro),
        ]:
            form.addRow(QLabel(rotulo, objectName="textoSecundario"), campo)
        self._form_widget.hide()
        layout.addWidget(self._form_widget)
        layout.addStretch(1)

        self.setWidget(corpo)

    def limpar(self) -> None:
        self._form_widget.hide()
        self._preview.clear()
        self._vazio.show()

    def mostrar(self, media: MediaFile, pixmap: QPixmap | None) -> None:
        self._vazio.hide()
        self._form_widget.show()

        if pixmap is not None and not pixmap.isNull():
            escalado = pixmap.scaled(
                260, 220, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._preview.setPixmap(escalado)
        else:
            self._preview.clear()

        self._nome.setText(media.nome)
        self._caminho.setText(media.caminho)
        self._tamanho.setText(_tamanho_legivel(media.tamanho))
        self._data.setText(
            media.data_capturada.strftime("%d/%m/%Y %H:%M:%S")
            if media.data_capturada else "sem data EXIF"
        )
        self._modificado.setText(
            media.mtime.strftime("%d/%m/%Y %H:%M:%S") if media.mtime else "—"
        )
        camera = " ".join(filter(None, [media.make, media.model]))
        self._camera.setText(camera or "—")
        self._lente.setText(media.lente or "—")
        self._dimensoes.setText(
            f"{media.largura} × {media.altura}" if media.largura else "—"
        )
        self._gps.setText(
            f"{media.gps_lat:.5f}, {media.gps_lon:.5f}"
            if media.gps_lat is not None else "—"
        )
        self._hash.setText(media.hash_rapido or "—")
        self._erro.setText(media.erro_leitura or "—")
