"""Consultas e ações de revisão sobre sugestões."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from fotoorganizer.models import (
    ConfidenceLevel,
    Evidence,
    MediaFile,
    Suggestion,
    SuggestionStatus,
)


@dataclass(frozen=True)
class SuggestionFilters:
    status: SuggestionStatus | None = SuggestionStatus.PENDENTE
    nivel: ConfidenceLevel | None = None


@dataclass(frozen=True, slots=True)
class SuggestionRow:
    id: int
    media_id: int
    nome: str
    pasta: str
    destino: str
    nivel: ConfidenceLevel
    status: SuggestionStatus
    # Contexto que a tela de revisão precisa para a decisão ser informada:
    # sem câmera e horário, 60 linhas com o mesmo destino são indistinguíveis.
    data_capturada: datetime | None = None
    camera: str | None = None
    gps_estimado: bool = False
    # A revisão precisa saber se dá para MOSTRAR a foto: o primeiro grupo da
    # fila de um acervo real estava inteiro num volume desmontado, e a tela
    # desenhou 18 ícones de imagem quebrada sem dizer por quê.
    source_id: int = 0
    arquivo_ausente: bool = False


def _agora() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class SuggestionRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._factory = session_factory

    def _query(self, filters: SuggestionFilters):
        stmt = select(Suggestion, MediaFile).join(
            MediaFile, Suggestion.media_id == MediaFile.id
        )
        if filters.status is not None:
            stmt = stmt.where(Suggestion.status == filters.status)
        if filters.nivel is not None:
            stmt = stmt.where(Suggestion.nivel == filters.nivel)
        return stmt

    def listar(self, filters: SuggestionFilters, limit: int,
               offset: int) -> list[SuggestionRow]:
        with self._factory() as session:
            stmt = (
                self._query(filters)
                .order_by(Suggestion.destino_sugerido, MediaFile.nome)
                .limit(limit).offset(offset)
            )
            return [
                SuggestionRow(
                    id=sugestao.id, media_id=media.id, nome=media.nome,
                    pasta=media.pasta, destino=sugestao.destino_sugerido,
                    nivel=sugestao.nivel, status=sugestao.status,
                    data_capturada=media.data_capturada,
                    camera=" ".join(
                        filter(None, [media.make, media.model])
                    ) or None,
                    gps_estimado=media.coordenada_estimada,
                    source_id=media.source_id,
                    arquivo_ausente=media.arquivo_ausente,
                )
                for sugestao, media in session.execute(stmt)
            ]

    def contar(self, filters: SuggestionFilters) -> int:
        with self._factory() as session:
            stmt = select(func.count()).select_from(self._query(filters).subquery())
            return session.scalar(stmt) or 0

    def contagens_por_status(self) -> dict[SuggestionStatus, int]:
        with self._factory() as session:
            stmt = select(Suggestion.status, func.count()).group_by(Suggestion.status)
            return dict(session.execute(stmt).all())

    def evidencias(self, suggestion_id: int) -> list[Evidence]:
        """Todas as evidências da foto da sugestão — o 'por quê?' completo,
        não só as vinculadas ao destino (ex.: país embutido no rótulo da
        viagem continua explicado)."""
        with self._factory() as session:
            sugestao = session.get(Suggestion, suggestion_id)
            if sugestao is None:
                return []
            stmt = (
                select(Evidence)
                .where(Evidence.media_id == sugestao.media_id)
                .order_by(Evidence.score.desc(), Evidence.campo)
            )
            return list(session.scalars(stmt))

    # -- ações de revisão --------------------------------------------------
    def _set_status(self, ids: list[int], status: SuggestionStatus,
                    revisado: bool) -> int:
        with self._factory() as session:
            alteradas = 0
            for sugestao in session.scalars(
                select(Suggestion).where(Suggestion.id.in_(ids))
            ):
                sugestao.status = status
                sugestao.revisado_em = _agora() if revisado else None
                alteradas += 1
            session.commit()
            return alteradas

    def aprovar(self, ids: list[int]) -> int:
        return self._set_status(ids, SuggestionStatus.APROVADA, revisado=True)

    def rejeitar(self, ids: list[int]) -> int:
        return self._set_status(ids, SuggestionStatus.REJEITADA, revisado=True)

    def desfazer(self, ids: list[int]) -> int:
        """Volta a PENDENTE — a decisão deixa de valer e a foto volta a ser
        regenerável pelo motor."""
        return self._set_status(ids, SuggestionStatus.PENDENTE, revisado=False)

    def editar_destino(self, suggestion_id: int, novo_destino: str) -> None:
        with self._factory() as session:
            sugestao = session.get(Suggestion, suggestion_id)
            if sugestao is None:
                return
            sugestao.destino_sugerido = novo_destino
            sugestao.status = SuggestionStatus.EDITADA
            sugestao.revisado_em = _agora()
            session.commit()
