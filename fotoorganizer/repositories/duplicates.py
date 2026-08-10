"""Consultas e decisões sobre grupos de duplicatas. Nenhuma ação toca nos
arquivos — apenas papéis registrados para uma futura fase de operações."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload, sessionmaker

from fotoorganizer.models import (
    DuplicateGroup,
    DuplicateLevel,
    DuplicateMember,
    DuplicateRole,
    MediaFile,
    MetadataEntry,
)

_NIVEL_ROTULO = {
    DuplicateLevel.EXATO: "Idênticos",
    DuplicateLevel.CONTEUDO: "Mesmo conteúdo",
    DuplicateLevel.VISUAL: "Parecidos",
    DuplicateLevel.SEQUENCIA: "Sequência (rajada)",
}


@dataclass(frozen=True, slots=True)
class MemberRow:
    member_id: int
    media_id: int
    nome: str
    caminho: str
    tamanho: int
    hash_rapido: str | None
    papel: DuplicateRole
    source_id: int = 0


@dataclass(frozen=True, slots=True)
class GroupRow:
    id: int
    nivel: DuplicateLevel
    rotulo_nivel: str
    membros: tuple[MemberRow, ...]
    decidido: bool
    resolvido_automaticamente: bool

    @property
    def bytes_recuperaveis(self) -> int:
        """Espaço liberado se só a maior cópia fosse mantida (informativo)."""
        tamanhos = sorted((m.tamanho for m in self.membros), reverse=True)
        return sum(tamanhos[1:])

    @property
    def n_fontes(self) -> int:
        """Mesma foto presente em mais de uma fonte é vínculo entre
        catálogos (âncora de correlação), não só espaço a recuperar."""
        return len({m.source_id for m in self.membros})


def _herdar_metadados(
    session: Session, principal_id: int, versoes: list[int]
) -> None:
    """A principal absorve o metadado que só as versões tinham.

    Escolher a principal não descarta as outras — o invariante 8 proíbe — mas
    tira as versões da grade, da revisão e do plano. Se o que sai levasse
    junto a única entrada de GPS ou de álbum do grupo, a escolha teria custado
    informação, e é justamente a informação que este catálogo existe para
    guardar. O Immich faz o mesmo ao resolver duplicata (álbum, favorito,
    nota, descrição); aqui a regra é mais simples e mais geral: qualquer par
    (namespace, chave) que a principal não tenha.

    Só ACRESCENTA. Onde as duas sabem a mesma chave, a da principal fica —
    ela é a referência de trabalho, e sobrescrever com o valor de quem está
    saindo inverteria a decisão que o usuário acabou de tomar. As entradas
    das versões continuam onde estão: nada é apagado.
    """
    if not versoes:
        return
    existentes = {
        (ns, chave) for ns, chave in session.execute(
            select(MetadataEntry.namespace, MetadataEntry.chave)
            .where(MetadataEntry.media_id == principal_id)
        )
    }
    for entrada in session.scalars(
        select(MetadataEntry)
        .where(MetadataEntry.media_id.in_(versoes))
        .order_by(MetadataEntry.media_id, MetadataEntry.id)
    ):
        chave = (entrada.namespace, entrada.chave)
        if chave in existentes:
            continue
        existentes.add(chave)
        session.add(MetadataEntry(
            media_id=principal_id, namespace=entrada.namespace,
            chave=entrada.chave, valor=entrada.valor,
        ))


class DuplicateRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._factory = session_factory

    def listar_grupos(self) -> list[GroupRow]:
        with self._factory() as session:
            grupos = session.scalars(
                select(DuplicateGroup)
                .options(selectinload(DuplicateGroup.membros))
                .order_by(DuplicateGroup.nivel, DuplicateGroup.id)
            )
            linhas = []
            for grupo in grupos:
                membros = []
                for membro in grupo.membros:
                    media = session.get(MediaFile, membro.media_id)
                    if media is None:
                        continue
                    membros.append(MemberRow(
                        member_id=membro.id, media_id=media.id, nome=media.nome,
                        caminho=media.caminho, tamanho=media.tamanho,
                        hash_rapido=media.hash_rapido, papel=membro.papel,
                        source_id=media.source_id,
                    ))
                linhas.append(GroupRow(
                    id=grupo.id, nivel=grupo.nivel,
                    rotulo_nivel=_NIVEL_ROTULO[grupo.nivel],
                    membros=tuple(membros),
                    decidido=any(
                        m.papel != DuplicateRole.INDEFINIDO for m in membros
                    ),
                    resolvido_automaticamente=grupo.resolvido_automaticamente,
                ))
            return linhas

    def contagens(self) -> dict[DuplicateLevel, int]:
        with self._factory() as session:
            from sqlalchemy import func

            stmt = select(DuplicateGroup.nivel, func.count()).group_by(
                DuplicateGroup.nivel
            )
            return dict(session.execute(stmt).all())

    # -- decisões ----------------------------------------------------------
    def escolher_principal(self, group_id: int, media_id: int) -> None:
        """O escolhido vira PRINCIPAL; os demais, VERSAO.

        Ação humana: mesmo que o grupo já tivesse sido resolvido pela regra
        automática (`duplicates/resolucao.py`), uma escolha explícita aqui
        substitui o algoritmo — a partir daqui a decisão é do usuário.
        """
        with self._factory() as session:
            self._marcar_decisao_humana(session, group_id)
            versoes: list[int] = []
            for membro in session.scalars(
                select(DuplicateMember).where(DuplicateMember.group_id == group_id)
            ):
                if membro.media_id == media_id:
                    membro.papel = DuplicateRole.PRINCIPAL
                else:
                    membro.papel = DuplicateRole.VERSAO
                    versoes.append(membro.media_id)
            _herdar_metadados(session, media_id, versoes)
            session.commit()

    def ignorar_grupo(self, group_id: int) -> None:
        """Manter todos / ignorar: nenhum arquivo será tocado."""
        self._set_papel_grupo(group_id, DuplicateRole.IGNORADO)

    def desfazer_grupo(self, group_id: int) -> None:
        self._set_papel_grupo(group_id, DuplicateRole.INDEFINIDO)

    def _set_papel_grupo(self, group_id: int, papel: DuplicateRole) -> None:
        with self._factory() as session:
            self._marcar_decisao_humana(session, group_id)
            for membro in session.scalars(
                select(DuplicateMember).where(DuplicateMember.group_id == group_id)
            ):
                membro.papel = papel
            session.commit()

    @staticmethod
    def _marcar_decisao_humana(session: Session, group_id: int) -> None:
        grupo = session.get(DuplicateGroup, group_id)
        if grupo is not None:
            grupo.resolvido_automaticamente = False
