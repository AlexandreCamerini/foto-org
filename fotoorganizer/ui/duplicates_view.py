"""Duplicatas lado a lado: lista de grupos à esquerda, membros em cartões
comparáveis à direita. Nenhuma exclusão — apenas papéis registrados."""

from __future__ import annotations

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from fotoorganizer.models import DuplicateRole
from fotoorganizer.repositories import DuplicateRepository, GroupRow, MemberRow
from fotoorganizer.ui import theme
from fotoorganizer.workers.thumbnail_service import ThumbnailService

_PAPEL_ROTULO = {
    DuplicateRole.INDEFINIDO: "",
    DuplicateRole.PRINCIPAL: "★ Principal",
    DuplicateRole.VERSAO: "Versão",
    DuplicateRole.IGNORADO: "Ignorado",
}


def _tamanho_legivel(n: int) -> str:
    for unidade in ("B", "KB", "MB", "GB"):
        if n < 1024 or unidade == "GB":
            return f"{n:.1f} {unidade}" if unidade != "B" else f"{n} B"
        n /= 1024
    return f"{n} B"


class DetectWorker(QThread):
    terminado = Signal(dict)
    falhou = Signal(str)

    def __init__(self, detector_factory, parent=None) -> None:
        super().__init__(parent)
        self._detector_factory = detector_factory

    def run(self) -> None:
        try:
            self.terminado.emit(self._detector_factory().detectar())
        except Exception as exc:  # noqa: BLE001 — erro vai para a UI
            self.falhou.emit(str(exc))


class _MemberCard(QFrame):
    escolher_principal = Signal(int)  # media_id

    def __init__(self, membro: MemberRow, thumbs: ThumbnailService,
                 parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("cartaoMembro")
        self.setFixedWidth(240)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        thumb = QLabel()
        thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        thumb.setFixedHeight(160)
        pixmap = thumbs.pixmap_for(membro.media_id, membro.hash_rapido,
                                   membro.caminho)
        if pixmap is not None:
            thumb.setPixmap(pixmap.scaled(
                224, 160, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            ))
        layout.addWidget(thumb)

        nome = QLabel(f"<b>{membro.nome}</b>")
        nome.setWordWrap(True)
        layout.addWidget(nome)

        caminho = QLabel(membro.caminho, objectName="textoSecundario")
        caminho.setWordWrap(True)
        caminho.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        layout.addWidget(caminho)
        layout.addWidget(
            QLabel(_tamanho_legivel(membro.tamanho), objectName="textoSecundario")
        )

        papel = _PAPEL_ROTULO[membro.papel]
        if papel:
            cor = (theme.CONF_ALTA if membro.papel == DuplicateRole.PRINCIPAL
                   else theme.TEXT_SECONDARY)
            rotulo = QLabel(papel)
            rotulo.setStyleSheet(f"color: {cor}; font-weight: 600;")
            layout.addWidget(rotulo)

        botao = QPushButton("Escolher como principal")
        botao.clicked.connect(
            lambda: self.escolher_principal.emit(membro.media_id)
        )
        layout.addWidget(botao)
        layout.addStretch(1)


class DuplicatesView(QWidget):
    mensagem = Signal(str)

    def __init__(self, repo: DuplicateRepository, detector_factory,
                 thumbs: ThumbnailService, parent=None) -> None:
        super().__init__(parent)
        self._repo = repo
        self._detector_factory = detector_factory
        self._thumbs = thumbs
        self._grupos: list[GroupRow] = []
        self._worker: DetectWorker | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        barra = QHBoxLayout()
        barra.setContentsMargins(12, 8, 12, 8)
        self._resumo = QLabel("", objectName="textoSecundario")
        barra.addWidget(self._resumo)
        barra.addStretch(1)
        self._btn_detectar = QPushButton("Detectar duplicatas")
        self._btn_ignorar = QPushButton("Manter todos / ignorar grupo")
        self._btn_desfazer = QPushButton("Desfazer decisão")
        for btn in (self._btn_detectar, self._btn_ignorar, self._btn_desfazer):
            barra.addWidget(btn)
        layout.addLayout(barra)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self._lista = QListWidget()
        self._lista.setFrameShape(QListWidget.Shape.NoFrame)
        splitter.addWidget(self._lista)

        self._membros_scroll = QScrollArea()
        self._membros_scroll.setWidgetResizable(True)
        self._membros_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._membros_area = QWidget()
        self._membros_layout = QHBoxLayout(self._membros_area)
        self._membros_layout.setContentsMargins(12, 12, 12, 12)
        self._membros_layout.setSpacing(12)
        self._membros_layout.addStretch(1)
        self._membros_scroll.setWidget(self._membros_area)
        splitter.addWidget(self._membros_scroll)
        splitter.setSizes([320, 680])
        layout.addWidget(splitter, stretch=1)

        self._btn_detectar.clicked.connect(self._detectar)
        self._btn_ignorar.clicked.connect(self._ignorar_grupo)
        self._btn_desfazer.clicked.connect(self._desfazer_grupo)
        self._lista.currentRowChanged.connect(self._mostrar_grupo)

        self.recarregar()

    # -- dados ------------------------------------------------------------
    def recarregar(self) -> None:
        linha = self._lista.currentRow()
        self._grupos = self._repo.listar_grupos()
        self._lista.blockSignals(True)
        self._lista.clear()
        for grupo in self._grupos:
            extra = " · decidido" if grupo.decidido else ""
            item = QListWidgetItem(
                f"{grupo.rotulo_nivel} · {len(grupo.membros)} arquivos · "
                f"{_tamanho_legivel(grupo.bytes_recuperaveis)} recuperáveis"
                f"{extra}"
            )
            item.setData(Qt.ItemDataRole.UserRole, grupo.id)
            self._lista.addItem(item)
        self._lista.blockSignals(False)

        total = len(self._grupos)
        self._resumo.setText(
            f"{total} grupo(s) de possíveis duplicatas" if total
            else "Nenhum grupo — rode a detecção."
        )
        if total:
            self._lista.setCurrentRow(min(max(linha, 0), total - 1))
        else:
            self._mostrar_grupo(-1)

    def grupo_atual(self) -> GroupRow | None:
        linha = self._lista.currentRow()
        return self._grupos[linha] if 0 <= linha < len(self._grupos) else None

    def _mostrar_grupo(self, _linha: int) -> None:
        while self._membros_layout.count() > 1:
            item = self._membros_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        grupo = self.grupo_atual()
        if grupo is None:
            return
        for membro in grupo.membros:
            cartao = _MemberCard(membro, self._thumbs)
            cartao.escolher_principal.connect(self._escolher_principal)
            self._membros_layout.insertWidget(
                self._membros_layout.count() - 1, cartao
            )

    # -- ações -------------------------------------------------------------
    def _detectar(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            return
        self._btn_detectar.setEnabled(False)
        self.mensagem.emit("Detectando duplicatas (hashes sob demanda)…")
        self._worker = DetectWorker(self._detector_factory, parent=self)
        self._worker.terminado.connect(self._on_detectado)
        self._worker.falhou.connect(self._on_falha)
        self._worker.start()

    def _on_detectado(self, stats: dict) -> None:
        self._btn_detectar.setEnabled(True)
        self.recarregar()
        self.mensagem.emit(
            f"Duplicatas: {stats['exato']} grupos idênticos, "
            f"{stats['conteudo']} de mesmo conteúdo, {stats['visual']} parecidos "
            f"({stats['preservados']} decisões preservadas)"
        )

    def _on_falha(self, erro: str) -> None:
        self._btn_detectar.setEnabled(True)
        self.mensagem.emit(f"Falha na detecção: {erro}")

    def _escolher_principal(self, media_id: int) -> None:
        grupo = self.grupo_atual()
        if grupo is None:
            return
        self._repo.escolher_principal(grupo.id, media_id)
        self.recarregar()
        self.mensagem.emit("Principal definido — demais membros marcados como versão")

    def _ignorar_grupo(self) -> None:
        grupo = self.grupo_atual()
        if grupo is None:
            return
        self._repo.ignorar_grupo(grupo.id)
        self.recarregar()
        self.mensagem.emit("Grupo ignorado — nenhum arquivo será tocado")

    def _desfazer_grupo(self) -> None:
        grupo = self.grupo_atual()
        if grupo is None:
            return
        self._repo.desfazer_grupo(grupo.id)
        self.recarregar()
        self.mensagem.emit("Decisão desfeita")
