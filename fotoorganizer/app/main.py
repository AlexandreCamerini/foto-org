"""Entrypoint: delega para a CLI. A UI é a web local (subcomando `web`)."""

from __future__ import annotations

import logging
import sys

log = logging.getLogger(__name__)


def main() -> int:
    # Sem argumentos, `python -m fotoorganizer` sobe a UI web local
    # (127.0.0.1). Com argumentos ("scan", "web", "bench"…), delega à CLI.
    from fotoorganizer.cli import main as cli_main

    if len(sys.argv) > 1:
        return cli_main()
    return cli_main(["web"])
