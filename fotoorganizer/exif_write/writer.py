"""Escreve GPS/cidade/país (D-075), escopo estreito, num arquivo original ou
num sidecar `.xmp`.

Autorizado por D-075 (revoga parte do invariante 7 do CLAUDE.md): só GPS
lat/long, cidade e país; só campo vazio (a checagem de "vazio" é
responsabilidade do planner, não deste módulo); nunca sobrescreve.
Invariante 5: subprocess sem shell habilitado, argumentos sempre em lista,
caminho resolvido pelo chamador antes de chegar aqui.

Diferença central para o analog de leitura (`metadata/exiftool.py`): aqui o
resultado do subprocesso **nunca** é o sinal de sucesso. Verificado
empiricamente que `exiftool -GPSLatitude=999 -GPSLatitudeRef=S <arquivo>`
é aceito em silêncio, exit 0 — quem aprova uma escrita é sempre
`verificacao.diferenca`/`campo_gravado`, chamado por quem invoca
`escrever()`, nunca o `CompletedProcess` devolvido aqui.
"""

from __future__ import annotations

import math
import shutil
import subprocess
from pathlib import Path

_TAMANHO_MAXIMO_TEXTO = 200


class ValorInvalido(ValueError):
    """Campo recusado antes de qualquer subprocesso."""


def validar_campos(campos: dict) -> None:
    """Única fronteira de validação deste pacote.

    Verificado empiricamente (RESEARCH.md Pitfall 1) que
    `-GPSLatitude=999` é aceito em silêncio pelo exiftool, exit 0 — sem
    validação aqui, ninguém valida.
    """
    if "gps" in campos:
        lat, lon = campos["gps"]
        if not math.isfinite(lat) or not (-90.0 <= lat <= 90.0):
            raise ValorInvalido(f"latitude fora de [-90, 90] ou não finita: {lat!r}")
        if not math.isfinite(lon) or not (-180.0 <= lon <= 180.0):
            raise ValorInvalido(f"longitude fora de [-180, 180] ou não finita: {lon!r}")

    for campo in ("cidade", "pais"):
        if campo not in campos:
            continue
        valor = campos[campo]
        if not isinstance(valor, str) or not valor.strip():
            raise ValorInvalido(f"{campo} vazio ou só espaço: {valor!r}")
        if "\n" in valor or "\r" in valor:
            raise ValorInvalido(f"{campo} contém quebra de linha, rejeitado: {valor!r}")
        if len(valor) > _TAMANHO_MAXIMO_TEXTO:
            raise ValorInvalido(
                f"{campo} passa de {_TAMANHO_MAXIMO_TEXTO} caracteres: {len(valor)}"
            )


class ExifToolWriter:
    """Um `subprocess.run` curto por escrita — não `-stay_open`.

    O leitor persistente serve um scan inteiro (dezenas de milhares de
    arquivos); o volume de escrita aqui é um plano revisado e aprovado
    (dezenas a milhares), então o custo de ~200 ms de partida por chamada é
    aceitável e evita disputar o lock do processo `-stay_open` do leitor
    compartilhado.
    """

    def __init__(self, binario: str | None = None) -> None:
        self._binario = binario or shutil.which("exiftool") or "exiftool"

    @staticmethod
    def disponivel(binario: str | None = None) -> bool:
        return shutil.which(binario or "exiftool") is not None

    @staticmethod
    def caminho_backup(alvo: Path) -> Path:
        """Nome que o exiftool usa por padrão para o backup do original."""
        return Path(str(alvo) + "_original")

    def escrever(
        self, origem: Path, campos: dict, destino: Path | None = None,
    ) -> subprocess.CompletedProcess:
        """Grava `campos` em `destino` (ou em `origem`, escrita direta).

        Sem `-overwrite_original`: o backup `_original` que o exiftool cria
        por padrão é a cópia literal de recuperação durante a janela entre
        escrita e verificação (RESEARCH.md Pitfall 7) — quem decide apagar
        esse backup é o executor, depois que o diff aprovar, como passo
        deliberado e auditado. Passar a flag aqui destruiria a recuperação
        exatamente na janela em que ela importa.

        `alvo.suffix == ".xmp"`: omite os argumentos `-IPTC:` — IPTC é
        formato de segmento binário de container de imagem, não existe num
        `.xmp` autônomo (verificado na pesquisa); só o grupo XMP vai.
        """
        validar_campos(campos)
        alvo = destino or origem
        sidecar = alvo.suffix.lower() == ".xmp"

        args = [self._binario]
        if "gps" in campos:
            lat, lon = campos["gps"]
            args += [
                f"-GPSLatitude={abs(lat)}",
                f"-GPSLatitudeRef={'N' if lat >= 0 else 'S'}",
                f"-GPSLongitude={abs(lon)}",
                f"-GPSLongitudeRef={'E' if lon >= 0 else 'W'}",
            ]
        if "cidade" in campos:
            # Os dois grupos são sempre gravados explicitamente: `-City`
            # sem prefixo cai em IPTC, `-Country` sem prefixo cai em
            # XMP-photoshop (assimetria verificada, RESEARCH.md Pitfall 3)
            # — gravar só um deixaria o dado invisível pra metade dos
            # consumidores. Sidecar não tem grupo IPTC (ver docstring).
            if not sidecar:
                args.append(f"-IPTC:City={campos['cidade']}")
            args.append(f"-XMP:City={campos['cidade']}")
        if "pais" in campos:
            if not sidecar:
                args.append(f"-IPTC:Country-PrimaryLocationName={campos['pais']}")
            args.append(f"-XMP:Country={campos['pais']}")

        args += ["-charset", "filename=utf8", str(alvo)]
        return subprocess.run(args, capture_output=True, text=True, check=False)
