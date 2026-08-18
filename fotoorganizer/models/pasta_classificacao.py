from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column

from fotoorganizer.models.base import Base, utcnow


class PastaClassificada(Base):
    """O que o GenAI de pasta propôs para uma pasta — cidade, país,
    categoria e/ou evento.

    A chave é o CAMINHO DA PASTA, não `media_id`: a classificação é da
    pasta, uma linha só serve todas as fotos dela — mesmo raciocínio de
    `NomeClassificado`, aplicado a caminho em vez de nome de segmento.

    A tabela existe porque `SuggestionEngine._persistir_sugestao()` apaga e
    reconstrói `Evidence` a cada `gerar()` — gravar o resultado do Claude
    direto em `Evidence` faria ele sumir na próxima regeneração e obrigaria
    a pagar de novo pela mesma chamada (D-07). Esta tabela sobrevive à
    regeneração; `Evidence` é reconstruída a partir dela sem nova chamada
    à API.

    `status` é um eixo separado de `origem`: `origem` responde "quem
    produziu o valor" (máquina ou dono) e `status` responde "o dono
    aceitou?". A evidência gerada na cascata continua com origem
    `llm_pasta` mesmo depois de aprovada — aprovar não transforma o
    palpite da máquina em palavra do dono (GENAI-03).
    """

    __tablename__ = "pasta_classificacoes_genai"

    pasta: Mapped[str] = mapped_column(primary_key=True)
    cidade: Mapped[str | None]
    pais: Mapped[str | None]
    categoria: Mapped[str | None]
    evento: Mapped[str | None]
    justificativa: Mapped[str]
    # 'llm' | 'manual'. A correção do dono nunca é sobrescrita pela máquina.
    origem: Mapped[str] = mapped_column(default="llm")
    # 'proposta' | 'aprovada' | 'descartada'. Só 'aprovada' é lida pela
    # cascata (T-07-01-02) — proposta e descartada são dado morto no banco,
    # nunca removido (invariante 8).
    status: Mapped[str] = mapped_column(default="proposta")
    # Carimbo ISO-8601 da rodada (sessão) que gerou a proposta.
    sessao: Mapped[str]
    classificado_em: Mapped[datetime] = mapped_column(default=utcnow)
