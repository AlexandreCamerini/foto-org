"""Organizador de Fotos — backend FastAPI.

Roda manualmente na porta 8000 (`uvicorn app.main:app --reload`, a partir de
`backend/`). Sem autenticação/deploy — ferramenta de uso local, no seu Mac.
"""

from __future__ import annotations

import logging

from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session

from app.database import get_db, init_db
from app.duplicates import find_all_duplicates
from app.models import Photo
from app.scanner import scan_directories
from app.schemas import PhotoOut, ScanRequest, ScanResponse
from app.suggestions import gerar_sugestoes

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("foto-organizer")

app = FastAPI(title="Organizador de Fotos", version="0.1.0")


@app.on_event("startup")
def _on_startup() -> None:
    init_db()


@app.get("/", include_in_schema=False)
def root() -> dict:
    return {"status": "ok", "docs": "/docs"}


@app.post("/scan", response_model=ScanResponse)
def scan(request: ScanRequest, db: Session = Depends(get_db)) -> ScanResponse:
    """Varre os diretórios recebidos, cataloga fotos novas (por caminho) e
    recalcula as sugestões de agrupamento pra coleção inteira — o agrupamento
    por viagem depende da linha do tempo completa, não só do que é novo."""
    encontradas = scan_directories(request.diretorios)

    novas = 0
    ja_catalogadas = 0
    com_erro = 0

    for foto in encontradas:
        try:
            existente = db.query(Photo).filter_by(caminho_original=foto.caminho_original).first()
            if existente:
                ja_catalogadas += 1
                continue
            db.add(
                Photo(
                    caminho_original=foto.caminho_original,
                    nome_arquivo=foto.nome_arquivo,
                    tamanho_bytes=foto.tamanho_bytes,
                    hash_md5=foto.hash_md5,
                    hash_perceptual=foto.hash_perceptual,
                    data_exif=foto.data_exif,
                    localizacao_exif=foto.localizacao_exif,
                    data_arquivo=foto.data_arquivo,
                    pasta_fonte=foto.pasta_fonte,
                )
            )
            novas += 1
        except Exception:
            logger.exception("Falha ao catalogar %s", foto.caminho_original)
            com_erro += 1

    db.commit()

    # Recalcula sugestão/score pra todo mundo (o agrupamento por viagem olha
    # a linha do tempo inteira) e persiste como cache — /suggestions também
    # recalcula na hora, então isto é só pra /photos já vir com o campo
    # preenchido sem precisar chamar /suggestions antes.
    todas_as_fotos = db.query(Photo).all()
    for sugestao in gerar_sugestoes(todas_as_fotos):
        db.query(Photo).filter_by(id=sugestao["photo_id"]).update(
            {
                "sugestao_agrupamento": sugestao["sugestao_agrupamento"],
                "score_confianca": sugestao["score_confianca"],
            }
        )
    db.commit()

    return ScanResponse(
        diretorios_varridos=request.diretorios,
        fotos_encontradas=len(encontradas),
        fotos_novas=novas,
        fotos_ja_catalogadas=ja_catalogadas,
        fotos_com_erro=com_erro,
    )


@app.get("/photos", response_model=list[PhotoOut])
def listar_fotos(limit: int = 500, offset: int = 0, db: Session = Depends(get_db)) -> list[Photo]:
    return db.query(Photo).order_by(Photo.data_arquivo.desc()).offset(offset).limit(limit).all()


@app.get("/duplicates")
def listar_duplicatas(db: Session = Depends(get_db)) -> dict:
    fotos = db.query(Photo).all()
    return find_all_duplicates(fotos)


@app.get("/suggestions")
def listar_sugestoes(db: Session = Depends(get_db)) -> list[dict]:
    fotos = db.query(Photo).all()
    return gerar_sugestoes(fotos)
