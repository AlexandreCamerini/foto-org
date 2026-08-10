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
from datetime import datetime, timezone
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


def _data(dados: dict) -> tuple[datetime | None, datetime | None]:
    """`photoTakenTime.timestamp` → (hora de parede, instante absoluto).

    O epoch do Takeout **é** o instante absoluto da captura — a informação de
    fuso mais confiável que esta fonte tem, e a única. Convertê-lo com
    `datetime.fromtimestamp(n)` sem fuso era um defeito com duas faces: a hora
    gravada passava a depender do fuso da MÁQUINA que rodou a importação (a
    mesma foto virava 13h em São Paulo, 18h em Paris e 16h em UTC), e o
    absoluto — que estava ali pronto — era descartado.

    O que o Takeout **não** diz é a hora que o relógio marcava no lugar da
    foto: para isso precisaria do fuso da captura, que o JSON não traz. Então
    os dois instantes saem iguais, que é como este catálogo diz "não sei o
    fuso" (`models/catalog.py`) — nunca "esta foto foi tirada em Greenwich".
    Quando a fase 11 estimar fuso a partir do GPS, é ela que separa os dois.
    """
    bruto = (dados.get("photoTakenTime") or {}).get("timestamp")
    if not bruto:
        return None, None
    try:
        absoluto = datetime.fromtimestamp(
            int(bruto), tz=timezone.utc
        ).replace(tzinfo=None)
    except (ValueError, OSError, OverflowError):
        return None, None
    return absoluto, absoluto


class GoogleTakeoutProvider:
    """Lê a pasta do Takeout.

    Por padrão **não abre as imagens**: o Takeout é uma exportação, quase
    sempre de fotos que o dono já tem em outro lugar, e costuma ter dezenas
    de GB. Ler cada arquivo significaria extrair EXIF, hashear e gerar
    miniatura de tudo para produzir uma biblioteca duplicada que será
    apagada. O que interessa é o sidecar JSON — em especial o `geoData`,
    que traz coordenada mesmo quando o export removeu o EXIF.

    Então os itens entram como referência: nome, tamanho e o que o Google
    sabe. `ler_arquivos=True` restaura o comportamento de catalogar de
    verdade, para quando o Takeout *for* o acervo.
    """

    def __init__(self, raiz: Path, ler_arquivos: bool = False) -> None:
        self._raiz = Path(raiz).expanduser()
        self._ler_arquivos = ler_arquivos

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
            # stat() lê a entrada de diretório, não o arquivo: o tamanho é
            # informação sobre a foto, não a foto.
            try:
                tamanho = media.stat().st_size
            except OSError:
                tamanho = None

            parede, absoluto = _data(dados)
            yield ExternalAsset(
                caminho=media if self._ler_arquivos else None,
                referencia=(
                    None if self._ler_arquivos
                    else str(media.relative_to(self._raiz))
                ),
                nome=media.name,
                tamanho=tamanho,
                data_capturada=parede,
                data_capturada_utc=absoluto,
                gps_lat=lat, gps_lon=lon,
                descricao=(dados.get("description") or "").strip() or None,
                favorito=bool(dados.get("favorited")),
                albuns=albuns,
                pessoas=pessoas,
            )
