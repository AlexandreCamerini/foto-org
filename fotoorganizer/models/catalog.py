"""Fontes, sessões de varredura e arquivos de mídia — o coração do catálogo."""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import JSON, Enum, ForeignKey, Index, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fotoorganizer.models.base import Base, utcnow


class ScanStatus(enum.StrEnum):
    RODANDO = "rodando"
    PAUSADO = "pausado"
    CONCLUIDO = "concluido"
    ERRO = "erro"


class SourceType(enum.StrEnum):
    """De onde vem uma fonte de fotos. Fontes externas (catálogos de outros
    apps) entram no MESMO catálogo — o cruzamento entre fontes é o que
    permite usar a informação mais correta disponível para cada foto."""

    PASTA = "pasta"
    APPLE_PHOTOS = "apple_photos"
    GOOGLE_TAKEOUT = "google_takeout"


class ReviewStatus(enum.StrEnum):
    NAO_REVISADO = "nao_revisado"
    PENDENTE = "pendente"
    REVISADO = "revisado"


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    caminho: Mapped[str] = mapped_column(Text, unique=True)
    tipo: Mapped[SourceType] = mapped_column(
        Enum(SourceType, native_enum=False), default=SourceType.PASTA
    )
    apelido: Mapped[str | None]
    ativo: Mapped[bool] = mapped_column(default=True)
    disponivel: Mapped[bool] = mapped_column(default=True)
    # Padrões glob de pastas a ignorar dentro desta fonte.
    padroes_ignorados: Mapped[list] = mapped_column(JSON, default=list)
    criado_em: Mapped[datetime] = mapped_column(default=utcnow)

    arquivos: Mapped[list["MediaFile"]] = relationship(back_populates="source")


class ScanSession(Base):
    __tablename__ = "scan_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"))
    status: Mapped[ScanStatus] = mapped_column(
        Enum(ScanStatus, native_enum=False), default=ScanStatus.RODANDO
    )
    iniciado_em: Mapped[datetime] = mapped_column(default=utcnow)
    finalizado_em: Mapped[datetime | None]
    # Último caminho processado + posição — permite retomar após interrupção.
    checkpoint: Mapped[dict | None] = mapped_column(JSON)
    arquivos_vistos: Mapped[int] = mapped_column(default=0)
    arquivos_indexados: Mapped[int] = mapped_column(default=0)
    erros: Mapped[int] = mapped_column(default=0)
    bytes_processados: Mapped[int] = mapped_column(default=0)
    versao_scanner: Mapped[str] = mapped_column(default="")


class MediaFile(Base):
    __tablename__ = "media_files"
    __table_args__ = (
        UniqueConstraint("source_id", "caminho"),
        Index("ix_media_files_hash_rapido", "hash_rapido"),
        Index("ix_media_files_data_capturada", "data_capturada"),
        Index("ix_media_files_mtime_tamanho", "mtime", "tamanho"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"))
    caminho: Mapped[str] = mapped_column(Text)
    # Referência: a foto existe no catálogo externo (iCloud) mas não há
    # arquivo no disco. Ela doa horário e GPS para a correlação e fica fora
    # de grade, miniatura, duplicata e plano de cópia — não há o que copiar.
    arquivo_ausente: Mapped[bool] = mapped_column(default=False)
    volume: Mapped[str | None]
    pasta: Mapped[str] = mapped_column(Text)
    nome: Mapped[str]
    extensao: Mapped[str]
    tamanho: Mapped[int]
    inode: Mapped[int | None]
    ctime: Mapped[datetime | None]
    mtime: Mapped[datetime | None]
    data_capturada: Mapped[datetime | None]
    tz_estimado: Mapped[str | None]
    make: Mapped[str | None]
    model: Mapped[str | None]
    lente: Mapped[str | None]
    orientacao: Mapped[int | None]
    largura: Mapped[int | None]
    altura: Mapped[int | None]
    gps_lat: Mapped[float | None]
    gps_lon: Mapped[float | None]
    # Coordenada HERDADA de outra foto, de outro dispositivo, próxima no
    # tempo. Fica separada de gps_lat/gps_lon porque estimativa e medição não
    # são a mesma coisa — misturar as duas apaga a distinção que o usuário
    # precisa ver antes de aprovar um destino. Ver docs/PLANO_LOCAL_ESTIMADO.md.
    gps_lat_estimado: Mapped[float | None]
    gps_lon_estimado: Mapped[float | None]
    gps_estimado_de_id: Mapped[int | None] = mapped_column(
        ForeignKey("media_files.id")
    )
    # Δt até a foto doadora, JÁ corrigido de deriva de relógio. Em coluna, e
    # não só dentro da justificativa, para poder filtrar por ele.
    gps_estimado_delta_s: Mapped[int | None]
    location_id: Mapped[int | None] = mapped_column(ForeignKey("locations.id"))
    trip_id: Mapped[int | None] = mapped_column(ForeignKey("trips.id"))
    event_id: Mapped[int | None] = mapped_column(ForeignKey("events.id"))
    # foto | captura | recebida | baixada. NULL = ainda não avaliado.
    # Ver fotoorganizer/classification/tipo_imagem.py.
    tipo_imagem: Mapped[str | None]
    hash_rapido: Mapped[str | None]
    hash_sha256: Mapped[str | None]
    # phash 64-bit em hex — calculado sob demanda pela detecção de duplicatas.
    hash_perceptual: Mapped[str | None]
    status_revisao: Mapped[ReviewStatus] = mapped_column(
        Enum(ReviewStatus, native_enum=False), default=ReviewStatus.NAO_REVISADO
    )
    erro_leitura: Mapped[str | None] = mapped_column(Text)
    indexado_em: Mapped[datetime] = mapped_column(default=utcnow)

    @property
    def coordenada(self) -> tuple[float, float] | None:
        """A coordenada que vale para esta foto: a lida, senão a estimada."""
        if self.gps_lat is not None:
            return self.gps_lat, self.gps_lon
        if self.gps_lat_estimado is not None:
            return self.gps_lat_estimado, self.gps_lon_estimado
        return None

    @property
    def coordenada_estimada(self) -> bool:
        """True quando o lugar veio de outra foto, não do arquivo."""
        return self.gps_lat is None and self.gps_lat_estimado is not None

    source: Mapped[Source] = relationship(back_populates="arquivos")
    metadados: Mapped[list["MetadataEntry"]] = relationship(
        back_populates="media", cascade="all, delete-orphan"
    )


class MetadataEntry(Base):
    __tablename__ = "metadata_entries"
    __table_args__ = (Index("ix_metadata_entries_media_id", "media_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    media_id: Mapped[int] = mapped_column(ForeignKey("media_files.id"))
    # exif | iptc | xmp | fs
    namespace: Mapped[str]
    chave: Mapped[str]
    valor: Mapped[str | None] = mapped_column(Text)

    media: Mapped[MediaFile] = relationship(back_populates="metadados")
