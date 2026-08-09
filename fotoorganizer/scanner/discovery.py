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
    # Cache de aplicativo. Ninguém guarda acervo numa pasta chamada "Cache",
    # e o que mora lá não é testemunha de nada: medido no acervo do dono,
    # 1.840 texturas de efeito do CapCut (~/Movies/CapCut/User Data/Cache)
    # entraram como ACERVO com 0 GPS, 0 câmera e 36 datas — e nunca doaram
    # lugar a foto nenhuma.
    "cache", "caches",
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
    # Smart Previews do Lightroom: DNG de pré-visualização dentro de
    # "<Catálogo> Smart Previews.lrdata". Medido no acervo do dono: 14.755
    # deles entraram como ACERVO e são 57% do que o app dizia ser
    # organizável — todos ilegíveis (LibRawFileUnsupportedError), porque não
    # são RAW de verdade. Rebaixar, e não pular, porque carregam 1.113
    # coordenadas: hoje inertes (não têm data, e a herança de D-025 casa por
    # tempo), mas é exatamente o tipo de testemunha que o invariante 8
    # protege. `.lrlibrary` NÃO entra aqui — aquele guarda original.
    ".lrdata",
)

# Destes sufixos, o pacote separa o ORIGINAL (uma pasta própria) do
# derivado (o resto): Apple Fotos guarda em "originals", Aperture/iPhoto em
# "Masters". `.lrdata` fica de fora — por dentro é sempre pré-visualização,
# nunca original, mesmo que uma subpasta por acaso se chame "originals".
SUFIXOS_COM_ORIGINAL_PROPRIO = (
    ".photoslibrary",
    ".photolibrary",
    ".migratedphotolibrary",
    ".aplibrary",
)

# A pasta que guarda o original dentro dos sufixos acima. Medido num
# acervo real: 21.387 arquivos aqui eram rebaixados a testemunha por
# `dentro_de_pacote` tratar o pacote inteiro como derivado — 8.419 deles
# sem cópia em lugar nenhum, nunca vistos em Revisão, Viagens ou Operações
# (docs/AVALIACAO_UX.md, seção C.2, medido em 2026-08-06).
_PASTAS_DE_ORIGINAL_NO_PACOTE = frozenset({"originals", "masters"})


def e_pasta_de_codigo(nome: str) -> bool:
    """Pasta de trabalho de programação — nem acervo, nem testemunha."""
    norm = nome.lower()
    return norm in PASTAS_DE_CODIGO or norm.endswith(SUFIXOS_DE_CODIGO)


def dentro_de_pacote(caminho: Path | str) -> bool:
    """True quando o arquivo mora dentro de um pacote de biblioteca de foto
    e não é ele próprio o original que o pacote guarda.

    Olha o caminho inteiro, não só o pai: os derivados ficam vários níveis
    abaixo, em `.../resources/derivatives/masters/`. Só o nível
    imediatamente abaixo da raiz do pacote decide original × derivado — o
    resto do caminho, além dele, não importa para essa decisão.
    """
    partes = Path(caminho).parts
    for i, parte in enumerate(partes):
        baixo = parte.lower()
        if not baixo.endswith(SUFIXOS_DE_PACOTE):
            continue
        if baixo.endswith(SUFIXOS_COM_ORIGINAL_PROPRIO):
            seguinte = partes[i + 1].lower() if i + 1 < len(partes) else ""
            if seguinte in _PASTAS_DE_ORIGINAL_NO_PACOTE:
                return False
        return True
    return False


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


def iter_media_files(
    root: Path, config: DiscoveryConfig, erros: list[Path] | None = None
) -> Iterator[Path]:
    """`erros`, se passado, recebe cada diretório que falhou (permissão,
    I/O) — por referência, do mesmo jeito que `ScanControl` coordena
    cancelamento. Sem isto, quem chama não tem como saber se o walk viu a
    árvore inteira ou parou de produzir itens no meio em silêncio: um NAS
    que cai ou uma subpasta que perde permissão faz o generator só parar de
    produzir dali pra frente, sem levantar exceção — e um scan que confia
    cegamente nisso para decidir "o que sumiu" marcaria arquivo de verdade
    como offline. Default `None` preserva o comportamento de sempre para
    quem não passa nada."""
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
            if erros is not None:
                erros.append(directory)
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
                if erros is not None:
                    erros.append(Path(entry.path))
