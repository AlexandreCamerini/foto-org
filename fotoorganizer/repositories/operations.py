"""Consultas de planos de operação para a UI."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from fotoorganizer.models import (
    AuditLog,
    OperationItem,
    OperationPlan,
    OperationStatus,
)


@dataclass(frozen=True, slots=True)
class PlanRow:
    id: int
    nome: str
    status: OperationStatus
    dry_run_em: datetime | None
    criado_em: datetime
    total_itens: int
    concluidos: int
    com_conflito: int
    com_erro: int


@dataclass(frozen=True, slots=True)
class ItemRow:
    id: int
    origem: str
    destino: str
    status: OperationStatus
    conflito: str | None
    erro: str | None


@dataclass(frozen=True, slots=True)
class AuditRow:
    id: int
    quando: datetime
    acao: str
    resultado: str
    detalhe: dict | None


class OperationRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._factory = session_factory

    @staticmethod
    def _linha(session: Session, plano: OperationPlan) -> PlanRow:
        def contar(*filtros) -> int:
            return session.scalar(
                select(func.count(OperationItem.id))
                .where(OperationItem.plan_id == plano.id, *filtros)
            ) or 0

        return PlanRow(
            id=plano.id, nome=plano.nome, status=plano.status,
            dry_run_em=plano.dry_run_em, criado_em=plano.criado_em,
            total_itens=contar(),
            concluidos=contar(OperationItem.status == OperationStatus.CONCLUIDA),
            com_conflito=contar(OperationItem.conflito.is_not(None)),
            com_erro=contar(OperationItem.status == OperationStatus.ERRO),
        )

    def listar_planos(self) -> list[PlanRow]:
        with self._factory() as session:
            return [
                self._linha(session, plano)
                for plano in session.scalars(
                    select(OperationPlan).order_by(OperationPlan.id.desc())
                )
            ]

    def plano(self, plan_id: int) -> PlanRow | None:
        """Um plano só — a tela de detalhe consulta isto a cada ação, e varrer
        a lista inteira para achar um id sairia caro com o tempo."""
        with self._factory() as session:
            plano = session.get(OperationPlan, plan_id)
            return self._linha(session, plano) if plano is not None else None

    def auditoria(self, plan_id: int, limit: int = 500) -> list[AuditRow]:
        """Trilha do plano, mais recente primeiro — a prova do que aconteceu
        com cada arquivo (invariante 3 do CLAUDE.md)."""
        with self._factory() as session:
            return [
                AuditRow(id=linha.id, quando=linha.quando, acao=linha.acao,
                         resultado=linha.resultado, detalhe=linha.detalhe)
                for linha in session.scalars(
                    select(AuditLog)
                    .where(AuditLog.plan_id == plan_id)
                    .order_by(AuditLog.id.desc())
                    .limit(limit)
                )
            ]

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
