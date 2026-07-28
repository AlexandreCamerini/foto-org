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
    # Veredito do ÚLTIMO dry-run. `com_erro` conta erro de execução e fica
    # em zero num plano que nunca rodou — sem estes dois campos o resumo
    # de um plano intransitável (origem em volume desmontado) se lê como
    # "0 erros, dry-run feito", ou seja, pronto para executar.
    prontos: int | None = None
    problemas: int | None = None

    @property
    def executavel(self) -> bool:
        """Há dry-run recente e ele achou ao menos um arquivo copiável."""
        return self.dry_run_em is not None and bool(self.prontos)


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

        prontos, problemas = OperationRepository._veredito(session, plano.id)
        return PlanRow(
            id=plano.id, nome=plano.nome, status=plano.status,
            dry_run_em=plano.dry_run_em, criado_em=plano.criado_em,
            total_itens=contar(),
            concluidos=contar(OperationItem.status == OperationStatus.CONCLUIDA),
            com_conflito=contar(OperationItem.conflito.is_not(None)),
            com_erro=contar(OperationItem.status == OperationStatus.ERRO),
            prontos=prontos, problemas=problemas,
        )

    @staticmethod
    def _veredito(session: Session, plan_id: int) -> tuple[int | None, int | None]:
        """(prontos, problemas) do último dry-run, lidos do audit log.

        O audit log já grava isso, e é onde a informação tem de viver: é a
        trilha do que aconteceu (invariante 3). Copiar os números para o
        plano criaria duas verdades livres para divergir.
        """
        detalhe = session.scalar(
            select(AuditLog.detalhe)
            .where(AuditLog.plan_id == plan_id, AuditLog.acao == "dry_run")
            .order_by(AuditLog.id.desc())
            .limit(1)
        )
        if not detalhe:
            return None, None
        return detalhe.get("prontos"), detalhe.get("problemas")

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
