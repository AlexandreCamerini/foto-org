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
JUNK_DIRS = {"@eadir", ".thumbnails"}

# Pastas de trabalho de programação. Diferente dos pacotes de biblioteca de
# foto abaixo, estas não são testemunha de nada: um ícone de app não tem data
# de captura nem GPS para doar. O estrago é duplo — entram na contagem como se
# fossem fotos e, pior, emprestam o nome da pasta para batizar evento de foto
# de verdade: num acervo real, 1.314 fotos foram parar num evento chamado
# "BoraChurrascoRio.imageset", vindo de um Assets.xcassets.
PASTAS_DE_CODIGO = {
    "node_modules", "bower_components", "__pycache__", "site-packages",
    "deriveddata", "pods", "venv", "vendor", "target",
}
# Pacotes de software cujo nome é "<QualquerCoisa>.sufixo". O miolo do nome
# não importa: o sufixo já diz que aquilo é um contêiner de app, não uma pasta
# de fotos.
SUFIXOS_DE_CODIGO = (
    ".xcassets", ".imageset", ".appiconset", ".colorset", ".dataset",
    ".xcodeproj", ".xcworkspace", ".playground", ".lproj",
    ".framework", ".bundle", ".app",
)

# Pacotes de biblioteca de foto do macOS. O nome real é "<Qualquer
# Nome>.photoslibrary", então o casamento é por SUFIXO — antes estavam em
# JUNK_DIRS, comparados por nome exato, e nunca casavam: um acervo real
# entrou com 45.822 miniaturas internas do Apple Fotos catalogadas como foto.
#
# Descer neles continua valendo: os derivados carregam GPS que o catálogo
# externo não reporta. O que muda é o papel — entram como testemunha, não
# como acervo (invariante 8, D-024).
SUFIXOS_DE_PACOTE = (
    ".photoslibrary",
    ".photolibrary",
    ".migratedphotolibrary",
    ".aplibrary",
)


def e_pasta_de_codigo(nome: str) -> bool:
    """Pasta de trabalho de programação — nem acervo, nem testemunha."""
    norm = nome.lower()
    return norm in PASTAS_DE_CODIGO or norm.endswith(SUFIXOS_DE_CODIGO)


def dentro_de_pacote(caminho: Path | str) -> bool:
    """True quando o arquivo mora dentro de um pacote de biblioteca de foto.

    Olha o caminho inteiro, não só o pai: os derivados ficam vários níveis
    abaixo, em `.../resources/derivatives/masters/`.
    """
    partes = Path(caminho).parts
    return any(
        parte.lower().endswith(SUFIXOS_DE_PACOTE) for parte in partes
    )


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
                    if name.lower() in JUNK_DIRS or e_pasta_de_codigo(name):
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
