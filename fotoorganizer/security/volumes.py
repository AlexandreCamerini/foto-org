"""Identidade de volume — o que sobrevive a desmontar e montar de novo.

Um acervo grande vive espalhado por NAS e discos externos que vão e voltam, e
o macOS não promete o ponto de montagem: um disco chamado "photo" monta em
`/Volumes/photo` hoje e em `/Volumes/photo 1` amanhã, se o nome colidir. Com o
caminho como identidade da fonte, essa remontagem vira "disco novo" e o app
recataloga 45 mil fotos do zero.

Então a identidade é o volume, não o caminho:

1. **UUID do volume** (`diskutil`), quando existe. Sobrevive a remontagem, a
   renomear e a trocar de máquina.
2. **Servidor e compartilhamento**, para NAS: um SMB não tem UUID, mas
   `//alex@nas/fotos` identifica o mesmo lugar em qualquer sessão.
3. **Ponto de montagem**, como último recurso, com o aviso de que essa
   identidade é frágil.

Subprocesso sem `shell=True`, argumentos em lista, caminho resolvido antes
(invariante 5). Falha de `diskutil` nunca levanta — devolve a identidade mais
fraca e segue.
"""

from __future__ import annotations

import logging
import os
import plistlib
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)

_TIMEOUT_S = 10.0
# "//alex@nas._smb._tcp.local/fotos on /Volumes/fotos (smbfs, ...)"
_RE_MOUNT = re.compile(r"^(?P<origem>.+?) on (?P<ponto>.+?) \((?P<opcoes>.*)\)$")
_TIPOS_DE_REDE = frozenset({"smbfs", "afpfs", "nfs", "webdav", "ftp"})


@dataclass(frozen=True, slots=True)
class Volume:
    """Onde um arquivo mora, de um jeito que sobrevive à remontagem."""

    identidade: str
    nome: str | None
    ponto_de_montagem: Path
    tipo: str | None = None
    removivel: bool = False
    # False quando a identidade é o próprio caminho: ela não sobrevive a
    # remontar noutro lugar, e quem depende dela precisa saber disso.
    estavel: bool = True
    # O volume está acessível agora? Um disco desligado ainda tem identidade
    # e não tem conteúdo — a diferença entre "sumiu" e "está na gaveta".
    montado: bool = True

    @property
    def de_rede(self) -> bool:
        return (self.tipo or "") in _TIPOS_DE_REDE


def volume_desmontado(caminho: Path | str) -> Path | None:
    """`/Volumes/<nome>` que o caminho pede e que não está montado.

    Sem esta checagem, subir a árvore a partir de um disco desligado chega
    até `/` e atribui as fotos dele ao disco de boot — trocando "está na
    gaveta" por "está aqui", que é o erro mais caro possível num acervo
    espalhado.
    """
    partes = Path(caminho).expanduser().parts
    if len(partes) < 3 or partes[1] != "Volumes":
        return None
    raiz = Path(partes[0], partes[1], partes[2])
    return None if os.path.ismount(raiz) else raiz


def ponto_de_montagem(caminho: Path | str) -> Path:
    """O volume onde o caminho vive. Sobe até achar um ponto de montagem —
    o caminho não precisa existir."""
    ausente = volume_desmontado(caminho)
    if ausente is not None:
        return ausente
    atual = Path(caminho).expanduser()
    atual = atual if atual.is_absolute() else atual.resolve()
    while True:
        try:
            if os.path.ismount(atual):
                return atual
        except OSError:
            pass
        if atual.parent == atual:
            return atual
        atual = atual.parent


def _tabela_de_montagem() -> dict[str, tuple[str, str]]:
    """{ponto: (origem, tipo)} lido de `mount`. Vazio se der errado."""
    try:
        saida = subprocess.run(
            ["/sbin/mount"], capture_output=True, text=True,
            timeout=_TIMEOUT_S, check=True,
        ).stdout
    except (OSError, subprocess.SubprocessError) as exc:
        log.debug("mount indisponível (%s)", exc)
        return {}
    tabela: dict[str, tuple[str, str]] = {}
    for linha in saida.splitlines():
        m = _RE_MOUNT.match(linha.strip())
        if m:
            tipo = m["opcoes"].split(",")[0].strip()
            tabela[m["ponto"]] = (m["origem"], tipo)
    return tabela


def _diskutil(ponto: Path) -> dict:
    try:
        saida = subprocess.run(
            ["diskutil", "info", "-plist", str(ponto)],
            capture_output=True, timeout=_TIMEOUT_S, check=True,
        ).stdout
        return plistlib.loads(saida)
    except (OSError, subprocess.SubprocessError, plistlib.InvalidFileException,
            ValueError) as exc:
        # Volume de rede não aparece no diskutil — é esperado, não é erro.
        log.debug("diskutil não descreveu %s (%s)", ponto, exc)
        return {}


def identificar(caminho: Path | str) -> Volume:
    """Descreve o volume de um caminho. Nunca levanta."""
    ausente = volume_desmontado(caminho)
    if ausente is not None:
        # Nada a perguntar ao sistema: o disco não está aqui. O nome do
        # ponto é tudo que se sabe, e é o bastante para reencontrá-lo.
        return Volume(f"caminho:{ausente}", ausente.name, ausente,
                      None, True, False, montado=False)

    ponto = ponto_de_montagem(caminho)
    tabela = _tabela_de_montagem()
    origem, tipo = tabela.get(str(ponto), (None, None))
    info = _diskutil(ponto)

    uuid = info.get("VolumeUUID") or ""
    nome = info.get("VolumeName") or (ponto.name or str(ponto))
    removivel = bool(info.get("Ejectable") or info.get("RemovableMedia"))
    tipo = info.get("FilesystemType") or tipo

    if uuid:
        return Volume(f"uuid:{uuid}", nome, ponto, tipo, removivel, True)
    if origem and (tipo or "") in _TIPOS_DE_REDE:
        # "//alex@nas._smb._tcp.local/fotos" → identidade sem a sessão.
        return Volume(f"rede:{origem}", nome, ponto, tipo, False, True)
    return Volume(f"caminho:{ponto}", nome, ponto, tipo, removivel, False)


def montado_em(identidade: str) -> Path | None:
    """Onde este volume está montado AGORA, ou None se não estiver.

    É o que permite reencontrar um disco que voltou noutro ponto: a fonte
    guarda a identidade, e o caminho é resolvido a cada uso.
    """
    if not identidade:
        return None
    for ponto in _tabela_de_montagem():
        try:
            if identificar(Path(ponto)).identidade == identidade:
                return Path(ponto)
        except OSError:
            continue
    return None
