"""Execução de planos de cópia — a ÚNICA parte do app que escreve fora do
catálogo.

Regras rígidas (CLAUDE.md, invariantes 1–3):
- dry-run é obrigatório antes de executar;
- criação exclusiva (open 'xb'): sobrescrever é impossível no nível do SO;
- hash SHA-256 verificado na origem antes e no destino depois; divergência
  remove a CÓPIA (nunca o original) e marca erro;
- cancelamento seguro (parcial é removido) e retomada (itens concluídos não
  são refeitos);
- disco cheio / volume desconectado viram erro por item, com audit log;
- operação é sempre CÓPIA — mover/excluir não existem no MVP.
"""

from __future__ import annotations

import errno
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from threading import Event
from typing import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from fotoorganizer.models import (
    AuditLog,
    OperationItem,
    OperationPlan,
    OperationStatus,
)
from fotoorganizer.operations import inventario
from fotoorganizer.security.hashing import sha256_full

log = logging.getLogger(__name__)

_CHUNK = 1024 * 1024


class ExecutionControl:
    def __init__(self) -> None:
        self._cancelado = Event()

    def cancelar(self) -> None:
        self._cancelado.set()

    @property
    def cancelado(self) -> bool:
        return self._cancelado.is_set()


class DryRunObrigatorio(RuntimeError):
    pass


def _agora() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class OperationExecutor:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._factory = session_factory

    # -- dry-run ------------------------------------------------------------
    def dry_run(self, plan_id: int) -> dict:
        """Simula o plano sem tocar em nada e registra o resultado.
        Obrigatório antes de executar."""
        with self._factory() as session:
            plano = session.get(OperationPlan, plan_id)
            itens = self._itens(session, plan_id)

            bytes_necessarios = 0
            problemas: list[str] = []
            prontos = 0
            for item in itens:
                if item.status == OperationStatus.CONCLUIDA:
                    continue
                origem = Path(item.origem)
                if not item.destino:
                    problemas.append(f"{origem.name}: {item.conflito}")
                    continue
                if not origem.is_file():
                    problemas.append(f"{origem}: origem indisponível")
                    continue
                if Path(item.destino).exists():
                    problemas.append(
                        f"{Path(item.destino).name}: destino já existe "
                        f"(nunca será sobrescrito)"
                    )
                    continue
                bytes_necessarios += origem.stat().st_size
                prontos += 1

            livre = None
            for candidato in (Path(itens[0].destino).parents if itens
                              and itens[0].destino else []):
                if candidato.exists():
                    livre = shutil.disk_usage(candidato).free
                    break

            plano.dry_run_em = _agora()
            session.add(AuditLog(
                plan_id=plan_id, acao="dry_run",
                detalhe={
                    "prontos": prontos, "problemas": len(problemas),
                    "bytes_necessarios": bytes_necessarios,
                    "bytes_livres": livre,
                },
                resultado="ok",
            ))
            session.commit()
            return {
                "prontos": prontos,
                "problemas": problemas,
                "bytes_necessarios": bytes_necessarios,
                "bytes_livres": livre,
                "espaco_suficiente": livre is None or livre > bytes_necessarios,
            }

    @staticmethod
    def _prontos_no_ultimo_dry_run(session: Session, plan_id: int) -> int | None:
        """Quantos arquivos o último dry-run considerou copiáveis.

        None quando não há veredito registrado (plano de versão anterior) —
        aí a porta antiga vale e a decisão fica com o usuário.
        """
        detalhe = session.scalar(
            select(AuditLog.detalhe)
            .where(AuditLog.plan_id == plan_id, AuditLog.acao == "dry_run")
            .order_by(AuditLog.id.desc())
            .limit(1)
        )
        return detalhe.get("prontos") if detalhe else None

    # -- execução -----------------------------------------------------------
    def executar(
        self,
        plan_id: int,
        progress: Callable[[int, int, str], None] | None = None,
        control: ExecutionControl | None = None,
    ) -> dict:
        control = control or ExecutionControl()
        with self._factory() as session:
            plano = session.get(OperationPlan, plan_id)
            if plano.dry_run_em is None:
                raise DryRunObrigatorio(
                    "execute o dry-run antes de qualquer operação física"
                )
            # Exigir que o dry-run tenha acontecido não basta: ele precisa
            # ter aprovado alguma coisa. Um plano cujas origens estão todas
            # num volume desmontado passava nesta porta e "executava" 97
            # itens sem copiar nenhum.
            prontos = self._prontos_no_ultimo_dry_run(session, plan_id)
            if prontos == 0:
                raise DryRunObrigatorio(
                    "o último dry-run não encontrou nenhum arquivo copiável "
                    "— verifique as origens (volume desmontado?) e rode o "
                    "dry-run de novo"
                )
            plano.status = OperationStatus.EXECUTANDO
            session.add(AuditLog(plan_id=plan_id, acao="execucao_iniciada",
                                 detalhe=None, resultado="ok"))
            session.commit()

            itens = self._itens(session, plan_id)
            pendentes = [i for i in itens
                         if i.status != OperationStatus.CONCLUIDA]
            stats = {"copiados": 0, "erros": 0, "pulados":
                     len(itens) - len(pendentes), "cancelado": False,
                     "inventario_falhou": 0}

            for n, item in enumerate(pendentes, start=1):
                if control.cancelado:
                    stats["cancelado"] = True
                    break
                if progress:
                    progress(n, len(pendentes), item.origem)
                self._executar_item(session, item, stats)
                session.commit()

            if stats["cancelado"]:
                plano.status = OperationStatus.CANCELADA
            elif stats["erros"]:
                plano.status = OperationStatus.ERRO
            else:
                plano.status = OperationStatus.CONCLUIDA
            session.add(AuditLog(
                plan_id=plan_id, acao="execucao_finalizada",
                detalhe=dict(stats), resultado=plano.status.value,
            ))
            session.commit()
            return stats

    def _executar_item(self, session: Session, item: OperationItem,
                       stats: dict) -> None:
        origem = Path(item.origem)
        try:
            if not item.destino:
                raise OSError(item.conflito or "sem destino calculado")
            destino = Path(item.destino)
            if not origem.is_file():
                raise OSError("origem indisponível (volume desconectado?)")

            item.hash_pre = sha256_full(origem)
            destino.parent.mkdir(parents=True, exist_ok=True)
            self._copiar_exclusivo(origem, destino)

            item.hash_pos = sha256_full(destino)
            if item.hash_pos != item.hash_pre:
                destino.unlink(missing_ok=True)  # remove a CÓPIA corrompida
                raise OSError("verificação de hash falhou após a cópia")

            shutil.copystat(origem, destino)
            item.status = OperationStatus.CONCLUIDA
            item.erro = None
            stats["copiados"] += 1
            self._audit_item(session, item, "copia_verificada", "ok")

            # Registro do inventário roda só DEPOIS da cópia já verificada
            # por hash — falha aqui nunca desfaz uma cópia válida (D-062):
            # o arquivo real já está correto no destino, só o manifesto
            # auxiliar não. Visível no relatório, não bloqueante.
            #
            # Except genérico de propósito, não só OSError: um
            # inventario.json de execução anterior corrompido levanta
            # json.JSONDecodeError (ValueError), não OSError — e
            # `inventario.py` já trata isso, mas qualquer outra falha
            # inesperada aqui (ex.: erro de banco ao ler Location) não pode
            # subir e abortar o PLANO INTEIRO no meio, deixando cópias já
            # verificadas com o commit do item pendente (achado da revisão
            # com olhos frescos antes deste commit). O manifesto é
            # auxiliar; a cópia real nunca pode depender dele.
            try:
                inventario.registrar(session, item)
            except Exception as exc:  # noqa: BLE001 — auxiliar, nunca bloqueia
                stats["inventario_falhou"] += 1
                self._audit_item(
                    session, item, "inventario", f"erro: {exc}"
                )
        except FileExistsError:
            item.status = OperationStatus.ERRO
            item.erro = "destino já existe — sobrescrita bloqueada"
            stats["erros"] += 1
            self._audit_item(session, item, "copia", "bloqueada_sobrescrita")
        except OSError as exc:
            item.status = OperationStatus.ERRO
            item.erro = ("disco cheio" if exc.errno == errno.ENOSPC
                         else str(exc))
            stats["erros"] += 1
            self._audit_item(session, item, "copia", f"erro: {item.erro}")

    @staticmethod
    def _copiar_exclusivo(origem: Path, destino: Path) -> None:
        """Cópia em streaming com criação exclusiva ('xb'): se o destino
        existir, o SO recusa — sobrescrita é impossível por construção.
        Falha no meio remove o parcial (nunca o original)."""
        try:
            with origem.open("rb") as src, destino.open("xb") as dst:
                while chunk := src.read(_CHUNK):
                    dst.write(chunk)
        except FileExistsError:
            raise
        except OSError:
            destino.unlink(missing_ok=True)
            raise

    def _itens(self, session: Session, plan_id: int) -> list[OperationItem]:
        return list(session.scalars(
            select(OperationItem)
            .where(OperationItem.plan_id == plan_id)
            .order_by(OperationItem.id)
        ))

    def _audit_item(self, session: Session, item: OperationItem, acao: str,
                    resultado: str) -> None:
        session.add(AuditLog(
            plan_id=item.plan_id, acao=acao,
            detalhe={"origem": item.origem, "destino": item.destino,
                     "hash_pre": item.hash_pre, "hash_pos": item.hash_pos},
            resultado=resultado,
        ))
