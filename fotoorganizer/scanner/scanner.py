"""Scanner incremental do catálogo.

Somente leitura sobre as fotos (invariante 1): a única escrita é no banco.
Incremental: arquivo com (tamanho, mtime, inode) inalterados não é relido.
Pausável/cancelável via ScanControl; commits em lote com checkpoint na
sessão de scan permitem retomar após interrupção — a retomada re-varre e
os inalterados são pulados a custo de um stat() cada.

Extração em paralelo: ler EXIF/RAW e calcular o hash rápido são o custo
dominante do primeiro scan (libraw leva ~0.4s por RAW) e rodam num
ThreadPoolExecutor — Pillow, libraw e xxhash soltam o GIL. O banco continua
sendo escrito por uma única thread (a do scan), na ordem de descoberta.
"""

from __future__ import annotations

import logging
import time
from collections import deque
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from threading import Event
from typing import Callable

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from fotoorganizer.config.settings import ScannerSettings
from fotoorganizer.metadata.base import MetadataExtractor
from fotoorganizer.models import (
    MediaFile,
    MediaRole,
    MetadataEntry,
    ScanSession,
    ScanStatus,
    Source,
)
from fotoorganizer.scanner.discovery import (
    DiscoveryConfig,
    dentro_de_pacote,
    iter_media_files,
)
from fotoorganizer.security.hashing import quick_signature
from fotoorganizer.thumbnails import ThumbnailCache

log = logging.getLogger(__name__)

SCANNER_VERSION = "1.0"
_BATCH_SIZE = 200
_MTIME_TOLERANCE = 1e-6  # segundos
# Teto por arquivo para a extração inteira (EXIF + hash + thumbnail).
# Folgado de propósito: um RAW de 25 MB num NAS frio leva segundos, não
# minutos. O que passar disto é tratado como erro de leitura — a foto entra
# no catálogo sem metadado e a varredura segue, em vez de congelar a fila.
_EXTRACAO_TIMEOUT_S = 120.0


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
        thumb_cache: ThumbnailCache | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._extractor = extractor
        self._settings = settings
        self._thumb_cache = thumb_cache

    def scan_source(
        self,
        caminho: Path,
        progress: ProgressCallback | None = None,
        control: ScanControl | None = None,
        padroes_ignorados: tuple[str, ...] = (),
        reprocessar: bool = False,
    ) -> tuple[ScanSession, ScanMetrics]:
        """`reprocessar` relê arquivo inalterado. O scan incremental existe
        para não repetir trabalho, mas quando a extração passa a capturar
        algo novo o catálogo antigo fica sem esse algo — e sem esta porta
        não haveria como preencher o que já está indexado."""
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
            self._run(session, source, scan, metrics, progress, control,
                      reprocessar)
            return scan, metrics

    def _run(
        self,
        session: Session,
        source: Source,
        scan: ScanSession,
        metrics: ScanMetrics,
        progress: ProgressCallback | None,
        control: ScanControl,
        reprocessar: bool = False,
    ) -> None:
        config = DiscoveryConfig(
            extensoes=frozenset(self._extractor.supported_extensions()),
            incluir_ocultos=self._settings.incluir_ocultos,
            seguir_symlinks=self._settings.seguir_symlinks,
            padroes_ignorados=tuple(source.padroes_ignorados or ()),
        )
        conhecidos = self._carregar_conhecidos(session, source.id)
        desde_commit = 0
        cancelado = False
        # Janela limitada de extrações em voo: paraleliza sem acumular
        # resultados (e memória) de milhares de arquivos à frente do escritor.
        janela = max(self._settings.workers * 2, 4)
        pendentes: deque[tuple[Path, object, Future]] = deque()

        def consumir(max_restantes: int) -> None:
            nonlocal desde_commit
            while len(pendentes) > max_restantes:
                path, stat, futuro = pendentes.popleft()
                try:
                    meta, assinatura = futuro.result(
                        timeout=_EXTRACAO_TIMEOUT_S
                    )
                    self._gravar(session, source.id, path, stat, meta, assinatura)
                    metrics.indexados += 1
                    metrics.bytes_processados += stat.st_size
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

        with ThreadPoolExecutor(
            max_workers=max(self._settings.workers, 1),
            thread_name_prefix="scan-extract",
        ) as pool:
            for path in iter_media_files(Path(source.caminho), config):
                control.aguardar_se_pausado()
                if control.cancelado:
                    cancelado = True
                    break

                metrics.vistos += 1
                try:
                    stat = path.stat()
                except OSError as exc:
                    metrics.erros += 1
                    log.error("scan: erro em %s: %s", path, exc)
                    continue

                assinatura = conhecidos.get(str(path))
                if (not reprocessar and assinatura is not None
                        and self._unchanged_sig(assinatura, stat)):
                    metrics.pulados += 1
                    if progress:
                        progress(metrics, str(path))
                    continue

                pendentes.append((path, stat, pool.submit(self._extrair, path)))
                consumir(janela)

            # Drena o que já estava em voo — inclusive após cancelamento,
            # para não perder trabalho de extração já pago.
            consumir(0)

        scan.status = ScanStatus.PAUSADO if cancelado else ScanStatus.CONCLUIDO
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

    def _carregar_conhecidos(
        self, session: Session, source_id: int
    ) -> dict[str, tuple[int, float | None, int | None]]:
        """Assinaturas de todos os arquivos já catalogados da fonte, numa
        query só: caminho → (tamanho, mtime_ts, inode). No re-scan, o comum
        (arquivo inalterado) é decidido em memória — sem um SELECT por
        arquivo, que em 30k fotos viravam 30k queries."""
        rows = session.execute(
            select(
                MediaFile.caminho, MediaFile.tamanho,
                MediaFile.mtime, MediaFile.inode,
            ).where(MediaFile.source_id == source_id)
        )
        return {
            caminho: (
                tamanho, mtime.timestamp() if mtime else None, inode
            )
            for caminho, tamanho, mtime, inode in rows
        }

    def _extrair(self, path: Path):
        """Roda nas threads do pool: só leitura do arquivo, nada de DB."""
        meta = self._extractor.extract(path)
        assinatura = quick_signature(path)
        if self._thumb_cache is not None:
            # Aproveita que o arquivo já está sendo lido para deixar a
            # miniatura pronta: a grade e o phash das duplicatas deixam de
            # reabrir o original (em RAW, ~0.4s a menos por arquivo depois).
            # Best-effort: imagem indecodificável vira placeholder na UI.
            self._thumb_cache.get_or_generate(assinatura, path)
        return meta, assinatura

    def _gravar(
        self, session: Session, source_id: int, path: Path, stat, meta,
        assinatura: str,
    ) -> None:
        """Escreve o resultado da extração — sempre na thread do scan."""
        caminho = str(path)
        # Só arquivos novos/alterados chegam aqui e pagam o SELECT individual
        # (para obter o registro ORM a atualizar).
        existing = session.scalar(
            select(MediaFile).where(
                MediaFile.source_id == source_id, MediaFile.caminho == caminho
            )
        )

        media = existing or MediaFile(
            source_id=source_id, caminho=caminho, pasta="", nome="", extensao="",
            tamanho=0,
        )
        # Reavaliado a cada passagem: uma pasta pode virar pacote entre scans.
        media.papel = (
            MediaRole.SINAL if dentro_de_pacote(path) else MediaRole.ACERVO
        )
        media.pasta = str(path.parent)
        media.nome = path.name
        media.extensao = path.suffix.lower().lstrip(".")
        media.tamanho = stat.st_size
        media.inode = stat.st_ino
        # macOS: st_birthtime é a criação real; st_ctime é mudança de inode.
        media.ctime = _ts(getattr(stat, "st_birthtime", stat.st_ctime))
        media.mtime = _ts(stat.st_mtime)
        media.hash_rapido = assinatura
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

        # A base bruta serve para o usuário inspecionar a foto dele. Ninguém
        # abre o IPTC de uma miniatura de cache: guardar isso custou 685 mil
        # linhas e 134 MB num acervo real, sem nada em troca. A testemunha
        # doa data, GPS e câmera — que ficam nas colunas acima.
        if meta.extras and media.papel is not MediaRole.SINAL:
            session.flush()
            # Re-scan reescreve a base bruta do arquivo: sem isto, cada nova
            # leitura empilharia outra cópia das mesmas dezenas de tags.
            if existing is not None:
                session.execute(delete(MetadataEntry).where(
                    MetadataEntry.media_id == media.id,
                    MetadataEntry.namespace.in_(
                        {ns for ns, _, _ in meta.extras}
                    ),
                ))
            for namespace, chave, valor in meta.extras:
                session.add(
                    MetadataEntry(
                        media_id=media.id, namespace=namespace, chave=chave,
                        valor=valor,
                    )
                )

    @staticmethod
    def _unchanged_sig(
        assinatura: tuple[int, float | None, int | None], stat
    ) -> bool:
        tamanho, mtime_ts, inode = assinatura
        if tamanho != stat.st_size or inode != stat.st_ino:
            return False
        if mtime_ts is None:
            return False
        return abs(mtime_ts - _ts(stat.st_mtime).timestamp()) < _MTIME_TOLERANCE

    def _get_or_create_source(
        self, session: Session, caminho: Path, padroes_ignorados: tuple[str, ...]
    ) -> Source:
        resolved = str(caminho.expanduser())
        source = session.scalar(select(Source).where(Source.caminho == resolved))
        if source is None:
            source = self._fonte_equivalente(session, caminho.expanduser())
        if source is None:
            source = Source(
                caminho=resolved, padroes_ignorados=list(padroes_ignorados)
            )
            session.add(source)
            session.flush()
        elif padroes_ignorados:
            source.padroes_ignorados = list(padroes_ignorados)
        return source

    @staticmethod
    def _fonte_equivalente(session: Session, caminho: Path) -> Source | None:
        """A fonte que já aponta para ESTA pasta, escrita de outro jeito.

        A comparação anterior era só de string, e o APFS não distingue
        maiúscula: varrer `/users/acamerini` depois de `/Users/acamerini`
        criava uma segunda fonte para a mesma pasta. No acervo do dono isso
        rendeu duas fontes chamadas "acamerini" (93.400 e 695 fotos), lado a
        lado na barra lateral, sem nenhuma forma de saber qual era qual.

        `samefile` compara dispositivo e inode, então resolve caixa,
        symlink e caminho equivalente de uma vez. Fonte cujo caminho não
        existe agora (volume desmontado) não pode ser comparada assim e é
        pulada — criar uma fonte a mais é recuperável, fundir duas pastas
        distintas num registro só não é.
        """
        for candidata in session.scalars(select(Source)):
            try:
                if caminho.samefile(candidata.caminho):
                    return candidata
            except OSError:
                continue
        return None
