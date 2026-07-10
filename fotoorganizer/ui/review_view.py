"""Tela de revisão de sugestões: aprovar/rejeitar/editar/desfazer, em lote,
com filtro por confiança e justificativas (evidências) sempre visíveis."""

from __future__ import annotations

from PySide6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    Qt,
    QThread,
    Signal,
)
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableView,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from fotoorganizer.models import ConfidenceLevel, SuggestionStatus
from fotoorganizer.repositories import (
    SuggestionFilters,
    SuggestionRepository,
    SuggestionRow,
)
from fotoorganizer.ui import theme

PAGE_SIZE = 256

_NIVEL_ROTULO = {
    ConfidenceLevel.ALTA: "Alta",
    ConfidenceLevel.MEDIA: "Média",
    ConfidenceLevel.BAIXA: "Baixa",
}
_NIVEL_COR = {
    ConfidenceLevel.ALTA: theme.CONF_ALTA,
    ConfidenceLevel.MEDIA: theme.CONF_MEDIA,
    ConfidenceLevel.BAIXA: theme.CONF_BAIXA,
}
_STATUS_ROTULO = {
    SuggestionStatus.PENDENTE: "Pendente",
    SuggestionStatus.APROVADA: "Aprovada",
    SuggestionStatus.REJEITADA: "Rejeitada",
    SuggestionStatus.EDITADA: "Editada",
}

COLUNAS = ["Foto", "Origem", "Destino sugerido", "Confiança", "Status"]
COL_DESTINO = 2


class SuggestionTableModel(QAbstractTableModel):
    def __init__(self, repo: SuggestionRepository, parent=None) -> None:
        super().__init__(parent)
        self._repo = repo
        self._filters = SuggestionFilters()
        self._rows: list[SuggestionRow] = []
        self._total = 0

    def set_filters(self, filters: SuggestionFilters) -> None:
        self.beginResetModel()
        self._filters = filters
        self._rows.clear()
        self._total = self._repo.contar(filters)
        self.endResetModel()

    def refresh(self) -> None:
        self.set_filters(self._filters)

    @property
    def total(self) -> int:
        return self._total

    def row_at(self, row: int) -> SuggestionRow | None:
        return self._rows[row] if 0 <= row < len(self._rows) else None

    # -- Qt model ----------------------------------------------------------
    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(COLUNAS)

    def canFetchMore(self, parent=QModelIndex()) -> bool:
        return not parent.isValid() and len(self._rows) < self._total

    def fetchMore(self, parent=QModelIndex()) -> None:
        offset = len(self._rows)
        page = self._repo.listar(self._filters, PAGE_SIZE, offset)
        if not page:
            self._total = offset
            return
        self.beginInsertRows(QModelIndex(), offset, offset + len(page) - 1)
        self._rows.extend(page)
        self.endInsertRows()

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if (orientation == Qt.Orientation.Horizontal
                and role == Qt.ItemDataRole.DisplayRole):
            return COLUNAS[section]
        return None

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        item = self._rows[index.row()]
        col = index.column()
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            return [
                item.nome, item.pasta, item.destino,
                _NIVEL_ROTULO[item.nivel], _STATUS_ROTULO[item.status],
            ][col]
        if role == Qt.ItemDataRole.ForegroundRole and col == 3:
            return QColor(_NIVEL_COR[item.nivel])
        if role == Qt.ItemDataRole.ToolTipRole:
            return f"{item.pasta}/{item.nome}\n→ {item.destino}"
        return None

    def flags(self, index: QModelIndex):
        base = super().flags(index)
        if index.column() == COL_DESTINO:
            return base | Qt.ItemFlag.ItemIsEditable
        return base

    def setData(self, index: QModelIndex, value, role=Qt.ItemDataRole.EditRole):
        if role != Qt.ItemDataRole.EditRole or index.column() != COL_DESTINO:
            return False
        novo = str(value).strip()
        item = self._rows[index.row()]
        if not novo or novo == item.destino:
            return False
        self._repo.editar_destino(item.id, novo)
        self._rows[index.row()] = SuggestionRow(
            id=item.id, media_id=item.media_id, nome=item.nome, pasta=item.pasta,
            destino=novo, nivel=item.nivel, status=SuggestionStatus.EDITADA,
        )
        self.dataChanged.emit(index, self.index(index.row(), len(COLUNAS) - 1))
        return True


class GenerateWorker(QThread):
    terminado = Signal(dict)
    falhou = Signal(str)

    def __init__(self, engine_factory, parent=None) -> None:
        super().__init__(parent)
        self._engine_factory = engine_factory

    def run(self) -> None:
        try:
            engine = self._engine_factory()
            self.terminado.emit(engine.gerar())
        except Exception as exc:  # noqa: BLE001 — erro vai para a UI
            self.falhou.emit(str(exc))


class ReviewView(QWidget):
    mensagem = Signal(str)

    def __init__(self, repo: SuggestionRepository, engine_factory,
                 parent=None) -> None:
        super().__init__(parent)
        self._repo = repo
        self._engine_factory = engine_factory
        self._worker: GenerateWorker | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # -- barra de ações ------------------------------------------------
        barra = QHBoxLayout()
        barra.setContentsMargins(12, 8, 12, 8)
        barra.setSpacing(8)

        self._filtro_status = QComboBox()
        for rotulo in ["Pendentes", "Aprovadas", "Rejeitadas", "Editadas", "Todas"]:
            self._filtro_status.addItem(rotulo)
        self._filtro_nivel = QComboBox()
        for rotulo in ["Qualquer confiança", "Alta", "Média", "Baixa"]:
            self._filtro_nivel.addItem(rotulo)
        barra.addWidget(self._filtro_status)
        barra.addWidget(self._filtro_nivel)
        barra.addStretch(1)

        self._btn_gerar = QPushButton("Gerar sugestões")
        self._btn_aprovar = QPushButton("Aprovar")
        self._btn_rejeitar = QPushButton("Rejeitar")
        self._btn_desfazer = QPushButton("Desfazer")
        for btn in (self._btn_gerar, self._btn_aprovar, self._btn_rejeitar,
                    self._btn_desfazer):
            barra.addWidget(btn)
        layout.addLayout(barra)

        # -- tabela ---------------------------------------------------------
        self.model = SuggestionTableModel(repo)
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableView.SelectionMode.ExtendedSelection)
        self.table.verticalHeader().hide()
        self.table.setShowGrid(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(False)
        self.table.setColumnWidth(0, 160)
        self.table.setColumnWidth(1, 260)
        header.setSectionResizeMode(COL_DESTINO, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(3, 90)
        self.table.setColumnWidth(4, 90)
        layout.addWidget(self.table, stretch=1)

        # -- evidências -------------------------------------------------------
        layout.addWidget(QLabel("POR QUÊ? (EVIDÊNCIAS)", objectName="tituloPainel"))
        self._evidencias = QTextBrowser()
        self._evidencias.setMaximumHeight(140)
        self._evidencias.setPlaceholderText(
            "Selecione uma sugestão para ver os critérios utilizados."
        )
        layout.addWidget(self._evidencias)

        # -- sinais -----------------------------------------------------------
        self._filtro_status.currentIndexChanged.connect(self._aplicar_filtros)
        self._filtro_nivel.currentIndexChanged.connect(self._aplicar_filtros)
        self._btn_gerar.clicked.connect(self._gerar)
        self._btn_aprovar.clicked.connect(lambda: self._acao(self._repo.aprovar))
        self._btn_rejeitar.clicked.connect(lambda: self._acao(self._repo.rejeitar))
        self._btn_desfazer.clicked.connect(lambda: self._acao(self._repo.desfazer))
        self.table.selectionModel().currentRowChanged.connect(
            self._mostrar_evidencias
        )

        self._aplicar_filtros()

    # -- filtros ---------------------------------------------------------------
    def _filtros(self) -> SuggestionFilters:
        status = [
            SuggestionStatus.PENDENTE, SuggestionStatus.APROVADA,
            SuggestionStatus.REJEITADA, SuggestionStatus.EDITADA, None,
        ][self._filtro_status.currentIndex()]
        nivel = [None, ConfidenceLevel.ALTA, ConfidenceLevel.MEDIA,
                 ConfidenceLevel.BAIXA][self._filtro_nivel.currentIndex()]
        return SuggestionFilters(status=status, nivel=nivel)

    def _aplicar_filtros(self) -> None:
        self.model.set_filters(self._filtros())
        self._evidencias.clear()

    # -- ações -----------------------------------------------------------------
    def _ids_selecionados(self) -> list[int]:
        linhas = {i.row() for i in self.table.selectionModel().selectedRows()}
        ids = []
        for linha in sorted(linhas):
            item = self.model.row_at(linha)
            if item is not None:
                ids.append(item.id)
        return ids

    def _acao(self, funcao) -> None:
        ids = self._ids_selecionados()
        if not ids:
            self.mensagem.emit("Nenhuma sugestão selecionada")
            return
        alteradas = funcao(ids)
        self.model.refresh()
        self.mensagem.emit(f"{alteradas} sugestão(ões) atualizada(s)")

    def _gerar(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            return
        self._btn_gerar.setEnabled(False)
        self.mensagem.emit("Gerando sugestões (evidências + agrupamentos)…")
        self._worker = GenerateWorker(self._engine_factory, parent=self)
        self._worker.terminado.connect(self._on_gerado)
        self._worker.falhou.connect(self._on_falha)
        self._worker.start()

    def _on_gerado(self, stats: dict) -> None:
        self._btn_gerar.setEnabled(True)
        self.model.refresh()
        self.mensagem.emit(
            f"Sugestões geradas: {stats['sugestoes']} "
            f"({stats['viagens']} viagens, {stats['preservadas']} decisões "
            f"do usuário preservadas)"
        )

    def _on_falha(self, erro: str) -> None:
        self._btn_gerar.setEnabled(True)
        self.mensagem.emit(f"Falha ao gerar sugestões: {erro}")

    # -- evidências ---------------------------------------------------------
    def _mostrar_evidencias(self, current: QModelIndex, _previous) -> None:
        self._evidencias.clear()
        if not current.isValid():
            return
        item = self.model.row_at(current.row())
        if item is None:
            return
        linhas = []
        for ev in self._repo.evidencias(item.id):
            cor = _NIVEL_COR[ev.nivel]
            linhas.append(
                f"<p style='margin:2px 0'>"
                f"<b>{ev.campo}</b> = {ev.valor} "
                f"<span style='color:{cor}'>[{_NIVEL_ROTULO[ev.nivel]} "
                f"· {ev.score:.2f}]</span><br>"
                f"<span style='color:{theme.TEXT_SECONDARY}'>"
                f"{ev.origem}: {ev.justificativa}</span></p>"
            )
        self._evidencias.setHtml(
            "".join(linhas) or "<i>Sem evidências registradas.</i>"
        )
