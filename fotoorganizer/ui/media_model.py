"""Modelo virtualizado da grade: páginas sob demanda via fetchMore.

Nunca carrega o catálogo inteiro: mantém apenas os itens já paginados e um
LRU de pixmaps no ThumbnailService. Com 100k fotos, a memória fica
proporcional ao que foi rolado, não ao acervo.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt
from PySide6.QtGui import QColor, QPixmap

from fotoorganizer.repositories import MediaFilters, MediaRepository
from fotoorganizer.workers.thumbnail_service import ThumbnailService

PAGE_SIZE = 256

MediaIdRole = Qt.ItemDataRole.UserRole + 1
CaminhoRole = Qt.ItemDataRole.UserRole + 2


@dataclass(slots=True)
class _Item:
    id: int
    nome: str
    caminho: str
    hash_rapido: str | None
    data_capturada: datetime | None


class MediaListModel(QAbstractListModel):
    def __init__(self, repo: MediaRepository, thumbs: ThumbnailService,
                 parent=None) -> None:
        super().__init__(parent)
        self._repo = repo
        self._thumbs = thumbs
        self._filters = MediaFilters()
        self._items: list[_Item] = []
        self._row_by_id: dict[int, int] = {}
        self._total = 0
        self._placeholder = QPixmap(1, 1)
        self._placeholder.fill(QColor("#2D2D30"))
        thumbs.pronta.connect(self._on_thumb_ready)

    # -- API ------------------------------------------------------------
    def set_filters(self, filters: MediaFilters) -> None:
        self.beginResetModel()
        self._filters = filters
        self._items.clear()
        self._row_by_id.clear()
        self._total = self._repo.contar(filters)
        self.endResetModel()

    def refresh(self) -> None:
        self.set_filters(self._filters)

    @property
    def total(self) -> int:
        return self._total

    def media_id_at(self, row: int) -> int | None:
        return self._items[row].id if 0 <= row < len(self._items) else None

    # -- QAbstractListModel ----------------------------------------------
    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._items)

    def canFetchMore(self, parent=QModelIndex()) -> bool:
        return not parent.isValid() and len(self._items) < self._total

    def fetchMore(self, parent=QModelIndex()) -> None:
        offset = len(self._items)
        page = self._repo.listar(self._filters, PAGE_SIZE, offset)
        if not page:
            self._total = offset
            return
        self.beginInsertRows(QModelIndex(), offset, offset + len(page) - 1)
        for media in page:
            self._row_by_id[media.id] = len(self._items)
            self._items.append(
                _Item(
                    id=media.id, nome=media.nome, caminho=media.caminho,
                    hash_rapido=media.hash_rapido,
                    data_capturada=media.data_capturada,
                )
            )
        self.endInsertRows()

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or index.row() >= len(self._items):
            return None
        item = self._items[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            return item.nome
        if role == Qt.ItemDataRole.DecorationRole:
            pixmap = self._thumbs.pixmap_for(item.id, item.hash_rapido, item.caminho)
            return pixmap if pixmap is not None else self._placeholder
        if role == Qt.ItemDataRole.ToolTipRole:
            data = (
                item.data_capturada.strftime("%d/%m/%Y %H:%M")
                if item.data_capturada else "sem data"
            )
            return f"{item.caminho}\n{data}"
        if role == MediaIdRole:
            return item.id
        if role == CaminhoRole:
            return item.caminho
        return None

    # -- slots ------------------------------------------------------------
    def _on_thumb_ready(self, media_id: int) -> None:
        row = self._row_by_id.get(media_id)
        if row is not None:
            index = self.index(row)
            self.dataChanged.emit(index, index, [Qt.ItemDataRole.DecorationRole])
