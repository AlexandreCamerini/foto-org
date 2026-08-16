"""Motor de evidências e sugestões (modelo v4 — docs/AGRUPAMENTO.md).

Fotos são agrupadas em sessões temporais; cada sessão passa por uma
cascata determinística (pasta de categoria → keyword de evento → país na
pasta → deslocamento GPS → estadia geocodificada → nome de álbum) e, sem
veredito, pelo advisor LLM opt-in. Cada inferência vira evidência com
origem, confiança e justificativa; a confiança final é o elo mais fraco.
Decisões do usuário são preservadas na regeneração.
"""

from __future__ import annotations

import logging
from bisect import bisect_left, bisect_right
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from fotoorganizer.classification.advisor import ClassificationAdvisor, ClusterInfo
from fotoorganizer.classification.confidence import (
    SCORES_REFERENCIA,
    elo_mais_fraco,
    nivel_para_score,
)
from fotoorganizer.classification.tipo_imagem import ROTULOS as ROTULOS_TIPO
from fotoorganizer.classification.tipo_imagem import classificar as classificar_tipo
from fotoorganizer.classification.tipo_imagem import FOTO as TIPO_FOTO
from fotoorganizer.classification.templates import (
    DESTINO_NAO_CLASSIFICADO,
    DESTINO_NAO_FOTO,
    TEMPLATE_PADRAO,
    render_destino,
)
from fotoorganizer.geolocation import LocationResolver, extrair_hierarquia_da_pasta
from fotoorganizer.geolocation.resolver import cache_key as _chave_de_coordenada
from fotoorganizer.grouping.datas import (
    data_no_caminho,
    data_no_nome,
    rotulo_mes,
)
from fotoorganizer.geolocation.folder_names import _normalizar
from fotoorganizer.geolocation.timezones import TZ_POR_PAIS
from fotoorganizer.metadata.base import NAMESPACE_CURADORIA
from fotoorganizer.metadata.camera import nome_da_camera
from fotoorganizer.geolocation.home import detectar_casa, distancia_km
from fotoorganizer.grouping import (
    FotoRef,
    Heranca,
    agrupar_viagens,
    dividir_por_transicao_casa,
    estimar_offsets,
    herdar_gps,
)
from fotoorganizer.grouping.eventos_temporais import Momento, dividir_sessao
from fotoorganizer.grouping.albuns import cameras_do_catalogo
from fotoorganizer.grouping.classifier import (
    ConfigClassificacao,
    DadosSessao,
    classificar_sessao,
)
from fotoorganizer.grouping.temporal import ViagemDraft
from fotoorganizer.models import (
    Event,
    Evidence,
    MediaFile,
    MetadataEntry,
    Suggestion,
    SuggestionStatus,
    Trip,
    suggestion_evidence,
)

log = logging.getLogger(__name__)

VERSAO_LOGICA = "4.1"


def _delta_legivel(delta: timedelta) -> str:
    segundos = int(delta.total_seconds())
    if segundos < 60:
        return f"{segundos}s"
    return f"{segundos // 60}min"


def _camera_legivel(media: MediaFile | None) -> str:
    if media is None:
        return ""
    partes = nome_da_camera(media.make, media.model)
    return f" ({partes})" if partes else ""

_CATEGORIAS_PASTA = {"viagens": "Viagens", "viagem": "Viagens",
                     "familia": "Família", "família": "Família",
                     "eventos": "Eventos", "evento": "Eventos"}
_MIN_FOTOS_SESSAO = 2
# Campos que dão nome ao destino. Sem nenhum deles, sobra só a data.
_CAMPOS_QUE_NOMEIAM = ("categoria", "viagem", "evento", "pais", "regiao",
                       "cidade")
# Lugar: entra na sugestão mesmo quando não vira pasta — é a resposta a
# "por que aqui?" e a única superfície da herança de GPS entre câmeras.
_CAMPOS_DE_LUGAR = ("pais", "regiao", "cidade")
# Como cada granularidade se lê numa frase (D-025).
_GRANULARIDADE = {"pais": "o país", "regiao": "a região", "cidade": "a cidade"}
# Fotos geocodificadas mínimas para um país contar como perna da viagem —
# uma escala de aeroporto com 1-2 fotos não nomeia a viagem.
_MIN_FOTOS_PERNA = 3


# Como o catálogo externo se chama numa frase, por namespace do importador.
_FONTES_DE_ALBUM = {"apple": "Apple Fotos", "lightroom": "Lightroom"}


def _carregar_curadoria(session: Session) -> dict[int, tuple[str, ...]]:
    """Palavras-chave humanas (XMP/IPTC, `NAMESPACE_CURADORIA`) por foto.

    Uma consulta para o catálogo inteiro, não uma por foto — mesmo motivo
    de `_IndiceDeAlbuns`: N+1 sobre `metadata_entries` não escala. Hoje só
    alimenta `_categoria` (regra 4, D-051); usar essas palavras para
    inferir LUGAR fica para quando esse uso existir de fato (mesmo domínio
    de `classification/lexico.py`, não duplicado aqui).
    """
    stmt = select(MetadataEntry.media_id, MetadataEntry.valor).where(
        MetadataEntry.namespace == NAMESPACE_CURADORIA,
        MetadataEntry.chave == "palavra_chave",
    )
    por_media: dict[int, list[str]] = {}
    for media_id, valor in session.execute(stmt):
        if valor:
            por_media.setdefault(media_id, []).append(valor)
    return {media_id: tuple(valores) for media_id, valores in por_media.items()}


class _IndiceDeAlbuns:
    """Nomeações de álbum na linha do tempo, consultáveis por período.

    O acervo real tem 27.226 linhas de álbum e nenhuma delas está numa foto
    organizável: 100% vive em registros SINAL do Apple Fotos e do Lightroom,
    sem arquivo local (D-028). O vínculo com a sessão é, portanto, o mesmo
    da herança de GPS — contemporaneidade entre fontes: um álbum nomeia uma
    sessão quando as fotos dele caem dentro do período dela.

    Carregado uma vez por geração e consultado por bisseção: uma consulta
    por sessão levaria a um N+1 sobre a maior tabela do catálogo.
    """

    __slots__ = ("_quando", "_linhas", "_fontes", "cameras")

    def __init__(self, session: Session) -> None:
        # Câmeras do catálogo inteiro (inclusive as referências): é o que
        # impede "Canon EOS 5D Mark IV" — o maior álbum deste acervo — de
        # virar nome de viagem.
        self.cameras = cameras_do_catalogo(
            session.execute(
                select(MediaFile.make, MediaFile.model)
                .where(MediaFile.model.is_not(None))
                .distinct()
            )
        )
        stmt = (
            select(MediaFile.data_capturada, MediaFile.mtime,
                   MetadataEntry.valor, MetadataEntry.namespace)
            .join(MetadataEntry, MetadataEntry.media_id == MediaFile.id)
            .where(MetadataEntry.chave == "album")
        )
        linhas = []
        for data, mtime, album, namespace in session.execute(stmt):
            quando = data or mtime
            if quando is None or not album:
                continue
            linhas.append((quando, album, namespace))
        linhas.sort(key=lambda t: t[0])
        self._quando = [t[0] for t in linhas]
        self._linhas = linhas
        self._fontes = {t[2] for t in linhas}

    def __len__(self) -> int:
        return len(self._linhas)

    @property
    def fonte_legivel(self) -> str:
        nomes = sorted(
            _FONTES_DE_ALBUM.get(ns, ns) for ns in self._fontes
        )
        return " / ".join(nomes) if nomes else "catálogo externo"

    def contagens(self, inicio: datetime, fim: datetime) -> tuple[tuple[str, int], ...]:
        """{álbum: fotos dele dentro de [inicio, fim]} como tupla ordenada.

        Sem folga nas bordas: a régua é o período que o agrupamento
        temporal já decidiu, não uma janela nova inventada aqui.
        """
        i = bisect_left(self._quando, inicio)
        j = bisect_right(self._quando, fim)
        contagem: Counter = Counter()
        for _quando, album, _ns in self._linhas[i:j]:
            contagem[album] += 1
        return tuple(sorted(contagem.items()))


@dataclass(slots=True)
class _Draft:
    campo: str
    origem: str
    valor: str
    justificativa: str
    # Herança de GPS modula o score da origem pelo Δt (fator ≤ 1.0).
    score_override: float | None = None

    @property
    def score(self) -> float:
        if self.score_override is not None:
            return self.score_override
        return SCORES_REFERENCIA[self.origem]


@dataclass(slots=True)
class _Sessao:
    draft: ViagemDraft
    tipo: str = "neutra"            # viagem | evento | neutra
    rotulo: str | None = None       # nome da viagem ou do evento
    origem: str = "agrupamento"
    # Origem só do nome — pode divergir de `origem` quando o rótulo veio de
    # um álbum de catálogo externo e o tipo veio do GPS.
    origem_do_rotulo: str = "agrupamento"
    justificativa: str = ""
    categoria: str | None = None    # só quando vinda do advisor
    pais_dominante: str | None = None
    lugares: tuple[str, ...] = ()
    trip_id: int | None = None
    event_id: int | None = None

    @property
    def duracao(self) -> timedelta:
        return self.draft.fim - self.draft.inicio

    def periodo_curto(self) -> str:
        inicio = self.draft.inicio.strftime("%d-%m")
        fim = self.draft.fim.strftime("%d-%m")
        return f"Viagem de {inicio}" if inicio == fim else f"Viagem de {inicio} a {fim}"


class SuggestionEngine:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        resolver: LocationResolver | None = None,
        template: str = TEMPLATE_PADRAO,
        advisor: ClassificationAdvisor | None = None,
        config: ConfigClassificacao = ConfigClassificacao(),
        lexico: dict[str, str] | None = None,
    ) -> None:
        self._factory = session_factory
        self._resolver = resolver
        self._template = template
        self._advisor = advisor
        self._config = config
        # O que cada nome de pasta significa. Vazio quando o léxico está
        # desligado (padrão) — e aí a cascata decide como sempre decidiu.
        self._tipos_de_nome: tuple[tuple[str, str], ...] = tuple(
            (lexico or {}).items()
        )

    # -- API ----------------------------------------------------------------
    def gerar(self) -> dict:
        with self._factory() as session:
            midias = list(session.scalars(select(MediaFile)))
            decididas = self._midias_com_decisao(session)
            por_id = {m.id: m for m in midias}
            curadoria = _carregar_curadoria(session)

            # Correlação entre fontes: fotos sem GPS herdam localização de
            # fotos de outra origem tiradas a minutos de distância. Entram
            # TODAS as mídias, inclusive as referências sem arquivo local —
            # são elas que trazem GPS de celular numa biblioteca em iCloud.
            herancas = self._correlacionar(midias)
            self._persistir_herancas(midias, herancas)

            # Geocodifica TODAS as fotos com coordenada (própria ou
            # herdada) aqui — antes de sessão/categoria rodarem, não
            # dentro delas. Regra 1 do diagnóstico geo-first (D-051/D-052):
            # mapear localização primeiro. `LocationResolver.resolve` já é
            # cache-keyed por coordenada (~110 m, geolocation/resolver.py),
            # então isto não duplica trabalho caro — garante que TODA foto
            # com coordenada tem `location_id` resolvido cedo, inclusive a
            # que já tem sugestão decidida e por isso nunca passa por
            # `_evidencias_geo` (que só roda para quem ainda vai ganhar
            # sugestão nesta rodada).
            self._resolver_locations(session, midias)

            # Daqui em diante só o que o usuário pode ver e organizar. Uma
            # referência não tem arquivo para copiar; uma miniatura de cache
            # tem arquivo e ainda assim não é acervo dele — as duas doaram o
            # que sabiam na correlação acima e param aqui.
            organizaveis = [m for m in midias if m.organizavel]
            orfas = self._descartar_sugestoes_orfas(session)

            sessoes, sessao_da_media = self._montar_sessoes(
                session, organizaveis, herancas
            )
            self._persistir_agrupamentos(
                session, organizaveis, midias, sessoes, sessao_da_media
            )

            # tz_estimado segue o mesmo padrão de recálculo incondicional
            # dos campos gps_*_estimado (`_persistir_herancas`, acima):
            # roda para TODA mídia organizável, inclusive a que já tem
            # sugestão decidida e por isso nunca passa pelo loop abaixo
            # (CR-01 — antes ficava congelado no valor da última rodada em
            # que a sugestão ainda estava pendente).
            self._atualizar_tz_estimado(
                session, organizaveis, sessao_da_media, herancas, por_id,
            )

            geradas = 0
            for media in organizaveis:
                if media.id in decididas:
                    continue
                drafts = self._evidencias_para(
                    session, media, sessao_da_media.get(media.id),
                    herancas, por_id, curadoria.get(media.id, ()),
                )
                self._persistir_sugestao(session, media, drafts)
                geradas += 1
                if geradas % 500 == 0:
                    session.commit()

            session.commit()
            return {
                "sugestoes": geradas,
                "viagens": sum(1 for s in sessoes if s.tipo == "viagem"),
                "eventos": sum(1 for s in sessoes if s.tipo == "evento"),
                "herancas_gps": len(herancas),
                "preservadas": len(decididas),
                "descartadas": orfas,
            }

    @staticmethod
    def _persistir_herancas(midias, herancas: dict[int, Heranca]) -> None:
        """Grava a coordenada herdada — quem doou e a que distância no tempo.

        Antes isto vivia só em memória durante a geração: o lugar resolvido
        virava `location_id` e a coordenada se perdia, então a foto seguia
        contando como "sem coordenada" em toda consulta. Reescreve a cada
        rodada porque a herança depende do conjunto: uma foto nova com GPS
        pode virar doadora melhor, e uma fonte removida invalida a antiga.
        """
        for media in midias:
            heranca = herancas.get(media.id)
            if heranca is None or media.gps_lat is not None:
                # Sem doador, ou a foto passou a ter coordenada própria: a
                # estimativa antiga não vale mais.
                media.gps_lat_estimado = None
                media.gps_lon_estimado = None
                media.gps_estimado_de_id = None
                media.gps_estimado_delta_s = None
                continue
            media.gps_lat_estimado = heranca.lat
            media.gps_lon_estimado = heranca.lon
            media.gps_estimado_de_id = heranca.doador_id
            media.gps_estimado_delta_s = int(heranca.delta.total_seconds())

    def _resolver_locations(self, session: Session, midias) -> None:
        """Resolve e grava `location_id` para toda foto com coordenada
        efetiva (própria ou herdada — `MediaFile.coordenada`), chamado
        logo após `_persistir_herancas`, antes de sessão/categoria.

        Não substitui a resolução que `_evidencias_geo` ainda faz por
        conta própria mais adiante — aquela decide QUAIS CAMPOS expor por
        granularidade (`heranca.fator_de`), o que continua exigindo o
        objeto `Heranca`, não só o `Location` resolvido. Rodar aqui
        também é redundante para quem passa pelos dois caminhos na mesma
        geração, mas o cache por coordenada em `LocationResolver.resolve`
        faz da segunda chamada uma leitura, não um recálculo.

        Memoiza por `cache_key` NESTE loop, não só na tabela `locations`:
        sem isso, uma viagem de 500 fotos na mesma coordenada arredondada
        vira 500 SELECTs em vez de 1 — achado da revisão com olhos
        frescos antes do commit, antes só a tabela cobria repetição
        ENTRE gerações, não dentro da mesma.
        """
        if self._resolver is None:
            return
        resolvidos: dict[str, int | None] = {}
        for media in midias:
            coordenada = media.coordenada
            if coordenada is None:
                continue
            chave = _chave_de_coordenada(*coordenada)
            if chave not in resolvidos:
                location = self._resolver.resolve(session, *coordenada)
                resolvidos[chave] = location.id if location is not None else None
            # Grava sempre, inclusive None: se a coordenada deixou de
            # resolver nesta rodada (doadora mudou, provider rejeitou o
            # ponto), o location_id de uma coordenada antiga não pode
            # sobreviver — sem isto a mídia ficava presa a um país que
            # ela não tem mais (WR-01).
            media.location_id = resolvidos[chave]

    def _pais_efetivo(self, session: Session, media: MediaFile,
                      sessao: "_Sessao | None",
                      herancas: dict[int, Heranca],
                      por_id: dict[int, MediaFile]) -> str | None:
        """País efetivo desta mídia, pela MESMA cascata de `_evidencias_geo`
        (GPS próprio > GPS herdado > pasta > vizinhança da sessão), mas sem
        gravar Evidence/Suggestion — usado por `_atualizar_tz_estimado`
        (CR-01) para recalcular `tz_estimado` incondicionalmente, inclusive
        para mídia com sugestão já decidida (que nunca chama
        `_evidencias_geo`). Duplicada em vez de compartilhada de propósito:
        reaproveitar `_evidencias_geo` aqui arriscaria mudar o texto de
        justificativa/score da evidência existente, fora do escopo deste
        fix. Mantém o mesmo critério de parada de cada ramo do original:
        GPS próprio decide sozinho assim que resolve (mesmo que
        `location.pais` seja `None`), herdado só decide quando a janela de
        tempo sustenta o campo país (`heranca.fator_de('pais')`)."""
        if media.gps_lat is not None and self._resolver is not None:
            location = self._resolver.resolve(session, media.gps_lat, media.gps_lon)
            if location is not None:
                return location.pais

        heranca = herancas.get(media.id)
        if heranca is not None and self._resolver is not None:
            location = self._resolver.resolve(session, heranca.lat, heranca.lon)
            if location is not None and heranca.fator_de("pais") is not None:
                return location.pais

        hierarquia = extrair_hierarquia_da_pasta(media.pasta)
        if hierarquia.pais:
            return hierarquia.pais

        if sessao is not None and sessao.pais_dominante:
            return sessao.pais_dominante

        return None

    def _atualizar_tz_estimado(self, session: Session, organizaveis,
                               sessao_da_media: dict[int, "_Sessao"],
                               herancas: dict[int, Heranca],
                               por_id: dict[int, MediaFile]) -> None:
        """tz_estimado segue o mesmo padrão de recálculo incondicional dos
        campos gps_*_estimado em `_persistir_herancas`: roda para TODA mídia
        organizável a cada `gerar()`, inclusive a que já tem sugestão
        decidida (CR-01 — antes só era recalculado dentro de
        `_persistir_sugestao`, que é pulada para mídia decidida, e o valor
        ficava congelado para sempre)."""
        for media in organizaveis:
            pais = self._pais_efetivo(
                session, media, sessao_da_media.get(media.id), herancas, por_id,
            )
            media.tz_estimado = TZ_POR_PAIS.get(pais) if pais else None

    # -- correlação entre fontes ---------------------------------------------
    @staticmethod
    def _correlacionar(midias) -> dict[int, Heranca]:
        refs = [
            FotoRef(
                media_id=m.id, source_id=m.source_id,
                quando=(m.data_capturada or m.mtime),
                camera=(m.make, m.model),
                lat=m.gps_lat, lon=m.gps_lon,
                hash_rapido=m.hash_rapido,
                hash_perceptual=m.hash_perceptual,
                hora_do_arquivo=m.data_capturada is None,
            )
            for m in midias
            if (m.data_capturada or m.mtime) is not None
        ]
        offsets = estimar_offsets(refs)
        if offsets:
            log.info("correlação: deriva de relógio estimada para %d câmeras",
                     len(offsets))
        return {h.media_id: h for h in herdar_gps(refs, offsets)}

    @staticmethod
    def _coords(media, herancas: dict[int, Heranca]) -> tuple[float, float] | None:
        """Coordenadas efetivas: GPS próprio, senão o herdado."""
        if media.gps_lat is not None:
            return media.gps_lat, media.gps_lon
        heranca = herancas.get(media.id)
        if heranca is not None:
            return heranca.lat, heranca.lon
        return None

    # -- sessões e cascata ----------------------------------------------------
    def _montar_sessoes(
        self, session: Session, midias, herancas: dict[int, Heranca]
    ) -> tuple[list[_Sessao], dict[int, _Sessao]]:
        por_id = {m.id: m for m in midias}
        itens = [
            (m.id, m.data_capturada or m.mtime)
            for m in midias
            if (m.data_capturada or m.mtime) is not None
        ]
        # Casa: só GPS real — coordenadas herdadas repetem as dos doadores
        # e inflariam artificialmente a célula modal.
        casa = detectar_casa([
            (m.gps_lat, m.gps_lon) for m in midias if m.gps_lat is not None
        ])
        drafts = agrupar_viagens(itens)
        if casa is not None:
            # Viagens coladas: o gap temporal não separa duas viagens com
            # menos de 3 dias em casa no meio — a transição casa↔fora sim.
            drafts = [
                sub for d in drafts
                for sub in self._dividir_draft(d, por_id, casa, herancas)
            ]
        drafts = [d for d in drafts if d.n_fotos >= _MIN_FOTOS_SESSAO]

        albuns = _IndiceDeAlbuns(session)
        if albuns:
            log.info("nomeação: %d marcações de álbum disponíveis (%s)",
                     len(albuns), albuns.fonte_legivel)

        sessoes: list[_Sessao] = []
        sessao_da_media: dict[int, _Sessao] = {}
        for draft in drafts:
            membros = [por_id[i] for i in draft.media_ids]
            if any(m.data_capturada for m in membros):
                sessao = self._classificar(
                    session, _Sessao(draft=draft), membros, casa, herancas,
                    albuns,
                )
                if sessao.tipo == "neutra" and self._advisor is not None:
                    self._consultar_advisor(sessao, membros)
            else:
                # Nenhum membro tem data de captura: o que sobrou é mtime, a
                # data em que o arquivo chegou ao disco. Agrupar por ela cria
                # uma "viagem" no dia do scan — captura de tela e arquivo
                # recuperado viram passeio. A sessão fica neutra; a foto
                # continua catalogada e cai no ramo de não classificadas.
                sessao = _Sessao(draft=draft)
            sessoes.append(sessao)

        # Uma sessão não-viagem pode conter mais de um acontecimento: o
        # agrupamento corta onde passam 3 dias, então aniversário de manhã e
        # show à noite chegam aqui juntos. Subdividir precisa da classificação
        # — viagem é uma pasta só (commit 9670765) — por isso vem depois dela,
        # e os pedaços são reclassificados: cada um tem duração e lugar
        # próprios, e um deles pode nomear onde o conjunto não nomeava.
        sessoes = [
            final
            for sessao in sessoes
            for final in self._subdividir(
                session, sessao, por_id, casa, herancas, albuns
            )
        ]

        for sessao in sessoes:
            for media_id in sessao.draft.media_ids:
                sessao_da_media[media_id] = sessao
        return sessoes, sessao_da_media

    def _subdividir(self, session: Session, sessao: _Sessao, por_id, casa,
                    herancas: dict[int, Heranca],
                    albuns: "_IndiceDeAlbuns") -> list[_Sessao]:
        """A sessão, ou os acontecimentos dentro dela."""
        membros = [por_id[i] for i in sessao.draft.media_ids]
        momentos = [
            Momento(
                m.id, m.data_capturada or m.mtime,
                *(self._coords(m, herancas) or (None, None)),
            )
            for m in membros
            if (m.data_capturada or m.mtime) is not None
        ]
        blocos = dividir_sessao(momentos, e_viagem=sessao.tipo == "viagem")
        if len(blocos) <= 1:
            return [sessao]

        novas: list[_Sessao] = []
        for bloco in blocos:
            membros_do_bloco = [por_id[i] for i in bloco]
            quando = [
                m.data_capturada or m.mtime for m in membros_do_bloco
                if (m.data_capturada or m.mtime) is not None
            ]
            draft = ViagemDraft(inicio=min(quando), fim=max(quando))
            draft.media_ids.extend(bloco)
            novas.append(self._classificar(
                session, _Sessao(draft=draft), membros_do_bloco, casa,
                herancas, albuns,
            ))
        log.info("sessão de %d fotos virou %d acontecimentos",
                 len(membros), len(novas))
        return novas

    def _dividir_draft(self, draft: ViagemDraft, por_id, casa,
                       herancas: dict[int, Heranca]) -> list[ViagemDraft]:
        itens = []
        for media_id in draft.media_ids:
            media = por_id[media_id]
            estado = None
            coords = self._coords(media, herancas)
            if coords is not None:
                estado = (
                    distancia_km(*coords, *casa) <= self._config.raio_casa_km
                )
            itens.append((media_id, media.data_capturada or media.mtime, estado))

        segmentos = dividir_por_transicao_casa(itens)
        if len(segmentos) <= 1:
            return [draft]
        return [
            ViagemDraft(
                inicio=seg[0][1], fim=seg[-1][1],
                media_ids=[media_id for media_id, _ in seg],
            )
            for seg in segmentos
        ]

    def _classificar(self, session: Session, sessao: _Sessao, membros,
                     casa, herancas: dict[int, Heranca],
                     albuns: "_IndiceDeAlbuns") -> _Sessao:
        pastas = tuple(sorted({m.pasta for m in membros}))
        sessao.pais_dominante, sessao.lugares, pernas = self._geo_da_sessao(
            session, membros, herancas
        )

        dist_mediana = None
        if casa is not None:
            coords = [
                self._coords(m, herancas) for m in membros
            ]
            dists = sorted(
                distancia_km(*c, *casa) for c in coords if c is not None
            )
            if dists:
                dist_mediana = dists[len(dists) // 2]

        decisao = classificar_sessao(
            DadosSessao(
                pastas=pastas,
                duracao=sessao.duracao,
                pais_dominante=sessao.pais_dominante,
                dist_mediana_casa_km=dist_mediana,
                periodo_curto=sessao.periodo_curto(),
                paises_no_tempo=pernas,
                albuns=albuns.contagens(sessao.draft.inicio, sessao.draft.fim),
                fonte_dos_albuns=albuns.fonte_legivel,
                cameras=albuns.cameras,
                tipos_de_nome=self._tipos_de_nome,
            ),
            self._config,
        )
        sessao.tipo = decisao.tipo
        sessao.rotulo = decisao.rotulo
        sessao.origem = decisao.origem
        sessao.origem_do_rotulo = decisao.origem_do_rotulo
        sessao.justificativa = decisao.justificativa
        return sessao

    def _geo_da_sessao(
        self, session: Session, membros, herancas: dict[int, Heranca]
    ) -> tuple[str | None, tuple[str, ...], tuple[str, ...]]:
        """(país dominante, lugares, pernas). Pernas = países em ordem
        cronológica de chegada com massa mínima de fotos — ≥ 2 caracterizam
        viagem multi-país. `membros` já vem na ordem temporal da sessão.
        Usa coordenadas efetivas (GPS próprio ou herdado de outra fonte)."""
        if self._resolver is None:
            return None, (), ()
        paises: Counter = Counter()
        ordem_paises: list[str] = []
        lugares: list[str] = []
        for media in membros:
            coords = self._coords(media, herancas)
            if coords is None:
                continue
            location = self._resolver.resolve(session, *coords)
            if location is None:
                continue
            # Coordenada herdada só vale até onde o Δt sustenta (D-025). País
            # aguenta horas; cidade não. Sem este corte, uma foto correlata a
            # 6 h de distância nomearia a viagem com a cidade errada.
            heranca = herancas.get(media.id) if media.gps_lat is None else None
            pode = (lambda campo: heranca.fator_de(campo) is not None) \
                if heranca is not None else (lambda campo: True)
            if location.pais and pode("pais"):
                paises[location.pais] += 1
                if location.pais not in ordem_paises:
                    ordem_paises.append(location.pais)
            cidade = location.cidade if pode("cidade") else None
            lugar = ", ".join(filter(None, [cidade, location.pais]))
            if lugar and lugar not in lugares:
                lugares.append(lugar)
        dominante = paises.most_common(1)[0][0] if paises else None
        pernas = tuple(
            pais for pais in ordem_paises
            if paises[pais] >= _MIN_FOTOS_PERNA
        )
        if len(pernas) < 2:
            pernas = ()
        return dominante, tuple(lugares[:5]), pernas

    def _consultar_advisor(self, sessao: _Sessao, membros) -> None:
        cluster = ClusterInfo(
            pastas=tuple(sorted({m.pasta for m in membros})),
            exemplos_arquivos=tuple(m.nome for m in membros[:8]),
            inicio=sessao.draft.inicio,
            fim=sessao.draft.fim,
            n_fotos=sessao.draft.n_fotos,
            lugares=sessao.lugares,
        )
        resultado = self._advisor.classificar(cluster)
        if resultado is None:
            return
        sessao.categoria = resultado.categoria
        # Simétrico ao caminho de Eventos logo abaixo: sem isto, um "Viagens"
        # do LLM só preenchia `categoria` (texto de fallback da pasta,
        # `_categoria` mais abaixo) e nunca criava/juntava um Trip de
        # verdade — a sessão nunca aparecia na aba Viagens. Medido em
        # docs/AVALIACAO_UX.md, seção C.4.
        if resultado.categoria == "Viagens":
            sessao.tipo = "viagem"
            # Nome de viagem do LLM manda; sem ele, o país já geocodificado
            # da sessão (sempre calculado antes do advisor ser consultado);
            # sem os dois, o período por extenso — nunca um rótulo vazio.
            sessao.rotulo = (
                resultado.evento or sessao.pais_dominante
                or sessao.periodo_curto()
            )
            sessao.origem = sessao.origem_do_rotulo = "llm"
            sessao.justificativa = (
                f"LLM (apenas metadados): {resultado.justificativa}"
            )
        elif resultado.evento:
            sessao.tipo = "evento"
            sessao.rotulo = resultado.evento
            sessao.origem = sessao.origem_do_rotulo = "llm"
            sessao.justificativa = (
                f"LLM (apenas metadados): {resultado.justificativa}"
            )

    # -- persistência de viagens/eventos -----------------------------------
    def _persistir_agrupamentos(self, session: Session, midias, todas,
                                sessoes: list[_Sessao],
                                sessao_da_media: dict[int, _Sessao]) -> None:
        # Deriváveis (sem edição do usuário no MVP): regenera tudo.
        #
        # A limpeza percorre TODAS as mídias, não só as organizáveis: uma que
        # foi rebaixada a testemunha guarda o trip_id da geração anterior, e
        # o DELETE abaixo esbarraria na chave estrangeira dela.
        for media in todas:
            media.trip_id = None
            media.event_id = None
        session.execute(delete(Trip))
        session.execute(delete(Event))
        session.flush()

        for sessao in sessoes:
            if sessao.tipo == "viagem":
                trip = Trip(nome=sessao.rotulo, inicio=sessao.draft.inicio,
                            fim=sessao.draft.fim, metodo=sessao.origem)
                session.add(trip)
                session.flush()
                sessao.trip_id = trip.id
            elif sessao.tipo == "evento":
                evento = Event(nome=sessao.rotulo, tipo="evento",
                               inicio=sessao.draft.inicio,
                               fim=sessao.draft.fim, metodo=sessao.origem)
                session.add(evento)
                session.flush()
                sessao.event_id = evento.id

        for media in midias:
            sessao = sessao_da_media.get(media.id)
            if sessao is not None:
                media.trip_id = sessao.trip_id
                media.event_id = sessao.event_id
        session.flush()

    # -- evidências -----------------------------------------------------------
    def _evidencias_para(self, session: Session, media: MediaFile,
                         sessao: _Sessao | None,
                         herancas: dict[int, Heranca],
                         por_id: dict[int, MediaFile],
                         palavras_chave: tuple[str, ...] = ()) -> list[_Draft]:
        drafts: list[_Draft] = []

        # Foto de câmera ou imagem que só passou pelo disco? Decide antes de
        # tudo: o que não é foto não deve ser organizado por viagem, e a
        # justificativa precisa aparecer junto do resto.
        veredito = classificar_tipo(
            nome=media.nome, pasta=media.pasta, extensao=media.extensao or "",
            largura=media.largura, altura=media.altura,
            make=media.make, model=media.model, lente=media.lente,
            # GPS LIDO do arquivo, não o efetivo: a coordenada herdada é
            # justamente o que uma captura de tela feita no meio da viagem
            # ganha das fotos vizinhas. Usar a efetiva aqui transformaria a
            # herança em atestado de que o arquivo veio de uma câmera.
            tem_gps=media.gps_lat is not None,
        )
        # O detector sempre opina — a opinião é reescrita a cada geração,
        # porque um arquivo reprocessado pode ganhar EXIF. O que ele NUNCA
        # toca é `tipo_confirmado`: aquilo é palavra do usuário.
        media.tipo_imagem = veredito.tipo
        if media.tipo_confirmado is not None:
            if media.tipo_confirmado != TIPO_FOTO:
                drafts.append(_Draft(
                    "tipo", "usuario", ROTULOS_TIPO[media.tipo_confirmado],
                    "classificado por você", score_override=1.0,
                ))
        elif not veredito.e_foto:
            drafts.append(_Draft(
                "tipo", "arquivo", ROTULOS_TIPO[veredito.tipo],
                veredito.justificativa + " — a confirmar",
                score_override=veredito.score,
            ))

        # Cascata da data: EXIF manda; sem ele, a data carimbada no NOME
        # (WhatsApp, câmera de celular, captura de tela) vale mais que o
        # mtime — o nome nasce com o arquivo, o mtime muda a cada cópia.
        # Uma evidência só de data por foto: é ela que vira o {ano} do
        # destino, e duas testemunhas do mesmo campo disputariam a vaga.
        data_nome = data_no_nome(media.nome) \
            if media.data_capturada is None else None
        if media.data_capturada is not None:
            drafts.append(_Draft(
                "data", "exif", media.data_capturada.isoformat(),
                "data de captura lida do EXIF (DateTimeOriginal)",
            ))
        elif data_nome is not None:
            drafts.append(_Draft(
                "data", "nome_arquivo", data_nome.data.isoformat(),
                f"sem EXIF; '{data_nome.texto}' no nome do arquivo "
                f"({data_nome.padrao})",
            ))
        elif media.mtime is not None:
            drafts.append(_Draft(
                "data", "fs", media.mtime.isoformat(),
                "sem EXIF; data de modificação do arquivo (pouco confiável)",
            ))

        # Data escrita no nome da pasta ("… - Abril 2015"): segunda
        # testemunha do ano, independente do EXIF. Quando as duas
        # concordam, o ano deixa de depender de uma fonte só; quando
        # divergem, a divergência aparece na justificativa em vez de
        # sumir. O EXIF continua mandando no destino (ver campos["ano"]).
        data_pasta = data_no_caminho(media.pasta)
        if data_pasta is not None:
            just = f"'{data_pasta.texto}' escrito no nome da pasta"
            if media.data_capturada is not None:
                if media.data_capturada.year == data_pasta.ano:
                    just += " — confere com o EXIF"
                else:
                    just += (f" — DIVERGE do EXIF "
                             f"({media.data_capturada.year})")
            drafts.append(_Draft("ano", "pasta", str(data_pasta.ano), just))

        drafts.extend(
            self._evidencias_geo(session, media, sessao, herancas, por_id)
        )

        if sessao is not None and sessao.tipo == "viagem":
            drafts.append(_Draft(
                "viagem", sessao.origem_do_rotulo, sessao.rotulo,
                f"{sessao.draft.n_fotos} fotos entre "
                f"{sessao.draft.periodo_legivel()} — {sessao.justificativa}",
            ))
        if sessao is not None and sessao.tipo == "evento":
            drafts.append(_Draft(
                "evento", sessao.origem_do_rotulo, sessao.rotulo,
                f"{sessao.draft.n_fotos} fotos em "
                f"{sessao.draft.periodo_legivel()} — {sessao.justificativa}",
            ))

        categoria = self._categoria(media, sessao, drafts, palavras_chave)
        if categoria is not None:
            drafts.append(categoria)
        return drafts

    def _evidencias_geo(self, session: Session, media: MediaFile,
                        sessao: _Sessao | None,
                        herancas: dict[int, Heranca],
                        por_id: dict[int, MediaFile]) -> list[_Draft]:
        # 1) GPS + geocodificação offline.
        if media.gps_lat is not None and self._resolver is not None:
            location = self._resolver.resolve(session, media.gps_lat, media.gps_lon)
            if location is not None:
                media.location_id = location.id
                just = (
                    f"geocodificação offline das coordenadas GPS do EXIF "
                    f"({media.gps_lat:.4f}, {media.gps_lon:.4f})"
                )
                return [
                    _Draft(campo, "geocoding_offline", valor, just)
                    for campo, valor in [
                        ("pais", location.pais), ("regiao", location.regiao),
                        ("cidade", location.cidade),
                    ]
                    if valor
                ]

        # 1b) GPS herdado de foto de outra fonte (correlação temporal).
        heranca = herancas.get(media.id)
        if heranca is not None and self._resolver is not None:
            location = self._resolver.resolve(session, heranca.lat, heranca.lon)
            if location is not None:
                media.location_id = location.id
                doador = por_id.get(heranca.doador_id)
                just = (
                    f"GPS herdado de '{doador.nome if doador else '?'}'"
                    f"{_camera_legivel(doador)} — tirada a "
                    f"{_delta_legivel(heranca.delta)} de distância"
                )
                if heranca.granularidade != "cidade":
                    # A distância no tempo não sustenta a cidade. Dizer só
                    # "a 3h de distância" deixaria o usuário concluir sozinho
                    # que a cidade veio junto — ela não veio.
                    just += (
                        f"; a essa distância dá para afirmar "
                        f"{_GRANULARIDADE[heranca.granularidade]}, não a cidade"
                    )
                if heranca.hora_incerta:
                    # Sem esta frase o usuário lê "a 2min de distância" e
                    # acredita numa precisão que a hora usada não tem.
                    just += (
                        "; a hora de uma delas é a do arquivo, não a da "
                        "captura — a proximidade pode ser coincidência"
                    )
                drafts = []
                for campo, valor in [
                    ("pais", location.pais), ("regiao", location.regiao),
                    ("cidade", location.cidade),
                ]:
                    fator = heranca.fator_de(campo)
                    if not valor or fator is None:
                        continue
                    score = round(
                        SCORES_REFERENCIA["vizinhanca_temporal"] * fator, 3
                    )
                    drafts.append(
                        _Draft(campo, "vizinhanca_temporal", valor, just,
                               score_override=score)
                    )
                if drafts:
                    return drafts

        # 2) Nome das pastas.
        hierarquia = extrair_hierarquia_da_pasta(media.pasta)
        if hierarquia.pais:
            just = f"reconhecido no caminho da pasta ('{hierarquia.segmento_pais}')"
            return [
                _Draft(campo, "pasta", valor, just)
                for campo, valor in [
                    ("pais", hierarquia.pais), ("regiao", hierarquia.regiao),
                    ("cidade", hierarquia.cidade),
                ]
                if valor
            ]

        # 3) Vizinhança: a sessão tem país dominante pelo GPS das outras.
        if sessao is not None and sessao.pais_dominante:
            return [_Draft(
                "pais", "vizinhanca", sessao.pais_dominante,
                f"outras fotos da mesma sessão têm GPS em "
                f"{sessao.pais_dominante}",
            )]

        return []  # sem evidência: não inventa localização

    def _categoria(self, media: MediaFile, sessao: _Sessao | None,
                   drafts: list[_Draft],
                   palavras_chave: tuple[str, ...] = ()) -> _Draft | None:
        # 1) Pasta de categoria explícita no caminho da foto.
        for segmento in reversed(media.pasta.split("/")):
            canonico = _CATEGORIAS_PASTA.get(_normalizar(segmento))
            if canonico:
                return _Draft(
                    "categoria", "pasta", canonico,
                    f"pasta '{segmento}' no caminho original",
                )
        # 2) Tipo da sessão — cascata determinística (GPS/geocodificação,
        # confiança 0.85-0.95). Decide ANTES da palavra-chave de propósito:
        # a sessão é o mesmo veredito para todas as fotos do grupo, e uma
        # palavra-chave de uma foto só (0.55, abaixo) não pode fragmentar
        # esse veredito — ver 2b.
        if sessao is not None:
            if sessao.tipo == "viagem":
                return _Draft("categoria", sessao.origem, "Viagens",
                              sessao.justificativa)
            if sessao.tipo == "evento":
                return _Draft("categoria", sessao.origem, "Eventos",
                              sessao.justificativa)
        # 2b) Palavra-chave humana (XMP/IPTC) com o mesmo vocabulário da
        # pasta. Só chega aqui quando pasta E a cascata da sessão não
        # decidiram — abaixo das duas porque é sinal por FOTO, não por
        # sessão, e pode ter vindo de um álbum externo que só coincide no
        # tempo, sem a mesma intenção de organizar (docs/CONFIANCA.md).
        # Acima do advisor (LLM, item 3) porque é determinístico e grátis.
        for palavra in palavras_chave:
            canonico = _CATEGORIAS_PASTA.get(_normalizar(palavra))
            if canonico:
                return _Draft(
                    "categoria", "curadoria", canonico,
                    f"palavra-chave '{palavra}' (XMP/IPTC) na foto",
                )
        # 3) Advisor deu categoria sem evento.
        if sessao is not None and sessao.categoria:
            return _Draft("categoria", "llm", sessao.categoria,
                          sessao.justificativa or
                          "sugerido por LLM a partir de metadados")
        return None

    @staticmethod
    def _destino_nao_foto(media: MediaFile, evidencias: dict) -> str:
        """Ramo do que não é foto: por tipo e ano.

        Separado por tipo porque as decisões são diferentes — captura de tela
        quase sempre se apaga, imagem recebida às vezes se guarda. Por ano
        porque um balde único com milhares não é revisável.
        """
        raiz = f"{DESTINO_NAO_FOTO}/{ROTULOS_TIPO[media.tipo_efetivo].capitalize()}"
        if "data" in evidencias:
            return f"{raiz}/{datetime.fromisoformat(evidencias['data'].valor).year}"
        return raiz

    @staticmethod
    def _destino_nao_classificado(media: MediaFile, evidencias: dict) -> str:
        """Ramo das fotos que nenhum sinal nomeia, quebrado por ano e mês.

        Um balde único com milhares de fotos não é revisável; por mês, é.
        A data vem da melhor fonte disponível — a de captura, ou a que a
        própria pasta escreve quando não há EXIF. Conhecendo só o ano,
        para no ano: mês inventado não é evidência. Sem data alguma, a
        foto vai para "sem data", que é uma lacuna a resolver e não um
        lugar definitivo.
        """
        raiz = DESTINO_NAO_CLASSIFICADO
        if "data" in evidencias:
            dt = datetime.fromisoformat(evidencias["data"].valor)
            return f"{raiz}/{dt.year}/{rotulo_mes(dt.year, dt.month)}"
        data = data_no_caminho(media.pasta)
        if data is None:
            return f"{raiz}/sem data"
        if data.mes is None:
            return f"{raiz}/{data.ano}"
        return f"{raiz}/{data.ano}/{rotulo_mes(data.ano, data.mes)}"

    # -- persistência de sugestões ------------------------------------------
    def _midias_com_decisao(self, session: Session) -> set[int]:
        stmt = select(Suggestion.media_id).where(
            Suggestion.status != SuggestionStatus.PENDENTE
        )
        return set(session.scalars(stmt))

    @staticmethod
    def _contexto_da_sugestao(
        evidencias: dict[str, Evidence], usados: dict[str, Evidence]
    ) -> dict[str, Evidence]:
        """Lugar que não virou pasta, mas que a sugestão precisa mostrar.

        O motor suprime país/região/cidade do caminho quando a viagem ou o
        evento já nomeiam a pasta — mas o lugar segue sendo a resposta a
        "por que aqui?", ainda mais quando veio herdado de outra câmera.
        Quem serializa para a API é `Suggestion.evidencias`; sem vínculo, a
        justificativa existe no banco e não chega a lugar nenhum.
        """
        return {
            campo: evidencias[campo]
            for campo in _CAMPOS_DE_LUGAR
            if campo in evidencias and campo not in usados
        }

    @staticmethod
    def _descartar_sugestoes_orfas(session: Session) -> int:
        """Sugestão pendente de mídia que deixou de ser acervo.

        Sem isto, um registro rebaixado a testemunha leva sua sugestão
        antiga junto: `_persistir_sugestao` só limpa a mídia que está
        processando, e essa não passa mais por lá. Num catálogo real foram
        45.822 sugestões que ficariam pedindo decisão sobre miniatura.

        Só as PENDENTES. Aprovada e rejeitada são decisão do usuário, e
        decisão dele não se apaga por mudança de classificação nossa.

        O alvo é uma subconsulta, não uma lista de ids: com 45.822 mídias
        rebaixadas de uma vez, o `IN (?, ?, …)` estoura o limite de
        variáveis do SQLite.
        """
        alvos = (
            select(Suggestion.id)
            .join(MediaFile, MediaFile.id == Suggestion.media_id)
            .where(
                Suggestion.status == SuggestionStatus.PENDENTE,
                ~MediaFile.organizavel,
            )
            .scalar_subquery()
        )
        session.execute(delete(suggestion_evidence).where(
            suggestion_evidence.c.suggestion_id.in_(alvos)
        ))
        removidas = session.execute(
            delete(Suggestion).where(Suggestion.id.in_(alvos))
        ).rowcount
        session.flush()
        if removidas:
            log.info("descartadas %d sugestões de mídia que não é acervo",
                     removidas)
        return removidas

    def _persistir_sugestao(self, session: Session, media: MediaFile,
                            drafts: list[_Draft]) -> None:
        antigas = list(
            session.scalars(select(Suggestion).where(
                Suggestion.media_id == media.id,
                Suggestion.status == SuggestionStatus.PENDENTE,
            ))
        )
        for sugestao in antigas:
            session.execute(delete(suggestion_evidence).where(
                suggestion_evidence.c.suggestion_id == sugestao.id
            ))
            session.delete(sugestao)
        session.execute(delete(Evidence).where(Evidence.media_id == media.id))
        session.flush()

        evidencias: dict[str, Evidence] = {}
        for draft in drafts:
            evidencia = Evidence(
                media_id=media.id, campo=draft.campo, origem=draft.origem,
                valor=draft.valor, nivel=nivel_para_score(draft.score),
                score=draft.score, justificativa=draft.justificativa,
                versao_logica=VERSAO_LOGICA,
            )
            session.add(evidencia)
            evidencias[draft.campo] = evidencia

        # tz_estimado NÃO é calculado aqui: esta função é pulada para mídia
        # com sugestão já decidida (ver `gerar()`), e tz_estimado precisa do
        # mesmo padrão de recálculo incondicional de gps_lat_estimado
        # (CR-01) — quem grava é `_atualizar_tz_estimado`, chamado sobre
        # TODA mídia organizável antes deste loop rodar.

        campos = {campo: ev.valor for campo, ev in evidencias.items()}
        if "data" in evidencias:
            campos["ano"] = str(datetime.fromisoformat(evidencias["data"].valor).year)
        sem_nome = not any(campos.get(campo) for campo in _CAMPOS_QUE_NOMEIAM)
        # ("2024 - França/França" é evitado pelo próprio render_destino,
        # que não repete valor já visto acima no caminho.)
        #
        # UMA VIAGEM É UMA PASTA. Viagem ou evento já nomeiam o destino;
        # país/região/cidade não descem abaixo deles. O motivo não é
        # estético: a geocodificação depende de a foto ter GPS, e a
        # cobertura é irregular — das 2.405 fotos de uma mesma viagem no
        # acervo, 106 tinham coordenada. Deixar a hierarquia descer
        # partia a viagem em três pastas conforme QUAL foto por acaso
        # gravou GPS, que é acidente de equipamento, não organização.
        # O lugar continua gravado como evidência e visível no inspetor;
        # ele só não vira pasta.
        if campos.get("viagem") or campos.get("evento"):
            campos["pais"] = campos["regiao"] = campos["cidade"] = None

        # O que não é foto sai do fluxo de organização por viagem: captura
        # de tela não pertence a "Viagens/2024 - França" por ter sido feita
        # durante a viagem. Vai para um ramo próprio, por tipo e ano, onde
        # dá para revisar em lote e apagar se quiser.
        if media.tipo_efetivo and media.tipo_efetivo != TIPO_FOTO:
            destino = self._destino_nao_foto(media, evidencias)
            usados = {"tipo": evidencias["tipo"]} if "tipo" in evidencias else {}
            if "data" in evidencias:
                usados["data"] = evidencias["data"]
            self._salvar_sugestao(session, media, destino, usados)
            return

        if sem_nome:
            # Nada nomeia a foto: em vez do template (que renderiza só o
            # ano, ou nada), o ramo de não classificadas por ano e mês.
            destino = self._destino_nao_classificado(media, evidencias)
            usados = (
                {"data": evidencias["data"]} if "data" in evidencias else {}
            )
            self._salvar_sugestao(
                session, media, destino, usados,
                self._contexto_da_sugestao(evidencias, usados),
            )
            return

        destino = render_destino(self._template, campos)
        usados = {
            campo: ev for campo, ev in evidencias.items()
            if f"{{{campo}}}" in self._template and campos.get(campo)
        }
        if "{ano}" in self._template and "data" in evidencias:
            usados["data"] = evidencias["data"]
            # O ano do destino veio do EXIF; o da pasta é testemunha, não
            # fonte. Continua gravado como evidência (o usuário vê a
            # confirmação ou a divergência), mas não puxa o elo mais fraco
            # para baixo por algo que não decidiu nada. Concordância também
            # não SOBE score: docs/CONFIANCA.md proíbe soma de confianças.
            usados.pop("ano", None)

        self._salvar_sugestao(
            session, media, destino, usados, self._contexto_da_sugestao(evidencias, usados),
        )

    def _salvar_sugestao(self, session: Session, media: MediaFile,
                         destino: str, usados: dict[str, Evidence],
                         contexto: dict[str, Evidence] | None = None) -> None:
        # O nível sai SÓ do que decidiu o destino: contexto que não virou
        # pasta não pode puxar o elo mais fraco para baixo (docs/CONFIANCA.md).
        nivel, _score = elo_mais_fraco([ev.score for ev in usados.values()])
        sugestao = Suggestion(
            media_id=media.id, destino_sugerido=destino, template=self._template,
            nivel=nivel, versao_logica=VERSAO_LOGICA,
        )
        sugestao.evidencias = list(usados.values()) + list(
            (contexto or {}).values()
        )
        session.add(sugestao)
