"""Consultas de plano de escrita EXIF (D-075, Fase 6) para a UI.

Espelha `repositories/operations.py` (mesmas formas: dataclasses
`frozen=True, slots=True`, `contar(*filtros)` agregado, veredito do último
dry-run lido do audit log em vez de copiado para a tabela do plano). A
única diferença estrutural real: a auditoria de um plano de escrita EXIF
**nunca** é filtrada por `AuditLog.plan_id` — aquela coluna tem FK real e
ativa para `operation_plans.id` (RESEARCH.md Pitfall 5), e as linhas deste
domínio são sempre gravadas com `plan_id=None`. O id do `ExifWritePlan`
viaja em `AuditLog.detalhe["exif_plan_id"]` (JSON), e é por esse caminho
que toda consulta de auditoria deste arquivo filtra.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from fotoorganizer.models import (
    AuditLog,
    CampoStatus,
    ExifWriteItem,
    ExifWritePlan,
    ExifWriteStatus,
)
from fotoorganizer.repositories.operations import AuditRow

# Reuso deliberado, não duplicação: a forma da linha de auditoria (id,
# quando, acao, resultado, detalhe) não muda entre os dois domínios — só a
# consulta que a produz muda (coluna vs. JSON).
__all__ = ["AuditRow", "ExifWriteRepository", "ItemRowExif", "PlanRowExif"]

_CAMPOS_RESOLVIDOS = (CampoStatus.GRAVADO, CampoStatus.PULADO)


@dataclass(frozen=True, slots=True)
class PlanRowExif:
    id: int
    nome: str
    status: ExifWriteStatus
    dry_run_em: datetime | None
    criado_em: datetime
    total_itens: int
    nao_suportados: int
    sincronizados: int
    gravados: int
    com_erro: int
    # Veredito do ÚLTIMO dry-run, lido do audit log (nunca copiado para a
    # tabela do plano — duas verdades divergiriam). `None` quando o plano
    # ainda não rodou dry-run nenhum.
    prontos: int | None = None
    problemas: int | None = None
    campos_a_gravar: int | None = None
    sidecars: int | None = None

    @property
    def executavel(self) -> bool:
        """Há dry-run recente e ele achou ao menos um item pronto."""
        return self.dry_run_em is not None and bool(self.prontos)


@dataclass(frozen=True, slots=True)
class ItemRowExif:
    id: int
    media_id: int
    origem: str
    incluido: bool
    formato_suportado: bool
    motivo_nao_suportado: str | None
    sidecar_destino: str | None
    pasta_sincronizada: str | None
    erro: str | None
    backup_original: str | None
    valor_gps: tuple[float, float] | None
    valor_cidade: str | None
    valor_pais: str | None
    status_gps: CampoStatus
    status_cidade: CampoStatus
    status_pais: CampoStatus
    motivo_gps: str | None
    motivo_cidade: str | None
    motivo_pais: str | None


class ExifWriteRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._factory = session_factory

    @staticmethod
    def _linha(session: Session, plano: ExifWritePlan) -> PlanRowExif:
        def contar(*filtros) -> int:
            return session.scalar(
                select(func.count(ExifWriteItem.id))
                .where(ExifWriteItem.plan_id == plano.id, *filtros)
            ) or 0

        prontos, problemas, campos_a_gravar, sidecars = (
            ExifWriteRepository._veredito(session, plano.id)
        )
        return PlanRowExif(
            id=plano.id, nome=plano.nome, status=plano.status,
            dry_run_em=plano.dry_run_em, criado_em=plano.criado_em,
            total_itens=contar(),
            # Item "gravado" no resumo do plano é item cujos TRÊS campos
            # terminaram resolvidos (GRAVADO ou PULADO — sem sobra
            # PENDENTE/PRONTO/SEM_VALOR/FALHA) e sem erro registrado. As
            # três colunas de status entram como filtros SEPARADOS: o
            # `contar` do analog faz AND de tudo que recebe no `.where()`,
            # então isto exige simultaneamente os três campos resolvidos,
            # não qualquer um deles.
            gravados=contar(
                ExifWriteItem.status_gps.in_(_CAMPOS_RESOLVIDOS),
                ExifWriteItem.status_cidade.in_(_CAMPOS_RESOLVIDOS),
                ExifWriteItem.status_pais.in_(_CAMPOS_RESOLVIDOS),
                ExifWriteItem.erro.is_(None),
            ),
            com_erro=contar(ExifWriteItem.erro.is_not(None)),
            nao_suportados=contar(ExifWriteItem.formato_suportado.is_(False)),
            sincronizados=contar(ExifWriteItem.pasta_sincronizada.is_not(None)),
            prontos=prontos, problemas=problemas,
            campos_a_gravar=campos_a_gravar, sidecars=sidecars,
        )

    @staticmethod
    def _veredito(
        session: Session, plan_id: int,
    ) -> tuple[int | None, int | None, int | None, int | None]:
        """(prontos, problemas, campos_a_gravar, sidecars) do último
        `dry_run_exif`, lidos do audit log.

        O audit log já grava isso (`exif_write/executor.py::dry_run`), e é
        onde a informação tem de viver: é a trilha do que aconteceu
        (invariante 3). Copiar os números para o plano criaria duas
        verdades livres para divergir — mesmo raciocínio do analog de
        operações, aplicado aqui com o filtro por JSON em vez da coluna
        `plan_id` (que fica sempre `None` neste domínio, Pitfall 5)."""
        detalhe = session.scalar(
            select(AuditLog.detalhe)
            .where(
                AuditLog.acao == "dry_run_exif",
                AuditLog.detalhe["exif_plan_id"].as_integer() == plan_id,
            )
            .order_by(AuditLog.id.desc())
            .limit(1)
        )
        if not detalhe:
            return None, None, None, None
        return (
            detalhe.get("prontos"), detalhe.get("problemas"),
            detalhe.get("campos_a_gravar"), detalhe.get("sidecars"),
        )

    def listar_planos(self) -> list[PlanRowExif]:
        with self._factory() as session:
            return [
                self._linha(session, plano)
                for plano in session.scalars(
                    select(ExifWritePlan).order_by(ExifWritePlan.id.desc())
                )
            ]

    def plano(self, plan_id: int) -> PlanRowExif | None:
        """Um plano só — a tela de detalhe consulta isto a cada ação, e
        varrer a lista inteira para achar um id sairia caro com o tempo."""
        with self._factory() as session:
            plano = session.get(ExifWritePlan, plan_id)
            return self._linha(session, plano) if plano is not None else None

    def itens(self, plan_id: int) -> list[ItemRowExif]:
        with self._factory() as session:
            linhas = []
            for i in session.scalars(
                select(ExifWriteItem)
                .where(ExifWriteItem.plan_id == plan_id)
                .order_by(ExifWriteItem.id)
            ):
                valor_gps = (
                    (i.valor_gps_lat, i.valor_gps_lon)
                    if i.valor_gps_lat is not None and i.valor_gps_lon is not None
                    else None
                )
                linhas.append(ItemRowExif(
                    id=i.id, media_id=i.media_id, origem=i.origem,
                    incluido=i.incluido, formato_suportado=i.formato_suportado,
                    motivo_nao_suportado=i.motivo_nao_suportado,
                    sidecar_destino=i.sidecar_destino,
                    pasta_sincronizada=i.pasta_sincronizada,
                    erro=i.erro, backup_original=i.backup_original,
                    valor_gps=valor_gps, valor_cidade=i.valor_cidade,
                    valor_pais=i.valor_pais,
                    status_gps=i.status_gps, status_cidade=i.status_cidade,
                    status_pais=i.status_pais,
                    motivo_gps=i.motivo_gps, motivo_cidade=i.motivo_cidade,
                    motivo_pais=i.motivo_pais,
                ))
            return linhas

    def auditoria(self, plan_id: int, limit: int = 500) -> list[AuditRow]:
        """Trilha do plano, mais recente primeiro — a prova do que
        aconteceu com cada arquivo (invariante 3 do CLAUDE.md). Filtrada
        por `detalhe["exif_plan_id"]`, nunca pela coluna `plan_id` (sempre
        `None` neste domínio)."""
        with self._factory() as session:
            return [
                AuditRow(id=linha.id, quando=linha.quando, acao=linha.acao,
                         resultado=linha.resultado, detalhe=linha.detalhe)
                for linha in session.scalars(
                    select(AuditLog)
                    .where(AuditLog.detalhe["exif_plan_id"].as_integer() == plan_id)
                    .order_by(AuditLog.id.desc())
                    .limit(limit)
                )
            ]
