"""Configuração local em TOML.

Leitura via tomllib (stdlib). O arquivo é opcional: na ausência dele valem
os defaults abaixo. Chaves desconhecidas são ignoradas com aviso — nunca
derrubam o app por causa de config.
"""

from __future__ import annotations

import logging
import tomllib
from dataclasses import dataclass, field, fields, replace
from pathlib import Path

from fotoorganizer.config import paths

log = logging.getLogger(__name__)

CONFIG_TEMPLATE = """\
# Configuração do Foto Organizer. Todas as chaves são opcionais.

[geral]
# data_dir = "~/Library/Application Support/FotoOrganizer"
# cache_dir = "~/Library/Caches/FotoOrganizer"

[scanner]
# workers = 4
# incluir_ocultos = false
# seguir_symlinks = false

[privacidade]
# servicos_externos = false
"""


@dataclass(frozen=True)
class ScannerSettings:
    workers: int = 4
    incluir_ocultos: bool = False
    seguir_symlinks: bool = False


@dataclass(frozen=True)
class PrivacySettings:
    # Nenhum dado sai da máquina enquanto isto for False (invariante 4).
    servicos_externos: bool = False
    # Reconhecimento facial: opcional e desativado por padrão (invariante 6).
    reconhecimento_facial: bool = False


@dataclass(frozen=True)
class Settings:
    data_dir: Path = field(default_factory=paths.default_data_dir)
    cache_dir: Path = field(default_factory=paths.default_cache_dir)
    scanner: ScannerSettings = field(default_factory=ScannerSettings)
    privacidade: PrivacySettings = field(default_factory=PrivacySettings)

    @property
    def db_path(self) -> Path:
        return paths.default_db_path(self.data_dir)

    @property
    def log_dir(self) -> Path:
        return paths.default_log_dir(self.data_dir)

    def ensure_dirs(self) -> None:
        for d in (self.data_dir, self.cache_dir, self.log_dir):
            d.mkdir(parents=True, exist_ok=True)


def _apply_section(instance, data: dict, section: str):
    known = {f.name for f in fields(instance)}
    updates = {}
    for key, value in data.items():
        if key not in known:
            log.warning("config: chave desconhecida ignorada: [%s] %s", section, key)
            continue
        updates[key] = value
    return replace(instance, **updates)


def load_settings(config_file: Path | None = None) -> Settings:
    """Carrega o TOML se existir; caso contrário retorna os defaults."""
    config_file = config_file or paths.default_config_file()
    settings = Settings()
    if not config_file.is_file():
        return settings

    try:
        with open(config_file, "rb") as fh:
            data = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        log.error("config: erro lendo %s (%s); usando defaults", config_file, exc)
        return settings

    geral = data.get("geral", {})
    if "data_dir" in geral:
        settings = replace(settings, data_dir=Path(geral["data_dir"]).expanduser())
    if "cache_dir" in geral:
        settings = replace(settings, cache_dir=Path(geral["cache_dir"]).expanduser())
    for key in geral:
        if key not in ("data_dir", "cache_dir"):
            log.warning("config: chave desconhecida ignorada: [geral] %s", key)

    settings = replace(
        settings,
        scanner=_apply_section(settings.scanner, data.get("scanner", {}), "scanner"),
        privacidade=_apply_section(
            settings.privacidade, data.get("privacidade", {}), "privacidade"
        ),
    )
    return settings


def write_config_template(config_file: Path) -> None:
    """Grava um template comentado, sem sobrescrever config existente."""
    if config_file.exists():
        return
    config_file.parent.mkdir(parents=True, exist_ok=True)
    config_file.write_text(CONFIG_TEMPLATE, encoding="utf-8")
