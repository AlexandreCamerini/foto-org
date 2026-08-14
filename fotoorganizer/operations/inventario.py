"""Inventário por pasta — manifesto legível ao lado das fotos copiadas.

Desenho completo em `docs/desenho-inventario-por-pasta.md` (D-062). Um
par `inventario.json` + `INVENTARIO.md` por PASTA de destino, aditivo
entre execuções de planos diferentes ao longo do tempo — nunca um par
por foto nem por plano.

Chamado só DEPOIS que `operations/executor.py` já verificou a cópia por
hash (`item.hash_pos == item.hash_pre`). Nunca decide se a cópia é
válida — só registra o que já foi verificado.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from fotoorganizer.metadata.camera import nome_da_camera
from fotoorganizer.models import (
    Location,
    MediaFile,
    OperationItem,
    Suggestion,
    SuggestionStatus,
)

log = logging.getLogger(__name__)

_GERADO_POR = "Foto Organizer"


def _escrever_atomico(caminho: Path, conteudo: str) -> None:
    """`write_text` trunca antes de escrever — um crash no meio deixa o
    arquivo corrompido para a PRÓXIMA leitura, o que travaria o
    inventário da pasta inteira (não só desta foto). Escreve num
    temporário no mesmo diretório e troca com `os.replace` (atômico no
    mesmo filesystem)."""
    tmp = caminho.with_suffix(caminho.suffix + ".tmp")
    tmp.write_text(conteudo, encoding="utf-8")
    os.replace(tmp, caminho)


def _carregar(caminho_json: Path, pasta: Path) -> dict:
    if not caminho_json.is_file():
        return {"pasta": str(pasta), "gerado_por": _GERADO_POR, "fotos": []}
    try:
        return json.loads(caminho_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        # Escrita anterior interrompida no meio (crash, disco cheio no
        # instante exato). O MD é sempre regenerado do JSON inteiro, então
        # recomeçar não perde nada que não já estivesse perdido — só
        # preserva o arquivo ruim ao lado, para inspeção, em vez de
        # sobrescrever em silêncio.
        corrompido = caminho_json.with_name(
            caminho_json.name + f".corrompido-{int(datetime.now().timestamp())}"
        )
        caminho_json.rename(corrompido)
        log.warning("inventario.json corrompido em %s, movido para %s",
                   pasta, corrompido)
        return {"pasta": str(pasta), "gerado_por": _GERADO_POR, "fotos": []}


def _lugar(session: Session, media: MediaFile) -> dict | None:
    if media.location_id is None:
        return None
    local = session.get(Location, media.location_id)
    if local is None:
        return None
    return {"pais": local.pais, "regiao": local.regiao, "cidade": local.cidade}


def _montar_entrada(session: Session, item: OperationItem, media: MediaFile,
                    destino: Path, sugestao: Suggestion | None) -> dict:
    entrada = {
        "arquivo": destino.name,
        "origem": item.origem,
        # Tamanho do arquivo REALMENTE copiado e verificado, não o que o
        # scan gravou em `media.tamanho` — os dois podem divergir se o
        # original mudou de tamanho entre o catálogo e esta execução.
        "tamanho": destino.stat().st_size,
        "hash_sha256": item.hash_pos,
        # Não existe coluna "copiado em" em OperationItem — esta função
        # roda logo depois da verificação de hash (executor.py), então
        # "agora" é o momento real da cópia, com a margem de milissegundos
        # de escrever o próprio inventário.
        "copiado_em": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
        "data_capturada": media.data_capturada.isoformat()
        if media.data_capturada else None,
        "camera": nome_da_camera(media.make, media.model),
        "lugar": _lugar(session, media),
        "evidencias": [],
        "versao_logica": sugestao.versao_logica if sugestao else None,
    }
    if sugestao is not None:
        entrada["evidencias"] = [
            {
                "campo": ev.campo, "origem": ev.origem, "valor": ev.valor,
                "nivel": ev.nivel.value, "score": ev.score,
                "justificativa": ev.justificativa,
            }
            for ev in sugestao.evidencias
        ]
    return entrada


def _renderizar_md(dados: dict) -> str:
    linhas = [f"# Inventário — {dados['pasta']}", ""]
    for foto in dados["fotos"]:
        linhas.append(f"## {foto['arquivo']}")
        detalhes = []
        if foto.get("data_capturada"):
            detalhes.append(f"capturada em {foto['data_capturada']}")
        if foto.get("camera"):
            detalhes.append(foto["camera"])
        lugar = foto.get("lugar")
        if lugar:
            partes = [v for v in (lugar.get("cidade"), lugar.get("regiao"),
                                  lugar.get("pais")) if v]
            if partes:
                detalhes.append(", ".join(partes))
        if detalhes:
            linhas.append(" — ".join(detalhes))
        linhas.append(f"- origem: `{foto['origem']}`")
        linhas.append(f"- hash sha256: `{foto['hash_sha256']}`")
        linhas.append("")
        linhas.append("**Por quê?**")
        for ev in foto["evidencias"]:
            linhas.append(
                f"- {ev['campo']}: {ev['valor']} — {ev['justificativa']} "
                f"({ev['nivel']})"
            )
        linhas.append("")
    return "\n".join(linhas)


def registrar(session: Session, item: OperationItem) -> None:
    """Acrescenta a foto já copiada e verificada ao inventário da pasta.

    Idempotente: se `arquivo` já está no inventário, não duplica — cobre
    o caso raro de reprocessamento do mesmo item.
    """
    media = session.get(MediaFile, item.media_id)
    destino = Path(item.destino)
    pasta = destino.parent
    caminho_json = pasta / "inventario.json"
    caminho_md = pasta / "INVENTARIO.md"

    dados = _carregar(caminho_json, pasta)
    if any(f["arquivo"] == destino.name for f in dados["fotos"]):
        return

    sugestao = session.scalar(
        select(Suggestion)
        .where(
            Suggestion.media_id == media.id,
            Suggestion.status.in_(
                [SuggestionStatus.APROVADA, SuggestionStatus.EDITADA]
            ),
        )
        .order_by(Suggestion.id.desc())
    )
    dados["fotos"].append(_montar_entrada(session, item, media, destino, sugestao))

    _escrever_atomico(
        caminho_json, json.dumps(dados, indent=2, ensure_ascii=False)
    )
    _escrever_atomico(caminho_md, _renderizar_md(dados))
