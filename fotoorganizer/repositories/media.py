"""Consultas do catálogo para a UI: paginadas, filtradas e sem estado.

Cada método abre a própria Session (expire_on_commit=False no factory faz
os objetos continuarem legíveis depois de fechada — a UI só lê colunas).
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, aliased, sessionmaker

from fotoorganizer.metadata.base import NAMESPACE_CURADORIA
from fotoorganizer.metadata.camera import nome_da_camera
from fotoorganizer.models import (
    ConfidenceLevel,
    Location,
    MediaFile,
    MediaRole,
    MetadataEntry,
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


def _acervo_ao_alcance():
    """Acervo cuja fonte responde AGORA — o que a grade promete ao dizer
    "organizáveis".

    `MediaFile.organizavel` classifica o registro (é acervo e tem arquivo) e
    não sabe se o disco está montado; quem sabe é `Source.disponivel`. Sem
    esta segunda metade, o filtro "Organizáveis" entregava 2.405 fotos de uma
    pasta que saiu do disco, cada miniatura escrevendo "volume ou pasta fora
    de alcance" — organizáveis que não abrem. Ver D-068.

    Subconsulta em vez de join: `sources` tem dezenas de linhas e o filtro
    entra em toda consulta da biblioteca, inclusive nas agregadas (linha do
    tempo), onde um join a mais mudaria a cardinalidade.
    """
    return and_(
        _ACERVO,
        MediaFile.source_id.not_in(
            select(Source.id).where(Source.disponivel.is_(False))
        ),
    )


# O que a grade mostra. Os dois recortes são complementares: o que não dá
# para organizar agora aparece em "faltantes", nunca em lugar nenhum.
ALCANCES: dict[str, str] = {
    "tudo": "tudo que o app conhece",
    "organizaveis": "acervo com o arquivo ao alcance agora",
    "faltantes": "o resto: sem arquivo, fora de alcance ou não é acervo",
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


def _sob_a_pasta(prefixo: str):
    """A pasta exata e tudo abaixo dela.

    `like` com `%` só no fim, e a barra explícita no segundo termo: sem ela
    `/Volumes/photo` casaria com `/Volumes/photo-backup`, que é outro disco.

    `escape` porque `_` é curinga de um caractere em SQL e pasta com
    underscore é regra, não exceção neste acervo (`2025_05_24`) — sem escapar,
    `/fotos/2025_05_24` casaria também com `/fotos/2025X05X24`.
    """
    limpo = prefixo.rstrip("/")
    seguro = limpo.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return or_(
        MediaFile.pasta == limpo,
        MediaFile.pasta.like(f"{seguro}/%", escape="\\"),
    )


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
    # --- facetas que funcionam sem pixel ------------------------------------
    # Este acervo tem ~95% de registros sem arquivo legível (D-028): busca
    # semântica e reconhecimento alcançam a minoria. O que alcança TUDO é o
    # metadado — câmera, lugar e o que alguém escreveu sobre a foto.
    #
    # `camera` casa contra make e model juntos, não contra uma coluna: o dono
    # pensa "a 5D", não "Canon" + "Canon EOS 5D Mark III".
    camera: str | None = None
    pais: str | None = None
    cidade: str | None = None
    # Palavra-chave do namespace unificado — a mesma que o `.lrcat` e o `.xmp`
    # alimentam sem duplicar (`metadata/base.py:NAMESPACE_CURADORIA`).
    palavra_chave: str | None = None
    # Prefixo de pasta: recorta a grade pela árvore do disco. Casa a pasta
    # exata e tudo abaixo dela — clicar em `/Volumes/photo/2019` mostra o
    # conteúdo direto e o dos meses dentro.
    pasta: str | None = None


class MediaRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._factory = session_factory

    def _query(self, filters: MediaFilters):
        # Testemunhas ficam fora da biblioteca visível, das contagens e de
        # qualquer filtro. Existem só para doar GPS e horário à correlação.
        # Junto delas fica o acervo cuja fonte não responde: é foto do dono,
        # e mesmo assim não há o que abrir, revisar ou copiar agora.
        if filters.alcance == "organizaveis":
            stmt = select(MediaFile).where(_acervo_ao_alcance())
        elif filters.alcance == "faltantes":
            stmt = select(MediaFile).where(~_acervo_ao_alcance())
        else:
            stmt = select(MediaFile)
        if filters.busca:
            like = f"%{filters.busca}%"
            # Nome, caminho — e a curadoria. Procurar "Pantanal" e não achar
            # a foto que alguém etiquetou como Pantanal é a busca falhando
            # justamente onde o metadado é mais confiável que o nome de
            # arquivo, que na maioria do acervo é `IMG_1234`.
            stmt = stmt.where(or_(
                MediaFile.nome.ilike(like),
                MediaFile.caminho.ilike(like),
                MediaFile.id.in_(
                    select(MetadataEntry.media_id).where(
                        MetadataEntry.namespace == NAMESPACE_CURADORIA,
                        MetadataEntry.valor.ilike(like),
                    )
                ),
            ))
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
        if filters.camera:
            # Contra make e model juntos: o dono pensa "a 5D", não "Canon" +
            # "Canon EOS 5D Mark III". `coalesce` porque metade do acervo tem
            # um dos dois nulo, e `NULL || 'texto'` em SQL é NULL — o mesmo
            # defeito que apagava o caminho do Lightroom.
            alvo = func.coalesce(MediaFile.make, "") + " " + func.coalesce(
                MediaFile.model, ""
            )
            stmt = stmt.where(alvo.ilike(f"%{filters.camera}%"))
        if filters.pais or filters.cidade:
            lugar = select(Location.id)
            if filters.pais:
                lugar = lugar.where(Location.pais.ilike(f"%{filters.pais}%"))
            if filters.cidade:
                lugar = lugar.where(Location.cidade.ilike(f"%{filters.cidade}%"))
            stmt = stmt.where(MediaFile.location_id.in_(lugar))
        if filters.palavra_chave:
            stmt = stmt.where(MediaFile.id.in_(
                select(MetadataEntry.media_id).where(
                    MetadataEntry.namespace == NAMESPACE_CURADORIA,
                    MetadataEntry.chave == "palavra_chave",
                    MetadataEntry.valor.ilike(f"%{filters.palavra_chave}%"),
                )
            ))
        if filters.pasta:
            stmt = stmt.where(_sob_a_pasta(filters.pasta))
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

    def cameras(self, limite: int = 60) -> list[dict]:
        """Câmeras do acervo, da mais usada para a menos.

        Com contagem porque a lista sozinha não ajuda a escolher: num acervo
        de doze câmeras, três respondem por 90% das fotos e as outras nove são
        celulares de outras pessoas que mandaram foto por mensagem.
        """
        with self._factory() as session:
            linhas = session.execute(
                select(MediaFile.make, MediaFile.model, func.count())
                .where(or_(
                    MediaFile.make.is_not(None), MediaFile.model.is_not(None)
                ))
                .group_by(MediaFile.make, MediaFile.model)
                .order_by(func.count().desc())
                .limit(limite)
            )
            saida = []
            for make, model, quantidade in linhas:
                nome = nome_da_camera(make, model)
                if nome:
                    saida.append({"nome": nome, "quantidade": quantidade})
            return saida

    def paises(self) -> list[dict]:
        with self._factory() as session:
            linhas = session.execute(
                select(Location.pais, func.count(MediaFile.id))
                .join(MediaFile, MediaFile.location_id == Location.id)
                .where(Location.pais.is_not(None))
                .group_by(Location.pais)
                .order_by(func.count(MediaFile.id).desc())
            )
            return [{"nome": p, "quantidade": n} for p, n in linhas]

    def palavras_chave(self, limite: int = 80) -> list[dict]:
        """O que alguém escreveu sobre as fotos, do mais frequente ao menos.

        Vem do namespace unificado, então "Selected" aparece uma vez mesmo
        chegando pelo `.lrcat` e pelo `.xmp` ao mesmo tempo.

        Os níveis intermediários de hierarquia entram junto do caminho
        completo ("Viagens|2019|Patagônia" e "Patagônia"), o que é
        proposital: quem filtra procura o termo, quem lê a lista quer ver a
        organização que existia.
        """
        with self._factory() as session:
            linhas = session.execute(
                select(MetadataEntry.valor, func.count(func.distinct(
                    MetadataEntry.media_id
                )))
                .where(
                    MetadataEntry.namespace == NAMESPACE_CURADORIA,
                    MetadataEntry.chave == "palavra_chave",
                )
                .group_by(MetadataEntry.valor)
                .order_by(func.count(func.distinct(
                    MetadataEntry.media_id
                )).desc())
                .limit(limite)
            )
            return [{"nome": v, "quantidade": n} for v, n in linhas]

    def arvore_de_pastas(
        self, prefixo: str | None = None, limite: int = 400
    ) -> dict:
        """Um nível da árvore de pastas: os filhos diretos de `prefixo`.

        Existe porque este acervo responde melhor à pergunta "onde isso
        estava?" do que a "quando isso foi tirado?". São 225.914 registros num
        volume que não está montado — para eles a pasta de origem é a única
        pista de lugar que sobrou, e é ela que o `.lrcat` guarda mesmo com o
        disco na gaveta.

        Um nível por chamada, não a árvore inteira: 371 mil registros geram
        dezenas de milhares de pastas, e mandar tudo de uma vez para a
        interface montar a árvore seria repetir na rede o erro que a grade
        virtualizada existe para evitar.

        As contagens são recursivas — a pasta mostra quantas fotos há nela e
        abaixo dela. Contagem só do nível direto faria uma pasta de ano
        aparecer com zero, que é o tipo de número que faz o usuário achar que
        o app perdeu as fotos dele.
        """
        raiz = (prefixo or "").rstrip("/")
        with self._factory() as session:
            if raiz:
                condicao = _sob_a_pasta(raiz)
                # O nome do filho direto é o que vem até a próxima barra
                # depois do prefixo. Resolvido em SQL para não trazer 371 mil
                # caminhos à memória só para cortar string.
                resto = func.substr(MediaFile.pasta, len(raiz) + 2)
            else:
                condicao = MediaFile.pasta.is_not(None)
                # Na raiz, o caminho absoluto começa com "/" e o primeiro
                # segmento sairia vazio. Pular a barra inicial só quando ela
                # existe: nem toda `pasta` do catálogo é absoluta — uma
                # referência de catálogo externo pode ter caminho relativo.
                resto = func.substr(
                    MediaFile.pasta,
                    func.iif(func.substr(MediaFile.pasta, 1, 1) == "/", 2, 1),
                )
            fim = func.instr(resto, "/")
            nome = func.substr(
                resto, 1, func.iif(fim > 0, fim - 1, func.length(resto))
            )
            # "Alcançável" tem TRÊS condições, não duas. Faltava a fonte
            # estar montada: sem ela, uma pasta em volume desligado aparecia
            # com 225 mil "alcançáveis" ao lado do Panorama dizendo "fora de
            # alcance — volume não montado". Dois números contraditórios na
            # mesma tela é pior que número nenhum.
            fontes_fora = select(Source.id).where(Source.disponivel.is_(False))
            linhas = session.execute(
                select(nome, func.count(), func.count(MediaFile.id).filter(
                    MediaFile.arquivo_offline.is_(False),
                    MediaFile.arquivo_ausente.is_(False),
                    MediaFile.source_id.not_in(fontes_fora),
                ))
                .where(condicao, MediaFile.pasta != "")
                .group_by(nome)
                .order_by(nome)
                .limit(limite)
            )
            filhos = []
            for nome_filho, total, alcancaveis in linhas:
                if not nome_filho:
                    continue
                filhos.append({
                    "nome": nome_filho,
                    # Na raiz o "/" foi pulado para o segmento não sair vazio;
                    # o caminho devolvido tem de voltar a ser absoluto, senão
                    # o próximo nível não casa com nada.
                    "caminho": f"{raiz}/{nome_filho}" if raiz else f"/{nome_filho}",
                    "total": total,
                    "alcancaveis": alcancaveis,
                })
            aqui = session.scalar(
                select(func.count()).select_from(MediaFile)
                .where(MediaFile.pasta == raiz)
            ) if raiz else 0
            return {"caminho": raiz, "aqui": aqui or 0, "filhos": filhos}

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
