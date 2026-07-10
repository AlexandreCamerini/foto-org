"""Manutenção de privacidade: limpar cache e remover o catálogo por
completo — SEM tocar em nenhuma foto original."""

from __future__ import annotations

import logging
import shutil

from fotoorganizer.config.settings import Settings

log = logging.getLogger(__name__)


def limpar_cache(settings: Settings) -> None:
    """Apaga miniaturas e temporários. Regeneráveis a qualquer momento."""
    if settings.cache_dir.is_dir():
        shutil.rmtree(settings.cache_dir)
    settings.cache_dir.mkdir(parents=True, exist_ok=True)
    log.info("cache limpo: %s", settings.cache_dir)


def remover_catalogo(settings: Settings) -> None:
    """Remove banco (com WAL/SHM), chave de embeddings e cache. As fotos
    originais nunca são tocadas — o app não guarda nada dentro delas."""
    for sufixo in ("", "-wal", "-shm"):
        candidato = settings.db_path.with_name(settings.db_path.name + sufixo)
        candidato.unlink(missing_ok=True)
    (settings.data_dir / "embeddings.key").unlink(missing_ok=True)
    limpar_cache(settings)
    log.info("catálogo removido: %s", settings.db_path)
