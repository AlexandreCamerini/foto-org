"""Planejamento de operações: plano → dry-run → confirmação → cópia.

O botão Executar só habilita depois do dry-run, e a execução pede
confirmação explícita — espelho fiel do princípio "revisar antes de
executar operações físicas".
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, QThread, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from fotoorganizer.models import OperationStatus
from fotoorganizer.operations import ExecutionControl, OperationExecutor, OperationPlanner
from fotoorganizer.repositories.operations import ItemRow, OperationRepository

_STATUS_ROTULO = {
    OperationStatus.PLANEJADA: "Planejada",
    OperationStatus.APROVADA: "Aprovada",
    OperationStatus.EXECUTANDO: "Executando",
    OperationStatus.CONCLUIDA: "Concluída",
    OperationStatus.CANCELADA: "Cancelada",
    OperationStatus.ERRO: "Erro",
}

COLUNAS = ["Origem", "Destino", "Status", "Observação"]


def _fmt_bytes(n: int | None) -> str:
    if n is None:
        return "?"
    valor = float(n)
    for unidade in ("B", "KB", "MB", "GB", "TB"):
        if valor < 1024 or unidade == "TB":
            return f"{valor:.1f} {unidade}"
        valor /= 1024
    return f"{n} B"


class ItemTableModel(QAbstractTableModel):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._rows: list[ItemRow] = []

    def set_rows(self, rows: list[ItemRow]) -> None:
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(COLUNAS)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if (orientation == Qt.Orientation.Horizontal
                and role == Qt.ItemDataRole.DisplayRole):
            return COLUNAS[section]
        return None

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or role != Qt.ItemDataRole.DisplayRole:
            return None
        item = self._rows[index.row()]
        return [
            item.origem, item.destino or "—",
            _STATUS_ROTULO[item.status],
            item.erro or item.conflito or "",
        ][index.column()]


class ExecuteWorker(QThread):
    progresso = Signal(int, int, str)
    terminado = Signal(dict)
    falhou = Signal(str)

    def __init__(self, executor: OperationExecutor, plan_id: int,
                 parent=None) -> None:
        super().__init__(parent)
        self._executor = executor
        self._plan_id = plan_id
        self.control = ExecutionControl()

    def run(self) -> None:
        try:
            stats = self._executor.executar(
                self._plan_id, progress=self.progresso.emit,
                control=self.control,
            )
            self.terminado.emit(stats)
        except Exception as exc:  # noqa: BLE001 — erro vai para a UI
            self.falhou.emit(str(exc))


class OperationsView(QWidget):
    mensagem = Signal(str)

    def __init__(self, session_factory, parent=None) -> None:
        super().__init__(parent)
        self._factory = session_factory
        self._repo = OperationRepository(session_factory)
        self._planner = OperationPlanner(session_factory)
        self._executor = OperationExecutor(session_factory)
        self._raiz_destino: Path | None = None
        self._worker: ExecuteWorker | None = None
        self._dry_run_ok: set[int] = set()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        barra = QHBoxLayout()
        barra.setContentsMargins(12, 8, 12, 8)
        barra.setSpacing(8)
        self._btn_destino = QPushButton("Escolher pasta de destino…")
        self._rotulo_destino = QLabel("nenhuma", objectName="textoSecundario")
        self._btn_plano = QPushButton("Criar plano das aprovadas")
        barra.addWidget(self._btn_destino)
        barra.addWidget(self._rotulo_destino, stretch=1)
        barra.addWidget(self._btn_plano)
        layout.addLayout(barra)

        barra2 = QHBoxLayout()
        barra2.setContentsMargins(12, 0, 12, 8)
        barra2.setSpacing(8)
        self._planos = QComboBox()
        barra2.addWidget(self._planos, stretch=1)
        self._btn_dry = QPushButton("Dry-run")
        self._btn_exec = QPushButton("Executar (copiar)")
        self._btn_exec.setEnabled(False)
        self._btn_cancelar = QPushButton("Cancelar")
        self._btn_cancelar.setEnabled(False)
        for btn in (self._btn_dry, self._btn_exec, self._btn_cancelar):
            barra2.addWidget(btn)
        layout.addLayout(barra2)

        self._resumo = QLabel("", objectName="textoSecundario")
        self._resumo.setContentsMargins(12, 0, 12, 4)
        self._resumo.setWordWrap(True)
        layout.addWidget(self._resumo)

        self.model = ItemTableModel()
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.verticalHeader().hide()
        self.table.setShowGrid(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table, stretch=1)

        self._btn_destino.clicked.connect(self._escolher_destino)
        self._btn_plano.clicked.connect(self._criar_plano)
        self._btn_dry.clicked.connect(self._dry_run)
        self._btn_exec.clicked.connect(self._executar)
        self._btn_cancelar.clicked.connect(self._cancelar)
        self._planos.currentIndexChanged.connect(lambda _i: self._mostrar_plano())

        self.recarregar()

    # -- dados -------------------------------------------------------------
    def plano_atual(self) -> int | None:
        return self._planos.currentData()

    def recarregar(self) -> None:
        atual = self.plano_atual()
        self._planos.blockSignals(True)
        self._planos.clear()
        for plano in self._repo.listar_planos():
            dry = " · dry-run feito" if plano.dry_run_em else ""
            rotulo = (
                f"#{plano.id} {plano.nome} — "
                f"{_STATUS_ROTULO[plano.status]} · "
                f"{plano.concluidos}/{plano.total_itens} itens"
                f"{' · ' + str(plano.com_conflito) + ' conflitos' if plano.com_conflito else ''}"
                f"{dry}"
            )
            self._planos.addItem(rotulo, plano.id)
            if plano.dry_run_em:
                self._dry_run_ok.add(plano.id)
        if atual is not None:
            idx = self._planos.findData(atual)
            if idx >= 0:
                self._planos.setCurrentIndex(idx)
        self._planos.blockSignals(False)
        self._mostrar_plano()

    def _mostrar_plano(self) -> None:
        plan_id = self.plano_atual()
        self.model.set_rows(self._repo.itens(plan_id) if plan_id else [])
        self._btn_exec.setEnabled(
            plan_id is not None and plan_id in self._dry_run_ok
        )

    # -- ações ------------------------------------------------------------
    def _escolher_destino(self) -> None:
        pasta = QFileDialog.getExistingDirectory(self, "Pasta de destino da cópia")
        if pasta:
            self.set_destino(Path(pasta))

    def set_destino(self, raiz: Path) -> None:
        self._raiz_destino = raiz
        self._rotulo_destino.setText(str(raiz))

    def _criar_plano(self) -> None:
        if self._raiz_destino is None:
            self.mensagem.emit("Escolha a pasta de destino primeiro")
            return
        plan_id = self._planner.criar_plano(self._raiz_destino)
        if plan_id is None:
            self.mensagem.emit(
                "Nada a planejar — aprove sugestões na aba Revisão antes"
            )
            return
        self.recarregar()
        idx = self._planos.findData(plan_id)
        if idx >= 0:
            self._planos.setCurrentIndex(idx)
        self.mensagem.emit(f"Plano #{plan_id} criado — rode o dry-run")

    def _dry_run(self) -> None:
        plan_id = self.plano_atual()
        if plan_id is None:
            return
        resultado = self._executor.dry_run(plan_id)
        self._dry_run_ok.add(plan_id)
        problemas = resultado["problemas"]
        espaco = (
            f"{_fmt_bytes(resultado['bytes_necessarios'])} necessários, "
            f"{_fmt_bytes(resultado['bytes_livres'])} livres"
        )
        detalhe = (
            f"Dry-run: {resultado['prontos']} arquivos prontos para copiar · "
            f"{espaco}"
            + ("" if resultado["espaco_suficiente"] else " · ESPAÇO INSUFICIENTE")
            + (f" · {len(problemas)} problema(s): " + "; ".join(problemas[:5])
               if problemas else "")
        )
        self._resumo.setText(detalhe)
        self.recarregar()
        self.mensagem.emit("Dry-run concluído — nada foi copiado ainda")

    def _executar(self) -> None:
        plan_id = self.plano_atual()
        if plan_id is None:
            return
        confirmacao = QMessageBox.question(
            self, "Confirmar cópia",
            "Copiar os arquivos do plano para o destino?\n\n"
            "Os originais NUNCA são movidos, alterados ou excluídos.",
        )
        if confirmacao != QMessageBox.StandardButton.Yes:
            return
        self._executar_confirmado(plan_id)

    def _executar_confirmado(self, plan_id: int) -> None:
        self._btn_exec.setEnabled(False)
        self._btn_cancelar.setEnabled(True)
        self._worker = ExecuteWorker(self._executor, plan_id, parent=self)
        self._worker.progresso.connect(
            lambda n, total, origem: self.mensagem.emit(
                f"Copiando {n}/{total}: {origem}"
            )
        )
        self._worker.terminado.connect(self._on_executado)
        self._worker.falhou.connect(self._on_falha)
        self._worker.start()

    def _on_executado(self, stats: dict) -> None:
        self._btn_cancelar.setEnabled(False)
        self.recarregar()
        extra = " (cancelado com segurança)" if stats["cancelado"] else ""
        self.mensagem.emit(
            f"Cópia finalizada: {stats['copiados']} copiados e verificados, "
            f"{stats['erros']} erros, {stats['pulados']} já feitos{extra}"
        )

    def _on_falha(self, erro: str) -> None:
        self._btn_cancelar.setEnabled(False)
        self.recarregar()
        self.mensagem.emit(f"Execução recusada: {erro}")

    def _cancelar(self) -> None:
        if self._worker is not None:
            self._worker.control.cancelar()
