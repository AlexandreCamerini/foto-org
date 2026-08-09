"""Reaponta uma fonte para onde o volume voltou montado.

`fotoorganizer/sources/disponibilidade.py` detecta que um volume remontou
noutro ponto (`/Volumes/photo` → `/Volumes/photo 1`) e **recusa-se, por
desenho, a reescrever o caminho**: mover 45 mil linhas de mídia é operação
do usuário, não efeito colateral de uma verificação. Este módulo é essa
operação. Ela nunca toca em arquivo — só reescreve `Source.caminho` e
`MediaFile.caminho` no catálogo, sempre com dry-run e validação de amostra
antes de qualquer escrita (invariantes 1-3 do CLAUDE.md).

Duas camadas, de propósito:

- `previa`/`aplicar` — a operação pura: dados dois prefixos explícitos,
  reescreve (ou simula reescrever) as linhas da fonte. Não sabe nada sobre
  volumes montados. Aceitar os prefixos como parâmetros, em vez de só "o
  estado atual do volume", é o que dá reversibilidade de graça — ver
  `desfazer_por_auditoria`.
- `prefixos_do_estado` — deriva os dois prefixos do estado ao vivo do
  volume (`sources.disponibilidade.EstadoDaFonte`), com a guarda de
  segurança que decide se o mecanismo pode agir.

**`MediaFile.caminho` nem sempre é um caminho de filesystem.** Fontes
externas (Apple Fotos, Lightroom) guardam `"apple://<uuid>"` ou
`"lightroom://<uuid>"` — a referência para o catálogo externo, sem raiz de
volume nenhuma (`sources/importer.py`). Fatiar essas strings pelo mesmo
prefixo de um caminho `/Volumes/...` destruiria a referência em silêncio
(invariante 8: nada que possa ser a única testemunha de uma foto é
apagado). Por isso `previa`/`aplicar` primeiro filtram por
`caminho.startswith(prefixo_antigo)` — só essas linhas contam, aparecem na
amostra e são reescritas; o resto fica bit-a-bit intocado.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from fotoorganizer.models import AuditLog, MediaFile, Source
from fotoorganizer.sources.disponibilidade import EstadoDaFonte

log = logging.getLogger(__name__)

# Amostra mostrada no dry-run — o bastante para o usuário conferir sem
# poluir a tela.
_TAMANHO_AMOSTRA = 10
# Amostra validada no disco antes de escrever — maior que a exibida, porque
# aqui o custo é um `Path.exists()`, não pixel de tela.
_TAMANHO_VALIDACAO = 20
_ACAO_AUDITORIA = "reapontar_fonte"


class ReapontamentoInaplicavel(Exception):
    """A fonte não está num formato em que o mecanismo pode agir com
    segurança, ou não há o que reapontar."""


class ValidacaoFalhou(Exception):
    """A amostra de caminhos novos não bate com o disco — nada foi escrito."""


class ColisaoDeCaminho(Exception):
    """Duas ou mais linhas reapontadas colidiriam no mesmo `caminho` sob a
    mesma fonte (UNIQUE `(source_id, caminho)`) — nada foi escrito."""


@dataclass(frozen=True, slots=True)
class PreviaReapontamento:
    source_id: int
    apelido: str
    prefixo_antigo: str
    prefixo_novo: str
    # Só as linhas que DE FATO começam com `prefixo_antigo` — não o total de
    # MediaFile da fonte. Uma fonte importada do Apple Fotos ou Lightroom
    # mistura caminho de arquivo com referência `apple://uuid`; a segunda
    # não muda nunca.
    total_media_files: int
    # Quantas linhas da fonte NÃO começam com o prefixo e por isso ficam de
    # fora — para o usuário entender que a fonte tem mais mídia do que o
    # que vai mudar, sem confundir "não mudou" com "não tem".
    total_ignoradas_sem_prefixo: int
    amostra: list[tuple[str, str]]


@dataclass(frozen=True, slots=True)
class ResultadoReapontamento:
    source_id: int
    prefixo_antigo: str
    prefixo_novo: str
    linhas_media_files: int
    # id da entrada de AuditLog criada por esta chamada — é o que
    # `desfazer_por_auditoria` recebe para reverter.
    audit_log_id: int


def resolver_fonte(factory: sessionmaker[Session], identificador: str) -> int:
    """Aceita id numérico ou apelido, como `cmd_volumes` já faz para
    exibição."""
    with factory() as session:
        if identificador.isdigit():
            source = session.get(Source, int(identificador))
            if source is not None:
                return source.id
        source = session.scalar(
            select(Source).where(Source.apelido == identificador)
        )
        if source is None:
            raise ReapontamentoInaplicavel(
                f"fonte não encontrada: {identificador!r}"
            )
        return source.id


def prefixos_do_estado(estado: EstadoDaFonte) -> tuple[str, str]:
    """`(prefixo_antigo, prefixo_novo)` a partir do estado ao vivo do
    volume — a matemática do prefixo, uma vez só.

    `prefixo_antigo` é `estado.caminho` (a raiz completa que o scanner
    varreu, sem ambiguidade). `prefixo_novo` troca só o pedaço
    `/Volumes/<nome>`; o resto do caminho (subpastas dentro do volume) é
    preservado.

    Guarda: só age quando `estado.caminho` é uma raiz `/Volumes/<nome>...`.
    Disco interno, ou uma identidade `caminho:` frágil que nunca seguiu essa
    convenção, não são um caso deste mecanismo — um replace genérico ali
    arriscaria reescrever o caminho errado.
    """
    if not estado.mudou_de_lugar:
        raise ReapontamentoInaplicavel(
            f"{estado.apelido!r} não mudou de lugar — nada a reapontar."
        )
    partes = Path(estado.caminho).parts
    if len(partes) < 3 or partes[1] != "Volumes":
        raise ReapontamentoInaplicavel(
            f"{estado.apelido!r}: caminho {estado.caminho!r} não é uma raiz "
            "/Volumes/<nome> — reapontamento automático não se aplica "
            "(disco interno, ou identidade de volume frágil)."
        )
    raiz_antiga = str(Path(partes[0], partes[1], partes[2]))
    assert estado.ponto_atual is not None  # garantido por `mudou_de_lugar`
    prefixo_novo = str(estado.ponto_atual) + estado.caminho[len(raiz_antiga):]
    return estado.caminho, prefixo_novo


def previa(
    factory: sessionmaker[Session],
    source_id: int,
    prefixo_antigo: str,
    prefixo_novo: str,
) -> PreviaReapontamento:
    """Dry-run: só leitura, nada é escrito no catálogo nem no disco.

    Conta e amostra só as linhas cujo `caminho` de fato começa com
    `prefixo_antigo` — uma referência de catálogo externo (`apple://uuid`)
    não é um caminho de filesystem e não tem esse prefixo nunca.
    """
    with factory() as session:
        source = session.get(Source, source_id)
        if source is None:
            raise ReapontamentoInaplicavel(f"fonte {source_id} não existe")
        caminhos = list(session.scalars(
            select(MediaFile.caminho)
            .where(MediaFile.source_id == source_id)
            .order_by(MediaFile.id)
        ))
        afetados = [c for c in caminhos if c.startswith(prefixo_antigo)]
        amostra = [
            (antigo, prefixo_novo + antigo[len(prefixo_antigo):])
            for antigo in afetados[:_TAMANHO_AMOSTRA]
        ]
        return PreviaReapontamento(
            source_id=source_id,
            apelido=source.apelido or Path(source.caminho).name,
            prefixo_antigo=prefixo_antigo,
            prefixo_novo=prefixo_novo,
            total_media_files=len(afetados),
            total_ignoradas_sem_prefixo=len(caminhos) - len(afetados),
            amostra=amostra,
        )


def aplicar(
    factory: sessionmaker[Session],
    source_id: int,
    prefixo_antigo: str,
    prefixo_novo: str,
    *,
    tamanho_validacao: int = _TAMANHO_VALIDACAO,
) -> ResultadoReapontamento:
    """Valida uma amostra dos caminhos NOVOS no disco e, só se todos
    existirem, reescreve `Source.caminho` + `MediaFile.caminho` numa única
    transação (tudo ou nada) e grava a entrada de auditoria.

    Só as linhas cujo `caminho` começa com `prefixo_antigo` são tocadas —
    uma referência de catálogo externo (`apple://uuid`, `lightroom://uuid`)
    fica bit-a-bit intocada, nunca entra na validação nem é reescrita.

    A validação é só leitura (`Path.exists()`) — nunca escreve no
    filesystem (invariante 1). Se algum caminho novo não existir, levanta
    `ValidacaoFalhou` e nenhuma linha é alterada. Se a reescrita faria duas
    linhas colidirem no mesmo `caminho` (UNIQUE `(source_id, caminho)`),
    levanta `ColisaoDeCaminho` e nenhuma linha é alterada.
    """
    with factory() as session:
        source = session.get(Source, source_id)
        if source is None:
            raise ReapontamentoInaplicavel(f"fonte {source_id} não existe")
        if source.caminho != prefixo_antigo:
            raise ReapontamentoInaplicavel(
                f"prefixo_antigo {prefixo_antigo!r} não bate com o caminho "
                f"atual da fonte ({source.caminho!r}) — abortando para não "
                "reescrever linhas da fonte errada."
            )

        linhas = list(session.execute(
            select(MediaFile.id, MediaFile.caminho)
            .where(MediaFile.source_id == source_id)
        ))
        afetados = [(id_, antigo) for id_, antigo in linhas
                    if antigo.startswith(prefixo_antigo)]
        intocados = {antigo for id_, antigo in linhas
                     if not antigo.startswith(prefixo_antigo)}

        if len(afetados) <= tamanho_validacao:
            amostra_validar = afetados
        else:
            passo = max(1, len(afetados) // tamanho_validacao)
            amostra_validar = afetados[::passo][:tamanho_validacao]

        ausentes = [
            novo for _id, antigo in amostra_validar
            if not Path(novo := prefixo_novo + antigo[len(prefixo_antigo):]).exists()
        ]
        if ausentes:
            raise ValidacaoFalhou(
                f"{len(ausentes)} de {len(amostra_validar)} caminhos novos "
                f"não existem no disco (ex.: {ausentes[0]!r}) — nenhuma "
                "linha do catálogo foi alterada."
            )

        novos = {
            id_: prefixo_novo + antigo[len(prefixo_antigo):]
            for id_, antigo in afetados
        }

        # Colisão proativa: duas linhas reapontadas caindo no mesmo
        # caminho, ou uma reapontada caindo em cima de uma que ficou
        # intocada. Mais barato de diagnosticar aqui, com uma mensagem que
        # diz qual caminho colidiu, do que deixar a UNIQUE do banco estourar
        # com um IntegrityError cru.
        vistos: set[str] = set()
        for novo in novos.values():
            if novo in vistos or novo in intocados:
                raise ColisaoDeCaminho(
                    f"reapontar colidiria em {novo!r} — mais de uma linha "
                    "cairia no mesmo caminho sob a fonte. Nenhuma linha foi "
                    "alterada."
                )
            vistos.add(novo)

        session.execute(
            update(Source)
            .where(Source.id == source_id)
            .values(caminho=prefixo_novo)
        )
        if novos:
            for media in session.scalars(
                select(MediaFile).where(MediaFile.id.in_(novos))
            ):
                media.caminho = novos[media.id]

        entrada = AuditLog(
            plan_id=None,
            acao=_ACAO_AUDITORIA,
            detalhe={
                "source_id": source_id,
                "prefixo_antigo": prefixo_antigo,
                "prefixo_novo": prefixo_novo,
                "linhas_media_files": len(afetados),
            },
            resultado="ok",
        )
        session.add(entrada)
        try:
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            raise ColisaoDeCaminho(
                "reapontar violaria a unicidade de caminho na fonte — "
                "nenhuma linha foi alterada."
            ) from exc
        audit_log_id = entrada.id

    log.info("fonte %s reapontada: %s -> %s (%d arquivos, %d ignorados "
              "sem prefixo)", source_id, prefixo_antigo, prefixo_novo,
              len(afetados), len(intocados))
    return ResultadoReapontamento(
        source_id=source_id,
        prefixo_antigo=prefixo_antigo,
        prefixo_novo=prefixo_novo,
        linhas_media_files=len(afetados),
        audit_log_id=audit_log_id,
    )


def desfazer_por_auditoria(
    factory: sessionmaker[Session], audit_log_id: int,
) -> ResultadoReapontamento:
    """Desfaz um reapontamento lendo a entrada de `AuditLog` que ele criou.

    Não é um mecanismo novo: chama `aplicar` de novo com `prefixo_antigo` e
    `prefixo_novo` TROCADOS, reaproveitando a mesma validação de amostra e a
    mesma trilha de auditoria — a chamada cria uma nova entrada, para que
    desfazer-o-desfazer continue funcionando pelo mesmo caminho.

    Só existe como recuperação (CLI); não há superfície de API/UI para
    isto — reapontar errado devia ser raro o bastante para não precisar de
    um botão para isso.
    """
    with factory() as session:
        entrada = session.get(AuditLog, audit_log_id)
        if entrada is None or entrada.acao != _ACAO_AUDITORIA:
            raise ReapontamentoInaplicavel(
                f"audit_log {audit_log_id} não é uma entrada de "
                f"{_ACAO_AUDITORIA!r}"
            )
        detalhe = entrada.detalhe or {}
        source_id = detalhe.get("source_id")
        prefixo_antigo = detalhe.get("prefixo_antigo")
        prefixo_novo = detalhe.get("prefixo_novo")
        if source_id is None or prefixo_antigo is None or prefixo_novo is None:
            raise ReapontamentoInaplicavel(
                f"audit_log {audit_log_id} não tem os campos esperados "
                "(source_id, prefixo_antigo, prefixo_novo)"
            )

    # Desfazer é reaplicar com os prefixos invertidos: o que era o destino
    # vira a origem, e vice-versa.
    return aplicar(factory, source_id, prefixo_novo, prefixo_antigo)
