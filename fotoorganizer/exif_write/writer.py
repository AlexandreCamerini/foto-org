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
import os
import shutil
import signal
import subprocess
from pathlib import Path

_TAMANHO_MAXIMO_TEXTO = 200

# Teto por escrita. O exiftool reescreve o arquivo inteiro (não edita no
# lugar), então um RAW de dezenas de MB num NAS via SMB leva segundos, não
# milissegundos — 120 s cobre isso com folga e ainda impede que um volume
# que sumiu no meio da escrita segure o job para sempre (B13 da auditoria
# de 2026-09-19; o leitor em `verificacao.py` já tinha 30 s). Ao estourar,
# o exiftool recebe SIGINT e, se não obedecer, SIGKILL — ver `_executar`.
# Quem decide o que fazer com o `_original` é o executor.
TIMEOUT_ESCRITA_S = 120.0
# Quanto esperar o exiftool limpar depois do SIGINT antes do SIGKILL.
FOLGA_SIGINT_S = 5.0


def _executar(args: list[str], timeout: float, folga_sigint: float) -> subprocess.CompletedProcess:
    """`subprocess.run` com um detalhe que importa aqui: no timeout, SIGINT
    ANTES de SIGKILL.

    `run(timeout=)` mata com SIGKILL, que pula o handler de SIGINT do
    próprio exiftool — é ele quem apaga o temporário `<alvo>_exiftool_tmp`
    (achado da revisão de D-095, verificado contra o exiftool real: SIGKILL
    e SIGTERM deixam o temporário; SIGINT sai com rc 1 e o remove). Um
    temporário deixado para trás bloqueia TODA escrita futura naquele
    arquivo ("Temporary file already exists") — o item passaria a falhar
    para sempre com um motivo que não diz isso.
    """
    # Sessão própria: os sinais vão para o GRUPO, não só para o pid. Se o
    # binário for um wrapper que delega a um filho (ou se um dia o exiftool
    # tiver filho), sinalizar só o pai deixaria o neto vivo segurando os
    # pipes herdados — e `communicate()` depois do kill ficaria preso até
    # ele morrer sozinho (medido: 10 s num dublê com `sh` + `sleep`).
    proc = subprocess.Popen(
        args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        start_new_session=True,
    )

    def sinalizar(sig: signal.Signals) -> None:
        try:
            os.killpg(proc.pid, sig)
        except ProcessLookupError:
            pass  # já morreu entre o timeout e o sinal

    try:
        saida, erro = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        sinalizar(signal.SIGINT)
        try:
            saida, erro = proc.communicate(timeout=folga_sigint)
        except subprocess.TimeoutExpired:
            sinalizar(signal.SIGKILL)
            saida, erro = proc.communicate()
        raise subprocess.TimeoutExpired(args, timeout, output=saida, stderr=erro)
    return subprocess.CompletedProcess(args, proc.returncode, saida, erro)


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
        timeout: float = TIMEOUT_ESCRITA_S, folga_sigint: float = FOLGA_SIGINT_S,
    ) -> subprocess.CompletedProcess:
        """Grava `campos` em `destino` (ou em `origem`, escrita direta).

        Levanta `subprocess.TimeoutExpired` (o processo já encerrado — por
        SIGINT, ou SIGKILL se não obedeceu em `folga_sigint`) quando o
        exiftool passa de `timeout` segundos — nunca devolve um
        `CompletedProcess` de uma escrita que não terminou.

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
            if sidecar:
                # XMP não tem os dois tags EXIF separados (valor +
                # Ref) — `GPSLatitudeRef`/`GPSLongitudeRef` sem prefixo
                # de grupo resolvem para o grupo EXIF binário, que não
                # existe num `.xmp` autônomo, e a escrita é aceita em
                # silêncio sem efeito (achado real, A2 da auditoria:
                # exiftool 13.55, `-listx` confirma `writable='false'`
                # nesse contexto). O valor de `GPSLatitude`/`GPSLongitude`
                # gravava com `abs()`, então toda coordenada do
                # hemisfério sul/oeste virava norte/leste — a mesma
                # tag presente, o valor errado, e a verificação por
                # presença (antiga) aprovava. XMP-exif:GPSLatitude
                # aceita o valor ASSINADO diretamente (embute o
                # hemisfério na própria string, "22,57.0S") — testado
                # contra o exiftool real antes desta correção.
                args += [
                    f"-GPSLatitude={lat}",
                    f"-GPSLongitude={lon}",
                ]
            else:
                # Escrita direta: o EXIF binário real não tem sinal no
                # próprio GPSLatitude (é um racional sem sinal) — o
                # hemisfério SÓ existe no Ref, tag irmã separada. Sem
                # ela o sinal se perde de vez (testado contra o
                # exiftool real: valor assinado sozinho grava como se
                # fosse sempre positivo, sem Ref nenhuma).
                #
                # Grupo `-GPS:` explícito (achado da revisão com olhos
                # frescos, mesmo A2): sem prefixo, `-GPSLatitude=` é
                # ambíguo — se o arquivo já tem `XMP-exif:GPSLatitude`
                # (comum em foto que passou por Lightroom/Aftershoot),
                # o exiftool resolve para ESSE grupo em vez de criar o
                # bloco EXIF binário, grava o `abs()` sem Ref gravável
                # ali (mesma causa raiz de A2) e SOBRESCREVE a
                # coordenada real com hemisfério errado — sem backup
                # (não é a primeira escrita do bloco) e aprovado por
                # todas as verificações. `_campo_ja_preenchido`
                # (executor.py) já bloqueia isso na origem detectando
                # `XMP-exif:GPSLatitude` como "campo preenchido"; este
                # prefixo é defesa em profundidade — verificado contra
                # o exiftool real: com `-GPS:` explícito, um arquivo com
                # GPS só em XMP ganha um bloco EXIF binário NOVO, sem
                # tocar no XMP existente.
                args += [
                    f"-GPS:GPSLatitude={abs(lat)}",
                    f"-GPS:GPSLatitudeRef={'N' if lat >= 0 else 'S'}",
                    f"-GPS:GPSLongitude={abs(lon)}",
                    f"-GPS:GPSLongitudeRef={'E' if lon >= 0 else 'W'}",
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
        return _executar(args, timeout, folga_sigint)
