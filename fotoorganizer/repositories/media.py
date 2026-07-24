"""Consultas do catálogo para a UI: paginadas, filtradas e sem estado.

Cada método abre a própria Session (expire_on_commit=False no factory faz
os objetos continuarem legíveis depois de fechada — a UI só lê colunas).
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, sessionmaker

from fotoorganizer.models import MediaFile, Source

ORDENACOES = {
    "data_desc": (MediaFile.data_capturada.desc().nulls_last(), MediaFile.id.desc()),
    "data_asc": (MediaFile.data_capturada.asc().nulls_last(), MediaFile.id.asc()),
    "nome": (MediaFile.nome.asc(),),
    "tamanho_desc": (MediaFile.tamanho.desc(),),
}


@dataclass(frozen=True)
class MediaFilters:
    busca: str | None = None
    extensao: str | None = None
    source_id: int | None = None
    ano: int | None = None
    trip_id: int | None = None
    event_id: int | None = None
    ordenacao: str = "data_desc"


class MediaRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._factory = session_factory

    def _query(self, filters: MediaFilters):
        stmt = select(MediaFile)
        if filters.busca:
            like = f"%{filters.busca}%"
            stmt = stmt.where(
                or_(MediaFile.nome.ilike(like), MediaFile.caminho.ilike(like))
            )
        if filters.extensao:
            stmt = stmt.where(MediaFile.extensao == filters.extensao)
        if filters.source_id is not None:
            stmt = stmt.where(MediaFile.source_id == filters.source_id)
        if filters.ano is not None:
            stmt = stmt.where(
                func.strftime("%Y", MediaFile.data_capturada) == str(filters.ano)
            )
        if filters.trip_id is not None:
            stmt = stmt.where(MediaFile.trip_id == filters.trip_id)
        if filters.event_id is not None:
            stmt = stmt.where(MediaFile.event_id == filters.event_id)
        return stmt

    def listar(
        self, filters: MediaFilters, limit: int, offset: int
    ) -> list[MediaFile]:
        ordem = ORDENACOES.get(filters.ordenacao, ORDENACOES["data_desc"])
        with self._factory() as session:
            stmt = self._query(filters).order_by(*ordem).limit(limit).offset(offset)
            return list(session.scalars(stmt))

    def contar(self, filters: MediaFilters) -> int:
        with self._factory() as session:
            stmt = select(func.count()).select_from(self._query(filters).subquery())
            return session.scalar(stmt) or 0

    def por_id(self, media_id: int) -> MediaFile | None:
        with self._factory() as session:
            return session.get(MediaFile, media_id)

    def extensoes(self) -> list[str]:
        with self._factory() as session:
            stmt = select(MediaFile.extensao).distinct().order_by(MediaFile.extensao)
            return list(session.scalars(stmt))

    def anos(self) -> list[int]:
        with self._factory() as session:
            expr = func.strftime("%Y", MediaFile.data_capturada)
            stmt = (
                select(expr)
                .where(MediaFile.data_capturada.is_not(None))
                .distinct()
                .order_by(expr.desc())
            )
            return [int(ano) for ano in session.scalars(stmt)]

    def fontes_com_contagem(self) -> list[tuple[Source, int]]:
        with self._factory() as session:
            stmt = (
                select(Source, func.count(MediaFile.id))
                .outerjoin(MediaFile, MediaFile.source_id == Source.id)
                .group_by(Source.id)
                .order_by(Source.caminho)
            )
            return [(source, contagem) for source, contagem in session.execute(stmt)]

    def estatisticas(self) -> dict:
        with self._factory() as session:
            total = session.scalar(select(func.count(MediaFile.id))) or 0
            erros = (
                session.scalar(
                    select(func.count(MediaFile.id)).where(
                        MediaFile.erro_leitura.is_not(None)
                    )
                )
                or 0
            )
            fontes = session.scalar(select(func.count(Source.id))) or 0
            return {"total": total, "erros": erros, "fontes": fontes}
