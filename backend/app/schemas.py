"""Schemas Pydantic — request/response da API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ScanRequest(BaseModel):
    diretorios: list[str]


class ScanResponse(BaseModel):
    diretorios_varridos: list[str]
    fotos_encontradas: int
    fotos_novas: int
    fotos_ja_catalogadas: int
    fotos_com_erro: int


class PhotoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    caminho_original: str
    nome_arquivo: str
    tamanho_bytes: int
    hash_md5: str
    hash_perceptual: str | None
    data_exif: datetime | None
    localizacao_exif: str | None
    data_arquivo: datetime
    pasta_fonte: str
    sugestao_agrupamento: str | None
    score_confianca: float | None
