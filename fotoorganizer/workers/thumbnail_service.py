"""Miniaturas assíncronas: cache em memória (LRU) + disco + QThreadPool.

A grade pede um pixmap; se não estiver pronto, recebe None na hora e um
sinal `pronta(media_id)` depois — nunca I/O na thread da UI.
"""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, Signal
from PySide6.QtGui import QPixmap

from fotoorganizer.thumbnails import ThumbnailCache

_MEM_CACHE_MAX = 600


class _GenerateTask(QRunnable):
    def __init__(self, service: "ThumbnailService", media_id: int, chave: str,
                 original: Path) -> None:
        super().__init__()
        self._service = service
        self._media_id = media_id
        self._chave = chave
        self._original = original

    def run(self) -> None:  # thread do pool
        cache = self._service._cache
        path = cache.get_or_generate(self._chave, self._original)
        self._service._on_generated(self._media_id, self._chave, path)


class ThumbnailService(QObject):
    pronta = Signal(int)  # media_id (conexão queued → thread da UI)
    falhou = Signal(int)

    def __init__(self, cache: ThumbnailCache, workers: int = 2,
                 parent=None) -> None:
        super().__init__(parent)
        self._cache = cache
        self._mem: OrderedDict[str, QPixmap] = OrderedDict()
        self._pendentes: set[str] = set()
        self._ilegiveis: set[str] = set()
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(workers)

    def pixmap_for(self, media_id: int, chave: str | None,
                   original: str) -> QPixmap | None:
        """Pixmap pronto, ou None (e agenda geração em background)."""
        if not chave:
            return None
        if chave in self._mem:
            self._mem.move_to_end(chave)
            return self._mem[chave]
        if chave in self._ilegiveis or chave in self._pendentes:
            return None

        disco = self._cache.get(chave)
        if disco is not None:
            return self._load_to_mem(chave, disco)

        self._pendentes.add(chave)
        self._pool.start(_GenerateTask(self, media_id, chave, Path(original)))
        return None

    def _load_to_mem(self, chave: str, path: Path) -> QPixmap | None:
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            self._ilegiveis.add(chave)
            return None
        self._mem[chave] = pixmap
        if len(self._mem) > _MEM_CACHE_MAX:
            self._mem.popitem(last=False)
        return pixmap

    def _on_generated(self, media_id: int, chave: str, path: Path | None) -> None:
        # Chamado na thread do pool; sinais cruzam para a UI como queued.
        self._pendentes.discard(chave)
        if path is None:
            self._ilegiveis.add(chave)
            self.falhou.emit(media_id)
        else:
            self.pronta.emit(media_id)

    def aguardar(self) -> None:
        """Bloqueia até o pool esvaziar (uso em testes)."""
        self._pool.waitForDone()
