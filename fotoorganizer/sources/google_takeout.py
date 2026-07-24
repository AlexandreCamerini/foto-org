"""Provider de Google Takeout (pasta local exportada de photos.google.com).

O Takeout é a via local-first para o Google Photos: desde março/2025 a
Library API só acessa mídia criada pelo próprio app, então a exportação
oficial é o caminho que não fura o invariante de privacidade — nada aqui
fala com a rede.

Estrutura esperada (qualquer nível acima também serve):
    Takeout/Google Photos/<álbum ou "Photos from 2024">/IMG_001.jpg
    ...IMG_001.jpg.json  (ou .supplemental-metadata.json)

O sidecar JSON carrega o que o Google sabe e o arquivo às vezes não:
`photoTakenTime` (epoch UTC), `geoData` (GPS que o app do Google Photos
registrou mesmo quando o EXIF foi removido no export), `description`,
`favorited` e pessoas nomeadas.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Iterator

from fotoorganizer.models import SourceType
from fotoorganizer.sources.base import ExternalAsset

log = logging.getLogger(__name__)

# Extensões de mídia que o Takeout costuma conter e o app cataloga.
_MEDIA_EXTS = {
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".tif", ".tiff", ".bmp",
    ".heic", ".heif",
}

# Pastas de ano ("Photos from 2024" / "Fotos de 2024") não são álbuns.
_RE_PASTA_ANO = re.compile(r"^(photos from|fotos de)\s+\d{4}$", re.IGNORECASE)


def _sidecar_de(media: Path) -> Path | None:
    """Acha o JSON do arquivo, cobrindo as variantes comuns do Takeout."""
    candidatos = [
        media.with_name(media.name + ".json"),
        media.with_name(media.name + ".supplemental-metadata.json"),
    ]
    # "IMG_001(1).jpg" ganha sidecar "IMG_001.jpg(1).json".
    m = re.match(r"^(.*)\((\d+)\)(\.[^.]+)$", media.name)
    if m:
        base, n, ext = m.groups()
        candidatos.append(media.with_name(f"{base}{ext}({n}).json"))
        candidatos.append(
            media.with_name(f"{base}{ext}.supplemental-metadata({n}).json")
        )
    for candidato in candidatos:
        if candidato.is_file():
            return candidato
    return None


def _gps(dados: dict) -> tuple[float | None, float | None]:
    for chave in ("geoData", "geoDataExif"):
        geo = dados.get(chave) or {}
        lat, lon = geo.get("latitude"), geo.get("longitude")
        # 0.0/0.0 é o "sem GPS" do Takeout, não uma coordenada real.
        if lat and lon:
            return float(lat), float(lon)
    return None, None


def _data(dados: dict) -> datetime | None:
    bruto = (dados.get("photoTakenTime") or {}).get("timestamp")
    if not bruto:
        return None
    try:
        # Epoch UTC → hora local naive, coerente com o resto do catálogo
        # (EXIF é hora local da câmera). Desvios entre fontes são tratados
        # pela correlação temporal, não aqui.
        return datetime.fromtimestamp(int(bruto))
    except (ValueError, OSError):
        return None


class GoogleTakeoutProvider:
    def __init__(self, raiz: Path) -> None:
        self._raiz = Path(raiz).expanduser()

    @property
    def tipo(self) -> SourceType:
        return SourceType.GOOGLE_TAKEOUT

    @property
    def raiz(self) -> Path:
        return self._raiz

    @property
    def apelido(self) -> str:
        return "Google Takeout"

    def iter_assets(self) -> Iterator[ExternalAsset]:
        for media in sorted(self._raiz.rglob("*")):
            if not media.is_file() or media.suffix.lower() not in _MEDIA_EXTS:
                continue

            dados: dict = {}
            sidecar = _sidecar_de(media)
            if sidecar is not None:
                try:
                    dados = json.loads(sidecar.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError) as exc:
                    log.warning("takeout: sidecar ilegível %s (%s)",
                                sidecar, exc)

            pasta = media.parent.name
            albuns: tuple[str, ...] = ()
            if pasta and not _RE_PASTA_ANO.match(pasta.strip()):
                albuns = (pasta,)

            lat, lon = _gps(dados)
            pessoas = tuple(
                p.get("name", "").strip()
                for p in dados.get("people", ())
                if p.get("name", "").strip()
            )
            yield ExternalAsset(
                caminho=media,
                data_capturada=_data(dados),
                gps_lat=lat, gps_lon=lon,
                descricao=(dados.get("description") or "").strip() or None,
                favorito=bool(dados.get("favorited")),
                albuns=albuns,
                pessoas=pessoas,
            )
