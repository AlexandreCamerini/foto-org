"""Descoberta de arquivos de mídia: recursiva, segura e previsível.

- Não atravessa symlinks por padrão (invariante 5) e evita ciclos de
  diretório rastreando (st_dev, st_ino) já visitados.
- Ignora ocultos e lixo de sistema por padrão (configurável).
- Erros de permissão/IO em um diretório são registrados e a varredura segue.
"""

from __future__ import annotations

import fnmatch
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

log = logging.getLogger(__name__)

SYSTEM_JUNK = {"thumbs.db", "desktop.ini", ".ds_store"}
JUNK_DIRS = {"@eadir", ".thumbnails", ".photoslibrary"}


@dataclass(frozen=True)
class DiscoveryConfig:
    extensoes: frozenset[str]
    incluir_ocultos: bool = False
    seguir_symlinks: bool = False
    padroes_ignorados: tuple[str, ...] = field(default_factory=tuple)


def _ignored(name: str, rel_path: str, patterns: tuple[str, ...]) -> bool:
    return any(
        fnmatch.fnmatch(name, pat) or fnmatch.fnmatch(rel_path, pat)
        for pat in patterns
    )


def iter_media_files(root: Path, config: DiscoveryConfig) -> Iterator[Path]:
    root = root.expanduser()
    visited: set[tuple[int, int]] = set()
    stack = [root]

    while stack:
        directory = stack.pop()
        try:
            stat = directory.stat()
            key = (stat.st_dev, stat.st_ino)
            if key in visited:  # ciclo (symlink/hardlink de diretório)
                continue
            visited.add(key)
            entries = sorted(os.scandir(directory), key=lambda e: e.name)
        except OSError as exc:
            log.warning("descoberta: pulando %s (%s)", directory, exc)
            continue

        for entry in entries:
            name = entry.name
            rel = os.path.relpath(entry.path, root)
            if not config.incluir_ocultos and name.startswith("."):
                continue
            if _ignored(name, rel, config.padroes_ignorados):
                continue
            try:
                is_symlink = entry.is_symlink()
                if entry.is_dir(follow_symlinks=config.seguir_symlinks):
                    if is_symlink and not config.seguir_symlinks:
                        continue
                    if name.lower() in JUNK_DIRS:
                        continue
                    stack.append(Path(entry.path))
                elif entry.is_file(follow_symlinks=config.seguir_symlinks):
                    if is_symlink and not config.seguir_symlinks:
                        continue
                    if name.lower() in SYSTEM_JUNK:
                        continue
                    if os.path.splitext(name)[1].lower() in config.extensoes:
                        yield Path(entry.path)
            except OSError as exc:
                log.warning("descoberta: pulando %s (%s)", entry.path, exc)
