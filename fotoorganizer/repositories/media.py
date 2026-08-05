"""Consultas do catálogo para a UI: paginadas, filtradas e sem estado.

Cada método abre a própria Session (expire_on_commit=False no factory faz
os objetos continuarem legíveis depois de fechada — a UI só lê colunas).
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, aliased, sessionmaker

from fotoorganizer.metadata.camera import nome_da_camera
from fotoorganizer.models import (
    ConfidenceLevel,
    MediaFile,
    MediaRole,
    Source,
    Suggestion,
)

ORDENACOES = {
    "data_desc": (MediaFile.data_capturada.desc().nulls_last(), MediaFile.id.desc()),
    "data_asc": (MediaFile.data_capturada.asc().nulls_last(), MediaFile.id.asc()),
    "nome": (MediaFile.nome.asc(),),
    "tamanho_desc": (MediaFile.tamanho.desc(),),
}

# COALESCE em SQL: `tipo_efetivo` do modelo é property Python e não serve
# em cláusula WHERE.
_TIPO_EFETIVO = func.coalesce(MediaFile.tipo_confirmado, MediaFile.tipo_imagem)

# O acervo do usuário: o que a grade mostra, a revisão decide e o plano copia.
# Fica de fora quem não tem arquivo (referência de catálogo externo) e quem
# tem arquivo mas não é foto dele (miniatura interna de outro app). Os dois
# doam data, GPS e correlação — ver MediaRole e o invariante 8.
_ACERVO = MediaFile.organizavel
_TESTEMUNHA = ~_ACERVO

# O que a grade mostra. Uma foto sem arquivo continua fora da revisão e do
# plano de cópia — aqui se decide se ela é VISÍVEL, não se é organizável.
ALCANCES: dict[str, str] = {
    "tudo": "tudo que o app conhece",
    "organizaveis": "só o que dá para organizar agora",
    "faltantes": "só o que está fora de alcance",
}

# O que impede uma foto de ser organizada sozinha. A chave é o filtro; o
# rótulo é o que o usuário lê. Ordem = ordem de exibição no panorama.
LACUNAS: dict[str, str] = {
    "sem_data": "sem data de captura",
    "sem_gps": "sem coordenada",
    "local_estimado": "lugar estimado de outra câmera",
    "nao_e_foto": "não é foto (captura, recebida, baixada)",
    "tipo_a_confirmar": "classificação a confirmar",
    "sem_grupo": "fora de viagem ou evento",
    "sem_camera": "sem câmera identificada",
    "sem_sugestao": "sem sugestão de destino",
    "confianca_baixa": "sugestão de confiança baixa",
    "confianca_media": "sugestão de confiança média",
    "erro_leitura": "erro ao ler o arquivo",
}


def _condicao_lacuna(chave: str):
    """Cada lacuna vira um predicado. Subconsulta em vez de join para a
    contagem não inflar quando a foto tem mais de uma sugestão."""
    def com_nivel(nivel: ConfidenceLevel):
        return MediaFile.id.in_(
            select(Suggestion.media_id).where(Suggestion.nivel == nivel)
        )

    condicoes = {
        "sem_data": MediaFile.data_capturada.is_(None),
        # Sem coordenada NENHUMA — nem lida, nem herdada de outra câmera.
        # Contar a estimada aqui mandaria o usuário procurar GPS numa foto
        # cujo lugar o sistema já sabe.
        "sem_gps": and_(
            or_(MediaFile.gps_lat.is_(None), MediaFile.gps_lon.is_(None)),
            MediaFile.gps_lat_estimado.is_(None),
        ),
        # Não é falta: é uma inferência que vale conferir antes de organizar.
        "local_estimado": MediaFile.gps_lat_estimado.is_not(None),
        # NULL = ainda não avaliado; só conta o que o detector já viu.
        # O tipo que vale é o do usuário, senão o do detector.
        "nao_e_foto": and_(
            _TIPO_EFETIVO.is_not(None),
            _TIPO_EFETIVO != "foto",
        ),
        # O que o detector marcou e você ainda não respondeu — a fila de
        # triagem. Some sozinha conforme você decide.
        "tipo_a_confirmar": and_(
            MediaFile.tipo_confirmado.is_(None),
            MediaFile.tipo_imagem.is_not(None),
            MediaFile.tipo_imagem != "foto",
        ),
        "sem_grupo": and_(
            MediaFile.trip_id.is_(None), MediaFile.event_id.is_(None)
        ),
        "sem_camera": and_(MediaFile.make.is_(None), MediaFile.model.is_(None)),
        "sem_sugestao": MediaFile.id.not_in(select(Suggestion.media_id)),
        "confianca_baixa": com_nivel(ConfidenceLevel.BAIXA),
        "confianca_media": com_nivel(ConfidenceLevel.MEDIA),
        "erro_leitura": MediaFile.erro_leitura.is_not(None),
    }
    return condicoes.get(chave)


@dataclass(frozen=True)
class MediaFilters:
    busca: str | None = None
    extensao: str | None = None
    source_id: int | None = None
    ano: int | None = None
    trip_id: int | None = None
    event_id: int | None = None
    lacuna: str | None = None
    ordenacao: str = "data_desc"
    # O que a grade mostra. "tudo" é o padrão porque a pergunta do dono ao
    # importar uma biblioteca é "cadê minhas fotos?": 44.661 do Apple Fotos
    # e 45.397 do Lightroom entravam no catálogo e a Biblioteca respondia
    # (0), sem dizer por quê. Ver ALCANCES.
    alcance: str = "tudo"
    # "2026-05". A âncora temporal salta filtrando, não rolando: com 103.938
    # registros paginados de 200 em 200, chegar em 2015 rolando exigiria
    # carregar tudo que veio antes.
    mes: str | None = None


class MediaRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._factory = session_factory

    def _query(self, filters: MediaFilters):
        # Testemunhas ficam fora da biblioteca visível, das contagens e de
        # qualquer filtro. Existem só para doar GPS e horário à correlação.
        if filters.alcance == "organizaveis":
            stmt = select(MediaFile).where(_ACERVO)
        elif filters.alcance == "faltantes":
            stmt = select(MediaFile).where(_TESTEMUNHA)
        else:
            stmt = select(MediaFile)
        if filters.busca:
            like = f"%{filters.busca}%"
            stmt = stmt.where(
                or_(MediaFile.nome.ilike(like), MediaFile.caminho.ilike(like))
            )
        if filters.extensao:
            stmt = stmt.where(MediaFile.extensao == filters.extensao)
        if filters.mes:
            stmt = stmt.where(
                func.strftime("%Y-%m", MediaFile.data_capturada) == filters.mes
            )
        if filters.source_id is not None:
            stmt = stmt.where(MediaFile.source_id == filters.source_id)
        if filters.ano is not None:
            stmt = stmt.where(
                func.strftime("%Y", MediaFile.data_capturada) == str(filters.ano)
            )
        if filters.trip_id is not None:
            stmt = stmt.where(MediaFile.trip_id == filters.trip_id)
        if filters.event_id is not None:
            stmt = stmt.where(MediaFile.event_id == filters.event_id)
        if filters.lacuna:
            condicao = _condicao_lacuna(filters.lacuna)
            if condicao is not None:
                stmt = stmt.where(condicao)
        return stmt

    def listar(
        self, filters: MediaFilters, limit: int, offset: int
    ) -> list[MediaFile]:
        ordem = ORDENACOES.get(filters.ordenacao, ORDENACOES["data_desc"])
        with self._factory() as session:
            stmt = self._query(filters).order_by(*ordem).limit(limit).offset(offset)
            return list(session.scalars(stmt))

    def contar(self, filters: MediaFilters) -> int:
        with self._factory() as session:
            stmt = select(func.count()).select_from(self._query(filters).subquery())
            return session.scalar(stmt) or 0

    def por_id(self, media_id: int) -> MediaFile | None:
        with self._factory() as session:
            return session.get(MediaFile, media_id)

    def extensoes(self) -> list[str]:
        with self._factory() as session:
            stmt = select(MediaFile.extensao).distinct().order_by(MediaFile.extensao)
            return list(session.scalars(stmt))

    def anos(self) -> list[int]:
        with self._factory() as session:
            expr = func.strftime("%Y", MediaFile.data_capturada)
            stmt = (
                select(expr)
                .where(MediaFile.data_capturada.is_not(None))
                .distinct()
                .order_by(expr.desc())
            )
            return [int(ano) for ano in session.scalars(stmt)]

    def linha_do_tempo(self, filters: MediaFilters) -> list[dict]:
        """Quantas fotos por mês, no recorte atual e na ordem da grade.

        É o que torna 100 mil fotos alcançáveis: sem isto, rolar é a única
        forma de chegar em 2015. Uma consulta agregada, não uma varredura —
        o banco conta por mês em milissegundos e a grade não precisa ter
        carregado a página onde aquele mês começa.
        """
        mes = func.strftime("%Y-%m", MediaFile.data_capturada)
        base = self._query(filters).subquery()
        alias = aliased(MediaFile, base)
        mes_alias = func.strftime("%Y-%m", alias.data_capturada)
        with self._factory() as session:
            linhas = session.execute(
                select(mes_alias, func.count(alias.id))
                .group_by(mes_alias)
                .order_by(mes_alias.desc())
            ).all()
        return [
            {"mes": m, "quantidade": n}
            for m, n in linhas if m is not None
        ]

    def fontes_com_contagem(self) -> list[tuple[Source, int]]:
        with self._factory() as session:
            stmt = (
                select(Source, func.count(MediaFile.id))
                .outerjoin(
                    MediaFile,
                    # A contagem é do que a fonte CONHECE, não do que ela
                    # entrega para organizar: contar só o organizável fazia o
                    # Apple Fotos aparecer como (0) depois de importar 44.661
                    # fotos, que foi o que o dono descreveu como "esquece".
                    MediaFile.source_id == Source.id,
                )
                .group_by(Source.id)
                .order_by(Source.caminho)
            )
            return [(source, contagem) for source, contagem in session.execute(stmt)]

    def panorama(self) -> dict:
        """O que a base sabe e onde ela não sabe.

        As lacunas vêm primeiro porque são acionáveis: cada uma é um filtro
        pronto para o usuário atacar o conjunto. As facetas existem para
        cruzar — o mesmo ano visto por fonte revela, por exemplo, que 2019
        só existe no Google Fotos e nunca foi baixado.
        """
        ano_expr = func.strftime("%Y", MediaFile.data_capturada)
        proprias = _ACERVO
        with self._factory() as session:
            def contar(condicao) -> int:
                return session.scalar(
                    select(func.count(MediaFile.id)).where(proprias, condicao)
                ) or 0

            def facetas(expr, ordenar_por_contagem: bool = True) -> list[dict]:
                stmt = (select(expr, func.count(MediaFile.id))
                        .where(proprias).group_by(expr))
                linhas = session.execute(stmt).all()
                chaves = [
                    {"chave": chave, "quantidade": n} for chave, n in linhas
                ]
                chaves.sort(
                    key=lambda f: (-f["quantidade"], str(f["chave"] or ""))
                    if ordenar_por_contagem
                    else (str(f["chave"] or ""),)
                )
                return chaves

            cameras: dict[str, int] = {}
            for make, model, n in session.execute(
                select(MediaFile.make, MediaFile.model, func.count(MediaFile.id))
                .where(proprias).group_by(MediaFile.make, MediaFile.model)
            ):
                rotulo = nome_da_camera(make, model) or "desconhecida"
                cameras[rotulo] = cameras.get(rotulo, 0) + n

            return {
                "total": session.scalar(
                    select(func.count(MediaFile.id)).where(proprias)
                ) or 0,
                "lacunas": [
                    {
                        "chave": chave,
                        "rotulo": rotulo,
                        "quantidade": contar(_condicao_lacuna(chave)),
                    }
                    for chave, rotulo in LACUNAS.items()
                ],
                "por_ano": [
                    {"chave": chave or "sem data", "quantidade": n}
                    for chave, n in sorted(
                        session.execute(
                            select(ano_expr, func.count(MediaFile.id))
                            .where(proprias).group_by(ano_expr)
                        ).all(),
                        key=lambda linha: (linha[0] is None, linha[0] or ""),
                        reverse=True,
                    )
                ],
                "por_camera": [
                    {"chave": rotulo, "quantidade": n}
                    for rotulo, n in sorted(
                        cameras.items(), key=lambda kv: (-kv[1], kv[0])
                    )
                ],
                "por_extensao": facetas(MediaFile.extensao),
                "cruzamento_ano_fonte": [
                    {
                        "ano": ano or "sem data",
                        "source_id": source_id,
                        "quantidade": n,
                    }
                    for ano, source_id, n in session.execute(
                        select(
                            ano_expr, MediaFile.source_id,
                            func.count(MediaFile.id),
                        ).where(proprias).group_by(ano_expr, MediaFile.source_id)
                    )
                ],
            }

    def estatisticas(self) -> dict:
        with self._factory() as session:
            def contar(*filtros) -> int:
                return session.scalar(
                    select(func.count(MediaFile.id)).where(*filtros)
                ) or 0

            proprias = _ACERVO
            referencias = _TESTEMUNHA
            return {
                "total": contar(proprias),
                "erros": contar(proprias, MediaFile.erro_leitura.is_not(None)),
                "fontes": session.scalar(select(func.count(Source.id))) or 0,
                # O que o app conhece mas não organiza — referência do
                # iCloud e miniatura de cache. Doam GPS para a correlação.
                "referencias": contar(referencias),
                "referencias_com_gps": contar(
                    referencias, MediaFile.gps_lat.is_not(None)
                ),
            }
