from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column

from fotoorganizer.models.base import Base, utcnow


class NomeClassificado(Base):
    """O que uma palavra é — lugar, ocasião, pessoa ou ruído.

    Cache do léxico (`fotoorganizer/classification/lexico.py`). A chave é o
    NOME, não a foto nem a sessão: um acervo inteiro tem uma centena de
    nomes distintos de pasta e álbum, então classificá-los uma vez resolve
    todas as sessões e todas as regenerações futuras.

    Guardar também a justificativa e a origem é o que torna o resultado
    revisável: o dono consegue ver por que "Pantanal" virou lugar, e
    corrigir com `origem='manual'` sem que a próxima consulta desfaça a
    correção.
    """

    __tablename__ = "nomes_classificados"

    nome: Mapped[str] = mapped_column(primary_key=True)
    categoria: Mapped[str]
    justificativa: Mapped[str | None]
    # 'llm' | 'manual'. A correção do dono nunca é sobrescrita pela máquina.
    origem: Mapped[str] = mapped_column(default="llm")
    classificado_em: Mapped[datetime] = mapped_column(default=utcnow)
