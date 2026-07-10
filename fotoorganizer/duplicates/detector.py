"""Detecção de duplicatas em três níveis — somente leitura, nada é excluído.

1. EXATO     — mesmo SHA-256 (bytes idênticos), confirmado sob demanda a
               partir de candidatos por (tamanho, hash rápido).
2. CONTEUDO  — mesmo phash (distância 0) com bytes diferentes: reexports,
               recompressões, metadados alterados.
3. VISUAL    — phash a distância 1..LIMIAR: sequências, edições leves,
               redimensionamentos.

Grupos com decisão do usuário (algum papel definido) são preservados na
redetecção; os demais são regenerados.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from pathlib import Path
from typing import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from fotoorganizer.duplicates.phash import BKTree, calcular_phash
from fotoorganizer.models import (
    DuplicateGroup,
    DuplicateLevel,
    DuplicateMember,
    DuplicateRole,
    MediaFile,
)
from fotoorganizer.security.hashing import sha256_full
from fotoorganizer.thumbnails import ThumbnailCache

log = logging.getLogger(__name__)

LIMIAR_VISUAL = 8


class DuplicateDetector:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        thumb_cache: ThumbnailCache | None = None,
    ) -> None:
        self._factory = session_factory
        self._thumb_cache = thumb_cache

    def detectar(self, progress: Callable[[str], None] | None = None) -> dict:
        with self._factory() as session:
            midias = list(session.scalars(
                select(MediaFile).where(MediaFile.tamanho > 0)
            ))

            if progress:
                progress("Calculando hashes que faltam…")
            self._completar_phashes(session, midias)
            self._completar_sha256(session, midias)
            session.commit()

            preservados = self._limpar_grupos_sem_decisao(session)

            if progress:
                progress("Agrupando…")
            ja_agrupados = self._media_ids_em_grupos(session)
            stats = {"exato": 0, "conteudo": 0, "visual": 0,
                     "preservados": preservados}

            # Cada grupo exato mantém 1 representante elegível na passada de
            # phash: uma recompressão da mesma foto agrupa com ele em vez de
            # ficar órfã.
            nao_representantes = self._grupos_exatos(
                session, midias, ja_agrupados, stats
            )
            self._grupos_por_phash(
                session, midias, ja_agrupados | nao_representantes, stats
            )
            session.commit()
            log.info("duplicatas: %s", stats)
            return stats

    # -- hashes sob demanda -------------------------------------------------
    def _completar_phashes(self, session: Session, midias) -> None:
        for media in midias:
            if media.hash_perceptual is not None or media.erro_leitura:
                continue
            thumb = None
            if self._thumb_cache is not None and media.hash_rapido:
                thumb = self._thumb_cache.get(media.hash_rapido)
            media.hash_perceptual = calcular_phash(Path(media.caminho), thumb)

    def _completar_sha256(self, session: Session, midias) -> None:
        """SHA-256 completo apenas para candidatos a duplicata exata
        (mesmo tamanho + hash rápido) — nunca para o acervo inteiro."""
        candidatos = defaultdict(list)
        for media in midias:
            if media.hash_rapido:
                candidatos[(media.tamanho, media.hash_rapido)].append(media)
        for grupo in candidatos.values():
            if len(grupo) < 2:
                continue
            for media in grupo:
                if media.hash_sha256 is None:
                    try:
                        media.hash_sha256 = sha256_full(Path(media.caminho))
                    except OSError as exc:
                        log.warning("sha256 falhou para %s: %s", media.caminho, exc)

    # -- agrupamento ----------------------------------------------------------
    def _grupos_exatos(self, session: Session, midias, ja_agrupados: set,
                       stats: dict) -> set[int]:
        """Cria grupos EXATO e devolve os membros NÃO-representantes
        (o primeiro de cada grupo segue elegível para a passada de phash)."""
        por_sha = defaultdict(list)
        for media in midias:
            if media.hash_sha256 and media.id not in ja_agrupados:
                por_sha[media.hash_sha256].append(media)
        nao_representantes = set()
        for membros in por_sha.values():
            if len(membros) >= 2:
                self._criar_grupo(session, DuplicateLevel.EXATO, membros)
                stats["exato"] += 1
                nao_representantes |= {m.id for m in membros[1:]}
        return nao_representantes

    def _grupos_por_phash(self, session: Session, midias, excluidos: set,
                          stats: dict) -> None:
        candidatas = [
            m for m in midias
            if m.hash_perceptual and m.id not in excluidos
        ]
        arvore = BKTree()
        for media in candidatas:
            arvore.inserir(int(media.hash_perceptual, 16), media)

        visitados: set[int] = set()
        for media in candidatas:
            if media.id in visitados:
                continue
            valor = int(media.hash_perceptual, 16)
            vizinhos = arvore.buscar(valor, LIMIAR_VISUAL)
            identicos, parecidos = [], []
            for dist, _v, payloads in vizinhos:
                for outro in payloads:
                    if outro.id in visitados or outro.id == media.id:
                        continue
                    (identicos if dist == 0 else parecidos).append(outro)

            if identicos:
                membros = [media, *identicos]
                self._criar_grupo(session, DuplicateLevel.CONTEUDO, membros)
                stats["conteudo"] += 1
                visitados |= {m.id for m in membros}
            elif parecidos:
                membros = [media, *parecidos]
                self._criar_grupo(session, DuplicateLevel.VISUAL, membros)
                stats["visual"] += 1
                visitados |= {m.id for m in membros}
            else:
                visitados.add(media.id)

    def _criar_grupo(self, session: Session, nivel: DuplicateLevel,
                     membros) -> None:
        grupo = DuplicateGroup(nivel=nivel)
        session.add(grupo)
        session.flush()
        for media in membros:
            session.add(DuplicateMember(group_id=grupo.id, media_id=media.id))

    # -- preservação de decisões -------------------------------------------
    def _limpar_grupos_sem_decisao(self, session: Session) -> int:
        grupos = list(session.scalars(select(DuplicateGroup)))
        preservados = 0
        for grupo in grupos:
            decidido = any(
                m.papel != DuplicateRole.INDEFINIDO for m in grupo.membros
            )
            if decidido:
                preservados += 1
            else:
                # O cascade delete-orphan de DuplicateGroup.membros remove
                # os membros junto.
                session.delete(grupo)
        session.flush()
        return preservados

    def _media_ids_em_grupos(self, session: Session) -> set[int]:
        return set(session.scalars(select(DuplicateMember.media_id)))
