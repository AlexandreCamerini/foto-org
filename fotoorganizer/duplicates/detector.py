"""Detecção de duplicatas em cinco níveis — somente leitura, nada é excluído.

1. EXATO     — mesmo SHA-256 (bytes idênticos), confirmado sob demanda a
               partir de candidatos por (tamanho, hash rápido).
2. CONTEUDO  — mesmo phash (distância 0) com bytes diferentes: reexports,
               recompressões, metadados alterados.
3. VISUAL    — phash a distância 1..LIMIAR: edições leves,
               redimensionamentos, recortes pequenos.
4. SEQUENCIA — grupo phash cujos membros são da MESMA câmera a segundos de
               distância: rajada/variações de uma cena. Não é duplicata —
               apresentar como tal induziria a descartar o melhor frame.
5. VARIANTE  — RAW e JPEG do MESMO clique (`IMG_1.CR3` + `IMG_1.JPG`). Também
               não é duplicata: o RAW é o negativo, o JPEG é a cópia de
               trabalho, e escolher uma é decisão errada por construção.

Grupos com decisão HUMANA (algum papel definido, fora da resolução
automática) são preservados na redetecção; os demais — inclusive um grupo
EXATO que a regra determinística resolveu sozinha e ninguém revisou ainda —
são regenerados, para que uma nova cópia idêntica descoberta depois se junte
ao grupo em vez de ficar invisível atrás de uma decisão que ninguém tomou.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import timedelta
from pathlib import Path
from typing import Callable

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload, sessionmaker

from fotoorganizer.duplicates.phash import BKTree, calcular_phash
from fotoorganizer.duplicates.resolucao import escolher_principal_automatico
from fotoorganizer.metadata.purepython import RAW_EXTENSIONS
from fotoorganizer.models import (
    DuplicateGroup,
    DuplicateLevel,
    DuplicateMember,
    DuplicateRole,
    MediaFile,
    MetadataEntry,
)
from fotoorganizer.security.hashing import sha256_full
from fotoorganizer.thumbnails import ThumbnailCache

log = logging.getLogger(__name__)

LIMIAR_VISUAL = 8
# Intervalo máximo entre frames consecutivos para caracterizar rajada.
GAP_RAJADA = timedelta(seconds=10)


def _eh_rajada(membros) -> bool:
    """Mesma câmera e todos os frames a ≤ GAP_RAJADA um do outro. Sem data
    de captura ou sem câmera identificada, não se afirma rajada."""
    datas = [m.data_capturada for m in membros]
    if any(d is None for d in datas):
        return False
    cameras = {(m.make, m.model) for m in membros}
    if len(cameras) != 1 or cameras == {(None, None)}:
        return False
    datas.sort()
    return all(b - a <= GAP_RAJADA for a, b in zip(datas, datas[1:]))


def _eh_variante_de_revelacao(membros) -> bool:
    """RAW e JPEG do mesmo clique — `IMG_1234.CR3` ao lado de `IMG_1234.JPG`.

    O par tem phash idêntico e caía em CONTEUDO, onde a interface pede para
    escolher uma e descartar as outras. Num par de revelação isso é decisão
    errada por construção: o RAW é o negativo, o JPEG é a cópia de trabalho, e
    o dono quase sempre quer os dois.

    O critério é o nome base igual e pelo menos um RAW no grupo. Nome base é
    o que a câmera atribui ao clique — as duas gravações do mesmo disparo
    saem com o mesmo número de série do arquivo, e é por isso que casar por
    nome funciona aqui e não funcionaria entre fotos quaisquer.

    Extensões diferentes são exigidas: dois `.CR3` de nome igual em pastas
    diferentes são cópia do mesmo arquivo, não variante — esses continuam
    caindo em CONTEUDO, que é onde devem cair.
    """
    bases = {Path(m.nome).stem.lower() for m in membros}
    if len(bases) != 1:
        return False
    extensoes = {f".{(m.extensao or '').lower()}" for m in membros}
    if len(extensoes) < 2:
        return False
    return bool(extensoes & RAW_EXTENSIONS)


def _riqueza_de_metadados(session: Session, membros) -> dict[int, int]:
    """`media_id` → quantas entradas de metadado o registro tem.

    Uma consulta agregada para o grupo inteiro, não uma por membro: grupos
    exatos são milhares num acervo grande, e N+1 aqui apareceria no relógio.
    """
    ids = [m.id for m in membros]
    if not ids:
        return {}
    linhas = session.execute(
        select(MetadataEntry.media_id, func.count())
        .where(MetadataEntry.media_id.in_(ids))
        .group_by(MetadataEntry.media_id)
    )
    return {media_id: n for media_id, n in linhas}


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
            # selectinload(source): a resolução automática de grupo EXATO
            # (resolucao.py) olha media.source.tipo para cada membro — sem
            # isto, cada grupo dispara um SELECT extra por membro.
            midias = list(session.scalars(
                select(MediaFile)
                .where(MediaFile.tamanho > 0)
                .options(selectinload(MediaFile.source))
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
            stats = {"exato": 0, "conteudo": 0, "visual": 0, "sequencia": 0,
                     "variante": 0, "preservados": preservados}

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

            if identicos or parecidos:
                membros = [media, *identicos] if identicos else [media, *parecidos]
                # Rajada tem precedência sobre os dois níveis de phash:
                # até phash idêntico (cena estática em burst) não é cópia
                # se veio da mesma câmera em segundos.
                if _eh_variante_de_revelacao(membros):
                    # Antes da rajada: um par RAW+JPEG é sempre da mesma
                    # câmera no mesmo segundo, então casaria como rajada
                    # também — e "rajada" convida a escolher o melhor frame,
                    # que aqui não é a pergunta.
                    nivel = DuplicateLevel.VARIANTE
                elif _eh_rajada(membros):
                    nivel = DuplicateLevel.SEQUENCIA
                elif identicos:
                    nivel = DuplicateLevel.CONTEUDO
                else:
                    nivel = DuplicateLevel.VISUAL
                self._criar_grupo(session, nivel, membros)
                stats[nivel.value] += 1
                visitados |= {m.id for m in membros}
            else:
                visitados.add(media.id)

    def _criar_grupo(self, session: Session, nivel: DuplicateLevel,
                     membros) -> None:
        grupo = DuplicateGroup(nivel=nivel)
        session.add(grupo)
        session.flush()
        # SHA-256 idêntico não deixa ambiguidade sobre o conteúdo — só resta
        # decidir qual caminho é a referência, e isso a regra determinística
        # de resolucao.py já responde sozinha. Os outros níveis (CONTEUDO,
        # VISUAL, SEQUENCIA) dependem de julgamento sobre o CONTEÚDO em si
        # (qual versão é a boa, qual frame é o melhor) e continuam INDEFINIDO
        # até um clique humano.
        principal = (
            escolher_principal_automatico(
                membros, _riqueza_de_metadados(session, membros)
            )
            if nivel == DuplicateLevel.EXATO else None
        )
        if principal is not None:
            grupo.resolvido_automaticamente = True
        for media in membros:
            papel = DuplicateRole.INDEFINIDO
            if principal is not None:
                papel = (
                    DuplicateRole.PRINCIPAL if media.id == principal.id
                    else DuplicateRole.VERSAO
                )
            session.add(DuplicateMember(
                group_id=grupo.id, media_id=media.id, papel=papel
            ))

    # -- preservação de decisões -------------------------------------------
    def _limpar_grupos_sem_decisao(self, session: Session) -> int:
        grupos = list(session.scalars(select(DuplicateGroup)))
        preservados = 0
        for grupo in grupos:
            # resolvido_automaticamente NÃO conta como decisão para efeito
            # de preservação: se contasse, um grupo EXATO resolvido sozinho
            # travaria para sempre no tamanho de quando foi criado, e uma
            # terceira cópia idêntica descoberta depois nunca se juntaria a
            # ele (`ja_agrupados` a excluiria da repescagem sem incluí-la em
            # grupo nenhum). Só decisão HUMANA fecha o grupo de verdade.
            decidido = not grupo.resolvido_automaticamente and any(
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
