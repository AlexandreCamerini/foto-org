"""Filtro composto sobre proveniência — parser + serializador simétrico.

Staging fora de `fotoorganizer/**` (protocolo em `docs/prompts/00-protocolo.md`).
Reimplementa o MECANISMO descrito em `docs/prompts/fase-14-photoprism-e-sintese.md`
§3 (Item A) — nunca código do PhotoPrism ou do Immich, que são AGPLv3.

O mecanismo copiado é o contrato "objeto de recorte é a única fonte de
verdade, Serialize/Unserialize são inversos um do outro" que o PhotoPrism
resolve em `internal/form/serialize.go` (citado só como referência de
mecanismo, não lido nesta sessão). Aqui a gramática nasce do schema real do
foto-organizer, não de uma tradução linha a linha daquele parser.

Vocabulário coberto (Item A do prompt): os quatro tokens que só este
catálogo pode oferecer, porque vêm de `evidence` e de colunas que o projeto
inventou — nenhum têm equivalente em app de mercado:

    confianca:baixa|media|alta   -> Evidence.nivel / ConfidenceLevel
    origem:<texto livre>         -> Evidence.origem (string livre no schema)
    papel:acervo|sinal           -> MediaFile.papel / MediaRole
    lugar:estimado|medido        -> gps_lat_estimado vs. gps_lat

Decisão de escopo (Classe A, registrada em docs/DECISOES.md): sem `!`
(negação) nem `|` (OU) nesta versão. A seção 6 do prompt de origem já
recomenda cortar isso do escopo inicial e medir depois se algum recorte
salvo pediu os dois — o corte é o que evita a parte mais frágil do parser
antes de saber se alguém precisa dela. O que sobra é conjunção pura de
tokens mais texto livre, que já resolve o caso descrito no prompt: "as fotos
cujo lugar veio de herança com confiança baixa e sem câmera identificada".

Onde plugar quando a fronteira abrir: ver README.md.
"""

from __future__ import annotations

import shlex
from dataclasses import dataclass, field, replace

# --- vocabulário -------------------------------------------------------

CONFIANCA_VALIDAS = frozenset({"baixa", "media", "alta"})
PAPEL_VALIDAS = frozenset({"acervo", "sinal"})
LUGAR_VALIDAS = frozenset({"estimado", "medido"})

# Ordem fixa de serialização: o round-trip não depende da ordem de entrada
# (parse é insensível a ordem), mas serialize sempre produz a MESMA string
# para o mesmo filtro — é isso que torna o recorte linkável e comparável.
_ORDEM_CAMPOS = ("papel", "confianca", "origem", "lugar")

_CHAVES_VALIDAS = frozenset(_ORDEM_CAMPOS)


class FiltroInvalido(ValueError):
    """Erro de sintaxe ou de vocabulário, sempre reportado — nunca engolido.

    Espelha a postura do mecanismo original: "erro de campo desconhecido ou
    de tipo é reportado, não silenciado" (fase-14 §3). Cada mensagem carrega
    o token exato que falhou, para a UI (quando existir) apontar a posição.
    """


@dataclass(frozen=True)
class FiltroProveniencia:
    """O objeto de recorte — única fonte de verdade.

    Digitação livre (parse) e controles de UI (construção direta do
    dataclass) escrevem os dois no MESMO objeto; nenhum dos dois é um
    segundo estado. `busca` preserva a ordem dos termos livres para o
    round-trip ser determinístico mesmo com texto multi-palavra.
    """

    confianca: str | None = None
    origem: str | None = None
    papel: str | None = None
    lugar: str | None = None
    busca: tuple[str, ...] = field(default_factory=tuple)

    def vazio(self) -> bool:
        return not any((self.confianca, self.origem, self.papel, self.lugar, self.busca))


def _validar_valor(campo: str, valor: str, token: str) -> str:
    if campo == "confianca" and valor not in CONFIANCA_VALIDAS:
        raise FiltroInvalido(
            f"valor inválido em {token!r}: confianca aceita "
            f"{sorted(CONFIANCA_VALIDAS)}, recebi {valor!r}"
        )
    if campo == "papel" and valor not in PAPEL_VALIDAS:
        raise FiltroInvalido(
            f"valor inválido em {token!r}: papel aceita "
            f"{sorted(PAPEL_VALIDAS)}, recebi {valor!r}"
        )
    if campo == "lugar" and valor not in LUGAR_VALIDAS:
        raise FiltroInvalido(
            f"valor inválido em {token!r}: lugar aceita "
            f"{sorted(LUGAR_VALIDAS)}, recebi {valor!r}"
        )
    return valor


def parse(texto: str) -> FiltroProveniencia:
    """Texto digitado (ou vindo da URL) -> objeto de recorte.

    Tokenização por `shlex` (aspas escapam espaço, como
    `origem:"vizinhanca temporal"` ou busca livre `"praia grande"`) em vez de
    um parser caractere a caractere — a ressalva do prompt de origem é
    explícita: não portar o parser próprio do mecanismo original, uma
    biblioteca testada da linguagem alvo entrega o mesmo contrato com menos
    borda.

    Token com `chave:valor` e chave conhecida vira campo estruturado; sem
    `:` (ou com chave desconhecida) vira termo de busca livre. Chave
    conhecida com valor fora do vocabulário é erro — nunca vira busca livre
    por acidente, o que esconderia um typo como se fosse um recorte válido.
    Campo repetido também é erro: qual dos dois vale seria ambíguo.
    """
    try:
        tokens = shlex.split(texto)
    except ValueError as exc:  # aspas não fechadas etc.
        raise FiltroInvalido(f"sintaxe inválida: {exc}") from exc

    campos: dict[str, str] = {}
    busca: list[str] = []
    for token in tokens:
        chave, sep, valor = token.partition(":")
        if not sep:
            busca.append(token)
            continue
        chave_norm = chave.strip().lower()
        if chave_norm not in _CHAVES_VALIDAS:
            raise FiltroInvalido(
                f"campo desconhecido: {chave!r} (token {token!r}); "
                f"campos válidos: {sorted(_CHAVES_VALIDAS)}"
            )
        if not valor:
            raise FiltroInvalido(f"valor vazio em {token!r}")
        if chave_norm in campos:
            raise FiltroInvalido(
                f"campo repetido: {chave_norm!r} já apareceu "
                f"({campos[chave_norm]!r} e {valor!r})"
            )
        valor_norm = valor.strip().lower() if chave_norm != "origem" else valor.strip()
        campos[chave_norm] = _validar_valor(chave_norm, valor_norm, token)

    return FiltroProveniencia(
        confianca=campos.get("confianca"),
        origem=campos.get("origem"),
        papel=campos.get("papel"),
        lugar=campos.get("lugar"),
        busca=tuple(busca),
    )


def _quote(valor: str) -> str:
    """Aspas só quando necessário — string simples fica legível sem elas."""
    return shlex.quote(valor) if valor else '""'


def serialize(filtro: FiltroProveniencia) -> str:
    """Objeto de recorte -> texto reversível.

    Ordem fixa de campo (`_ORDEM_CAMPOS`) para a mesma combinação lógica
    sempre produzir a mesma string, independente da ordem em que os
    controles de UI foram tocados — sem isso, dois links para o "mesmo"
    recorte seriam strings diferentes, e comparar recortes salvos exigiria
    reparsear em vez de comparar texto.
    """
    partes: list[str] = []
    for campo in _ORDEM_CAMPOS:
        valor = getattr(filtro, campo)
        if valor:
            partes.append(f"{campo}:{_quote(valor) if campo == 'origem' else valor}")
    partes.extend(_quote(termo) for termo in filtro.busca)
    return " ".join(partes)


def com_campo(filtro: FiltroProveniencia, campo: str, valor: str | None) -> FiltroProveniencia:
    """Escreve um campo por cima de um recorte existente — o caminho que os
    controles de UI usam (chip, dropdown) para gravar no MESMO objeto que a
    caixa de texto edita. Não existe um segundo estado para a UI estruturada.
    """
    if campo not in _CHAVES_VALIDAS:
        raise FiltroInvalido(f"campo desconhecido: {campo!r}")
    if valor is not None:
        _validar_valor(campo, valor, f"{campo}:{valor}")
    return replace(filtro, **{campo: valor})


# --- composição em N predicados -----------------------------------------
#
# Este item entrega o parser/serializador; a composição real em SQLAlchemy
# fica em `repositories/media.py` quando a fronteira abrir (ver README.md).
# `Condicao` é uma descrição abstrata e testável de "para que predicado cada
# token vira" — prova que o filtro compõe N condições em AND, sem depender
# de SQLAlchemy nem do ORM do foto-organizer.


@dataclass(frozen=True)
class Condicao:
    """Um predicado abstrato: campo alvo, operador, valor.

    `tabela` diz onde o campo mora no schema real (`evidence` ou
    `media_files`) — é a informação que falta para alguém que só olhar o
    predicado saber se ele exige um JOIN/subconsulta contra `evidence` (como
    `_condicao_lacuna` já faz em `repositories/media.py:69-110`) ou é direto
    em `media_files`.
    """

    tabela: str
    campo: str
    operador: str
    valor: str


def para_condicoes(filtro: FiltroProveniencia) -> tuple[Condicao, ...]:
    """O recorte estruturado -> lista de predicados a compor em AND.

    Conjunção pura (ver docstring do módulo): esta função nunca produz OR
    nem negação. Confiança e origem miram `evidence` (miram a MESMA linha de
    evidência quando os dois aparecem juntos — combinação que este MVP não
    força, mas deixa registrada como limitação: hoje elas filtram
    independentemente, cada uma podendo casar com uma evidência diferente da
    mesma mídia). Papel e lugar miram colunas diretas de `media_files`.
    """
    condicoes: list[Condicao] = []
    if filtro.confianca:
        condicoes.append(Condicao("evidence", "nivel", "=", filtro.confianca))
    if filtro.origem:
        condicoes.append(Condicao("evidence", "origem", "=", filtro.origem))
    if filtro.papel:
        condicoes.append(Condicao("media_files", "papel", "=", filtro.papel))
    if filtro.lugar == "estimado":
        condicoes.append(Condicao("media_files", "gps_lat_estimado", "is not", "null"))
    elif filtro.lugar == "medido":
        condicoes.append(Condicao("media_files", "gps_lat", "is not", "null"))
    return tuple(condicoes)
