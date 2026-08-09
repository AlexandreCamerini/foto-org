"""Laço de reconciliação: mantém `MediaFile.arquivo_offline` honesto sem
depender de um re-scan manual.

O scan normal (`scanner.py`) já marca sumiço na passada em que descobre,
mas um acervo em NAS ou disco externo pode passar semanas sem re-scan — e
ninguém percebe que um arquivo sumiu até tentar abri-lo. Este módulo é o
laço independente que resolve isso: mais barato que um scan completo (só
`Path.exists()` por linha, sem reler metadado nem recalcular hash — "rehash
só sob demanda" é regra do M1), e auto-limitado por tempo OU percentual do
acervo elegível, o que vier primeiro.

Este projeto não tem scheduler (`server/jobs.py` roda um trabalho de cada
vez, sempre disparado por CLI/API, nunca automático), então cada chamada é
UMA passada — processa um pedaço e para sozinha. O checkpoint entre chamadas
fica em `application_settings` (via `SettingsRepository`), de propósito NÃO
em `ScanSession`: `webapp/src/components/RetomarScan.tsx` já lista sessão
`PAUSADO` como "varredura interrompida, clique para retomar" e dispara um
scan de PASTA de verdade — se a reconciliação também gravasse `ScanSession`,
uma passada parcial apareceria ali e "Retomar" chamaria o comando errado.

Nunca toca em referência de catálogo externo (`caminho` com "://"): não é
caminho de filesystem, e chamar `Path.exists()` nisso não tem sentido —
essas linhas são puladas inteiramente, nunca lidas nem escritas aqui.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from fotoorganizer.models import MediaFile, Source
from fotoorganizer.repositories.settings import SettingsRepository
from fotoorganizer.scanner.elegibilidade import PADRAO_SQL_REFERENCIA_EXTERNA

log = logging.getLogger(__name__)

CHAVE_RECONCILIACAO_CHECKPOINT = "reconciliacao_checkpoint"

# Orçamento padrão de uma chamada: o que vier primeiro entre tempo e
# percentual do acervo ELEGÍVEL (fontes disponíveis, caminho de arquivo de
# verdade, ainda não referência ausente) para esta fonte.
_ORCAMENTO_SEGUNDOS_PADRAO = 30.0
_ORCAMENTO_PERCENTUAL_PADRAO = 0.20
# Teto duro por chamada, além do orçamento por percentual: nunca carregar o
# acervo inteiro na memória de uma vez, mesmo com um percentual generoso
# ou um catálogo pequeno onde 100% caberia inteiro.
_TETO_DURO_POR_CHAMADA = 20_000


@dataclass(frozen=True, slots=True)
class ResultadoReconciliacao:
    verificados: int
    marcados_offline: int
    marcados_online: int
    # True quando esta chamada alcançou o fim do acervo elegível (o
    # checkpoint volta a zero) — a próxima passada recomeça do início.
    ciclo_concluido: bool


def _condicoes_elegiveis():
    """Só o que faz sentido perguntar ao filesystem: fonte respondendo
    agora, caminho de arquivo real (nunca `apple://…`/`lightroom://…`), e
    que não seja já uma referência sem arquivo local — essas nunca tiveram
    o que verificar. Mesmo predicado de `elegibilidade.py`, aqui em SQL —
    o `%://%` usa o marcador compartilhado para não divergir do lado
    Python que `scanner.py` usa ao marcar sumiço."""
    return (
        Source.disponivel.is_(True),
        MediaFile.arquivo_ausente.is_(False),
        MediaFile.caminho.not_like(PADRAO_SQL_REFERENCIA_EXTERNA),
    )


def _checkpoint_atual(settings_repo: SettingsRepository) -> int:
    valor = settings_repo.obter(CHAVE_RECONCILIACAO_CHECKPOINT)
    if isinstance(valor, dict):
        try:
            return max(int(valor.get("ultimo_media_id") or 0), 0)
        except (TypeError, ValueError):
            return 0
    return 0


def reconciliar(
    session_factory: sessionmaker[Session],
    *,
    orcamento_segundos: float = _ORCAMENTO_SEGUNDOS_PADRAO,
    orcamento_percentual: float = _ORCAMENTO_PERCENTUAL_PADRAO,
) -> ResultadoReconciliacao:
    """Uma passada, auto-limitada. Retoma de onde a passada anterior parou.

    Percorre `MediaFile` em ordem de id, começando logo depois do
    checkpoint salvo. Cada linha só paga um `Path.exists()` — nada de EXIF,
    hash ou thumbnail. Ao alcançar o fim do acervo elegível, o checkpoint
    volta a zero: a chamada seguinte recomeça um novo ciclo, em vez de ficar
    presa no fim para sempre.
    """
    settings_repo = SettingsRepository(session_factory)
    ultimo_id = _checkpoint_atual(settings_repo)

    inicio = time.monotonic()
    verificados = marcados_offline = marcados_online = 0
    ultimo_processado = ultimo_id
    ha_mais_depois_deste_lote = False

    with session_factory() as session:
        total_elegivel = session.scalar(
            select(func.count(MediaFile.id))
            .join(Source, Source.id == MediaFile.source_id)
            .where(*_condicoes_elegiveis())
        ) or 0

        teto_linhas = min(
            _TETO_DURO_POR_CHAMADA,
            max(1, int(total_elegivel * orcamento_percentual)),
        ) if total_elegivel else 0

        candidatos: list[MediaFile] = []
        if teto_linhas:
            # +1: se vier essa linha extra, sabemos que sobrou trabalho
            # além do teto sem precisar de uma segunda consulta de contagem.
            candidatos = list(session.scalars(
                select(MediaFile)
                .join(Source, Source.id == MediaFile.source_id)
                .where(*_condicoes_elegiveis(), MediaFile.id > ultimo_id)
                .order_by(MediaFile.id)
                .limit(teto_linhas + 1)
            ))

        ha_mais_depois_deste_lote = len(candidatos) > teto_linhas
        a_processar = candidatos[:teto_linhas]

        parou_por_tempo = False
        for media in a_processar:
            if time.monotonic() - inicio >= orcamento_segundos:
                parou_por_tempo = True
                break
            existe = Path(media.caminho).exists()
            if existe and media.arquivo_offline:
                media.arquivo_offline = False
                marcados_online += 1
            elif not existe and not media.arquivo_offline:
                media.arquivo_offline = True
                marcados_offline += 1
            verificados += 1
            ultimo_processado = media.id

        sobrou_no_lote_por_tempo = parou_por_tempo and verificados < len(a_processar)
        session.commit()

    ciclo_concluido = not (ha_mais_depois_deste_lote or sobrou_no_lote_por_tempo)
    if ciclo_concluido:
        novo_checkpoint = {
            "ultimo_media_id": 0,
            "concluido_em": datetime.now(timezone.utc).isoformat(),
        }
    else:
        novo_checkpoint = {"ultimo_media_id": ultimo_processado}
    settings_repo.definir(CHAVE_RECONCILIACAO_CHECKPOINT, novo_checkpoint)

    log.info(
        "reconciliação: %d verificado(s), %d offline, %d online de novo "
        "(%s)",
        verificados, marcados_offline, marcados_online,
        "ciclo completo" if ciclo_concluido else "orçamento consumido",
    )
    return ResultadoReconciliacao(
        verificados=verificados,
        marcados_offline=marcados_offline,
        marcados_online=marcados_online,
        ciclo_concluido=ciclo_concluido,
    )
