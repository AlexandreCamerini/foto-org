"""Executa migrações Alembic programaticamente (o app migra ao iniciar)."""

from __future__ import annotations

import logging
from pathlib import Path

from alembic import command
from alembic.config import Config

from fotoorganizer.database.engine import db_url

log = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def alembic_config(db_path: Path) -> Config:
    cfg = Config()
    cfg.set_main_option("script_location", str(MIGRATIONS_DIR))
    cfg.set_main_option("sqlalchemy.url", db_url(db_path))
    return cfg


def upgrade_to_head(db_path: Path) -> None:
    log.info("migrando catálogo em %s", db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    command.upgrade(alembic_config(db_path), "head")
