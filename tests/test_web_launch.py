"""Lançamento do servidor web em porta efêmera para o empacotamento Tauri.

Cobre os três riscos transversais do embarque (docs/EMPACOTAMENTO.md):
(a) porta efêmera anunciada no stdout; (c) o guard de origem local segue
barrando Origin externa; (b) SIGTERM encerra o processo limpo.
"""

from __future__ import annotations

import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


def _iniciar_web(data_dir: Path) -> tuple[subprocess.Popen, str]:
    proc = subprocess.Popen(
        [
            sys.executable, "-m", "fotoorganizer",
            "--data-dir", str(data_dir), "web", "--porta", "0",
        ],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    url = None
    prazo = time.monotonic() + 40
    while time.monotonic() < prazo:
        linha = proc.stdout.readline() if proc.stdout else ""
        if not linha:
            if proc.poll() is not None:
                raise RuntimeError("o servidor saiu antes de anunciar a porta")
            continue
        if linha.startswith("FOTOORG_READY "):
            url = linha.split(" ", 1)[1].strip()
            break
    assert url, "servidor não anunciou FOTOORG_READY"
    return proc, url


def _status(url: str, origin: str | None = None) -> int:
    req = urllib.request.Request(url)
    if origin:
        req.add_header("Origin", origin)
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status
    except urllib.error.HTTPError as exc:
        return exc.code


def test_web_porta_efemera_anuncio_guard_e_shutdown(tmp_path):
    proc, url = _iniciar_web(tmp_path)
    try:
        # (a) a porta anunciada é efêmera (o SO escolheu), não a default 8765.
        assert url.startswith("http://127.0.0.1:")
        assert not url.endswith(":8765")

        # espera o servidor passar a aceitar conexões
        for _ in range(60):
            try:
                if _status(url + "/api/status") == 200:
                    break
            except OSError:
                pass
            time.sleep(0.1)

        # a UI (origem local, herdada da própria página) é atendida
        assert _status(url + "/api/status") == 200
        # (c) origem externa continua barrada — guard intacto
        assert _status(url + "/api/status", origin="https://evil.example") == 403
    finally:
        # (b) SIGTERM deve encerrar limpo, sem precisar de kill
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
            raise AssertionError(
                "o servidor não encerrou em SIGTERM (shutdown não-gracioso)"
            )
    assert proc.returncode is not None


def test_web_encerra_com_pai_nao_deixa_orfao(tmp_path):
    """Com --encerrar-com-pai o backend se auto-encerra se o pai morrer de
    qualquer forma (o shell Tauri usa isto para nunca deixar órfão)."""
    # Pai intermediário: nós matamos ELE; o backend (neto) deve perceber a
    # reparentação (ppid → 1) e sair sozinho.
    pai_src = (
        "import subprocess, sys, time\n"
        f"p = subprocess.Popen([sys.executable, '-m', 'fotoorganizer',"
        f" '--data-dir', {str(tmp_path)!r}, 'web', '--porta', '0',"
        f" '--encerrar-com-pai'])\n"
        "print(p.pid, flush=True)\n"
        "time.sleep(300)\n"
    )
    pai = subprocess.Popen(
        [sys.executable, "-c", pai_src], stdout=subprocess.PIPE, text=True
    )
    try:
        neto_pid = int(pai.stdout.readline().strip())
        # dá tempo do backend subir e iniciar o watchdog
        time.sleep(4)
        assert _pid_vivo(neto_pid), "backend não subiu"

        pai.kill()  # SIGKILL no pai → backend vira órfão (ppid=1)

        # o watchdog (poll de ~2s) deve encerrar o backend em poucos segundos
        for _ in range(20):
            if not _pid_vivo(neto_pid):
                break
            time.sleep(0.5)
        assert not _pid_vivo(neto_pid), "backend ficou órfão (watchdog falhou)"
    finally:
        pai.kill()
        try:
            import os
            import signal

            os.kill(neto_pid, signal.SIGKILL)
        except (ProcessLookupError, NameError, ValueError):
            pass


def _pid_vivo(pid: int) -> bool:
    import os

    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
