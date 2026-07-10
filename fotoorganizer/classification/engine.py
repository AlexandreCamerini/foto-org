"""Motor de evidências e sugestões.

Para cada foto, colhe evidências estruturadas (origem, valor, confiança,
justificativa), monta o destino pelo template e agrega a confiança pelo elo
mais fraco. Decisões do usuário são preservadas: fotos com sugestão
aprovada/rejeitada/editada não são regeneradas.
"""

from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, sessionmaker

from fotoorganizer.classification.confidence import (
    SCORES_REFERENCIA,
    elo_mais_fraco,
    nivel_para_score,
)
from fotoorganizer.classification.templates import TEMPLATE_PADRAO, render_destino
from fotoorganizer.geolocation import LocationResolver, extrair_hierarquia_da_pasta
from fotoorganizer.grouping import agrupar_viagens
from fotoorganizer.models import (
    Evidence,
    MediaFile,
    Suggestion,
    SuggestionStatus,
    Trip,
    suggestion_evidence,
)

log = logging.getLogger(__name__)

VERSAO_LOGICA = "3.0"

_CATEGORIAS_PASTA = {"viagens": "Viagens", "familia": "Família",
                     "família": "Família", "eventos": "Eventos"}
_MIN_FOTOS_VIAGEM = 2


@dataclass(slots=True)
class _Draft:
    campo: str
    origem: str
    valor: str
    justificativa: str

    @property
    def score(self) -> float:
        return SCORES_REFERENCIA[self.origem]


class SuggestionEngine:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        resolver: LocationResolver | None = None,
        template: str = TEMPLATE_PADRAO,
    ) -> None:
        self._factory = session_factory
        self._resolver = resolver
        self._template = template

    # -- API --------------------------------------------------------------
    def gerar(self) -> dict:
        with self._factory() as session:
            midias = list(session.scalars(select(MediaFile)))
            decididas = self._midias_com_decisao(session)

            viagens = self._agrupar_e_persistir_viagens(session, midias)
            pais_por_trip = self._pais_dominante_por_viagem(session, midias)
            self._nomear_viagens(session, viagens, pais_por_trip)

            geradas = 0
            for media in midias:
                if media.id in decididas:
                    continue
                drafts = self._evidencias_para(session, media, pais_por_trip)
                self._persistir(session, media, drafts)
                geradas += 1
                if geradas % 500 == 0:
                    session.commit()

            session.commit()
            return {
                "sugestoes": geradas,
                "viagens": len(viagens),
                "preservadas": len(decididas),
            }

    # -- viagens ------------------------------------------------------------
    def _agrupar_e_persistir_viagens(self, session: Session, midias) -> list[Trip]:
        itens = [
            (m.id, m.data_capturada or m.mtime)
            for m in midias
            if (m.data_capturada or m.mtime) is not None
        ]
        drafts = [d for d in agrupar_viagens(itens) if d.n_fotos >= _MIN_FOTOS_VIAGEM]

        # Viagens são deriváveis (sem edição do usuário no MVP): regenera.
        for media in midias:
            media.trip_id = None
        session.execute(delete(Trip))
        session.flush()

        por_media: dict[int, Trip] = {}
        trips: list[Trip] = []
        for draft in drafts:
            trip = Trip(nome="", inicio=draft.inicio, fim=draft.fim,
                        metodo=f"lacuna_temporal>{3}d")
            session.add(trip)
            session.flush()
            trips.append(trip)
            for media_id in draft.media_ids:
                por_media[media_id] = trip
        for media in midias:
            trip = por_media.get(media.id)
            if trip is not None:
                media.trip_id = trip.id
        session.flush()
        return trips

    def _pais_dominante_por_viagem(self, session: Session, midias) -> dict[int, tuple[str, int]]:
        """trip_id → (país dominante, nº de fotos com GPS que o confirmam)."""
        if self._resolver is None:
            return {}
        paises: dict[int, Counter] = {}
        for media in midias:
            if media.trip_id is None or media.gps_lat is None:
                continue
            location = self._resolver.resolve(session, media.gps_lat, media.gps_lon)
            if location is not None and location.pais:
                paises.setdefault(media.trip_id, Counter())[location.pais] += 1
        return {
            trip_id: contador.most_common(1)[0]
            for trip_id, contador in paises.items()
        }

    def _nomear_viagens(self, session: Session, trips: list[Trip],
                        pais_por_trip: dict[int, tuple[str, int]]) -> None:
        # Nome curto, sem ano e sem "/": o template compõe "{ano} - {viagem}"
        # (ex.: "2024 - França"), então o rótulo não pode repetir o ano.
        for trip in trips:
            pais = pais_por_trip.get(trip.id)
            if pais is not None:
                trip.nome = pais[0]
            else:
                inicio = trip.inicio.strftime("%d-%m")
                fim = trip.fim.strftime("%d-%m")
                trip.nome = (
                    f"Viagem de {inicio}" if inicio == fim
                    else f"Viagem de {inicio} a {fim}"
                )
        session.flush()

    # -- evidências -----------------------------------------------------------
    def _evidencias_para(self, session: Session, media: MediaFile,
                         pais_por_trip: dict) -> list[_Draft]:
        drafts: list[_Draft] = []

        # Data
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

        # Geografia
        drafts.extend(self._evidencias_geo(session, media, pais_por_trip))

        # Viagem
        trip = session.get(Trip, media.trip_id) if media.trip_id else None
        if trip is not None:
            n = session.scalar(
                select(func.count(MediaFile.id)).where(MediaFile.trip_id == trip.id)
            )
            inicio = trip.inicio.strftime("%d/%m")
            fim = trip.fim.strftime("%d/%m/%Y")
            drafts.append(_Draft(
                "viagem", "agrupamento", trip.nome,
                f"{n} fotos próximas entre {inicio} e {fim} "
                f"(lacunas > 3 dias separam viagens)",
            ))

        # Categoria
        categoria = self._categoria(media, drafts)
        if categoria is not None:
            drafts.append(categoria)

        return drafts

    def _evidencias_geo(self, session: Session, media: MediaFile,
                        pais_por_trip: dict) -> list[_Draft]:
        # 1) GPS + geocodificação offline: a melhor evidência disponível.
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

        # 3) Vizinhança: outras fotos da mesma viagem têm GPS.
        if media.trip_id in pais_por_trip:
            pais, n = pais_por_trip[media.trip_id]
            return [_Draft(
                "pais", "vizinhanca", pais,
                f"{n} fotos da mesma viagem têm GPS em {pais}",
            )]

        return []  # sem evidência: não inventa localização

    def _categoria(self, media: MediaFile, drafts: list[_Draft]) -> _Draft | None:
        from fotoorganizer.geolocation.folder_names import _normalizar

        for segmento in reversed(media.pasta.split("/")):
            canonico = _CATEGORIAS_PASTA.get(_normalizar(segmento))
            if canonico:
                return _Draft(
                    "categoria", "pasta", canonico,
                    f"pasta '{segmento}' no caminho original",
                )
        campos = {d.campo for d in drafts}
        if "viagem" in campos and "pais" in campos:
            return _Draft(
                "categoria", "vizinhanca", "Viagens",
                "foto pertence a uma viagem com país identificado",
            )
        return None

    # -- persistência -----------------------------------------------------------
    def _midias_com_decisao(self, session: Session) -> set[int]:
        stmt = select(Suggestion.media_id).where(
            Suggestion.status != SuggestionStatus.PENDENTE
        )
        return set(session.scalars(stmt))

    def _persistir(self, session: Session, media: MediaFile,
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
            # Uma evidência por campo (a melhor origem já foi escolhida acima).
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
        # Evita "2024 - França/França/...": quando o rótulo da viagem é o
        # próprio país, o nível {pais} não acrescenta nada.
        if campos.get("viagem") and campos.get("pais") == campos["viagem"]:
            campos["pais"] = None

        destino = render_destino(self._template, campos)
        # Evidências realmente usadas no destino ({ano} deriva de "data").
        usados = {
            campo: ev for campo, ev in evidencias.items()
            if f"{{{campo}}}" in self._template and campos.get(campo)
        }
        if "{ano}" in self._template and "data" in evidencias:
            usados["data"] = evidencias["data"]

        nivel, _score = elo_mais_fraco([ev.score for ev in usados.values()])
        sugestao = Suggestion(
            media_id=media.id, destino_sugerido=destino, template=self._template,
            nivel=nivel, versao_logica=VERSAO_LOGICA,
        )
        sugestao.evidencias = list(usados.values())
        session.add(sugestao)
