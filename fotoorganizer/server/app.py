"""Servidor local da UI web — o motor Python exposto em 127.0.0.1.

Mesma regra da UI nativa: o servidor fala com repositórios/serviços,
nunca com filesystem/DB direto nos handlers além do que os serviços
oferecem. Nada escuta fora do loopback; nenhuma chamada externa.

Cobre leitura do catálogo (fontes, mídia, evidências, viagens/eventos,
sugestões, duplicatas), os trabalhos de background e as operações físicas.

Operações são o único caminho que escreve fora do catálogo, e por isso o
único com dois passos obrigatórios antes de qualquer byte se mover: criar
o plano e rodar o dry-run. O servidor recusa executar um plano sem
dry-run — o executor recusa de novo, por dentro.
"""

from __future__ import annotations

import logging
from pathlib import Path
from urllib.parse import urlsplit

import asyncio
import json as jsonlib

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from fotoorganizer import __version__
from fotoorganizer.config.settings import Settings
from fotoorganizer.models import (
    Event,
    Location,
    MediaFile,
    MetadataEntry,
    Suggestion,
    SuggestionStatus,
    Trip,
)
from fotoorganizer.operations import OperationExecutor, OperationPlanner
from fotoorganizer.repositories import (
    DuplicateRepository,
    MediaRepository,
    OperationRepository,
    SuggestionRepository,
)
from fotoorganizer.repositories.media import LACUNAS, MediaFilters
from fotoorganizer.repositories.suggestions import SuggestionFilters
from fotoorganizer.server.jobs import JobManager
from fotoorganizer.thumbnails import ThumbnailCache
from fotoorganizer.thumbnails.generator import generate_thumbnail

log = logging.getLogger(__name__)

# Escutar só no loopback impede acesso pela rede, mas NÃO impede que uma
# página qualquer aberta no navegador do usuário chame este servidor: POSTs
# sem corpo são "simple requests" e o navegador os envia sem preflight.
# Sem isto, um site poderia disparar jobs e mexer em decisões de duplicatas
# — furando o invariante "nada acontece sem o usuário no circuito".
_HOSTS_LOCAIS = frozenset({"127.0.0.1", "localhost", "::1"})


def _hostname(valor: str | None, *, com_esquema: bool) -> str | None:
    if not valor:
        return None
    try:
        # Host ("127.0.0.1:8765", "[::1]:8765") não tem esquema; Origin tem.
        return urlsplit(valor if com_esquema else f"//{valor}").hostname
    except ValueError:
        return None


class ScanBody(BaseModel):
    caminho: str


class ImportBody(BaseModel):
    tipo: str  # apple_photos | google_takeout
    caminho: str | None = None


class AcaoSugestoesBody(BaseModel):
    ids: list[int]
    acao: str  # aprovar | rejeitar | desfazer


class PrincipalBody(BaseModel):
    media_id: int


class PlanoBody(BaseModel):
    raiz_destino: str
    nome: str | None = None

# O usuário não precisa saber o que é "libraw" — precisa saber de onde o
# dado veio. O nome técnico fica na chave; o rótulo explica a origem.
ROTULOS_NAMESPACE = {
    "exif": "EXIF (gravado pela câmera)",
    "gps": "GPS (coordenadas no arquivo)",
    "iptc": "IPTC (autor, direitos, palavras-chave)",
    "xmp": "XMP (escrito por editor de imagem)",
    "libraw": "RAW (lido do arquivo bruto)",
    "apple": "Apple Fotos (catálogo importado)",
    "google": "Google Takeout (catálogo importado)",
}

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
        # Coordenada efetiva + se ela é estimada: a grade precisa marcar a
        # diferença sem uma consulta por miniatura.
        "tipo_imagem": m.tipo_imagem,
        "gps_estimado": m.coordenada_estimada,
        "gps_lat_efetivo": m.coordenada[0] if m.coordenada else None,
        "gps_lon_efetivo": m.coordenada[1] if m.coordenada else None,
        "source_id": m.source_id,
        "trip_id": m.trip_id,
        "event_id": m.event_id,
        "erro_leitura": m.erro_leitura,
    }


def create_app(
    settings: Settings, session_factory: sessionmaker[Session]
) -> FastAPI:
    app = FastAPI(title="Foto Organizer", version=__version__)

    @app.middleware("http")
    async def _exigir_origem_local(request: Request, call_next):
        """Recusa o que não vem da própria janela do app.

        `Host` não-local denuncia DNS rebinding (domínio do atacante
        apontando para 127.0.0.1); `Origin` presente e não-local denuncia
        uma página de terceiros chamando o servidor — o navegador sempre
        manda Origin nessas requisições. Sem Origin (curl, CLI, navegação
        na própria página) segue normal."""
        if _hostname(request.headers.get("host"), com_esquema=False) \
                not in _HOSTS_LOCAIS:
            return JSONResponse({"detail": "host não local"}, status_code=403)

        origem = request.headers.get("origin")
        if origem is not None and _hostname(origem, com_esquema=True) \
                not in _HOSTS_LOCAIS:
            log.warning("bloqueada requisição de origem externa: %s", origem)
            return JSONResponse(
                {"detail": "origem não permitida"}, status_code=403
            )
        return await call_next(request)

    media_repo = MediaRepository(session_factory)
    suggestion_repo = SuggestionRepository(session_factory)
    duplicate_repo = DuplicateRepository(session_factory)
    operation_repo = OperationRepository(session_factory)
    planner = OperationPlanner(session_factory)
    executor = OperationExecutor(session_factory)
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
        trip_id: int | None = None,
        event_id: int | None = None,
        lacuna: str | None = None,
        ordenacao: str = "data_desc",
        offset: int = 0,
        limit: int = 200,
    ) -> dict:
        if lacuna is not None and lacuna not in LACUNAS:
            raise HTTPException(422, f"lacuna desconhecida: {lacuna}")
        filters = MediaFilters(
            busca=busca, extensao=extensao, source_id=source_id,
            ano=ano, trip_id=trip_id, event_id=event_id, lacuna=lacuna,
            ordenacao=ordenacao,
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

    @app.get("/api/panorama")
    def panorama() -> dict:
        return media_repo.panorama()

    @app.get("/api/midia/{media_id}")
    def detalhe_midia(media_id: int) -> dict:
        media = media_repo.por_id(media_id)
        if media is None:
            raise HTTPException(404, "foto não encontrada")
        detalhe = _media_json(media)
        with session_factory() as session:
            # Só no detalhe: na grade isto seria uma consulta por miniatura.
            # O lugar pode ter vindo de GPS próprio ou herdado de outra
            # câmera — qual dos dois foi está nas evidências, abaixo.
            if media.location_id is not None:
                local = session.get(Location, media.location_id)
                if local is not None:
                    detalhe["local"] = {
                        "pais": local.pais,
                        "regiao": local.regiao,
                        "cidade": local.cidade,
                        "fonte": local.fonte,
                        "estimado": media.coordenada_estimada,
                    }
            if media.gps_estimado_de_id is not None:
                doadora = session.get(MediaFile, media.gps_estimado_de_id)
                if doadora is not None:
                    detalhe["estimativa"] = {
                        "doadora_id": doadora.id,
                        "doadora_nome": doadora.nome,
                        "doadora_camera": " ".join(
                            filter(None, [doadora.make, doadora.model])
                        ) or None,
                        "delta_s": media.gps_estimado_delta_s,
                        "lat": media.gps_lat_estimado,
                        "lon": media.gps_lon_estimado,
                    }
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

    @app.get("/api/midia/{media_id}/metadados")
    def metadados(media_id: int) -> dict:
        """Tudo que estava gravado no arquivo, agrupado por padrão.

        Endpoint próprio e não parte do detalhe: um JPEG editado traz
        dezenas de chaves XMP, e o detalhe é pedido a cada seleção na
        grade. Aqui o custo só existe quando o usuário pergunta.
        """
        with session_factory() as session:
            linhas = session.scalars(
                select(MetadataEntry)
                .where(MetadataEntry.media_id == media_id)
                .order_by(MetadataEntry.namespace, MetadataEntry.chave)
            ).all()
        grupos: dict[str, list[dict]] = {}
        for linha in linhas:
            grupos.setdefault(linha.namespace, []).append(
                {"chave": linha.chave, "valor": linha.valor}
            )
        return {
            "total": len(linhas),
            "namespaces": [
                {"nome": nome, "rotulo": ROTULOS_NAMESPACE.get(nome, nome),
                 "itens": itens}
                for nome, itens in grupos.items()
            ],
        }

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
    def _capa_disponivel(session, coluna, valor) -> int | None:
        """Capa do card: prefere foto com miniatura já em cache — fotos em
        volume desconectado não conseguem gerar imagem agora."""
        candidatos = list(session.scalars(
            select(MediaFile)
            .where(coluna == valor)
            .order_by(MediaFile.data_capturada)
            .limit(24)
        ))
        for media in candidatos:
            if media.hash_rapido and thumb_cache.get(media.hash_rapido):
                return media.id
        return candidatos[0].id if candidatos else None

    def _agrupamentos(session, modelo, coluna) -> list[dict]:
        resultado = []
        for grupo in session.scalars(select(modelo).order_by(modelo.inicio)):
            contagem = session.scalar(
                select(func.count(MediaFile.id)).where(coluna == grupo.id)
            ) or 0
            resultado.append({
                "id": grupo.id,
                "nome": grupo.nome,
                "inicio": grupo.inicio.isoformat() if grupo.inicio else None,
                "fim": grupo.fim.isoformat() if grupo.fim else None,
                "metodo": grupo.metodo,
                "fotos": contagem,
                "capa_id": _capa_disponivel(session, coluna, grupo.id),
            })
        return resultado

    @app.get("/api/viagens")
    def viagens() -> list[dict]:
        with session_factory() as session:
            return _agrupamentos(session, Trip, MediaFile.trip_id)

    @app.get("/api/eventos")
    def eventos() -> list[dict]:
        with session_factory() as session:
            return _agrupamentos(session, Event, MediaFile.event_id)

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
                    "data_capturada": (
                        linha.data_capturada.isoformat()
                        if linha.data_capturada else None
                    ),
                    "camera": linha.camera,
                    "gps_estimado": linha.gps_estimado,
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

    @app.post("/api/sugestoes/gerar")
    def gerar_sugestoes() -> dict:
        if not jobs.iniciar_sugestoes():
            raise HTTPException(409, "já existe um trabalho em andamento")
        return jobs.estado()

    @app.post("/api/sugestoes/acao")
    def acao_sugestoes(body: AcaoSugestoesBody) -> dict:
        acoes = {
            "aprovar": suggestion_repo.aprovar,
            "rejeitar": suggestion_repo.rejeitar,
            "desfazer": suggestion_repo.desfazer,
        }
        if body.acao not in acoes:
            raise HTTPException(422, f"ação desconhecida: {body.acao}")
        return {"afetadas": acoes[body.acao](body.ids)}

    @app.post("/api/duplicatas/detectar")
    def detectar_duplicatas() -> dict:
        if not jobs.iniciar_duplicatas():
            raise HTTPException(409, "já existe um trabalho em andamento")
        return jobs.estado()

    @app.post("/api/duplicatas/{group_id}/principal")
    def duplicata_principal(group_id: int, body: PrincipalBody) -> dict:
        duplicate_repo.escolher_principal(group_id, body.media_id)
        return {"ok": True}

    @app.post("/api/duplicatas/{group_id}/ignorar")
    def duplicata_ignorar(group_id: int) -> dict:
        duplicate_repo.ignorar_grupo(group_id)
        return {"ok": True}

    @app.post("/api/duplicatas/{group_id}/desfazer")
    def duplicata_desfazer(group_id: int) -> dict:
        duplicate_repo.desfazer_grupo(group_id)
        return {"ok": True}

    # -- operações físicas (plano → dry-run → execução) ----------------------
    def _plano_json(row) -> dict:
        return {
            "id": row.id,
            "nome": row.nome,
            "status": row.status.value,
            "dry_run_em": row.dry_run_em.isoformat() if row.dry_run_em else None,
            "criado_em": row.criado_em.isoformat(),
            "total_itens": row.total_itens,
            "concluidos": row.concluidos,
            "com_conflito": row.com_conflito,
            "com_erro": row.com_erro,
            # Veredito do último dry-run: sem ele a tela mostra "0 erros"
            # para um plano que não copiaria nada.
            "prontos": row.prontos,
            "problemas": row.problemas,
            "executavel": row.executavel,
        }

    @app.get("/api/operacoes")
    def listar_planos() -> list[dict]:
        return [_plano_json(p) for p in operation_repo.listar_planos()]

    @app.post("/api/operacoes")
    def criar_plano(body: PlanoBody) -> dict:
        raiz = Path(body.raiz_destino).expanduser()
        if not raiz.is_absolute():
            raise HTTPException(422, "informe um caminho absoluto de destino")
        # A raiz pode ainda não existir (a cópia cria as pastas), mas o volume
        # que a contém precisa existir — senão o plano nasce apontando para um
        # disco desconectado.
        if not raiz.is_dir() and not raiz.parent.is_dir():
            raise HTTPException(422, f"destino indisponível: {raiz.parent}")

        plan_id = planner.criar_plano(raiz, body.nome)
        if plan_id is None:
            raise HTTPException(
                409, "nenhuma sugestão aprovada aguardando cópia"
            )
        return _plano_json(operation_repo.plano(plan_id))

    @app.get("/api/operacoes/{plan_id}")
    def detalhe_plano(plan_id: int) -> dict:
        plano = operation_repo.plano(plan_id)
        if plano is None:
            raise HTTPException(404, "plano não encontrado")
        return {
            **_plano_json(plano),
            "itens": [
                {
                    "id": item.id,
                    "origem": item.origem,
                    "destino": item.destino,
                    "status": item.status.value,
                    "conflito": item.conflito,
                    "erro": item.erro,
                }
                for item in operation_repo.itens(plan_id)
            ],
        }

    @app.get("/api/operacoes/{plan_id}/auditoria")
    def auditoria_plano(plan_id: int) -> list[dict]:
        if operation_repo.plano(plan_id) is None:
            raise HTTPException(404, "plano não encontrado")
        return [
            {
                "id": linha.id,
                "quando": linha.quando.isoformat(),
                "acao": linha.acao,
                "resultado": linha.resultado,
                "detalhe": linha.detalhe,
            }
            for linha in operation_repo.auditoria(plan_id)
        ]

    @app.post("/api/operacoes/{plan_id}/dry-run")
    def dry_run_plano(plan_id: int) -> dict:
        """Só lê: confere origens, destinos livres e espaço em disco."""
        if operation_repo.plano(plan_id) is None:
            raise HTTPException(404, "plano não encontrado")
        return executor.dry_run(plan_id)

    @app.post("/api/operacoes/{plan_id}/executar")
    def executar_plano(plan_id: int) -> dict:
        plano = operation_repo.plano(plan_id)
        if plano is None:
            raise HTTPException(404, "plano não encontrado")
        if plano.dry_run_em is None:
            raise HTTPException(409, "rode o dry-run antes de executar")
        if not jobs.iniciar_execucao(plan_id):
            raise HTTPException(409, "já existe um trabalho em andamento")
        return jobs.estado()

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
