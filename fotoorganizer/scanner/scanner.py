"""Scanner incremental do catálogo.

Somente leitura sobre as fotos (invariante 1): a única escrita é no banco.
Incremental: arquivo com (tamanho, mtime, inode) inalterados não é relido.
Pausável/cancelável via ScanControl; commits em lote com checkpoint na
sessão de scan permitem retomar após interrupção — a retomada re-varre e
os inalterados são pulados a custo de um stat() cada.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from threading import Event
from typing import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from fotoorganizer.config.settings import ScannerSettings
from fotoorganizer.metadata.base import MetadataExtractor
from fotoorganizer.models import (
    MediaFile,
    MetadataEntry,
    ScanSession,
    ScanStatus,
    Source,
)
from fotoorganizer.scanner.discovery import DiscoveryConfig, iter_media_files
from fotoorganizer.security.hashing import quick_signature

log = logging.getLogger(__name__)

SCANNER_VERSION = "1.0"
_BATCH_SIZE = 200
_MTIME_TOLERANCE = 1e-6  # segundos


@dataclass
class ScanMetrics:
    vistos: int = 0
    indexados: int = 0
    pulados: int = 0
    erros: int = 0
    bytes_processados: int = 0
    _inicio: float = field(default_factory=time.monotonic)

    @property
    def segundos_decorridos(self) -> float:
        return max(time.monotonic() - self._inicio, 1e-9)

    @property
    def arquivos_por_segundo(self) -> float:
        return self.vistos / self.segundos_decorridos


class ScanControl:
    """Pausa/cancelamento cooperativos, seguros entre threads."""

    def __init__(self) -> None:
        self._pausado = Event()
        self._cancelado = Event()

    def pausar(self) -> None:
        self._pausado.set()

    def continuar(self) -> None:
        self._pausado.clear()

    def cancelar(self) -> None:
        self._cancelado.set()

    @property
    def cancelado(self) -> bool:
        return self._cancelado.is_set()

    def aguardar_se_pausado(self) -> None:
        while self._pausado.is_set() and not self._cancelado.is_set():
            time.sleep(0.05)


ProgressCallback = Callable[[ScanMetrics, str], None]


def _ts(epoch: float) -> datetime:
    """mtime/ctime como datetime UTC naive — forma canônica no SQLite."""
    return datetime.fromtimestamp(epoch, tz=timezone.utc).replace(tzinfo=None)


class CatalogScanner:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        extractor: MetadataExtractor,
        settings: ScannerSettings,
    ) -> None:
        self._session_factory = session_factory
        self._extractor = extractor
        self._settings = settings

    def scan_source(
        self,
        caminho: Path,
        progress: ProgressCallback | None = None,
        control: ScanControl | None = None,
        padroes_ignorados: tuple[str, ...] = (),
    ) -> tuple[ScanSession, ScanMetrics]:
        control = control or ScanControl()
        metrics = ScanMetrics()

        with self._session_factory() as session:
            source = self._get_or_create_source(session, caminho, padroes_ignorados)
            scan = ScanSession(
                source_id=source.id,
                status=ScanStatus.RODANDO,
                versao_scanner=SCANNER_VERSION,
            )
            session.add(scan)

            source.disponivel = caminho.expanduser().is_dir()
            if not source.disponivel:
                scan.status = ScanStatus.ERRO
                scan.finalizado_em = datetime.now(timezone.utc).replace(tzinfo=None)
                scan.checkpoint = {"motivo": "volume ou pasta indisponível"}
                session.commit()
                log.warning("scan: fonte indisponível: %s", caminho)
                return scan, metrics

            session.commit()
            self._run(session, source, scan, metrics, progress, control)
            return scan, metrics

    def _run(
        self,
        session: Session,
        source: Source,
        scan: ScanSession,
        metrics: ScanMetrics,
        progress: ProgressCallback | None,
        control: ScanControl,
    ) -> None:
        config = DiscoveryConfig(
            extensoes=frozenset(self._extractor.supported_extensions()),
            incluir_ocultos=self._settings.incluir_ocultos,
            seguir_symlinks=self._settings.seguir_symlinks,
            padroes_ignorados=tuple(source.padroes_ignorados or ()),
        )
        desde_commit = 0

        for path in iter_media_files(Path(source.caminho), config):
            control.aguardar_se_pausado()
            if control.cancelado:
                scan.status = ScanStatus.PAUSADO
                break

            metrics.vistos += 1
            try:
                bytes_indexados = self._index_file(session, source.id, path)
                if bytes_indexados is not None:
                    metrics.indexados += 1
                    metrics.bytes_processados += bytes_indexados
                else:
                    metrics.pulados += 1
            except Exception as exc:
                # Nada derruba a varredura inteira (aceite do M1).
                metrics.erros += 1
                log.error("scan: erro em %s: %s", path, exc)

            desde_commit += 1
            if desde_commit >= _BATCH_SIZE:
                self._checkpoint(session, scan, metrics, str(path))
                desde_commit = 0
            if progress:
                progress(metrics, str(path))

        else:
            scan.status = ScanStatus.CONCLUIDO

        scan.finalizado_em = datetime.now(timezone.utc).replace(tzinfo=None)
        self._checkpoint(session, scan, metrics, checkpoint_path=None)
        log.info(
            "scan %s: %s — vistos=%d indexados=%d pulados=%d erros=%d (%.1f arq/s)",
            source.caminho, scan.status.value, metrics.vistos, metrics.indexados,
            metrics.pulados, metrics.erros, metrics.arquivos_por_segundo,
        )

    def _checkpoint(
        self,
        session: Session,
        scan: ScanSession,
        metrics: ScanMetrics,
        checkpoint_path: str | None,
    ) -> None:
        scan.arquivos_vistos = metrics.vistos
        scan.arquivos_indexados = metrics.indexados
        scan.erros = metrics.erros
        scan.bytes_processados = metrics.bytes_processados
        if checkpoint_path is not None:
            scan.checkpoint = {"ultimo_caminho": checkpoint_path}
        session.commit()

    def _index_file(self, session: Session, source_id: int, path: Path) -> int | None:
        """Indexa um arquivo; retorna os bytes lidos, ou None se inalterado."""
        stat = path.stat()
        caminho = str(path)

        existing = session.scalar(
            select(MediaFile).where(
                MediaFile.source_id == source_id, MediaFile.caminho == caminho
            )
        )
        if existing is not None and self._unchanged(existing, stat):
            return None

        meta = self._extractor.extract(path)
        media = existing or MediaFile(
            source_id=source_id, caminho=caminho, pasta="", nome="", extensao="",
            tamanho=0,
        )
        media.pasta = str(path.parent)
        media.nome = path.name
        media.extensao = path.suffix.lower().lstrip(".")
        media.tamanho = stat.st_size
        media.inode = stat.st_ino
        # macOS: st_birthtime é a criação real; st_ctime é mudança de inode.
        media.ctime = _ts(getattr(stat, "st_birthtime", stat.st_ctime))
        media.mtime = _ts(stat.st_mtime)
        media.hash_rapido = quick_signature(path)
        media.data_capturada = meta.data_capturada
        media.make = meta.make
        media.model = meta.model
        media.lente = meta.lente
        media.orientacao = meta.orientacao
        media.largura = meta.largura
        media.altura = meta.altura
        media.gps_lat = meta.gps_lat
        media.gps_lon = meta.gps_lon
        media.erro_leitura = meta.erro
        media.indexado_em = datetime.now(timezone.utc).replace(tzinfo=None)
        if existing is None:
            session.add(media)

        if meta.extras:
            session.flush()
            for namespace, chave, valor in meta.extras:
                session.add(
                    MetadataEntry(
                        media_id=media.id, namespace=namespace, chave=chave,
                        valor=valor,
                    )
                )
        return stat.st_size

    @staticmethod
    def _unchanged(media: MediaFile, stat) -> bool:
        if media.tamanho != stat.st_size or media.inode != stat.st_ino:
            return False
        if media.mtime is None:
            return False
        delta = abs(media.mtime.timestamp() - _ts(stat.st_mtime).timestamp())
        return delta < _MTIME_TOLERANCE

    def _get_or_create_source(
        self, session: Session, caminho: Path, padroes_ignorados: tuple[str, ...]
    ) -> Source:
        resolved = str(caminho.expanduser())
        source = session.scalar(select(Source).where(Source.caminho == resolved))
        if source is None:
            source = Source(
                caminho=resolved, padroes_ignorados=list(padroes_ignorados)
            )
            session.add(source)
            session.flush()
        elif padroes_ignorados:
            source.padroes_ignorados = list(padroes_ignorados)
        return source
