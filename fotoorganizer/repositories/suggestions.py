"""Consultas e ações de revisão sobre sugestões."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone

from sqlalchemy import case, func, select, update
from sqlalchemy.orm import Session, sessionmaker

from fotoorganizer.metadata.camera import nome_da_camera
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
    # A barra lateral vale aqui também: com 5.048 pendentes, decidir uma
    # fonte de cada vez é o que torna a fila abordável.
    source_id: int | None = None
    # Recorta na unidade em que a decisão é tomada (D-018): o grupo de
    # destino. É o que permite listar as fotos de UM grupo sem carregar a
    # fila inteira, e aprovar o grupo todo sem mandar 2.406 ids pela rede.
    destino: str | None = None


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


@dataclass(frozen=True, slots=True)
class GrupoSugestoes:
    """Um destino proposto e tudo que a decisão sobre ele precisa saber.

    A unidade de decisão é o grupo, não a foto (D-018), e a medição do
    acervo real mostra o quanto: 5.048 sugestões pendentes caem em 10
    destinos, e **o nível de confiança é constante dentro de cada um** —
    não existe uma única foto que discorde do grupo dela. Pedir 5.048
    confirmações para 10 escolhas era o defeito central da tela.

    Contado no banco, nunca na página carregada: o cabeçalho dizia
    "· 85 fotos" para um grupo de 597 porque contava o que a consulta
    tinha trazido, e o botão "Aprovar 85" fazia o que dizia — deixando 512
    para trás sem avisar.
    """

    destino: str
    total: int
    nivel: ConfidenceLevel
    # Quantas herdaram o lugar de outra câmera: é o que a linha do grupo
    # precisa para o dono saber que a pasta veio de inferência, não de GPS.
    estimadas: int
    # Quantas não podem ser abertas agora (volume desmontado ou referência
    # de nuvem). Sem isto o dono aprova 2.405 fotos de um disco desligado
    # sem saber — o caso que D-033 já obrigou a dizer no mapa.
    fora_de_alcance: int
    # De onde vêm, na ordem de quantas cada pasta contribui. É a metade
    # "situação atual" do par que a tela precisa mostrar, e que hoje não
    # aparece em tela nenhuma.
    origens: tuple[tuple[str, int], ...]


# Do mais fraco para o mais forte. A ordem alfabética do enum NÃO é esta
# (ALTA < BAIXA < MEDIA), então deixar o banco escolher com `min` daria o
# nível errado no dia em que um grupo deixar de ser uniforme.
_FORCA = (ConfidenceLevel.BAIXA, ConfidenceLevel.MEDIA, ConfidenceLevel.ALTA)


def _nivel_do_grupo(niveis: str | None) -> ConfidenceLevel:
    """O elo mais fraco entre os níveis presentes no grupo.

    Medido no acervo real: o nível é constante dentro de cada um dos 10
    destinos, então hoje isto sempre devolve o único valor que existe. A
    regra existe para quando deixar de ser — e é a mesma de
    `docs/CONFIANCA.md`: a confiança de um conjunto é a do seu elo mais
    fraco, nunca uma média.
    """
    presentes = {n for n in (niveis or "").split(",") if n}
    for nivel in _FORCA:
        if nivel.name in presentes or nivel.value in presentes:
            return nivel
    return ConfidenceLevel.BAIXA


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
        if filters.source_id is not None:
            stmt = stmt.where(MediaFile.source_id == filters.source_id)
        if filters.destino is not None:
            stmt = stmt.where(Suggestion.destino_sugerido == filters.destino)
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
                    camera=nome_da_camera(media.make, media.model),
                    gps_estimado=media.coordenada_estimada,
                    source_id=media.source_id,
                    arquivo_ausente=media.arquivo_ausente,
                )
                for sugestao, media in session.execute(stmt)
            ]

    def grupos(self, filters: SuggestionFilters) -> list[GrupoSugestoes]:
        """Um resumo por destino, contado no banco.

        São dez linhas no acervo real, então cabe tudo numa consulta e a
        tela nunca mais precisa adivinhar o tamanho de um grupo a partir da
        página que carregou. As origens saem numa segunda consulta, também
        agregada — juntar as duas num `group_concat` daria a pasta certa e
        a contagem errada.
        """
        base = filters if filters.destino is None else replace(filters, destino=None)
        with self._factory() as session:
            linhas = session.execute(
                self._query(base)
                .with_only_columns(
                    Suggestion.destino_sugerido,
                    func.count(Suggestion.id),
                    func.group_concat(Suggestion.nivel.distinct()),
                    func.sum(
                        case((MediaFile.gps_lat_estimado.is_not(None), 1), else_=0)
                    ),
                    func.sum(case((MediaFile.arquivo_ausente, 1), else_=0)),
                )
                .group_by(Suggestion.destino_sugerido)
                .order_by(func.count(Suggestion.id).desc())
            ).all()

            origens: dict[str, list[tuple[str, int]]] = {}
            for destino, pasta, n in session.execute(
                self._query(base)
                .with_only_columns(
                    Suggestion.destino_sugerido, MediaFile.pasta,
                    func.count(Suggestion.id),
                )
                .group_by(Suggestion.destino_sugerido, MediaFile.pasta)
                .order_by(func.count(Suggestion.id).desc())
            ):
                origens.setdefault(destino, []).append((pasta or "", n))

        return [
            GrupoSugestoes(
                destino=destino,
                total=total,
                nivel=_nivel_do_grupo(niveis),
                estimadas=int(estimadas or 0),
                fora_de_alcance=int(fora or 0),
                origens=tuple(origens.get(destino, ())[:3]),
            )
            for destino, total, niveis, estimadas, fora in linhas
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

    # Ações válidas e o que cada uma faz com o carimbo de revisão.
    _ACOES = {
        "aprovar": (SuggestionStatus.APROVADA, True),
        "rejeitar": (SuggestionStatus.REJEITADA, True),
        "desfazer": (SuggestionStatus.PENDENTE, False),
    }

    def aplicar_em_lote(self, filters: SuggestionFilters, acao: str) -> int:
        """Aplica a ação a TUDO que casa com o filtro, num UPDATE só.

        É o que permite "Aprovar 2.406" aprovar as 2.406: a tela manda o
        destino do grupo, o banco resolve o resto. Mandar os ids pela rede
        seria pedir à tela um número que ela não tem (ela só carregou uma
        página) e, com grupos grandes, esbarraria no limite de variáveis
        do SQLite num `IN (...)`.

        Um `UPDATE` com subconsulta, e não um laço carregando cada objeto:
        o acervo do dono é uma fração do real, e o laço cresce com ele.
        """
        if acao not in self._ACOES:
            raise ValueError(f"ação desconhecida: {acao}")
        status, revisado = self._ACOES[acao]
        alvo = self._query(filters).with_only_columns(Suggestion.id)
        with self._factory() as session:
            resultado = session.execute(
                update(Suggestion)
                .where(Suggestion.id.in_(alvo))
                .values(status=status, revisado_em=_agora() if revisado else None)
            )
            session.commit()
            return resultado.rowcount or 0

    def aprovar(self, ids: list[int]) -> int:
        return self._set_status(ids, SuggestionStatus.APROVADA, revisado=True)

    def rejeitar(self, ids: list[int]) -> int:
        return self._set_status(ids, SuggestionStatus.REJEITADA, revisado=True)

    def desfazer(self, ids: list[int]) -> int:
        """Volta a PENDENTE — a decisão deixa de valer e a foto volta a ser
        regenerável pelo motor."""
        return self._set_status(ids, SuggestionStatus.PENDENTE, revisado=False)

    def editar_destino(
        self, suggestion_id: int, novo_destino: str
    ) -> SuggestionRow | None:
        """Sobrescreve o destino sugerido/editado e marca EDITADA — sem
        restrição por status anterior: o PySide6 permite editar qualquer
        linha (aprovada, rejeitada ou pendente), porque o plano só olha o
        destino no momento em que é criado, não quando a sugestão nasceu.
        Devolve `None` se a sugestão não existe."""
        with self._factory() as session:
            linha = session.execute(
                select(Suggestion, MediaFile)
                .join(MediaFile, Suggestion.media_id == MediaFile.id)
                .where(Suggestion.id == suggestion_id)
            ).first()
            if linha is None:
                return None
            sugestao, media = linha
            sugestao.destino_sugerido = novo_destino
            sugestao.status = SuggestionStatus.EDITADA
            sugestao.revisado_em = _agora()
            session.commit()
            return SuggestionRow(
                id=sugestao.id, media_id=media.id, nome=media.nome,
                pasta=media.pasta, destino=sugestao.destino_sugerido,
                nivel=sugestao.nivel, status=sugestao.status,
                data_capturada=media.data_capturada,
                camera=nome_da_camera(media.make, media.model),
                gps_estimado=media.coordenada_estimada,
            )
