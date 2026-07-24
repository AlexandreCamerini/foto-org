"""Servidor local da UI web — o motor Python exposto em 127.0.0.1.

Mesma regra da UI nativa: o servidor fala com repositórios/serviços,
nunca com filesystem/DB direto nos handlers além do que os serviços
oferecem. Nada escuta fora do loopback; nenhuma chamada externa.

F1 (read-only): fontes, mídia paginada, thumb/preview, evidências,
viagens/eventos, sugestões e duplicatas. Mutations chegam nas fatias
seguintes (scan/import, revisão, duplicatas).
"""

from __future__ import annotations

import logging
from pathlib import Path

import asyncio
import json as jsonlib

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from fotoorganizer import __version__
from fotoorganizer.config.settings import Settings
from fotoorganizer.models import (
    Event,
    MediaFile,
    Suggestion,
    SuggestionStatus,
    Trip,
)
from fotoorganizer.repositories import (
    DuplicateRepository,
    MediaRepository,
    SuggestionRepository,
)
from fotoorganizer.repositories.media import MediaFilters
from fotoorganizer.repositories.suggestions import SuggestionFilters
from fotoorganizer.server.jobs import JobManager
from fotoorganizer.thumbnails import ThumbnailCache
from fotoorganizer.thumbnails.generator import generate_thumbnail

log = logging.getLogger(__name__)


class ScanBody(BaseModel):
    caminho: str


class ImportBody(BaseModel):
    tipo: str  # apple_photos | google_takeout
    caminho: str | None = None

_PREVIEW_SIZE = 2048

_WEBAPP_DIST = Path(__file__).resolve().parents[2] / "webapp" / "dist"


def _media_json(m: MediaFile) -> dict:
    return {
        "id": m.id,
        "nome": m.nome,
        "caminho": m.caminho,
        "pasta": m.pasta,
        "extensao": m.extensao,
        "tamanho": m.tamanho,
        "data_capturada": m.data_capturada.isoformat() if m.data_capturada else None,
        "make": m.make,
        "model": m.model,
        "lente": m.lente,
        "largura": m.largura,
        "altura": m.altura,
        "gps_lat": m.gps_lat,
        "gps_lon": m.gps_lon,
        "source_id": m.source_id,
        "trip_id": m.trip_id,
        "event_id": m.event_id,
        "erro_leitura": m.erro_leitura,
    }


def create_app(
    settings: Settings, session_factory: sessionmaker[Session]
) -> FastAPI:
    app = FastAPI(title="Foto Organizer", version=__version__)

    media_repo = MediaRepository(session_factory)
    suggestion_repo = SuggestionRepository(session_factory)
    duplicate_repo = DuplicateRepository(session_factory)
    thumb_cache = ThumbnailCache(settings.cache_dir)
    preview_dir = settings.cache_dir / "previews"
    jobs = JobManager(settings, session_factory)

    # -- status e fontes ---------------------------------------------------
    @app.get("/api/status")
    def status() -> dict:
        stats = media_repo.estatisticas()
        return {"versao": __version__, **stats}

    @app.get("/api/fontes")
    def fontes() -> list[dict]:
        return [
            {
                "id": source.id,
                "caminho": source.caminho,
                "apelido": source.apelido,
                "tipo": source.tipo.value,
                "disponivel": source.disponivel,
                "fotos": contagem,
            }
            for source, contagem in media_repo.fontes_com_contagem()
        ]

    # -- mídia ---------------------------------------------------------------
    @app.get("/api/midia")
    def listar_midia(
        busca: str | None = None,
        extensao: str | None = None,
        source_id: int | None = None,
        ano: int | None = None,
        ordenacao: str = "data_desc",
        offset: int = 0,
        limit: int = 200,
    ) -> dict:
        filters = MediaFilters(
            busca=busca, extensao=extensao, source_id=source_id,
            ano=ano, ordenacao=ordenacao,
        )
        limit = max(1, min(limit, 500))
        itens = media_repo.listar(filters, limit=limit, offset=offset)
        return {
            "total": media_repo.contar(filters),
            "offset": offset,
            "itens": [_media_json(m) for m in itens],
        }

    @app.get("/api/midia/filtros")
    def filtros_midia() -> dict:
        return {"extensoes": media_repo.extensoes(), "anos": media_repo.anos()}

    @app.get("/api/midia/{media_id}")
    def detalhe_midia(media_id: int) -> dict:
        media = media_repo.por_id(media_id)
        if media is None:
            raise HTTPException(404, "foto não encontrada")
        detalhe = _media_json(media)
        with session_factory() as session:
            sugestao = session.scalar(
                select(Suggestion).where(Suggestion.media_id == media_id)
            )
            if sugestao is not None:
                detalhe["sugestao"] = {
                    "id": sugestao.id,
                    "destino": sugestao.destino_sugerido,
                    "nivel": sugestao.nivel.value,
                    "status": sugestao.status.value,
                    "evidencias": [
                        {
                            "campo": ev.campo,
                            "origem": ev.origem,
                            "valor": ev.valor,
                            "nivel": ev.nivel.value,
                            "score": ev.score,
                            "justificativa": ev.justificativa,
                        }
                        for ev in sugestao.evidencias
                    ],
                }
        return detalhe

    # -- imagens ---------------------------------------------------------------
    @app.get("/api/midia/{media_id}/thumb")
    def thumb(media_id: int):
        media = media_repo.por_id(media_id)
        if media is None or media.hash_rapido is None:
            raise HTTPException(404, "sem miniatura")
        path = thumb_cache.get_or_generate(media.hash_rapido, Path(media.caminho))
        if path is None:
            raise HTTPException(404, "imagem indecodificável")
        return FileResponse(path, media_type="image/jpeg",
                            headers={"Cache-Control": "max-age=31536000"})

    @app.get("/api/midia/{media_id}/preview")
    def preview(media_id: int):
        """JPEG grande para o loupe (RAW usa a prévia embutida do arquivo)."""
        media = media_repo.por_id(media_id)
        if media is None or media.hash_rapido is None:
            raise HTTPException(404, "sem preview")
        chave = media.hash_rapido.replace(":", "_")
        destino = preview_dir / chave[:2] / f"{chave}.jpg"
        if not destino.is_file():
            if not generate_thumbnail(
                Path(media.caminho), destino, size=_PREVIEW_SIZE
            ):
                raise HTTPException(404, "imagem indecodificável")
        return FileResponse(destino, media_type="image/jpeg",
                            headers={"Cache-Control": "max-age=31536000"})

    # -- agrupamentos ---------------------------------------------------------
    @app.get("/api/viagens")
    def viagens() -> list[dict]:
        with session_factory() as session:
            resultado = []
            for trip in session.scalars(select(Trip).order_by(Trip.inicio)):
                contagem = session.scalar(
                    select(func.count(MediaFile.id)).where(
                        MediaFile.trip_id == trip.id
                    )
                ) or 0
                capa = session.scalar(
                    select(MediaFile.id)
                    .where(MediaFile.trip_id == trip.id)
                    .order_by(MediaFile.data_capturada)
                )
                resultado.append({
                    "id": trip.id,
                    "nome": trip.nome,
                    "inicio": trip.inicio.isoformat() if trip.inicio else None,
                    "fim": trip.fim.isoformat() if trip.fim else None,
                    "metodo": trip.metodo,
                    "fotos": contagem,
                    "capa_id": capa,
                })
            return resultado

    @app.get("/api/eventos")
    def eventos() -> list[dict]:
        with session_factory() as session:
            resultado = []
            for evento in session.scalars(select(Event).order_by(Event.inicio)):
                contagem = session.scalar(
                    select(func.count(MediaFile.id)).where(
                        MediaFile.event_id == evento.id
                    )
                ) or 0
                capa = session.scalar(
                    select(MediaFile.id)
                    .where(MediaFile.event_id == evento.id)
                    .order_by(MediaFile.data_capturada)
                )
                resultado.append({
                    "id": evento.id,
                    "nome": evento.nome,
                    "inicio": evento.inicio.isoformat() if evento.inicio else None,
                    "fim": evento.fim.isoformat() if evento.fim else None,
                    "metodo": evento.metodo,
                    "fotos": contagem,
                    "capa_id": capa,
                })
            return resultado

    # -- sugestões e duplicatas (leitura; ações nas fatias seguintes) --------
    @app.get("/api/sugestoes")
    def sugestoes(status: str = "pendente", offset: int = 0,
                  limit: int = 200) -> dict:
        try:
            status_enum = SuggestionStatus(status)
        except ValueError:
            raise HTTPException(422, f"status inválido: {status}")
        filters = SuggestionFilters(status=status_enum)
        linhas = suggestion_repo.listar(
            filters, limit=max(1, min(limit, 500)), offset=offset
        )
        contagens = suggestion_repo.contagens_por_status()
        return {
            "contagens": {s.value: n for s, n in contagens.items()},
            "itens": [
                {
                    "id": linha.id,
                    "media_id": linha.media_id,
                    "nome": linha.nome,
                    "pasta": linha.pasta,
                    "destino": linha.destino,
                    "nivel": linha.nivel.value,
                    "status": linha.status.value,
                }
                for linha in linhas
            ],
        }

    @app.get("/api/duplicatas")
    def duplicatas() -> list[dict]:
        return [
            {
                "id": grupo.id,
                "nivel": grupo.nivel.value,
                "rotulo": grupo.rotulo_nivel,
                "decidido": grupo.decidido,
                "bytes_recuperaveis": grupo.bytes_recuperaveis,
                "n_fontes": grupo.n_fontes,
                "membros": [
                    {
                        "member_id": membro.member_id,
                        "media_id": membro.media_id,
                        "nome": membro.nome,
                        "caminho": membro.caminho,
                        "tamanho": membro.tamanho,
                        "papel": membro.papel.value,
                        "source_id": membro.source_id,
                    }
                    for membro in grupo.membros
                ],
            }
            for grupo in duplicate_repo.listar_grupos()
        ]

    # -- trabalhos em background (scan/importação) ---------------------------
    @app.post("/api/scan")
    def iniciar_scan(body: ScanBody) -> dict:
        caminho = Path(body.caminho).expanduser()
        if not caminho.is_dir():
            raise HTTPException(422, f"pasta não encontrada: {caminho}")
        if not jobs.iniciar_scan(caminho):
            raise HTTPException(409, "já existe um trabalho em andamento")
        return jobs.estado()

    @app.post("/api/importar")
    def iniciar_import(body: ImportBody) -> dict:
        if body.tipo == "apple_photos":
            iniciado = jobs.iniciar_import_apple()
        elif body.tipo == "google_takeout":
            if not body.caminho:
                raise HTTPException(422, "informe a pasta do Takeout")
            caminho = Path(body.caminho).expanduser()
            if not caminho.is_dir():
                raise HTTPException(422, f"pasta não encontrada: {caminho}")
            iniciado = jobs.iniciar_import_takeout(caminho)
        else:
            raise HTTPException(422, f"tipo desconhecido: {body.tipo}")
        if not iniciado:
            raise HTTPException(409, "já existe um trabalho em andamento")
        return jobs.estado()

    @app.get("/api/job")
    def job_estado() -> dict:
        return jobs.estado()

    @app.post("/api/job/cancelar")
    def job_cancelar() -> dict:
        jobs.cancelar()
        return jobs.estado()

    @app.get("/api/progresso")
    async def progresso() -> StreamingResponse:
        """SSE com o estado do trabalho atual até ele terminar."""

        async def stream():
            anterior: dict | None = None
            while True:
                estado = jobs.estado()
                if estado != anterior:
                    yield f"data: {jsonlib.dumps(estado)}\n\n"
                    anterior = estado
                if estado.get("status") != "rodando":
                    break
                await asyncio.sleep(0.5)

        return StreamingResponse(stream(), media_type="text/event-stream")

    # -- frontend estático -----------------------------------------------------
    if _WEBAPP_DIST.is_dir():
        app.mount(
            "/", StaticFiles(directory=_WEBAPP_DIST, html=True), name="webapp"
        )

    return app
