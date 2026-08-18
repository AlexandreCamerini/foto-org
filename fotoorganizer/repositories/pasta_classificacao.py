"""Persistência do GenAI de pasta — o que já foi proposto não sai de novo,
e o que foi aprovado é o único que a cascata lê.

Ver `fotoorganizer/models/pasta_classificacao.py` para o porquê da tabela
(D-07) e o eixo origem/status.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from fotoorganizer.models import PastaClassificada


@dataclass(frozen=True, slots=True)
class PropostaDePasta:
    pasta: str
    cidade: str | None
    pais: str | None
    categoria: str | None
    evento: str | None
    justificativa: str


def _para_proposta(linha: PastaClassificada) -> PropostaDePasta:
    return PropostaDePasta(
        pasta=linha.pasta,
        cidade=linha.cidade,
        pais=linha.pais,
        categoria=linha.categoria,
        evento=linha.evento,
        justificativa=linha.justificativa,
    )


class ClassificacaoPastaRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._factory = session_factory

    def _por_status(self, status: str) -> dict[str, PropostaDePasta]:
        with self._factory() as session:
            linhas = session.scalars(
                select(PastaClassificada).where(
                    PastaClassificada.status == status
                )
            )
            # Converter DENTRO da sessão — devolver instância ORM para fora
            # do `with` entrega objeto destacado ao consumidor.
            return {linha.pasta: _para_proposta(linha) for linha in linhas}

    def aprovadas(self) -> dict[str, PropostaDePasta]:
        """{pasta: PropostaDePasta} só das linhas `status == 'aprovada'` —
        é isto, e só isto, que a cascata (07-05) lê."""
        return self._por_status("aprovada")

    def propostas(self) -> dict[str, PropostaDePasta]:
        """{pasta: PropostaDePasta} das linhas `status == 'proposta'` — a
        UI reabre uma sessão paga que ainda não foi aprovada."""
        return self._por_status("proposta")

    def conhecidas(self) -> set[str]:
        """Pastas com linha na tabela, em qualquer status — o que o
        pré-filtro de candidatas (07-03) usa para não mandar de novo o que
        já foi classificado."""
        with self._factory() as session:
            return set(session.scalars(select(PastaClassificada.pasta)))

    def salvar_propostas(
        self, propostas: list[PropostaDePasta], sessao: str
    ) -> int:
        """Grava por CAMPO, disciplina mais estrita que a guarda por linha
        de `LexicoRepository.salvar()` (D-02, mesma disciplina de
        EXIF-02/D-075): um campo já preenchido (`cidade`/`pais`/
        `categoria`/`evento` não-`None`) nunca é sobrescrito, mesmo por uma
        proposta nova e mesmo quando o valor discorda. Linha com
        `origem == 'manual'` é inteiramente intocável — nenhum campo dela é
        tocado, mesmo os que estão vazios (a máquina não completa o que o
        dono já assumiu a autoria de decidir). Devolve a quantidade de
        linhas criadas ou alteradas.
        """
        gravadas = 0
        campos = ("cidade", "pais", "categoria", "evento")
        with self._factory() as session:
            for proposta in propostas:
                atual = session.get(PastaClassificada, proposta.pasta)
                if atual is not None:
                    if atual.origem == "manual":
                        continue
                    alterou = False
                    for campo in campos:
                        if getattr(atual, campo) is None:
                            valor_novo = getattr(proposta, campo)
                            if valor_novo is not None:
                                setattr(atual, campo, valor_novo)
                                alterou = True
                    if alterou:
                        atual.justificativa = proposta.justificativa
                        atual.sessao = sessao
                        gravadas += 1
                else:
                    session.add(PastaClassificada(
                        pasta=proposta.pasta,
                        cidade=proposta.cidade,
                        pais=proposta.pais,
                        categoria=proposta.categoria,
                        evento=proposta.evento,
                        justificativa=proposta.justificativa,
                        origem="llm",
                        status="proposta",
                        sessao=sessao,
                    ))
                    gravadas += 1
            session.commit()
        return gravadas

    def _mudar_status(
        self, pastas: list[str], de: str, para: str
    ) -> int:
        afetadas = 0
        with self._factory() as session:
            for pasta in pastas:
                linha = session.get(PastaClassificada, pasta)
                if linha is not None and linha.status == de:
                    linha.status = para
                    afetadas += 1
            session.commit()
        return afetadas

    def aprovar(self, pastas: list[str]) -> int:
        """Muda `status` para 'aprovada' só nas linhas listadas que hoje
        estão em 'proposta'. Nunca apaga linha (invariante 8)."""
        return self._mudar_status(pastas, de="proposta", para="aprovada")

    def descartar(self, pastas: list[str]) -> int:
        """Muda `status` para 'descartada' só nas linhas listadas que hoje
        estão em 'proposta'. Nunca apaga linha — o registro rebaixado
        continua no banco como fonte de sinal e de auditoria
        (invariante 8)."""
        return self._mudar_status(pastas, de="proposta", para="descartada")
