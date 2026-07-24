"""Importa um catálogo externo para o catálogo próprio.

Regra de fusão: o ARQUIVO manda (EXIF lido por extração normal); o
catálogo externo preenche o que o arquivo não tem (data/GPS de exports
sem EXIF) e contribui contexto que só ele conhece (título, descrição,
álbuns, favorito) — gravado em `metadata_entries` com namespace do tipo
da fonte, para toda informação continuar respondendo "de onde veio?".

Somente leitura sobre a biblioteca externa (invariante 1); re-importar é
idempotente (upsert por caminho, namespaces regravados).
"""

from __future__ import annotations

import logging
from collections import deque
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from fotoorganizer.config.settings import ScannerSettings
from fotoorganizer.metadata import MetadataExtractor
from fotoorganizer.models import MediaFile, MetadataEntry, Source
from fotoorganizer.security.hashing import quick_signature
from fotoorganizer.sources.base import ExternalAsset, ExternalCatalogProvider
from fotoorganizer.thumbnails import ThumbnailCache

log = logging.getLogger(__name__)

_BATCH_SIZE = 200

# Namespace de metadata_entries por tipo de fonte ("apple", "google").
_NAMESPACES = {
    "apple_photos": "apple",
    "google_takeout": "google",
}


@dataclass(slots=True)
class ImportMetrics:
    vistos: int = 0
    importados: int = 0
    pulados: int = 0
    erros: int = 0
    inicio: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class ExternalCatalogImporter:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        extractor: MetadataExtractor,
        settings: ScannerSettings,
        thumb_cache: ThumbnailCache | None = None,
    ) -> None:
        self._factory = session_factory
        self._extractor = extractor
        self._settings = settings
        self._thumb_cache = thumb_cache

    # -- API ------------------------------------------------------------
    def importar(
        self,
        provider: ExternalCatalogProvider,
        progress: Callable[[ImportMetrics, str], None] | None = None,
    ) -> ImportMetrics:
        metrics = ImportMetrics()
        namespace = _NAMESPACES[provider.tipo.value]

        with self._factory() as session:
            source = self._obter_source(session, provider)
            conhecidos = self._assinaturas_conhecidas(session, source.id)

            janela = max(self._settings.workers * 2, 4)
            pendentes: deque[tuple[ExternalAsset, object, Future]] = deque()
            desde_commit = 0

            def consumir(max_restantes: int) -> None:
                nonlocal desde_commit
                while len(pendentes) > max_restantes:
                    asset, stat, futuro = pendentes.popleft()
                    try:
                        meta, assinatura = futuro.result()
                        self._gravar(
                            session, source.id, namespace, asset, stat,
                            meta, assinatura,
                        )
                        metrics.importados += 1
                    except Exception as exc:
                        metrics.erros += 1
                        log.error("import: erro em %s: %s", asset.caminho, exc)
                    desde_commit += 1
                    if desde_commit >= _BATCH_SIZE:
                        session.commit()
                        desde_commit = 0
                    if progress:
                        progress(metrics, str(asset.caminho))

            with ThreadPoolExecutor(
                max_workers=max(self._settings.workers, 1),
                thread_name_prefix="import-extract",
            ) as pool:
                for asset in provider.iter_assets():
                    metrics.vistos += 1
                    try:
                        stat = asset.caminho.stat()
                    except OSError as exc:
                        metrics.erros += 1
                        log.error("import: sem acesso a %s: %s",
                                  asset.caminho, exc)
                        continue

                    assinatura = conhecidos.get(str(asset.caminho))
                    if assinatura is not None and self._inalterado(
                        assinatura, stat
                    ):
                        metrics.pulados += 1
                        if progress:
                            progress(metrics, str(asset.caminho))
                        continue

                    pendentes.append(
                        (asset, stat, pool.submit(self._extrair, asset.caminho))
                    )
                    consumir(janela)
                consumir(0)

            session.commit()
        return metrics

    # -- internos ---------------------------------------------------------
    def _obter_source(
        self, session: Session, provider: ExternalCatalogProvider
    ) -> Source:
        caminho = str(provider.raiz)
        source = session.scalar(select(Source).where(Source.caminho == caminho))
        if source is None:
            source = Source(
                caminho=caminho, tipo=provider.tipo, apelido=provider.apelido
            )
            session.add(source)
            session.flush()
        source.disponivel = True
        return source

    def _assinaturas_conhecidas(
        self, session: Session, source_id: int
    ) -> dict[str, tuple[int, float | None]]:
        rows = session.execute(
            select(MediaFile.caminho, MediaFile.tamanho, MediaFile.mtime)
            .where(MediaFile.source_id == source_id)
        )
        return {
            caminho: (tamanho, mtime.timestamp() if mtime else None)
            for caminho, tamanho, mtime in rows
        }

    @staticmethod
    def _inalterado(assinatura: tuple[int, float | None], stat) -> bool:
        tamanho, mtime_ts = assinatura
        if tamanho != stat.st_size or mtime_ts is None:
            return False
        return abs(mtime_ts - datetime.fromtimestamp(
            stat.st_mtime, tz=timezone.utc
        ).replace(tzinfo=None).timestamp()) < 2.0

    def _extrair(self, path: Path):
        meta = self._extractor.extract(path)
        assinatura = quick_signature(path)
        if self._thumb_cache is not None:
            self._thumb_cache.get_or_generate(assinatura, path)
        return meta, assinatura

    def _gravar(self, session: Session, source_id: int, namespace: str,
                asset: ExternalAsset, stat, meta, assinatura: str) -> None:
        caminho = str(asset.caminho)
        existing = session.scalar(
            select(MediaFile).where(
                MediaFile.source_id == source_id,
                MediaFile.caminho == caminho,
            )
        )
        media = existing or MediaFile(
            source_id=source_id, caminho=caminho, pasta="", nome="",
            extensao="", tamanho=0,
        )
        media.pasta = str(asset.caminho.parent)
        media.nome = asset.caminho.name
        media.extensao = asset.caminho.suffix.lower().lstrip(".")
        media.tamanho = stat.st_size
        media.inode = stat.st_ino
        media.ctime = _ts(getattr(stat, "st_birthtime", stat.st_ctime))
        media.mtime = _ts(stat.st_mtime)
        media.hash_rapido = assinatura
        # Arquivo manda; catálogo externo preenche as lacunas.
        media.data_capturada = meta.data_capturada or asset.data_capturada
        media.make = meta.make
        media.model = meta.model
        media.lente = meta.lente
        media.orientacao = meta.orientacao
        media.largura = meta.largura
        media.altura = meta.altura
        if meta.gps_lat is not None:
            media.gps_lat, media.gps_lon = meta.gps_lat, meta.gps_lon
        elif asset.gps_lat is not None:
            media.gps_lat, media.gps_lon = asset.gps_lat, asset.gps_lon
        media.erro_leitura = meta.erro
        media.indexado_em = datetime.now(timezone.utc).replace(tzinfo=None)
        if existing is None:
            session.add(media)
        session.flush()

        # Contexto que só o catálogo externo tem — regravado a cada import.
        session.execute(delete(MetadataEntry).where(
            MetadataEntry.media_id == media.id,
            MetadataEntry.namespace == namespace,
        ))
        entradas: list[tuple[str, str]] = []
        if asset.titulo:
            entradas.append(("titulo", asset.titulo))
        if asset.descricao:
            entradas.append(("descricao", asset.descricao))
        if asset.favorito:
            entradas.append(("favorito", "true"))
        for album in asset.albuns:
            entradas.append(("album", album))
        if asset.gps_lat is not None:
            entradas.append(("gps", f"{asset.gps_lat:.6f},{asset.gps_lon:.6f}"))
        if asset.data_capturada is not None:
            entradas.append(("data", asset.data_capturada.isoformat()))
        for chave, valor in entradas:
            session.add(MetadataEntry(
                media_id=media.id, namespace=namespace, chave=chave,
                valor=valor,
            ))


def _ts(epoch: float) -> datetime:
    return datetime.fromtimestamp(epoch, tz=timezone.utc).replace(tzinfo=None)
