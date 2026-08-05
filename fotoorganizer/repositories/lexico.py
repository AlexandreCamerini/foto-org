"""Cache do léxico de nomes — o que já foi classificado não volta a sair.

Ver `fotoorganizer/classification/lexico.py` para o porquê da classificação
e para o contrato de privacidade.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from fotoorganizer.models import NomeClassificado


class LexicoRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._factory = session_factory

    def conhecidos(self) -> dict[str, str]:
        """{nome: categoria} de tudo que já foi classificado."""
        with self._factory() as session:
            return {
                n.nome: n.categoria
                for n in session.scalars(select(NomeClassificado))
            }

    def faltantes(self, nomes: set[str]) -> list[str]:
        """O que ainda não tem classificação — é isto, e só isto, que sai
        da máquina."""
        return sorted(nomes - set(self.conhecidos()))

    def salvar(self, categorias: dict[str, str],
               justificativas: dict[str, str] | None = None,
               origem: str = "llm") -> int:
        """Grava, sem sobrescrever correção manual do dono.

        A máquina propõe; o dono decide. Uma linha com `origem='manual'`
        sobrevive a qualquer reclassificação posterior — senão a próxima
        consulta desfaria a correção em silêncio.
        """
        justificativas = justificativas or {}
        gravadas = 0
        with self._factory() as session:
            for nome, categoria in categorias.items():
                atual = session.get(NomeClassificado, nome)
                if atual is not None:
                    if atual.origem == "manual" and origem != "manual":
                        continue
                    atual.categoria = categoria
                    atual.justificativa = justificativas.get(nome)
                    atual.origem = origem
                else:
                    session.add(NomeClassificado(
                        nome=nome, categoria=categoria,
                        justificativa=justificativas.get(nome), origem=origem,
                    ))
                gravadas += 1
            session.commit()
        return gravadas
