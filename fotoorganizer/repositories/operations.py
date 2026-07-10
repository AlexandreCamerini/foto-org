"""Consultas de planos de operação para a UI."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from fotoorganizer.models import OperationItem, OperationPlan, OperationStatus


@dataclass(frozen=True, slots=True)
class PlanRow:
    id: int
    nome: str
    status: OperationStatus
    dry_run_em: datetime | None
    total_itens: int
    concluidos: int
    com_conflito: int


@dataclass(frozen=True, slots=True)
class ItemRow:
    id: int
    origem: str
    destino: str
    status: OperationStatus
    conflito: str | None
    erro: str | None


class OperationRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._factory = session_factory

    def listar_planos(self) -> list[PlanRow]:
        with self._factory() as session:
            linhas = []
            for plano in session.scalars(
                select(OperationPlan).order_by(OperationPlan.id.desc())
            ):
                total = session.scalar(select(func.count(OperationItem.id)).where(
                    OperationItem.plan_id == plano.id))
                concluidos = session.scalar(
                    select(func.count(OperationItem.id)).where(
                        OperationItem.plan_id == plano.id,
                        OperationItem.status == OperationStatus.CONCLUIDA,
                    ))
                conflitos = session.scalar(
                    select(func.count(OperationItem.id)).where(
                        OperationItem.plan_id == plano.id,
                        OperationItem.conflito.is_not(None),
                    ))
                linhas.append(PlanRow(
                    id=plano.id, nome=plano.nome, status=plano.status,
                    dry_run_em=plano.dry_run_em, total_itens=total or 0,
                    concluidos=concluidos or 0, com_conflito=conflitos or 0,
                ))
            return linhas

    def itens(self, plan_id: int) -> list[ItemRow]:
        with self._factory() as session:
            return [
                ItemRow(id=i.id, origem=i.origem, destino=i.destino,
                        status=i.status, conflito=i.conflito, erro=i.erro)
                for i in session.scalars(
                    select(OperationItem)
                    .where(OperationItem.plan_id == plan_id)
                    .order_by(OperationItem.id)
                )
            ]
