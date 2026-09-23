"""Plano de escrita EXIF órfão — EXECUTANDO no banco com o servidor nascendo.

Espelho de `scanner.reconciliar_orfas` para o domínio de escrita EXIF
(D-095, item 10 da auditoria de 2026-09-19). Só o fim feliz, o
cancelamento ou o erro escrevem o status final do plano; quando o
processo morre no meio (app fechado, Mac desligado, kill), o plano fica
EXECUTANDO para sempre e a tela mente sobre trabalho em curso.

Chamar no boot do servidor é seguro por construção: nenhum job pode
estar rodando antes de o servidor existir. Nada além do status do plano
e uma linha de auditoria é tocado — em especial, nenhum arquivo: um
`_original` que o exiftool tenha deixado ao lado de um item interrompido
fica onde está, e quem decide restaurar é o dono (invariante 8). Rerodar
o plano retoma de onde parou: a execução reconfere ao vivo, item a item,
o que já está gravado (`executor.py`).
"""

from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from fotoorganizer.models import (
    AuditLog,
    CampoStatus,
    ExifWriteItem,
    ExifWritePlan,
    ExifWriteStatus,
)

log = logging.getLogger(__name__)


def reconciliar_planos_orfaos(session_factory: sessionmaker[Session]) -> int:
    """Carimba como INTERROMPIDA todo plano EXECUTANDO sem processo por trás.
    Devolve quantos foram carimbados."""
    with session_factory() as session:
        orfaos = list(session.scalars(
            select(ExifWritePlan).where(
                ExifWritePlan.status == ExifWriteStatus.EXECUTANDO
            )
        ))
        if not orfaos:
            return 0
        for plano in orfaos:
            plano.status = ExifWriteStatus.INTERROMPIDA
            # Quantos itens ainda esperam escrita: é o que a retomada vai
            # encontrar, e o que a auditoria precisa para o dono saber se
            # o plano parou no começo ou no fim.
            pendentes = _pendentes(session, plano.id)
            detalhe: dict = {
                "exif_plan_id": plano.id, "itens_restantes": len(pendentes),
            }
            # O item que estava em voo é determinístico: a execução anda em
            # ordem de id, então é o primeiro ainda pendente. Se o exiftool
            # deixou `_original`/temporário ao lado dele, a retomada vai
            # ver o campo "já preenchido" e pular sem apontar o backup
            # órfão — este é o único lugar que pode apontá-lo (achado da
            # revisão). Só `exists()`, num item; nada é tocado.
            if pendentes:
                em_voo = pendentes[0]
                alvo = Path(em_voo.sidecar_destino or em_voo.origem)
                deixados = [
                    str(p) for p in (
                        Path(str(alvo) + "_original"),
                        Path(str(alvo) + "_exiftool_tmp"),
                    ) if p.exists()
                ]
                detalhe["item_em_voo"] = {
                    "item_id": em_voo.id, "origem": em_voo.origem,
                    "arquivos_deixados": deixados,
                }
            session.add(AuditLog(
                plan_id=None, acao="execucao_exif_interrompida",
                detalhe=detalhe, resultado="interrompida",
            ))
        session.commit()
    log.info(
        "escrita exif: %d plano(s) órfão(s) marcado(s) como interrompido(s)",
        len(orfaos),
    )
    return len(orfaos)


def _pendentes(session: Session, plan_id: int) -> list[ExifWriteItem]:
    """Mesmo filtro e mesma ordem de `ExifWriteExecutor.executar`."""
    return [
        item for item in session.scalars(
            select(ExifWriteItem).where(
                ExifWriteItem.plan_id == plan_id,
                ExifWriteItem.incluido.is_(True),
            ).order_by(ExifWriteItem.id)
        )
        if CampoStatus.PRONTO in (item.status_gps, item.status_cidade, item.status_pais)
    ]
