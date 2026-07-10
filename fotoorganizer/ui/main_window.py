"""Janela principal: sidebar | grade virtualizada | inspetor.

Todo trabalho pesado (scan, miniaturas) roda fora da thread da UI.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListView,
    QMainWindow,
    QSlider,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.orm import Session, sessionmaker

from fotoorganizer import __version__
from fotoorganizer.classification import SuggestionEngine
from fotoorganizer.config.settings import Settings
from fotoorganizer.geolocation import LocationResolver
from fotoorganizer.geolocation.offline import OfflineGeocoder
from fotoorganizer.metadata import PurePythonExtractor
from fotoorganizer.duplicates import DuplicateDetector
from fotoorganizer.repositories import (
    DuplicateRepository,
    MediaRepository,
    SuggestionRepository,
)
from fotoorganizer.scanner import CatalogScanner
from fotoorganizer.thumbnails import ThumbnailCache
from fotoorganizer.ui.duplicates_view import DuplicatesView
from fotoorganizer.ui.filter_bar import FilterBar
from fotoorganizer.ui.operations_view import OperationsView
from fotoorganizer.ui.inspector import Inspector
from fotoorganizer.ui.media_model import MediaIdRole, MediaListModel
from fotoorganizer.ui.review_view import ReviewView
from fotoorganizer.ui.sidebar import Sidebar
from fotoorganizer.workers import ScanWorker, ThumbnailService

_ICON_MIN, _ICON_MAX, _ICON_DEFAULT = 96, 320, 160


class MainWindow(QMainWindow):
    def __init__(
        self, settings: Settings, session_factory: sessionmaker[Session]
    ) -> None:
        super().__init__()
        self.setWindowTitle("Foto Organizer")
        self.resize(1280, 800)

        self._settings = settings
        self._session_factory = session_factory
        self._repo = MediaRepository(session_factory)
        self._thumb_service = ThumbnailService(
            ThumbnailCache(settings.cache_dir), workers=settings.scanner.workers
        )
        self._scan_worker: ScanWorker | None = None

        # -- painéis -----------------------------------------------------
        self.sidebar = Sidebar(self._repo)
        self.inspector = Inspector()
        biblioteca = self._build_centro()

        self._suggestion_repo = SuggestionRepository(session_factory)
        self.review = ReviewView(self._suggestion_repo, self._criar_engine)
        self.review.mensagem.connect(self.statusBar().showMessage)

        self._duplicate_repo = DuplicateRepository(session_factory)
        self.duplicates = DuplicatesView(
            self._duplicate_repo, self._criar_detector, self._thumb_service
        )
        self.duplicates.mensagem.connect(self.statusBar().showMessage)

        self.operations = OperationsView(session_factory)
        self.operations.mensagem.connect(self.statusBar().showMessage)

        self.tabs = QTabWidget()
        self.tabs.addTab(biblioteca, "Biblioteca")
        self.tabs.addTab(self.review, "Revisão")
        self.tabs.addTab(self.duplicates, "Duplicatas")
        self.tabs.addTab(self.operations, "Operações")

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.addWidget(self.sidebar)
        self.splitter.addWidget(self.tabs)
        self.splitter.addWidget(self.inspector)
        self.splitter.setSizes([240, 760, 280])
        self.splitter.setCollapsible(1, False)
        self.setCentralWidget(self.splitter)

        self._status_total = QLabel("")
        self.statusBar().addPermanentWidget(self._status_total)
        self.statusBar().showMessage(f"Pronto — catálogo local, v{__version__}")

        QShortcut(QKeySequence("Ctrl+1"), self, activated=self._toggle_sidebar)
        QShortcut(QKeySequence("Ctrl+3"), self, activated=self._toggle_inspector)

        # -- sinais --------------------------------------------------------
        self.sidebar.adicionar_pasta.connect(self._escolher_pasta)
        self.sidebar.fonte_selecionada.connect(self._on_fonte_selecionada)
        self.sidebar.pausar_scan.connect(self._pausar_scan)
        self.sidebar.continuar_scan.connect(self._continuar_scan)
        self.sidebar.cancelar_scan.connect(self._cancelar_scan)
        self.filter_bar.filtros_alterados.connect(self._aplicar_filtros)
        self.grid.selectionModel().currentChanged.connect(self._on_selecao)

        self._aplicar_filtros()

    def _criar_engine(self) -> SuggestionEngine:
        """Factory usada pelo worker de sugestões (geocoder é lazy/pesado)."""
        return SuggestionEngine(
            self._session_factory, LocationResolver(OfflineGeocoder())
        )

    def _criar_detector(self) -> DuplicateDetector:
        return DuplicateDetector(
            self._session_factory, ThumbnailCache(self._settings.cache_dir)
        )

    # -- construção -------------------------------------------------------
    def _build_centro(self) -> QWidget:
        centro = QWidget(objectName="areaGrade")
        layout = QVBoxLayout(centro)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(QLabel("BIBLIOTECA", objectName="tituloPainel"))
        self.filter_bar = FilterBar(self._repo)
        layout.addWidget(self.filter_bar)

        self.model = MediaListModel(self._repo, self._thumb_service)
        self.grid = QListView()
        self.grid.setModel(self.model)
        self.grid.setViewMode(QListView.ViewMode.IconMode)
        self.grid.setResizeMode(QListView.ResizeMode.Adjust)
        self.grid.setLayoutMode(QListView.LayoutMode.Batched)
        self.grid.setBatchSize(64)
        self.grid.setUniformItemSizes(True)
        self.grid.setSpacing(8)
        self.grid.setIconSize(QSize(_ICON_DEFAULT, _ICON_DEFAULT))
        self.grid.setWordWrap(True)
        self.grid.setSelectionMode(QListView.SelectionMode.ExtendedSelection)
        layout.addWidget(self.grid, stretch=1)

        rodape = QWidget()
        rodape_layout = QHBoxLayout(rodape)
        rodape_layout.setContentsMargins(12, 4, 12, 4)
        self._contagem = QLabel("", objectName="textoSecundario")
        rodape_layout.addWidget(self._contagem)
        rodape_layout.addStretch(1)
        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(_ICON_MIN, _ICON_MAX)
        self._slider.setValue(_ICON_DEFAULT)
        self._slider.setFixedWidth(140)
        self._slider.valueChanged.connect(
            lambda v: self.grid.setIconSize(QSize(v, v))
        )
        rodape_layout.addWidget(QLabel("Zoom", objectName="textoSecundario"))
        rodape_layout.addWidget(self._slider)
        layout.addWidget(rodape)
        return centro

    # -- filtros e seleção -------------------------------------------------
    def _aplicar_filtros(self) -> None:
        self.filter_bar.set_source_id(self.sidebar.fonte_atual())
        self.model.set_filters(self.filter_bar.filtros())
        self._contagem.setText(f"{self.model.total} fotos")
        self._status_total.setText(f"{self.model.total} no filtro atual")

    def _on_fonte_selecionada(self, _source_id) -> None:
        self._aplicar_filtros()

    def _on_selecao(self, current, _previous) -> None:
        if not current.isValid():
            self.inspector.limpar()
            return
        media_id = current.data(MediaIdRole)
        media = self._repo.por_id(media_id)
        if media is None:
            self.inspector.limpar()
            return
        pixmap = self._thumb_service.pixmap_for(
            media.id, media.hash_rapido, media.caminho
        )
        self.inspector.mostrar(media, pixmap)

    # -- varredura ----------------------------------------------------------
    def _escolher_pasta(self) -> None:
        pasta = QFileDialog.getExistingDirectory(self, "Adicionar pasta de fotos")
        if pasta:
            self._iniciar_scan(Path(pasta))

    def _iniciar_scan(self, caminho: Path) -> None:
        if self._scan_worker is not None and self._scan_worker.isRunning():
            return
        scanner = CatalogScanner(
            self._session_factory, PurePythonExtractor(), self._settings.scanner
        )
        self._scan_worker = ScanWorker(scanner, caminho, parent=self)
        self._scan_worker.progresso.connect(self.sidebar.scan_progresso)
        self._scan_worker.progresso.connect(self._on_scan_progresso)
        self._scan_worker.terminado.connect(self._on_scan_terminado)
        self.sidebar.scan_iniciado(str(caminho))
        self.statusBar().showMessage(f"Varrendo {caminho} (somente leitura)…")
        self._scan_worker.start()

    def _on_scan_progresso(self, vistos: int, indexados: int, erros: int,
                           aps: float) -> None:
        self.statusBar().showMessage(
            f"Varrendo… {vistos} vistos, {indexados} indexados, "
            f"{erros} erros ({aps:.0f} arq/s)"
        )

    def _on_scan_terminado(self, status: str, indexados: int, pulados: int,
                           erros: int) -> None:
        self.sidebar.scan_terminado()
        self.filter_bar.recarregar_opcoes()
        self._aplicar_filtros()
        rotulo = "Varredura concluída" if status == "concluido" else (
            "Varredura pausada" if status == "pausado" else "Varredura com erro"
        )
        self.statusBar().showMessage(
            f"{rotulo}: {indexados} indexados, {pulados} pulados, {erros} erros"
        )

    def _pausar_scan(self) -> None:
        if self._scan_worker is not None:
            self._scan_worker.control.pausar()
            self.statusBar().showMessage("Varredura pausada")

    def _continuar_scan(self) -> None:
        if self._scan_worker is not None:
            self._scan_worker.control.continuar()

    def _cancelar_scan(self) -> None:
        if self._scan_worker is not None:
            self._scan_worker.control.continuar()  # sai da pausa para cancelar
            self._scan_worker.control.cancelar()

    def closeEvent(self, event) -> None:
        if self._scan_worker is not None and self._scan_worker.isRunning():
            self._cancelar_scan()
            self._scan_worker.wait(5000)
        event.accept()

    # -- painéis -------------------------------------------------------------
    def _toggle_sidebar(self) -> None:
        self.sidebar.setVisible(self.sidebar.isHidden())

    def _toggle_inspector(self) -> None:
        self.inspector.setVisible(self.inspector.isHidden())
