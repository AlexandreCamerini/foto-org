"""Entrypoint: config → logging → migração do catálogo → UI."""

from __future__ import annotations

import logging
import sys

from fotoorganizer.config import load_settings
from fotoorganizer.config.paths import default_config_file
from fotoorganizer.config.settings import write_config_template

log = logging.getLogger(__name__)


def main() -> int:
    settings = load_settings()
    settings.ensure_dirs()

    from fotoorganizer.app.logsetup import setup_logging

    setup_logging(settings.log_dir)
    write_config_template(default_config_file())

    from fotoorganizer.database import (
        create_db_engine,
        create_session_factory,
        upgrade_to_head,
    )

    upgrade_to_head(settings.db_path)
    engine = create_db_engine(settings.db_path)
    session_factory = create_session_factory(engine)

    from PySide6.QtWidgets import QApplication

    from fotoorganizer.ui.main_window import MainWindow
    from fotoorganizer.ui.theme import QSS

    app = QApplication(sys.argv)
    app.setApplicationName("Foto Organizer")
    app.setStyleSheet(QSS)

    window = MainWindow(settings, session_factory)
    window.show()
    log.info("app iniciado; catálogo em %s", settings.db_path)
    return app.exec()
