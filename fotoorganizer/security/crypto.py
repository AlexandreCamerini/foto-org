"""Criptografia de dados biométricos (embeddings faciais).

Chave Fernet guardada no Keychain do macOS (via `security`, subprocesso
sem shell); fallback para arquivo 0600 no diretório de dados quando o
Keychain não está disponível (CI, testes). Limitações documentadas em
docs/PRIVACIDADE.md: protege o banco em repouso, não contra código rodando
na sessão desbloqueada do usuário.
"""

from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path
from typing import Protocol

from cryptography.fernet import Fernet

log = logging.getLogger(__name__)

_SERVICE = "FotoOrganizer"
_ACCOUNT = "embeddings-key"


class KeyStore(Protocol):
    def obter_ou_criar_chave(self) -> bytes: ...


class FileKeyStore:
    """Fallback: chave em arquivo com permissão 0600."""

    def __init__(self, data_dir: Path) -> None:
        self._path = data_dir / "embeddings.key"

    def obter_ou_criar_chave(self) -> bytes:
        if self._path.is_file():
            return self._path.read_bytes()
        chave = Fernet.generate_key()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.touch(mode=0o600)
        self._path.write_bytes(chave)
        self._path.chmod(0o600)
        return chave


class KeychainKeyStore:
    """Chave no Keychain do macOS. Argumentos em lista — nunca shell=True."""

    def obter_ou_criar_chave(self) -> bytes:
        achada = subprocess.run(
            ["security", "find-generic-password", "-a", _ACCOUNT,
             "-s", _SERVICE, "-w"],
            capture_output=True, text=True, timeout=10,
        )
        if achada.returncode == 0:
            return achada.stdout.strip().encode()

        chave = Fernet.generate_key()
        criada = subprocess.run(
            ["security", "add-generic-password", "-a", _ACCOUNT,
             "-s", _SERVICE, "-w", chave.decode(), "-U"],
            capture_output=True, text=True, timeout=10,
        )
        if criada.returncode != 0:
            raise OSError(f"keychain indisponível: {criada.stderr.strip()}")
        return chave


def keystore_padrao(data_dir: Path) -> KeyStore:
    """Keychain quando funciona; senão arquivo 0600 (com aviso no log)."""
    keychain = KeychainKeyStore()
    try:
        keychain.obter_ou_criar_chave()
        return keychain
    except (OSError, subprocess.SubprocessError):
        log.warning("keychain indisponível — usando chave em arquivo 0600")
        return FileKeyStore(data_dir)


class EmbeddingCipher:
    def __init__(self, keystore: KeyStore) -> None:
        self._fernet = Fernet(keystore.obter_ou_criar_chave())

    def cifrar(self, vetor: list[float]) -> bytes:
        return self._fernet.encrypt(json.dumps(vetor).encode())

    def decifrar(self, blob: bytes) -> list[float]:
        return json.loads(self._fernet.decrypt(blob))
