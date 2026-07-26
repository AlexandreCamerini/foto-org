"""Provider do Apple Fotos (biblioteca local, somente leitura).

Lê o catálogo do Fotos via osxphotos — data, GPS, favoritos, álbuns,
título/descrição e pessoas que o usuário já nomeou lá. Nenhuma escrita
na biblioteca; nada de rede; originais do iCloud ainda não baixados são
pulados (sem arquivo local não há o que catalogar).

Requisitos de ambiente: o pacote opcional `osxphotos` (extra "apple") e
Acesso Total ao Disco concedido ao app — sem ele o macOS bloqueia a
leitura da biblioteca e o provider falha com mensagem clara, sem
derrubar o resto do app.
"""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path
from typing import Iterator

from fotoorganizer.models import SourceType
from fotoorganizer.sources.base import ExternalAsset

log = logging.getLogger(__name__)

_BIBLIOTECA_PADRAO = Path(
    "~/Pictures/Photos Library.photoslibrary"
).expanduser()


class ApplePhotosError(RuntimeError):
    """Biblioteca inacessível (permissão/ausente) ou osxphotos faltando."""


def _app_responsavel() -> str:
    """Nome do app no topo da árvore de processos — é a ele que o TCC do
    macOS atribui o Acesso Total ao Disco, não ao script Python.

    Saber isso economiza a hora que se perde autorizando o app errado. Em
    qualquer falha, devolve uma descrição genérica: a mensagem de erro não
    pode virar um segundo erro.
    """
    try:
        pid, encontrado = os.getpid(), None
        for _ in range(8):
            saida = subprocess.run(
                ["ps", "-o", "ppid=,comm=", "-p", str(pid)],
                capture_output=True, text=True, timeout=2, check=False,
            ).stdout.strip()
            if not saida:
                break
            ppid, _, comm = saida.partition(" ")
            if ".app/Contents/MacOS/" in comm:
                encontrado = comm.split("/")[-1]  # topo vence: sobrescreve
            if ppid.strip() in ("", "0", "1"):
                break
            pid = int(ppid)
        return f"o app «{encontrado}»" if encontrado else "o app que você usa"
    except Exception:  # pragma: no cover - diagnóstico best-effort
        return "o app que você usa"


def _asset_de(photo) -> ExternalAsset | None:
    """Converte um PhotoInfo (duck-typed, testável com fakes) em asset.
    None quando não há arquivo local (original só no iCloud)."""
    if photo.path is None:
        return None
    data = photo.date
    if data is not None and data.tzinfo is not None:
        # Hora local da foto, naive — coerente com EXIF no resto do catálogo.
        data = data.replace(tzinfo=None)
    lat, lon = (photo.location or (None, None))
    return ExternalAsset(
        caminho=Path(photo.path),
        data_capturada=data,
        gps_lat=lat, gps_lon=lon,
        titulo=(photo.title or None),
        descricao=(photo.description or None),
        favorito=bool(photo.favorite),
        albuns=tuple(dict.fromkeys(photo.albums or ())),
        pessoas=tuple(
            p for p in dict.fromkeys(photo.persons or ()) if p
        ),
    )


class ApplePhotosProvider:
    def __init__(self, biblioteca: Path | None = None) -> None:
        self._biblioteca = Path(biblioteca or _BIBLIOTECA_PADRAO).expanduser()

    @property
    def tipo(self) -> SourceType:
        return SourceType.APPLE_PHOTOS

    @property
    def raiz(self) -> Path:
        return self._biblioteca

    @property
    def apelido(self) -> str:
        return "Apple Fotos"

    def iter_assets(self) -> Iterator[ExternalAsset]:
        try:
            import osxphotos
        except ImportError as exc:  # extra "apple" não instalado
            raise ApplePhotosError(
                "osxphotos não instalado — instale com "
                "'pip install fotoorganizer[apple]'"
            ) from exc

        try:
            db = osxphotos.PhotosDB(str(self._biblioteca))
        except Exception as exc:
            raise ApplePhotosError(
                f"não consegui ler a biblioteca do Fotos em "
                f"{self._biblioteca}. O macOS concede Acesso Total ao Disco "
                f"por app, e quem precisa estar na lista é "
                f"{_app_responsavel()} — o app que iniciou este processo, "
                f"não o Foto Organizer. Ajustes → Privacidade e Segurança → "
                f"Acesso Total ao Disco, e reinicie o app depois de marcar."
            ) from exc

        pulados_icloud = 0
        for photo in db.photos(movies=False):
            asset = _asset_de(photo)
            if asset is None:
                pulados_icloud += 1
                continue
            yield asset
        if pulados_icloud:
            log.info(
                "apple_photos: %d itens sem original local (iCloud) pulados",
                pulados_icloud,
            )
