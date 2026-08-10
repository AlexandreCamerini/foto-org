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
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from fotoorganizer.config.settings import ScannerSettings
from fotoorganizer.metadata import MetadataExtractor
from fotoorganizer.metadata.base import NAMESPACE_CURADORIA, data_plausivel
from fotoorganizer.models import MediaFile, MediaRole, MetadataEntry, Source
from fotoorganizer.security.hashing import quick_signature
from fotoorganizer.sources.base import ExternalAsset, ExternalCatalogProvider
from fotoorganizer.thumbnails import ThumbnailCache

log = logging.getLogger(__name__)

_BATCH_SIZE = 200

# Quanto duas horas de parede podem diferir e ainda ser a mesma captura. É
# subsegundo, não folga de relógio: só absorve a diferença de precisão entre
# quem grava com microssegundo e quem trunca no segundo.
_TOLERANCIA_DE_PAREDE = timedelta(seconds=1)

# Namespace de metadata_entries por tipo de fonte ("apple", "google").
_NAMESPACES = {
    "apple_photos": "apple",
    "google_takeout": "google",
    "lightroom": "lightroom",
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
                    if asset.caminho is None:
                        # Referência: não há arquivo para ler nem hashear.
                        self._gravar_referencia(
                            session, source.id, namespace, asset
                        )
                        metrics.importados += 1
                        desde_commit += 1
                        if desde_commit >= _BATCH_SIZE:
                            session.commit()
                            desde_commit = 0
                        if progress:
                            progress(metrics, asset.referencia or "")
                        continue
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
        # O par (local, absoluto) é escolhido JUNTO. Casar a hora de parede
        # de uma origem com o instante absoluto de outra inventaria um
        # offset que ninguém mediu — e offset aqui não é coluna, é a
        # diferença entre as duas, então a mentira seria invisível.
        #
        # A exceção é o caso que vale ouro: arquivo e catálogo externo
        # descrevem a MESMA captura (o Apple Fotos importou a data do próprio
        # EXIF) e só o catálogo sabe o fuso. Aí o que se empresta é o OFFSET,
        # aplicado à hora do arquivo — ver `_com_o_fuso_do_catalogo`.
        if meta.data_capturada is not None:
            media.data_capturada_utc = (
                meta.data_capturada_utc
                or _com_o_fuso_do_catalogo(meta.data_capturada, asset)
                or meta.data_capturada
            )
        elif asset.data_capturada is None:
            # Sem hora de parede não há instante absoluto: o espelho da regra
            # das referências. Nenhum provider faz isso hoje, e o tipo
            # `ExternalAsset` não impede que um futuro faça.
            media.data_capturada_utc = None
        else:
            media.data_capturada_utc = (
                asset.data_capturada_utc or asset.data_capturada
            )
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
        self._gravar_metadados_externos(session, media, namespace, asset)

    def _gravar_referencia(self, session: Session, source_id: int,
                           namespace: str, asset: ExternalAsset) -> None:
        """Grava um item sem abrir o arquivo. Sem EXIF, sem hash, sem
        miniatura — o valor está em `data_capturada` e no GPS, que fazem
        dele um doador para a correlação entre fontes.

        Nome e tamanho entram quando o provider os conhece: são informação
        do arquivo, não conteúdo, e casam cópias entre fontes sem leitura.
        """
        caminho = f"{namespace}://{asset.referencia}"
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
        media.arquivo_ausente = True
        # Uma referência é testemunha por definição: não há arquivo para
        # entrar na grade, na revisão nem no plano. Sem isto o registro fica
        # dizendo duas coisas contraditórias ao mesmo tempo — foi o que
        # aconteceu com as 54.086 do Lightroom na primeira importação.
        media.papel = MediaRole.SINAL
        # A pasta de origem é o que responde "onde estava esta foto?" quando
        # o volume não está montado. Sem isto, uma referência do Lightroom
        # sabe a data e o GPS e não sabe dizer de que disco veio.
        if asset.caminho_original is not None:
            media.pasta = str(asset.caminho_original.parent)
        media.nome = (
            asset.nome or asset.titulo or f"{namespace}:{asset.referencia}"
        )
        if asset.nome and "." in asset.nome:
            media.extensao = asset.nome.rsplit(".", 1)[-1].lower()
        if asset.tamanho is not None:
            media.tamanho = asset.tamanho
        # Catálogo externo também erra: o .lrcat do dono trazia um registro
        # datado de 2100.
        media.data_capturada = (
            asset.data_capturada
            if data_plausivel(asset.data_capturada) else None
        )
        # Sem fuso conhecido, os dois instantes são iguais — nunca nulo com a
        # hora local preenchida, senão "não sei o fuso" viraria "não sei
        # quando". Data implausível sai das duas colunas junto: manter o
        # registro de 2100 no absoluto seria trocar o lugar do problema.
        media.data_capturada_utc = (
            None if media.data_capturada is None
            else (asset.data_capturada_utc or media.data_capturada)
        )
        if asset.gps_lat is not None:
            media.gps_lat, media.gps_lon = asset.gps_lat, asset.gps_lon
        media.indexado_em = datetime.now(timezone.utc).replace(tzinfo=None)
        if existing is None:
            session.add(media)
        session.flush()
        self._gravar_metadados_externos(session, media, namespace, asset)

    @staticmethod
    def _gravar_metadados_externos(session: Session, media: MediaFile,
                                   namespace: str, asset: ExternalAsset) -> None:
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
        for pessoa in asset.pessoas:
            entradas.append(("pessoa", pessoa))
        for palavra in asset.palavras_chave:
            entradas.append(("palavra_chave", palavra))
        if asset.gps_lat is not None:
            entradas.append(("gps", f"{asset.gps_lat:.6f},{asset.gps_lon:.6f}"))
        if asset.data_capturada is not None:
            entradas.append(("data", asset.data_capturada.isoformat()))
        # O fuso emprestado do catálogo externo responde "de onde veio?" como
        # todo o resto: sem isto, o offset viraria a única informação do
        # catálogo cuja origem some depois de gravada.
        if asset.data_capturada_utc is not None:
            entradas.append(("data_utc", asset.data_capturada_utc.isoformat()))
        for chave, valor in entradas:
            session.add(MetadataEntry(
                media_id=media.id, namespace=namespace, chave=chave,
                valor=valor,
            ))
        _unificar_curadoria(session, media, asset.palavras_chave)


def _unificar_curadoria(
    session: Session, media: MediaFile, palavras: tuple[str, ...]
) -> None:
    """Junta a palavra-chave do catálogo externo à do arquivo, sem repetir.

    Este é o ponto onde a leitura do Lightroom deixa de contar duas vezes. O
    mesmo "Selected" chega por dois caminhos que nunca se encontraram: o
    `.lrcat` importado como fonte, e o `.xmp` que o mesmo fluxo gravou ao lado
    do arquivo e que o extrator passou a ler. São a mesma afirmação da mesma
    origem — o Aftershoot rodou uma vez e escreveu nos dois lugares — e somar
    as duas inflaria a confiança de uma decisão que tem uma fonte só.

    O namespace da fonte continua guardando o que aquela fonte disse: é ele
    que responde "de onde veio?". Aqui fica o conjunto, com cada termo uma vez,
    que é o que a classificação lê.
    """
    if not palavras:
        return
    ja_tem = {
        valor for (valor,) in session.execute(
            select(MetadataEntry.valor).where(
                MetadataEntry.media_id == media.id,
                MetadataEntry.namespace == NAMESPACE_CURADORIA,
                MetadataEntry.chave == "palavra_chave",
            )
        )
    }
    for palavra in palavras:
        if palavra in ja_tem:
            continue
        ja_tem.add(palavra)
        session.add(MetadataEntry(
            media_id=media.id, namespace=NAMESPACE_CURADORIA,
            chave="palavra_chave", valor=palavra,
        ))


def _com_o_fuso_do_catalogo(
    local: datetime, asset: ExternalAsset
) -> datetime | None:
    """O instante absoluto da foto quando o ARQUIVO diz a hora e o CATÁLOGO
    EXTERNO diz o fuso. `None` quando os dois não estão falando da mesma
    captura, e aí o arquivo manda sozinho.

    O que se empresta é o OFFSET (`utc - local` do catálogo), aplicado à hora
    do arquivo — não o instante absoluto do catálogo direto. Os dois medem o
    mesmo momento com precisão diferente: o Apple Fotos guarda a data com
    subsegundo e o EXIF trunca no segundo (`exiftool.py:_data()` faz
    `split(".")[0]`). Copiar o absoluto do catálogo ao lado da hora do
    arquivo deixaria a diferença entre as colunas em 1h59min59,184s em vez do
    offset real de duas horas.

    Pela mesma razão a concordância se mede com tolerância de um segundo, e
    não por igualdade exata: 65% das 44.661 linhas do Apple Fotos no acervo
    real têm microssegundo, e nenhuma das 120.448 de EXIF tem. Exigir
    igualdade descartaria o fuso medido em quase toda foto — em silêncio,
    porque sem coluna de offset não há onde a perda apareceria.
    """
    if asset.data_capturada is None or asset.data_capturada_utc is None:
        return None
    # Discordância maior que o subsegundo é outra data (editada no Fotos, por
    # exemplo), não a mesma captura arredondada.
    if abs(asset.data_capturada - local) >= _TOLERANCIA_DE_PAREDE:
        return None
    return local + (asset.data_capturada_utc - asset.data_capturada)


def _ts(epoch: float) -> datetime:
    return datetime.fromtimestamp(epoch, tz=timezone.utc).replace(tzinfo=None)
