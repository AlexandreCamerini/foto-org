"""Caminhos padrão do app no macOS (Application Support / Caches)."""

from __future__ import annotations

from pathlib import Path

APP_NAME = "FotoOrganizer"


def default_data_dir() -> Path:
    return Path.home() / "Library" / "Application Support" / APP_NAME


def default_cache_dir() -> Path:
    return Path.home() / "Library" / "Caches" / APP_NAME


def default_config_file() -> Path:
    return default_data_dir() / "config.toml"


def default_db_path(data_dir: Path | None = None) -> Path:
    return (data_dir or default_data_dir()) / "catalog.db"


def default_log_dir(data_dir: Path | None = None) -> Path:
    return (data_dir or default_data_dir()) / "logs"
