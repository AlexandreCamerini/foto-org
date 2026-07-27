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
from fotoorganizer.classification.templates import (
    DESTINO_NAO_CLASSIFICADO,
    TEMPLATE_PADRAO,
    render_destino,
)
from fotoorganizer.geolocation import LocationResolver, extrair_hierarquia_da_pasta
from fotoorganizer.grouping.datas import data_no_caminho, rotulo_mes
from fotoorganizer.geolocation.folder_names import _normalizar
from fotoorganizer.geolocation.home import detectar_casa, distancia_km
from fotoorganizer.grouping import (
    FotoRef,
    Heranca,
    agrupar_viagens,
    dividir_por_transicao_casa,
    estimar_offsets,
    herdar_gps,
)
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
    partes = " ".join(filter(None, [media.make, media.model]))
    return f" ({partes})" if partes else ""

_CATEGORIAS_PASTA = {"viagens": "Viagens", "viagem": "Viagens",
                     "familia": "Família", "família": "Família",
                     "eventos": "Eventos", "evento": "Eventos"}
_MIN_FOTOS_SESSAO = 2
# Campos que dão nome ao destino. Sem nenhum deles, sobra só a data.
_CAMPOS_QUE_NOMEIAM = ("categoria", "viagem", "evento", "pais", "regiao",
                       "cidade")
# Fotos geocodificadas mínimas para um país contar como perna da viagem —
# uma escala de aeroporto com 1-2 fotos não nomeia a viagem.
_MIN_FOTOS_PERNA = 3


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
    ) -> None:
        self._factory = session_factory
        self._resolver = resolver
        self._template = template
        self._advisor = advisor
        self._config = config

    # -- API ----------------------------------------------------------------
    def gerar(self) -> dict:
        with self._factory() as session:
            midias = list(session.scalars(select(MediaFile)))
            decididas = self._midias_com_decisao(session)
            por_id = {m.id: m for m in midias}

            # Correlação entre fontes: fotos sem GPS herdam localização de
            # fotos de outra origem tiradas a minutos de distância. Entram
            # TODAS as mídias, inclusive as referências sem arquivo local —
            # são elas que trazem GPS de celular numa biblioteca em iCloud.
            herancas = self._correlacionar(midias)

            # Daqui em diante só o que o usuário pode ver e organizar: uma
            # referência não tem arquivo para agrupar nem para copiar.
            organizaveis = [m for m in midias if not m.arquivo_ausente]

            sessoes, sessao_da_media = self._montar_sessoes(
                session, organizaveis, herancas
            )
            self._persistir_agrupamentos(
                session, organizaveis, sessoes, sessao_da_media
            )

            geradas = 0
            for media in organizaveis:
                if media.id in decididas:
                    continue
                drafts = self._evidencias_para(
                    session, media, sessao_da_media.get(media.id),
                    herancas, por_id,
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
            }

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

        sessoes: list[_Sessao] = []
        sessao_da_media: dict[int, _Sessao] = {}
        for draft in drafts:
            membros = [por_id[i] for i in draft.media_ids]
            sessao = self._classificar(
                session, _Sessao(draft=draft), membros, casa, herancas
            )
            if sessao.tipo == "neutra" and self._advisor is not None:
                self._consultar_advisor(sessao, membros)
            sessoes.append(sessao)
            for media_id in draft.media_ids:
                sessao_da_media[media_id] = sessao
        return sessoes, sessao_da_media

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
                     casa, herancas: dict[int, Heranca]) -> _Sessao:
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
            ),
            self._config,
        )
        sessao.tipo = decisao.tipo
        sessao.rotulo = decisao.rotulo
        sessao.origem = decisao.origem
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
            if location.pais:
                paises[location.pais] += 1
                if location.pais not in ordem_paises:
                    ordem_paises.append(location.pais)
            lugar = ", ".join(filter(None, [location.cidade, location.pais]))
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
        if resultado.evento:
            sessao.tipo = "evento"
            sessao.rotulo = resultado.evento
            sessao.origem = "llm"
            sessao.justificativa = (
                f"LLM (apenas metadados): {resultado.justificativa}"
            )

    # -- persistência de viagens/eventos -----------------------------------
    def _persistir_agrupamentos(self, session: Session, midias,
                                sessoes: list[_Sessao],
                                sessao_da_media: dict[int, _Sessao]) -> None:
        # Deriváveis (sem edição do usuário no MVP): regenera tudo.
        for media in midias:
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
                         por_id: dict[int, MediaFile]) -> list[_Draft]:
        drafts: list[_Draft] = []

        if media.data_capturada is not None:
            drafts.append(_Draft(
                "data", "exif", media.data_capturada.isoformat(),
                "data de captura lida do EXIF (DateTimeOriginal)",
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
                "viagem", sessao.origem, sessao.rotulo,
                f"{sessao.draft.n_fotos} fotos entre "
                f"{sessao.draft.periodo_legivel()} — {sessao.justificativa}",
            ))
        if sessao is not None and sessao.tipo == "evento":
            drafts.append(_Draft(
                "evento", sessao.origem, sessao.rotulo,
                f"{sessao.draft.n_fotos} fotos em "
                f"{sessao.draft.periodo_legivel()} — {sessao.justificativa}",
            ))

        categoria = self._categoria(media, sessao, drafts)
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
                score = round(
                    SCORES_REFERENCIA["vizinhanca_temporal"]
                    * heranca.score_fator, 3,
                )
                return [
                    _Draft(campo, "vizinhanca_temporal", valor, just,
                           score_override=score)
                    for campo, valor in [
                        ("pais", location.pais), ("regiao", location.regiao),
                        ("cidade", location.cidade),
                    ]
                    if valor
                ]

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
                   drafts: list[_Draft]) -> _Draft | None:
        # 1) Pasta de categoria explícita no caminho da foto.
        for segmento in reversed(media.pasta.split("/")):
            canonico = _CATEGORIAS_PASTA.get(_normalizar(segmento))
            if canonico:
                return _Draft(
                    "categoria", "pasta", canonico,
                    f"pasta '{segmento}' no caminho original",
                )
        # 2) Tipo da sessão.
        if sessao is not None:
            if sessao.tipo == "viagem":
                return _Draft("categoria", sessao.origem, "Viagens",
                              sessao.justificativa)
            if sessao.tipo == "evento":
                return _Draft("categoria", sessao.origem, "Eventos",
                              sessao.justificativa)
            # 3) Advisor deu categoria sem evento.
            if sessao.categoria:
                return _Draft("categoria", "llm", sessao.categoria,
                              sessao.justificativa or
                              "sugerido por LLM a partir de metadados")
        return None

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

        campos = {campo: ev.valor for campo, ev in evidencias.items()}
        if "data" in evidencias:
            campos["ano"] = str(datetime.fromisoformat(evidencias["data"].valor).year)
        sem_nome = not any(campos.get(campo) for campo in _CAMPOS_QUE_NOMEIAM)
        # Evita "2024 - França/França/…".
        if campos.get("viagem") and campos.get("pais") == campos["viagem"]:
            campos["pais"] = None
        # Evento local não ganha hierarquia geográfica no destino
        # ("Eventos/2026/Serena 15 Anos", não ".../Serena 15 Anos/São Paulo").
        if campos.get("evento"):
            campos["pais"] = campos["regiao"] = campos["cidade"] = None

        if sem_nome:
            # Nada nomeia a foto: em vez do template (que renderiza só o
            # ano, ou nada), o ramo de não classificadas por ano e mês.
            destino = self._destino_nao_classificado(media, evidencias)
            usados = (
                {"data": evidencias["data"]} if "data" in evidencias else {}
            )
            self._salvar_sugestao(session, media, destino, usados)
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

        self._salvar_sugestao(session, media, destino, usados)

    def _salvar_sugestao(self, session: Session, media: MediaFile,
                         destino: str, usados: dict[str, Evidence]) -> None:
        nivel, _score = elo_mais_fraco([ev.score for ev in usados.values()])
        sugestao = Suggestion(
            media_id=media.id, destino_sugerido=destino, template=self._template,
            nivel=nivel, versao_logica=VERSAO_LOGICA,
        )
        sugestao.evidencias = list(usados.values())
        session.add(sugestao)
