"""Fontes, sessões de varredura e arquivos de mídia — o coração do catálogo."""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    JSON,
    Enum,
    ForeignKey,
    Index,
    Text,
    UniqueConstraint,
    and_,
)
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fotoorganizer.models.base import Base, utcnow


class ScanStatus(enum.StrEnum):
    RODANDO = "rodando"
    PAUSADO = "pausado"
    CONCLUIDO = "concluido"
    ERRO = "erro"
    # O processo morreu com a varredura em curso (app fechado, queda). É o
    # boot do servidor quem carimba isto: RODANDO no banco sem servidor de
    # pé é sempre órfã — no acervo real, duas sessões ficaram dias assim.
    INTERROMPIDO = "interrompido"


class SourceType(enum.StrEnum):
    """De onde vem uma fonte de fotos. Fontes externas (catálogos de outros
    apps) entram no MESMO catálogo — o cruzamento entre fontes é o que
    permite usar a informação mais correta disponível para cada foto."""

    PASTA = "pasta"
    APPLE_PHOTOS = "apple_photos"
    GOOGLE_TAKEOUT = "google_takeout"
    LIGHTROOM = "lightroom"


class MediaRole(enum.StrEnum):
    """O que um registro é para o catálogo — acervo ou testemunha.

    ACERVO é foto do usuário: entra na grade, na revisão e no plano de cópia.

    SINAL não é acervo — miniatura interna de outro app, derivado de
    biblioteca, referência de catálogo externo. Fica fora de tudo que
    organiza e continua doando data, GPS e correlação.

    A separação existe porque as duas coisas se misturaram: 89% do acervo
    local eram miniaturas 540×360 do pacote do Apple Fotos, e elas inundaram
    a revisão. Apagá-las seria pior — são a única testemunha do lugar de
    milhares de fotos sem GPS próprio (invariante 8, D-024).
    """

    ACERVO = "acervo"
    SINAL = "sinal"


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
    # Alcançável AGORA. Um HD na gaveta é indisponível, não perdido — e a
    # diferença muda o que a interface deve dizer ao usuário.
    disponivel: Mapped[bool] = mapped_column(default=True)
    # Identidade do volume (`security/volumes.py`): "uuid:…", "rede:…" ou
    # "caminho:…". É ela que reencontra um disco que voltou noutro ponto de
    # montagem — com o caminho como identidade, remontar vira disco novo e
    # 45 mil fotos são recatalogadas do zero.
    volume_id: Mapped[str | None]
    volume_nome: Mapped[str | None]
    visto_em: Mapped[datetime | None]
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
        Index("ix_media_files_papel", "papel"),
        # Mesma razão de `ix_media_files_papel`: entra em `organizavel`, que
        # é filtrado em SQL sobre o acervo inteiro (alcance=organizaveis/
        # faltantes na Biblioteca). Coluna booleana é barata de indexar e a
        # consulta de "faltantes" — a tela que este campo existe para servir
        # — filtra exatamente por ela.
        Index("ix_media_files_arquivo_offline", "arquivo_offline"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"))
    caminho: Mapped[str] = mapped_column(Text)
    # Referência: a foto existe no catálogo externo (iCloud) mas não há
    # arquivo no disco. Ela doa horário e GPS para a correlação e fica fora
    # de grade, miniatura, duplicata e plano de cópia — não há o que copiar.
    arquivo_ausente: Mapped[bool] = mapped_column(default=False)
    # O terceiro estado de alcance (o outro é `Source.disponivel`, abaixo):
    # a FONTE está montada e este arquivo específico sumiu de onde estava —
    # apagado, movido para fora, renomeado por outro programa. Diferente de
    # `arquivo_ausente` (nunca teve arquivo local, é referência de nuvem) e
    # de `Source.disponivel` (a fonte INTEIRA fora de alcance): aqui é UM
    # registro, e a fonte continua respondendo. Sem isto, um arquivo apagado
    # ficava indistinguível de "sempre esteve lá" — ninguém verificava de
    # novo. Mantido por dois mecanismos complementares: o scan normal marca
    # quem não apareceu no walk desta passada (`scanner/scanner.py`), e o
    # laço de reconciliação confere periodicamente sem esperar um scan
    # manual (`scanner/reconciliacao.py`). Nunca apaga o registro nem seus
    # metadados (invariante 8) — volta a `False` sozinho se o arquivo
    # reaparecer.
    arquivo_offline: Mapped[bool] = mapped_column(default=False)
    # Acervo ou testemunha. Ortogonal a `arquivo_ausente`: uma miniatura do
    # pacote do Apple Fotos existe no disco e mesmo assim não é acervo.
    papel: Mapped[MediaRole] = mapped_column(
        Enum(MediaRole, native_enum=False), default=MediaRole.ACERVO
    )
    volume: Mapped[str | None]
    pasta: Mapped[str] = mapped_column(Text)
    nome: Mapped[str]
    extensao: Mapped[str]
    tamanho: Mapped[int]
    inode: Mapped[int | None]
    ctime: Mapped[datetime | None]
    mtime: Mapped[datetime | None]
    # A hora de PAREDE da captura: a que o relógio marcava no lugar onde a
    # foto foi tirada, sem fuso. É esta que ordena a grade e agrupa evento e
    # viagem — 8 da manhã em Roma e 8 da manhã no Rio são a mesma manhã para
    # quem viveu as duas. Todos os extratores já entregam assim; o EXIF não
    # tem fuso, e `sources/apple_photos.py` descarta de propósito o do Apple
    # Fotos ("coerente com EXIF no resto do catálogo").
    data_capturada: Mapped[datetime | None]
    # O MESMO instante, absoluto (UTC), gravado naive como todo datetime
    # deste catálogo. Dois instantes e nenhuma coluna de offset: o offset é a
    # DIFERENÇA entre os dois. Guardá-lo em coluna própria criaria um terceiro
    # lugar para a mesma verdade, livre para discordar dos outros dois em
    # silêncio — foi assim que o Immich resolveu e é a parte do desenho deles
    # que vale copiar (`docs/referencia-immich/03-modelo-de-dados.md` §3).
    #
    # Hoje os dois são iguais na maioria das linhas: **sem fuso conhecido, os
    # dois instantes são iguais**, e é justamente a igualdade que diz "não sei
    # o fuso desta foto" — nunca "esta foto foi tirada em UTC". Quem derivar o
    # offset precisa ler zero como desconhecido, não como Greenwich.
    #
    # O preço disso, dito em voz alta: fuso REAL de +00:00 fica indistinguível
    # de desconhecido — Londres e Lisboa no inverno, Islândia, Marrocos. É
    # limitação inerente ao padrão (o `keepLocalTime` do Immich tem a mesma) e
    # está aceita. A saída não é uma terceira coluna de offset: é `tz_estimado`
    # — quando a fase 11 existir, o sinal de "fuso conhecido" é
    # `tz_estimado IS NOT NULL`, nunca a diferença entre estas duas datas.
    #
    # Quem hoje sabe o fuso de verdade: o Apple Fotos, que guarda offset e
    # nome de zona POR FOTO e chega via osxphotos em `photo.date`. O EXIF
    # (`OffsetTimeOriginal`) e o QuickTime também trazem, às vezes, e ainda
    # não são lidos — fica para a fase 11, que já mexe em fuso (D-038).
    #
    # Sem índice de propósito: ordenação, recorte por mês/ano e agrupamento
    # usam a hora local (`ix_media_files_data_capturada`), e não há consulta
    # que filtre por esta coluna. Índice sem consumidor é custo de escrita em
    # 101 mil linhas em troca de nada.
    data_capturada_utc: Mapped[datetime | None]
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
    # O que o DETECTOR concluiu: foto | captura | recebida | baixada.
    # NULL = ainda não avaliado. Reescrito a cada geração de sugestões.
    tipo_imagem: Mapped[str | None]
    # O que o USUÁRIO disse. Nada no motor sobrescreve isto — é o que separa
    # "o sistema achou" de "eu decidi".
    tipo_confirmado: Mapped[str | None]
    tipo_confirmado_em: Mapped[datetime | None]
    hash_rapido: Mapped[str | None]
    hash_sha256: Mapped[str | None]
    # phash 64-bit em hex — calculado sob demanda pela detecção de duplicatas.
    hash_perceptual: Mapped[str | None]
    status_revisao: Mapped[ReviewStatus] = mapped_column(
        Enum(ReviewStatus, native_enum=False), default=ReviewStatus.NAO_REVISADO
    )
    erro_leitura: Mapped[str | None] = mapped_column(Text)
    indexado_em: Mapped[datetime] = mapped_column(default=utcnow)

    @hybrid_property
    def organizavel(self) -> bool:
        """Entra na grade, na revisão e no plano de cópia.

        Uma referência sem arquivo não tem o que copiar; uma miniatura tem
        arquivo e ainda assim não é acervo; um arquivo que sumiu não tem o
        que copiar AGORA, mesmo que volte depois. As três ficam de fora.

        É `hybrid` para valer nos dois lados: em memória ao percorrer mídias,
        e em SQL dentro de um WHERE. Filtrar por lista de ids em Python
        estourou o limite de variáveis do SQLite num acervo real — a
        condição precisa poder descer para o banco.
        """
        return (
            self.papel == MediaRole.ACERVO
            and not self.arquivo_ausente
            and not self.arquivo_offline
        )

    @organizavel.inplace.expression
    @classmethod
    def _organizavel_sql(cls):
        return and_(
            cls.papel == MediaRole.ACERVO,
            cls.arquivo_ausente.is_(False),
            cls.arquivo_offline.is_(False),
        )

    @property
    def tipo_efetivo(self) -> str | None:
        """O tipo que vale: o do usuário, senão o do detector."""
        return self.tipo_confirmado or self.tipo_imagem

    @property
    def tipo_provisorio(self) -> bool:
        """True quando o detector opinou e o usuário ainda não respondeu.

        É o que permite a interface perguntar em vez de afirmar.
        """
        return self.tipo_confirmado is None and self.tipo_imagem is not None

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
