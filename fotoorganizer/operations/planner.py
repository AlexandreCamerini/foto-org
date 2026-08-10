"""Gera planos de cópia a partir das sugestões aprovadas/editadas.

O plano é só registro — nenhum arquivo é tocado aqui. Cada item carrega
origem, destino calculado (com colisões resolvidas por sufixo) e conflito
detectado. A execução (executor.py) exige dry-run antes.
"""

from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from fotoorganizer.models import (
    AuditLog,
    DuplicateMember,
    DuplicateRole,
    MediaFile,
    OperationItem,
    OperationPlan,
    OperationStatus,
    Source,
    Suggestion,
    SuggestionStatus,
)
from fotoorganizer.security.paths import (
    CaminhoInvalido,
    destino_recursivo,
    resolver_destino,
)

log = logging.getLogger(__name__)


def _destino_livre(destino: Path, usados: set[str]) -> tuple[str, bool]:
    """Resolve colisões com o disco e com o próprio plano, sufixando ANTES
    da extensão: IMG_1 (2).jpg — nunca sobrescreve nome ocupado."""
    candidato = destino
    i = 2
    while str(candidato) in usados or candidato.exists():
        candidato = destino.with_name(f"{destino.stem} ({i}){destino.suffix}")
        i += 1
    return str(candidato), candidato != destino


class OperationPlanner:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._factory = session_factory

    def criar_plano(self, raiz_destino: Path, nome: str | None = None) -> int | None:
        """Cria um plano de CÓPIA para toda sugestão aprovada/editada cuja
        foto ainda não foi copiada por um plano anterior. Devolve o id do
        plano, ou None se não havia nada a planejar."""
        raiz = raiz_destino.expanduser()
        with self._factory() as session:
            sugestoes = list(session.execute(
                select(Suggestion, MediaFile, Source)
                .join(MediaFile, Suggestion.media_id == MediaFile.id)
                .join(Source, MediaFile.source_id == Source.id)
                .where(Suggestion.status.in_(
                    [SuggestionStatus.APROVADA, SuggestionStatus.EDITADA]
                ))
                .order_by(Suggestion.destino_sugerido, MediaFile.nome)
            ))
            ja_copiadas = set(session.scalars(
                select(OperationItem.media_id).where(
                    OperationItem.status == OperationStatus.CONCLUIDA
                )
            ))
            # VERSAO é a cópia redundante de um grupo de duplicata que já tem
            # PRINCIPAL definido (automático para EXATO, ou humano em
            # qualquer nível) — não entra no plano de cópia. IGNORADO é
            # diferente: o usuário olhou o grupo e decidiu que não são
            # duplicatas de fato ("nenhum arquivo será tocado",
            # repositories/duplicates.py) — continua entrando normalmente.
            versoes = set(session.scalars(
                select(DuplicateMember.media_id).where(
                    DuplicateMember.papel == DuplicateRole.VERSAO
                )
            ))
            pendentes = [
                (s, m, f) for s, m, f in sugestoes
                if m.id not in ja_copiadas and m.id not in versoes
            ]
            if not pendentes:
                return None

            plano = OperationPlan(
                nome=nome or f"Cópia para {raiz}",
                status=OperationStatus.PLANEJADA,
            )
            session.add(plano)
            session.flush()

            usados: set[str] = set()
            for sugestao, media, fonte in pendentes:
                origem = Path(media.caminho)
                conflito = None
                destino_str = ""
                try:
                    pasta_destino = resolver_destino(raiz, sugestao.destino_sugerido)
                    destino = pasta_destino / media.nome
                    if destino_recursivo(Path(fonte.caminho), raiz):
                        conflito = "raiz de destino dentro da árvore de origem"
                    resolvido, renomeado = _destino_livre(destino, usados)
                    if renomeado and conflito is None:
                        conflito = (
                            f"destino ocupado; renomeado para "
                            f"{Path(resolvido).name}"
                        )
                    destino_str = resolvido
                    usados.add(resolvido)
                except CaminhoInvalido as exc:
                    conflito = f"caminho inválido: {exc}"
                    destino_str = ""

                session.add(OperationItem(
                    plan_id=plano.id, media_id=media.id,
                    origem=str(origem), destino=destino_str,
                    conflito=conflito,
                    status=OperationStatus.PLANEJADA,
                ))

            session.add(AuditLog(
                plan_id=plano.id, acao="plano_criado",
                detalhe={"raiz": str(raiz), "itens": len(pendentes)},
                resultado="ok",
            ))
            session.commit()
            log.info("plano %s criado com %d itens", plano.id, len(pendentes))
            return plano.id
