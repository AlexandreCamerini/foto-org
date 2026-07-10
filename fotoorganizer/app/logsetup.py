"""Logging estruturado (JSON por linha) em arquivo + formato legível no stderr.

Regra de privacidade: mensagens de log não devem conter conteúdo de fotos
nem metadados sensíveis — caminhos de arquivo são permitidos por serem
essenciais ao diagnóstico local; nada disso sai da máquina.
"""

from __future__ import annotations

import json
import logging
import logging.handlers
from datetime import datetime, timezone
from pathlib import Path


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "nivel": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def setup_logging(log_dir: Path, level: int = logging.INFO) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()

    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / "fotoorganizer.jsonl", maxBytes=5 * 1024 * 1024, backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(JsonFormatter())
    root.addHandler(file_handler)

    console = logging.StreamHandler()
    console.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s")
    )
    root.addHandler(console)

    _instalar_captura_de_excecoes()


def _instalar_captura_de_excecoes() -> None:
    """Exceções não tratadas (inclusive em slots Qt e threads) iam só para
    o stderr — invisíveis quando o app é aberto fora de um terminal. Agora
    tudo cai no log estruturado antes do comportamento padrão."""
    import sys
    import threading

    logger = logging.getLogger("fotoorganizer.crash")

    def excepthook(tipo, valor, tb):
        logger.critical(
            "exceção não tratada", exc_info=(tipo, valor, tb)
        )
        sys.__excepthook__(tipo, valor, tb)

    def threading_hook(args):
        logger.critical(
            "exceção não tratada em thread %s", args.thread.name,
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )

    sys.excepthook = excepthook
    threading.excepthook = threading_hook
