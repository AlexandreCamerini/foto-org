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

from datetime import datetime, timedelta, timezone

from fotoorganizer import __version__
from fotoorganizer.classification.templates import (
    _PLACEHOLDER,
    TEMPLATE_PADRAO,
    render_destino,
)
from fotoorganizer.classification.tipo_imagem import TIPOS as TIPOS_IMAGEM
from fotoorganizer.config.settings import Settings
from fotoorganizer.geolocation.escala import metros_por_grau
from fotoorganizer.metadata.camera import nome_da_camera
from fotoorganizer.grouping.correlacao import (
    NOTA_DO_RAIO,
    RAIO_TETO_M,
    campos_confiaveis,
    frase_do_raio,
    raio_incerteza,
)
from fotoorganizer.models import (
    Event,
    Source,
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
    SettingsRepository,
    SuggestionRepository,
)
from fotoorganizer.repositories.inventario import funil as levantar_funil, levantar
from fotoorganizer.repositories.media import ALCANCES, LACUNAS, MediaFilters
from fotoorganizer.repositories.suggestions import SuggestionFilters, SuggestionRow
from fotoorganizer.security.paths import CaminhoInvalido, caminho_relativo_seguro
from fotoorganizer.server.jobs import JobManager
from fotoorganizer.sources.disponibilidade import verificar
from fotoorganizer.sources.reapontar import (
    ColisaoDeCaminho,
    ReapontamentoInaplicavel,
    ValidacaoFalhou,
    aplicar as aplicar_reapontamento,
    prefixos_do_estado,
    previa as previa_reapontamento,
)
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


class ReapontarBody(BaseModel):
    # Confirmação explícita no corpo, não só o método POST — a mesma
    # disciplina de `--confirmar` no CLI (invariante 2: aprovação explícita
    # antes de qualquer escrita em massa).
    confirmar: bool = False


class AcaoSugestoesBody(BaseModel):
    acao: str  # aprovar | rejeitar | desfazer
    ids: list[int] | None = None
    # Alternativa a `ids`: age sobre o GRUPO inteiro, que é a unidade de
    # decisão (D-018). A tela não tem como mandar 2.406 ids — ela só
    # carregou uma página —, e era exatamente por isso que "Aprovar 85"
    # aprovava 85 de um grupo de 597.
    destino: str | None = None
    source_id: int | None = None
    status: str = "pendente"


class PrincipalBody(BaseModel):
    media_id: int


class TipoBody(BaseModel):
    """`None` devolve a decisão ao detector."""
    tipo: str | None = None


class PlanoBody(BaseModel):
    raiz_destino: str
    nome: str | None = None


class EditarDestinoBody(BaseModel):
    destino: str


class TemplateBody(BaseModel):
    template: str


# Fase 10: nenhum placeholder novo além destes — ver docstring de
# fotoorganizer/classification/templates.py. Mudar esta lista sem mudar
# render_destino quebra o contrato entre editor e motor.
PLACEHOLDERS_TEMPLATE_VALIDOS = frozenset(
    {"categoria", "ano", "viagem", "evento", "pais", "regiao", "cidade"}
)

# Dois exemplos fixos: um mostra o regime "viagem/evento nomeiam o lugar",
# o outro o fallback quando não há — o editor precisa ver os dois regimes
# do render, não só um deles parecendo bonito.
_EXEMPLOS_PREVIEW_TEMPLATE = (
    {
        "rotulo": "com viagem",
        "campos": {
            "categoria": "Viagens", "ano": "2024", "viagem": "Tailândia",
            "evento": None, "pais": "Tailândia", "regiao": None,
            "cidade": "Chiang Mai",
        },
    },
    {
        "rotulo": "sem viagem nem evento — cai para país, região, cidade",
        "campos": {
            "categoria": "Viagens", "ano": "2024", "viagem": None,
            "evento": None, "pais": "Tailândia", "regiao": None,
            "cidade": "Chiang Mai",
        },
    },
)


def _placeholders_invalidos(template: str) -> set[str]:
    return set(_PLACEHOLDER.findall(template)) - PLACEHOLDERS_TEMPLATE_VALIDOS


# O usuário não precisa saber o que é "libraw" — precisa saber de onde o
# dado veio. O nome técnico fica na chave; o rótulo explica a origem.
TIPOS_VALIDOS = frozenset(TIPOS_IMAGEM)

ROTULOS_NAMESPACE = {
    "exif": "EXIF (gravado pela câmera)",
    "gps": "GPS (coordenadas no arquivo)",
    "iptc": "IPTC (autor, direitos, palavras-chave)",
    "xmp": "XMP (escrito por editor de imagem)",
    "libraw": "RAW (lido do arquivo bruto)",
    "makernotes": "MakerNotes (bloco do fabricante da câmera)",
    "icc": "ICC (perfil de cor)",
    "quicktime": "QuickTime (contêiner de vídeo e RAW moderno)",
    "png": "PNG (cabeçalho do arquivo)",
    "apple": "Apple Fotos (catálogo importado)",
    "google": "Google Takeout (catálogo importado)",
    "lightroom": "Lightroom (catálogo importado)",
    "xmp_sidecar": "XMP em arquivo ao lado (.xmp)",
    "curadoria": "Curadoria (o que alguém escreveu sobre a foto)",
    "derivado": "Derivado (calculado a partir do arquivo)",
}

_PREVIEW_SIZE = 2048

_WEBAPP_DIST = Path(__file__).resolve().parents[2] / "webapp" / "dist"


def _sugestao_json(linha: SuggestionRow, fora: frozenset[int] = frozenset()) -> dict:
    return {
        "id": linha.id,
        "media_id": linha.media_id,
        "nome": linha.nome,
        "pasta": linha.pasta,
        "destino": linha.destino,
        "nivel": linha.nivel.value,
        "status": linha.status.value,
        "data_capturada": (
            linha.data_capturada.isoformat() if linha.data_capturada else None
        ),
        "camera": linha.camera,
        "gps_estimado": linha.gps_estimado,
        # Por que a foto não pode ser aberta agora (a tela diz em vez de
        # desenhar imagem quebrada). None quando está alcançável.
        "motivo_indisponivel": (
            "sem arquivo neste Mac" if linha.arquivo_ausente
            else "volume ou pasta fora de alcance"
            if linha.source_id in fora else None
        ),
    }


def _campos_do_lugar(m: MediaFile) -> tuple[str, ...]:
    """Que partes do lugar dá para mostrar, do mais grosso ao mais fino.

    GPS lido no arquivo entrega tudo. Lugar herdado entrega só o que o Δt
    até a doadora sustenta — a mesma regra que o motor usou para montar a
    evidência (D-025), aplicada aqui para a tela não afirmar mais que ela.
    """
    if not m.coordenada_estimada:
        return ("pais", "regiao", "cidade")
    if m.gps_estimado_delta_s is None:
        return ("pais",)
    campos = campos_confiaveis(timedelta(seconds=m.gps_estimado_delta_s))
    return tuple(campo for campo, _ in campos)


# Por que esta foto não pode ser aberta agora. `None` quando pode.
#
# A resposta vem da FONTE, não de um `stat` por foto: a grade pede centenas de
# miniaturas de uma vez, e tocar o disco (ou pior, um NAS) uma vez por
# miniatura transformaria rolagem em espera. `Source.disponivel` é mantido por
# `sources/disponibilidade.verificar`.
def _motivo_indisponivel(m: MediaFile, fontes_off: frozenset[int]) -> str | None:
    if m.arquivo_ausente:
        return "sem arquivo neste Mac"
    if m.source_id in fontes_off:
        return "volume ou pasta fora de alcance"
    # A fonte responde, mas ESTE arquivo sumiu de onde estava — apagado,
    # movido para fora, renomeado por outro programa. "Sumiu" e não "não
    # encontrado": a segunda soaria como erro do app, e o app não errou.
    if m.arquivo_offline:
        return "arquivo sumiu do disco"
    return None


def _media_json(m: MediaFile, fontes_off: frozenset[int] = frozenset()) -> dict:
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
        "tipo_imagem": m.tipo_efetivo,
        # Provisório: o detector opinou e o usuário ainda não respondeu. A
        # interface pergunta em vez de afirmar.
        "tipo_provisorio": m.tipo_provisorio,
        "gps_estimado": m.coordenada_estimada,
        "gps_lat_efetivo": m.coordenada[0] if m.coordenada else None,
        "gps_lon_efetivo": m.coordenada[1] if m.coordenada else None,
        "source_id": m.source_id,
        "trip_id": m.trip_id,
        "event_id": m.event_id,
        "erro_leitura": m.erro_leitura,
        # A interface precisa separar "miniatura ainda não pronta" de "não
        # tenho como abrir isto" — sem esta marca ela desenha o ícone de
        # imagem quebrada e o usuário conclui que o app está quebrado.
        "motivo_indisponivel": _motivo_indisponivel(m, fontes_off),
    }


def _ponto_do_mapa(
    m: MediaFile,
    coordenada: tuple[float, float],
    doadoras: dict[int, MediaFile],
    motivo_indisponivel: str | None = None,
) -> dict:
    """Uma foto como o mapa a desenha: ponto cheio ou círculo.

    `estimado=False` é ponto — coordenada lida do arquivo, e `raio_m` é
    None porque não há dúvida a desenhar. `estimado=True` é círculo, e aí
    `raio_m` é o tamanho da dúvida e `porque` a frase que a explica. As duas
    saem de `grouping/correlacao.py`; a UI recebe metros e texto prontos.
    """
    lat, lon = coordenada
    ponto = {
        "media_id": m.id,
        "nome": m.nome,
        "lat": lat,
        "lon": lon,
        "data_capturada": (
            m.data_capturada.isoformat() if m.data_capturada else None
        ),
        "camera": nome_da_camera(m.make, m.model),
        # A coordenada é do catálogo; a miniatura é do disco. Um disco
        # desligado tira a segunda, não a primeira — o ponto é desenhado e
        # a tela diz por que não tem imagem.
        "motivo_indisponivel": motivo_indisponivel,
        "estimado": m.coordenada_estimada,
        "raio_m": None,
        "delta_s": None,
        "doadora_id": None,
        "doadora_nome": None,
        "porque": None,
    }
    if not m.coordenada_estimada:
        return ponto

    doadora = doadoras.get(m.gps_estimado_de_id or -1)
    # Δt ausente não é Δt zero: sem ele não dá para afirmar tamanho nenhum,
    # e o raio vai ao teto — a dúvida máxima é a resposta honesta para
    # "não sei há quanto tempo".
    delta = timedelta(seconds=m.gps_estimado_delta_s or 0) \
        if m.gps_estimado_delta_s is not None else None
    ponto["delta_s"] = m.gps_estimado_delta_s
    ponto["doadora_id"] = m.gps_estimado_de_id
    ponto["doadora_nome"] = doadora.nome if doadora else None
    if delta is None:
        ponto["raio_m"] = RAIO_TETO_M
        ponto["porque"] = (
            "Lugar herdado de outra foto, sem registro de quanto tempo as "
            f"separa — o círculo é o maior que o acervo justifica "
            f"({RAIO_TETO_M / 1000:.0f} km)."
        )
    else:
        ponto["raio_m"] = raio_incerteza(delta)
        ponto["porque"] = frase_do_raio(
            delta, doadora.nome if doadora else None
        )
    return ponto


def _enquadramento(pontos: list[dict]) -> dict:
    """O retângulo que o mapa precisa mostrar, e a escala para desenhá-lo.

    Os limites já vêm ESTICADOS pelo raio de cada círculo: num grupo em que
    todas as fotos herdaram da mesma doadora — o caso comum neste acervo — a
    caixa dos pontos tem lado zero e os círculos, 50 km. Enquadrar só os
    pontos cortaria fora tudo o que o mapa existe para mostrar.

    `escala` traduz metros em graus na latitude do grupo, para que o desenho
    do raio não precise da constante geodésica do outro lado da API.
    """
    if not pontos:
        return {"limites": None, "escala": None}
    lat_min = lon_min = float("inf")
    lat_max = lon_max = float("-inf")
    for p in pontos:
        raio = p["raio_m"] or 0.0
        por_lat, por_lon = metros_por_grau(p["lat"])
        d_lat, d_lon = raio / por_lat, raio / por_lon
        lat_min = min(lat_min, p["lat"] - d_lat)
        lat_max = max(lat_max, p["lat"] + d_lat)
        lon_min = min(lon_min, p["lon"] - d_lon)
        lon_max = max(lon_max, p["lon"] + d_lon)
    por_lat, por_lon = metros_por_grau((lat_min + lat_max) / 2)
    return {
        "limites": {
            "lat_min": lat_min, "lat_max": lat_max,
            "lon_min": lon_min, "lon_max": lon_max,
        },
        "escala": {"metros_por_grau_lat": por_lat,
                   "metros_por_grau_lon": por_lon},
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

    def _fontes_fora_de_alcance() -> frozenset[int]:
        """Ids das fontes que não respondem agora. Uma consulta por
        requisição, em vez de um `stat` por miniatura."""
        with session_factory() as session:
            return frozenset(session.scalars(
                select(Source.id).where(Source.disponivel.is_(False))
            ))

    media_repo = MediaRepository(session_factory)
    suggestion_repo = SuggestionRepository(session_factory)
    duplicate_repo = DuplicateRepository(session_factory)
    operation_repo = OperationRepository(session_factory)
    settings_repo = SettingsRepository(session_factory)
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

    @app.get("/api/funil")
    def funil() -> dict:
        """Os degraus entre "existe" e "dá para organizar", numa leitura só.

        Caro por natureza (percorre o catálogo inteiro para contar foto, não
        registro — ~1,4 s em 197 mil linhas), e por isso o cliente guarda o
        resultado e só refaz quando um trabalho em background termina. O
        número não muda sozinho: só scan, importação e geração de sugestões
        o alteram.
        """
        f = levantar_funil(session_factory)
        return {
            "conhecidas": f.conhecidas,
            "alcancaveis": f.alcancaveis,
            "organizaveis": f.organizaveis,
            "registros": f.registros,
        }

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

    @app.get("/api/fontes/reapontamentos")
    def fontes_reapontamentos() -> list[dict]:
        """Fontes cujo volume voltou noutro ponto de montagem — a
        affordance da sidebar aparece só para elas. Custa um `diskutil` por
        fonte fora de alcance (mesmo custo de `verificar()` no boot), então
        o cliente chama isto sob demanda, não a cada render."""
        estados = [e for e in verificar(session_factory) if e.mudou_de_lugar]
        resultado = []
        for estado in estados:
            try:
                prefixo_antigo, prefixo_novo = prefixos_do_estado(estado)
            except ReapontamentoInaplicavel:
                continue
            resultado.append({
                "source_id": estado.source_id,
                "apelido": estado.apelido,
                "prefixo_antigo": prefixo_antigo,
                "prefixo_novo": prefixo_novo,
            })
        return resultado

    def _estado_para_reapontar(source_id: int):
        estado = next(
            (e for e in verificar(session_factory) if e.source_id == source_id),
            None,
        )
        if estado is None:
            raise HTTPException(404, "fonte não encontrada")
        try:
            return prefixos_do_estado(estado)
        except ReapontamentoInaplicavel as exc:
            raise HTTPException(409, str(exc))

    @app.post("/api/fontes/{source_id}/reapontar/preview")
    def reapontar_preview(source_id: int) -> dict:
        prefixo_antigo, prefixo_novo = _estado_para_reapontar(source_id)
        try:
            p = previa_reapontamento(
                session_factory, source_id, prefixo_antigo, prefixo_novo
            )
        except ReapontamentoInaplicavel as exc:
            raise HTTPException(409, str(exc))
        return {
            "source_id": p.source_id,
            "apelido": p.apelido,
            "prefixo_antigo": p.prefixo_antigo,
            "prefixo_novo": p.prefixo_novo,
            "total_media_files": p.total_media_files,
            "total_ignoradas_sem_prefixo": p.total_ignoradas_sem_prefixo,
            "amostra": [
                {"antigo": antigo, "novo": novo} for antigo, novo in p.amostra
            ],
        }

    @app.post("/api/fontes/{source_id}/reapontar")
    def reapontar(source_id: int, body: ReapontarBody) -> dict:
        if not body.confirmar:
            raise HTTPException(422, 'confirme com {"confirmar": true}')
        prefixo_antigo, prefixo_novo = _estado_para_reapontar(source_id)
        try:
            r = aplicar_reapontamento(
                session_factory, source_id, prefixo_antigo, prefixo_novo
            )
        except (ValidacaoFalhou, ReapontamentoInaplicavel,
                ColisaoDeCaminho) as exc:
            raise HTTPException(409, str(exc))
        return {
            "source_id": r.source_id,
            "prefixo_antigo": r.prefixo_antigo,
            "prefixo_novo": r.prefixo_novo,
            "linhas_media_files": r.linhas_media_files,
            "audit_log_id": r.audit_log_id,
        }

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
        alcance: str = "tudo",
        mes: str | None = None,
        pasta: str | None = None,
        camera: str | None = None,
        pais: str | None = None,
        cidade: str | None = None,
        palavra_chave: str | None = None,
        offset: int = 0,
        limit: int = 200,
    ) -> dict:
        if lacuna is not None and lacuna not in LACUNAS:
            raise HTTPException(422, f"lacuna desconhecida: {lacuna}")
        if alcance not in ALCANCES:
            raise HTTPException(422, f"alcance desconhecido: {alcance}")
        filters = MediaFilters(
            busca=busca, extensao=extensao, source_id=source_id,
            ano=ano, trip_id=trip_id, event_id=event_id, lacuna=lacuna,
            ordenacao=ordenacao, alcance=alcance, mes=mes,
            camera=camera, pais=pais, cidade=cidade,
            palavra_chave=palavra_chave, pasta=pasta,
        )
        limit = max(1, min(limit, 500))
        itens = media_repo.listar(filters, limit=limit, offset=offset)
        fora = _fontes_fora_de_alcance()
        return {
            "total": media_repo.contar(filters),
            "offset": offset,
            "itens": [_media_json(m, fora) for m in itens],
        }

    @app.get("/api/pastas")
    def arvore_de_pastas(prefixo: str | None = None) -> dict:
        """Um nível da árvore de pastas do disco.

        Sem `prefixo`, devolve as raízes. Um nível por chamada — a árvore
        inteira de 371 mil registros na rede seria o erro que a grade
        virtualizada existe para evitar.
        """
        return media_repo.arvore_de_pastas(prefixo)

    @app.get("/api/midia/alcances")
    def alcances() -> list[dict]:
        return [{"chave": k, "rotulo": v} for k, v in ALCANCES.items()]

    @app.get("/api/midia/filtros")
    def filtros_midia() -> dict:
        """Os valores que existem no acervo, para a UI oferecer em vez de
        pedir que o usuário adivinhe o que digitar."""
        return {
            "extensoes": media_repo.extensoes(),
            "anos": media_repo.anos(),
            "cameras": media_repo.cameras(),
            "paises": media_repo.paises(),
            "palavras_chave": media_repo.palavras_chave(),
        }

    @app.get("/api/midia/linha-do-tempo")
    def linha_do_tempo(
        busca: str | None = None,
        extensao: str | None = None,
        source_id: int | None = None,
        ano: int | None = None,
        trip_id: int | None = None,
        event_id: int | None = None,
        lacuna: str | None = None,
        alcance: str = "tudo",
    ) -> list[dict]:
        """Meses do recorte atual, com contagem. A grade usa para saltar."""
        if alcance not in ALCANCES:
            raise HTTPException(422, f"alcance desconhecido: {alcance}")
        return media_repo.linha_do_tempo(MediaFilters(
            busca=busca, extensao=extensao, source_id=source_id, ano=ano,
            trip_id=trip_id, event_id=event_id, lacuna=lacuna, alcance=alcance,
        ))

    @app.get("/api/panorama")
    def panorama() -> dict:
        return media_repo.panorama()

    @app.get("/api/inventario")
    def inventario() -> dict:
        """O acervo inteiro, alcançável ou não.

        O Panorama respondia só sobre o que dá para abrir agora. Num acervo
        em NAS e discos externos isso é a minoria — 5.191 de 100.164 num caso
        real —, e a pergunta de quem está descobrindo é outra: o que existe,
        e onde.
        """
        inv = levantar(session_factory)
        return {
            "fotos": inv.fotos,
            "alcancaveis": inv.alcancaveis,
            "registros": inv.total_registros,
            "sem_caminho": inv.sem_caminho,
            "lugares": [
                {
                    "raiz": lugar.raiz,
                    "fotos": lugar.fotos,
                    "alcancaveis": lugar.alcancaveis,
                    "so_no_catalogo": lugar.so_no_catalogo,
                    "fontes": list(lugar.fontes),
                }
                for lugar in inv.lugares
            ],
        }

    @app.get("/api/midia/{media_id}")
    def detalhe_midia(media_id: int) -> dict:
        media = media_repo.por_id(media_id)
        if media is None:
            raise HTTPException(404, "foto não encontrada")
        detalhe = _media_json(media, _fontes_fora_de_alcance())
        with session_factory() as session:
            # Só no detalhe: na grade isto seria uma consulta por miniatura.
            # O lugar pode ter vindo de GPS próprio ou herdado de outra
            # câmera — qual dos dois foi está nas evidências, abaixo.
            if media.location_id is not None:
                local = session.get(Location, media.location_id)
                if local is not None:
                    # Lugar herdado só é entregue até onde o Δt sustenta
                    # (D-025). Devolver a cidade quando a evidência só afirma
                    # o país mostraria na tela uma precisão que ninguém apurou.
                    pode = _campos_do_lugar(media)
                    detalhe["local"] = {
                        "pais": local.pais if "pais" in pode else None,
                        "regiao": local.regiao if "regiao" in pode else None,
                        "cidade": local.cidade if "cidade" in pode else None,
                        "fonte": local.fonte,
                        "estimado": media.coordenada_estimada,
                        "granularidade": pode[-1] if pode else None,
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

    @app.post("/api/midia/{media_id}/tipo")
    def confirmar_tipo(media_id: int, body: TipoBody) -> dict:
        """A palavra do usuário sobre o que a imagem é.

        Grava em `tipo_confirmado`, que nenhuma geração de sugestões
        sobrescreve — ao contrário de `tipo_imagem`, que é a opinião do
        detector e é recalculada a cada passagem. `tipo: null` devolve a
        decisão ao detector.
        """
        if body.tipo is not None and body.tipo not in TIPOS_VALIDOS:
            raise HTTPException(422, f"tipo desconhecido: {body.tipo}")
        with session_factory() as session:
            media = session.get(MediaFile, media_id)
            if media is None:
                raise HTTPException(404, "foto não encontrada")
            media.tipo_confirmado = body.tipo
            media.tipo_confirmado_em = (
                datetime.now(timezone.utc).replace(tzinfo=None)
                if body.tipo else None
            )
            session.commit()
            return {
                "tipo_imagem": media.tipo_efetivo,
                "tipo_provisorio": media.tipo_provisorio,
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

    def _agrupamentos(session, modelo, coluna,
                      source_id: int | None = None) -> list[dict]:
        # Uma consulta agregada para o recorte inteiro, não uma por grupo:
        # ~190 grupos (viagens+eventos) faziam ~190 SELECT COUNT separados —
        # N+1 clássico, e sem índice em trip_id/event_id cada um era um SCAN
        # completo de 477 mil linhas (D-069 achado 3, D-072).
        filtro_contagem = [coluna.is_not(None)]
        if source_id is not None:
            filtro_contagem.append(MediaFile.source_id == source_id)
        contagens = dict(session.execute(
            select(coluna, func.count(MediaFile.id))
            .where(*filtro_contagem)
            .group_by(coluna)
        ).all())

        resultado = []
        for grupo in session.scalars(select(modelo).order_by(modelo.inicio)):
            contagem = contagens.get(grupo.id, 0)
            # Grupo sem nenhuma foto da fonte escolhida não é resultado vazio,
            # é um grupo que não pertence a este recorte.
            if source_id is not None and contagem == 0:
                continue
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
    def viagens(source_id: int | None = None) -> list[dict]:
        with session_factory() as session:
            return _agrupamentos(session, Trip, MediaFile.trip_id, source_id)

    @app.get("/api/eventos")
    def eventos(source_id: int | None = None) -> list[dict]:
        with session_factory() as session:
            return _agrupamentos(session, Event, MediaFile.event_id, source_id)

    # -- mapa do lugar (lido × estimado) -------------------------------------
    @app.get("/api/mapa")
    def mapa(trip_id: int | None = None, event_id: int | None = None) -> dict:
        """A geometria do lugar de UM grupo: pontos, círculos e doadoras.

        Um grupo por vez, e não o acervo inteiro, por duas razões: sem
        cartografia real (D-031) 5.191 pontos numa tela só não têm escala em
        que informem nada, e o grupo (viagem ou evento) já é a unidade da
        navegação — é o card que o usuário abriu.

        Só lê. Não recalcula herança (ela está no banco desde a geração de
        sugestões), não escreve nada, não toca em arquivo. O raio e a frase
        que o explica vêm de `grouping/correlacao.py`, a mesma função pura
        que a calibração mediu — a UI não remonta nenhum dos dois.
        """
        if (trip_id is None) == (event_id is None):
            raise HTTPException(422, "informe trip_id OU event_id")

        fontes_off = _fontes_fora_de_alcance()
        with session_factory() as session:
            if trip_id is not None:
                grupo, tipo = session.get(Trip, trip_id), "viagem"
                coluna, valor = MediaFile.trip_id, trip_id
            else:
                grupo, tipo = session.get(Event, event_id), "evento"
                coluna, valor = MediaFile.event_id, event_id
            if grupo is None:
                raise HTTPException(404, "grupo não encontrado")

            fotos = list(session.scalars(
                select(MediaFile).where(coluna == valor)
                .order_by(MediaFile.data_capturada, MediaFile.id)
            ))

            # Passo 1: quem tem coordenada é desenhado; quem não tem é
            # contado. Estar fora de alcance NÃO tira a foto do mapa: o
            # arquivo é que sumiu, a coordenada continua no catálogo, e
            # esconder o ponto por causa de um disco desligado apagaria da
            # tela justamente a informação que o catálogo guardou (invariante
            # 8). Medido: o evento "Pantanal" tem 80 das 97 fotos em
            # /Volumes/Externo — excluí-las deixaria o mapa VAZIO com todas
            # as coordenadas conhecidas. O ponto vai com `motivo_indisponivel`
            # para a tela dizer por que não há miniatura, como a grade já faz.
            desenhaveis: list[tuple[MediaFile, tuple[float, float]]] = []
            sem_coordenada = fora_de_alcance = 0
            for media in fotos:
                coordenada = media.coordenada
                if coordenada is None:
                    sem_coordenada += 1
                    continue
                if _motivo_indisponivel(media, fontes_off) is not None:
                    fora_de_alcance += 1
                desenhaveis.append((media, coordenada))

            # Passo 2: as doadoras, numa consulta só. Uma por ponto herdado
            # seria N+1 numa viagem de 2.406 fotos.
            ids_doadoras = {
                media.gps_estimado_de_id for media, _ in desenhaveis
                if media.coordenada_estimada
                and media.gps_estimado_de_id is not None
            }
            doadoras = {
                d.id: d for d in session.scalars(
                    select(MediaFile).where(MediaFile.id.in_(ids_doadoras))
                )
            } if ids_doadoras else {}

            pontos = [
                _ponto_do_mapa(media, coordenada, doadoras,
                               _motivo_indisponivel(media, fontes_off))
                for media, coordenada in desenhaveis
            ]

        return {
            "grupo": {
                "tipo": tipo,
                "id": grupo.id,
                "nome": grupo.nome,
                "inicio": grupo.inicio.isoformat() if grupo.inicio else None,
                "fim": grupo.fim.isoformat() if grupo.fim else None,
            },
            "contagens": {
                "total": len(fotos),
                # `no_mapa + sem_coordenada == total`. `fora_de_alcance` é um
                # SUBCONJUNTO de `no_mapa`: desenhadas, mas sem miniatura para
                # mostrar. Duas perguntas diferentes, dois números — o que não
                # cabe é qualquer uma delas sumir em silêncio (aceite 6).
                "no_mapa": len(pontos),
                "sem_coordenada": sem_coordenada,
                "fora_de_alcance": fora_de_alcance,
            },
            "pontos": pontos,
            # A doadora costuma estar FORA do grupo (no acervo real ela é uma
            # referência do Apple Fotos, sem viagem nem evento). Sem esta
            # lista o traço do protótipo não teria a outra ponta.
            "doadoras": [
                {
                    "id": d.id,
                    "nome": d.nome,
                    "lat": d.gps_lat,
                    "lon": d.gps_lon,
                    "camera": nome_da_camera(d.make, d.model),
                    # Ela também é um dos pontos desenhados, ou vem de fora?
                    "no_grupo": (
                        d.trip_id if trip_id is not None else d.event_id
                    ) == valor,
                }
                for d in doadoras.values()
            ],
            **_enquadramento(pontos),
            "nota_do_raio": NOTA_DO_RAIO,
        }

    # -- configurações: template de destino (fase 10) ------------------------
    @app.get("/api/configuracoes/template")
    def obter_template() -> dict:
        return {"template": settings_repo.obter_template(TEMPLATE_PADRAO)}

    @app.put("/api/configuracoes/template")
    def salvar_template(body: TemplateBody) -> dict:
        template = body.template.strip()
        if not template:
            raise HTTPException(422, "template não pode ser vazio")
        invalidos = _placeholders_invalidos(template)
        if invalidos:
            nomes = ", ".join(
                "{" + p + "}" for p in sorted(invalidos)
            )
            raise HTTPException(
                422, f"placeholder inválido: {nomes}"
            )
        # Intencional: não regenera sugestões aqui — trocar o texto no
        # editor não pode disparar um job pesado a cada tecla/salvar.
        # Regenerar é ação explícita separada (POST /api/sugestoes/gerar).
        settings_repo.salvar_template(template)
        return {"template": template}

    @app.post("/api/configuracoes/template/preview")
    def preview_template(body: TemplateBody) -> dict:
        return {
            "exemplos": [
                {**exemplo, "destino": render_destino(body.template, exemplo["campos"])}
                for exemplo in _EXEMPLOS_PREVIEW_TEMPLATE
            ]
        }

    # -- sugestões e duplicatas (leitura; ações nas fatias seguintes) --------
    @app.get("/api/sugestoes")
    def sugestoes(status: str = "pendente", source_id: int | None = None,
                  destino: str | None = None,
                  offset: int = 0,
                  limit: int = 200) -> dict:
        try:
            status_enum = SuggestionStatus(status)
        except ValueError:
            raise HTTPException(422, f"status inválido: {status}")
        # `destino` recorta um grupo: é o que permite abrir "Dubai" e
        # paginar dentro das 2.406 sem carregar a fila inteira.
        filters = SuggestionFilters(
            status=status_enum, source_id=source_id, destino=destino
        )
        linhas = suggestion_repo.listar(
            filters, limit=max(1, min(limit, 500)), offset=offset
        )
        contagens = suggestion_repo.contagens_por_status()
        fora = _fontes_fora_de_alcance()
        return {
            "contagens": {s.value: n for s, n in contagens.items()},
            # O total do RECORTE, para a tela nunca mais deduzir tamanho de
            # grupo a partir do que a página trouxe.
            "total": suggestion_repo.contar(filters),
            "itens": [_sugestao_json(linha, fora) for linha in linhas],
        }

    @app.get("/api/duplicatas")
    def duplicatas() -> list[dict]:
        return [
            {
                "id": grupo.id,
                "nivel": grupo.nivel.value,
                "rotulo": grupo.rotulo_nivel,
                "decidido": grupo.decidido,
                "resolvido_automaticamente": grupo.resolvido_automaticamente,
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
        if body.destino is not None:
            # O grupo inteiro, resolvido no banco. `status` importa: um
            # "desfazer" age sobre aprovadas, não sobre pendentes.
            try:
                status_enum = SuggestionStatus(body.status)
            except ValueError:
                raise HTTPException(422, f"status inválido: {body.status}")
            filtros = SuggestionFilters(
                status=status_enum, source_id=body.source_id,
                destino=body.destino,
            )
            return {"afetadas": suggestion_repo.aplicar_em_lote(filtros, body.acao)}
        if not body.ids:
            raise HTTPException(422, "informe `ids` ou `destino`")
        return {"afetadas": acoes[body.acao](body.ids)}

    @app.get("/api/sugestoes/grupos")
    def grupos_de_sugestoes(status: str = "pendente",
                            source_id: int | None = None) -> list[dict]:
        """Um resumo por destino, com a contagem VERDADEIRA de cada grupo.

        A tela pedia 200 itens e deduzia o tamanho do grupo do que tinha
        chegado: no acervo real isso mostrava 3 dos 10 grupos, dizia "85
        fotos" para um de 597, e deixava 4.848 das 5.048 pendências sem
        nenhum gesto que chegasse até elas.
        """
        try:
            status_enum = SuggestionStatus(status)
        except ValueError:
            raise HTTPException(422, f"status inválido: {status}")
        filtros = SuggestionFilters(status=status_enum, source_id=source_id)
        return [
            {
                "destino": g.destino,
                "total": g.total,
                "nivel": g.nivel.value,
                "estimadas": g.estimadas,
                "fora_de_alcance": g.fora_de_alcance,
                "origens": [{"pasta": p, "fotos": n} for p, n in g.origens],
            }
            for g in suggestion_repo.grupos(filtros)
        ]

    @app.patch("/api/sugestoes/{suggestion_id}/destino")
    def editar_destino_sugestao(suggestion_id: int, body: EditarDestinoBody) -> dict:
        # Mesma sanitização/segurança de caminho do planejador (invariante
        # 5): sem isto, um destino como "../../../etc" só seria pego na
        # hora do plano, e mesmo assim só como "conflito", não recusa.
        try:
            destino = str(caminho_relativo_seguro(body.destino))
        except CaminhoInvalido as exc:
            raise HTTPException(422, str(exc))
        atualizada = suggestion_repo.editar_destino(suggestion_id, destino)
        if atualizada is None:
            raise HTTPException(404, "sugestão não encontrada")
        return _sugestao_json(atualizada, _fontes_fora_de_alcance())

    @app.post("/api/duplicatas/detectar")
    def detectar_duplicatas() -> dict:
        if not jobs.iniciar_duplicatas():
            raise HTTPException(409, "já existe um trabalho em andamento")
        return jobs.estado()

    @app.post("/api/reconciliacao")
    def iniciar_reconciliacao() -> dict:
        """Uma passada da varredura de alcance: confere se arquivos
        catalogados ainda existem, sem reler metadado nem hash. Auto-
        limitada — termina sozinha dentro do orçamento e retoma na próxima
        chamada de onde parou (checkpoint em `application_settings`)."""
        if not jobs.iniciar_reconciliacao():
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

    @app.get("/api/scan/interrompidos")
    def scans_interrompidos() -> list[dict]:
        """Varreduras que morreram com o processo, uma por fonte.

        Só a sessão MAIS RECENTE de cada fonte conta: se um scan posterior
        concluiu, a interrupção antiga é história, não pendência. A
        retomada é um novo POST /api/scan no mesmo caminho — o incremental
        pula o que já foi indexado.
        """
        from fotoorganizer.models import ScanSession, ScanStatus

        with session_factory() as session:
            ultimas = select(func.max(ScanSession.id)).group_by(
                ScanSession.source_id
            )
            linhas = session.execute(
                select(ScanSession, Source)
                .join(Source, Source.id == ScanSession.source_id)
                .where(
                    ScanSession.id.in_(ultimas),
                    ScanSession.status == ScanStatus.INTERROMPIDO,
                )
                .order_by(ScanSession.finalizado_em.desc())
            )
            return [
                {
                    "source_id": fonte.id,
                    "caminho": fonte.caminho,
                    "apelido": fonte.apelido or Path(fonte.caminho).name,
                    "disponivel": fonte.disponivel,
                    "quando": (
                        scan.finalizado_em.isoformat()
                        if scan.finalizado_em else None
                    ),
                    "vistos": scan.arquivos_vistos,
                    "indexados": scan.arquivos_indexados,
                }
                for scan, fonte in linhas
            ]

    @app.get("/api/job")
    def job_estado() -> dict:
        return jobs.estado()

    @app.post("/api/job/cancelar")
    def job_cancelar() -> dict:
        jobs.cancelar()
        return jobs.estado()

    @app.post("/api/job/pausar")
    def job_pausar() -> dict:
        if not jobs.pausar():
            raise HTTPException(409, "nenhum scan em andamento para pausar")
        return jobs.estado()

    @app.post("/api/job/continuar")
    def job_continuar() -> dict:
        if not jobs.continuar():
            raise HTTPException(409, "nenhum scan pausado para continuar")
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

    @app.on_event("startup")
    def _reconciliar_scans() -> None:
        """RODANDO no banco com o servidor nascendo agora é sempre órfã:
        vira INTERROMPIDO, e a UI oferece a retomada. Sem isto o catálogo
        mente sobre trabalho em curso — para sempre."""
        from fotoorganizer.scanner import reconciliar_orfas

        try:
            reconciliar_orfas(session_factory)
        except Exception:
            log.warning("não consegui reconciliar sessões de scan órfãs",
                        exc_info=True)

    @app.on_event("startup")
    def _conferir_fontes() -> None:
        """Quem está ao alcance agora, uma vez ao abrir.

        Sem isto, `Source.disponivel` guarda o estado da última verificação —
        e o usuário que plugou o disco antes de abrir o app veria tudo como
        fora de alcance. Custa um `diskutil` por fonte, no boot."""
        try:
            estados = verificar(session_factory)
        except Exception:
            log.warning("não consegui conferir as fontes ao abrir",
                        exc_info=True)
            return
        fora = [e for e in estados if not e.disponivel]
        if fora:
            log.info("fontes fora de alcance: %s",
                     ", ".join(f"{e.apelido} ({e.resumo()})" for e in fora))

    return app
