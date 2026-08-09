"""Testes do downloader seguro.

Servidor HTTP local em 127.0.0.1 (porta efêmera) — nenhum teste toca a
rede real. As rotas existem para exercitar as três formas de o corpo
chegar sem tamanho confiável: `Content-Length` honesto, `chunked` (sem
header nenhum) e delimitação por fecho de conexão.
"""

from __future__ import annotations

import errno
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from fotoorganizer.security.http_seguro import (
    CorpoNaoConfere,
    DestinoJaExiste,
    ErroDeArquivo,
    ErroDeDownload,
    ErroDeRede,
    ErroHTTP,
    EsquemaNaoPermitido,
    TamanhoExcedido,
    TempoEsgotado,
    UrlInvalida,
    baixar_arquivo,
)

CONTEUDO = b"conteudo pequeno e honesto\n"
GRANDE = b"x" * 200_000
TRUNCADO = b"y" * 500


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):  # silencia o servidor no output do pytest
        pass

    def _corpo(self, corpo: bytes, *, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def _chunked(self, corpo: bytes, *, encerrar: bool = True) -> None:
        """Sem Content-Length: o cliente só descobre o tamanho lendo."""
        self.send_response(200)
        self.send_header("Transfer-Encoding", "chunked")
        self.end_headers()
        for inicio in range(0, len(corpo), 8192):
            pedaco = corpo[inicio:inicio + 8192]
            self.wfile.write(f"{len(pedaco):x}\r\n".encode() + pedaco + b"\r\n")
        if encerrar:
            self.wfile.write(b"0\r\n\r\n")

    def do_GET(self):  # noqa: N802
        rota = self.path

        if rota == "/ok":
            self._corpo(CONTEUDO)

        elif rota == "/grande":
            # Content-Length honesto e acima do limite: falha rápida.
            self._corpo(GRANDE)

        elif rota == "/chunked-grande":
            # Nenhum header de tamanho — só o teto real segura.
            self._chunked(GRANDE)

        elif rota == "/sem-tamanho":
            # Delimitado por fecho de conexão: idem.
            self.send_response(200)
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(GRANDE)
            self.close_connection = True

        elif rota == "/mentiroso":
            # Content-Length minúsculo, corpo enorme atrás dele.
            self.send_response(200)
            self.send_header("Content-Length", "10")
            self.end_headers()
            self.wfile.write(GRANDE)
            self.close_connection = True

        elif rota == "/truncado":
            # Content-Length grande, corpo curto, conexão cortada no meio:
            # `HTTPResponse.read` devolve b"" sem levantar erro nenhum.
            self.send_response(200)
            self.send_header("Content-Length", str(len(GRANDE)))
            self.end_headers()
            self.wfile.write(TRUNCADO)
            self.close_connection = True

        elif rota == "/interrompido":
            # Chunked que morre no meio: erro depois de bytes já lidos.
            self._chunked(b"y" * 16384, encerrar=False)
            self.close_connection = True

        elif rota == "/lento":
            time.sleep(5)
            self._corpo(CONTEUDO)

        elif rota == "/redir-file":
            self.send_response(302)
            self.send_header("Location", "file:///etc/passwd")
            self.send_header("Content-Length", "0")
            self.end_headers()

        elif rota == "/redir-ftp":
            # ftp é aceito pelo urllib por padrão; nossa allow-list não.
            self.send_response(302)
            self.send_header("Location", "ftp://exemplo.invalido/x")
            self.send_header("Content-Length", "0")
            self.end_headers()

        elif rota == "/redir-ok":
            self.send_response(302)
            self.send_header("Location", "/ok")
            self.send_header("Content-Length", "0")
            self.end_headers()

        elif rota == "/erro":
            self._corpo(b"nao existe", status=404)

        else:
            self._corpo(b"?", status=404)


class _Servidor(ThreadingHTTPServer):
    daemon_threads = True  # /lento não pode segurar o shutdown


@pytest.fixture(scope="module")
def base_url():
    servidor = _Servidor(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=servidor.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{servidor.server_address[1]}"
    finally:
        servidor.shutdown()
        servidor.server_close()
        thread.join(timeout=5)


def _restos(diretorio: Path) -> list[str]:
    return sorted(p.name for p in diretorio.iterdir())


# --- allow-list de esquema -------------------------------------------------

@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "FILE:///etc/passwd",
        "ftp://exemplo.invalido/x",
        "data:text/plain,oi",
        "javascript:alert(1)",
        "gopher://exemplo.invalido/x",
    ],
)
def test_esquema_rejeitado(url, tmp_path):
    destino = tmp_path / "saida.bin"
    with pytest.raises(EsquemaNaoPermitido):
        baixar_arquivo(url, destino)
    assert not destino.exists()
    assert _restos(tmp_path) == []


def test_esquema_e_case_insensitive(base_url, tmp_path):
    """`HTTP://` é permitido; `FILE://` não (coberto acima) — a
    comparação não pode depender da caixa."""
    destino = tmp_path / "a.bin"
    url = base_url.replace("http://", "HTTP://") + "/ok"
    assert baixar_arquivo(url, destino) == len(CONTEUDO)
    assert destino.read_bytes() == CONTEUDO


def test_url_sem_host(tmp_path):
    with pytest.raises(UrlInvalida):
        baixar_arquivo("http:///caminho", tmp_path / "a.bin")


def test_redirecionamento_para_esquema_proibido(base_url, tmp_path):
    destino = tmp_path / "a.bin"
    with pytest.raises(EsquemaNaoPermitido):
        baixar_arquivo(f"{base_url}/redir-file", destino)
    assert not destino.exists()
    assert _restos(tmp_path) == []


def test_redirecionamento_para_ftp(base_url, tmp_path):
    destino = tmp_path / "a.bin"
    with pytest.raises(EsquemaNaoPermitido):
        baixar_arquivo(f"{base_url}/redir-ftp", destino)
    assert _restos(tmp_path) == []


def test_redirecionamento_http_e_seguido(base_url, tmp_path):
    destino = tmp_path / "a.bin"
    assert baixar_arquivo(f"{base_url}/redir-ok", destino) == len(CONTEUDO)
    assert destino.read_bytes() == CONTEUDO


# --- caminho feliz ---------------------------------------------------------

def test_download_simples(base_url, tmp_path):
    destino = tmp_path / "sub" / "a.bin"
    gravados = baixar_arquivo(f"{base_url}/ok", destino)
    assert gravados == len(CONTEUDO)
    assert destino.read_bytes() == CONTEUDO
    assert _restos(destino.parent) == ["a.bin"]


def test_permissao_do_arquivo_final(base_url, tmp_path):
    destino = tmp_path / "a.bin"
    baixar_arquivo(f"{base_url}/ok", destino)
    assert destino.stat().st_mode & 0o777 == 0o600


# --- limite real de tamanho ------------------------------------------------

def test_content_length_honesto_acima_do_limite(base_url, tmp_path):
    destino = tmp_path / "a.bin"
    with pytest.raises(TamanhoExcedido) as info:
        baixar_arquivo(f"{base_url}/grande", destino, tamanho_maximo_bytes=1024)
    assert info.value.limite == 1024
    assert not destino.exists()
    assert _restos(tmp_path) == []


def test_corpo_chunked_sem_content_length_acima_do_limite(base_url, tmp_path):
    """Sem header nenhum, só o teto real da leitura segura."""
    destino = tmp_path / "a.bin"
    with pytest.raises(TamanhoExcedido):
        baixar_arquivo(
            f"{base_url}/chunked-grande", destino, tamanho_maximo_bytes=32_768
        )
    assert not destino.exists()
    assert _restos(tmp_path) == []


def test_corpo_delimitado_por_fecho_acima_do_limite(base_url, tmp_path):
    destino = tmp_path / "a.bin"
    with pytest.raises(TamanhoExcedido):
        baixar_arquivo(
            f"{base_url}/sem-tamanho", destino, tamanho_maximo_bytes=32_768
        )
    assert not destino.exists()
    assert _restos(tmp_path) == []


def test_limite_invalido(tmp_path):
    with pytest.raises(ValueError):
        baixar_arquivo("http://127.0.0.1/x", tmp_path / "a", tamanho_maximo_bytes=0)


# --- o corpo tem de bater com o Content-Length -----------------------------
#
# As duas direções do header mentiroso. O estrago é o mesmo nas duas: um
# arquivo no disco que o chamador acredita ser o recurso inteiro e não é.
# Nenhuma das duas levanta erro sozinha — `HTTPResponse.read` devolve b""
# no corte e corta a leitura no excesso.

def test_content_length_maior_que_o_corpo_e_rejeitado(base_url, tmp_path):
    """Servidor declara 200 KB, manda 500 bytes e fecha a conexão.

    Sem a conferência, isto virava um arquivo de 500 bytes promovido a
    download completo — o pior desfecho possível, porque é silencioso.
    """
    destino = tmp_path / "a.bin"
    with pytest.raises(CorpoNaoConfere) as info:
        baixar_arquivo(f"{base_url}/truncado", destino, timeout=5)
    assert info.value.declarado == len(GRANDE)
    assert info.value.lidos == len(TRUNCADO)
    assert not destino.exists()
    assert _restos(tmp_path) == []


def test_content_length_menor_que_o_corpo_e_rejeitado(base_url, tmp_path):
    """Servidor declara 10 bytes e manda 200 KB.

    O `urllib` corta a leitura nos 10 declarados, então o contador sozinho
    bateria (10 == 10) e o arquivo sairia como completo. Tem de falhar.
    """
    destino = tmp_path / "a.bin"
    with pytest.raises(CorpoNaoConfere) as info:
        baixar_arquivo(f"{base_url}/mentiroso", destino, timeout=5)
    assert info.value.declarado == 10
    assert not destino.exists()
    assert _restos(tmp_path) == []


def test_content_length_mentiroso_nunca_grava_alem_do_limite(base_url, tmp_path):
    """Mesma rota, agora com o teto de tamanho apertado: seja qual for o
    caminho de falha, nada do corpo de 200 KB chega ao disco e nenhum
    `.part` fica para trás."""
    destino = tmp_path / "a.bin"
    with pytest.raises(ErroDeDownload):
        baixar_arquivo(
            f"{base_url}/mentiroso", destino, tamanho_maximo_bytes=1024, timeout=5
        )
    assert not destino.exists()
    assert _restos(tmp_path) == []


def test_content_length_honesto_nao_e_falso_positivo(base_url, tmp_path):
    """A conferência não pode acusar corpo divergente em resposta normal —
    inclusive na que chega em vários pedaços."""
    destino = tmp_path / "a.bin"
    assert baixar_arquivo(
        f"{base_url}/grande", destino, tamanho_maximo_bytes=1_000_000
    ) == len(GRANDE)
    assert destino.read_bytes() == GRANDE


# --- falhas de rede e timeout ---------------------------------------------

def test_timeout(base_url, tmp_path):
    destino = tmp_path / "a.bin"
    inicio = time.monotonic()
    with pytest.raises(TempoEsgotado):
        baixar_arquivo(f"{base_url}/lento", destino, timeout=0.5)
    assert time.monotonic() - inicio < 4  # não esperou os 5s do servidor
    assert not destino.exists()
    assert _restos(tmp_path) == []


def test_conexao_recusada(tmp_path):
    # Porta fechada em loopback: erro de rede, não travamento.
    destino = tmp_path / "a.bin"
    with pytest.raises(ErroDeRede):
        baixar_arquivo("http://127.0.0.1:9/nada", destino, timeout=2)
    assert not destino.exists()


def test_status_de_erro(base_url, tmp_path):
    destino = tmp_path / "a.bin"
    with pytest.raises(ErroHTTP) as info:
        baixar_arquivo(f"{base_url}/erro", destino)
    assert info.value.status == 404
    assert not destino.exists()
    assert _restos(tmp_path) == []


def test_corpo_interrompido_no_meio_nao_deixa_parcial(base_url, tmp_path):
    """Erro depois de já ter lido e gravado bytes: o destino não pode
    existir e o `.part` tem de sumir."""
    destino = tmp_path / "a.bin"
    with pytest.raises(ErroDeRede):
        baixar_arquivo(f"{base_url}/interrompido", destino, timeout=3)
    assert not destino.exists()
    assert _restos(tmp_path) == []


# --- escrita atômica -------------------------------------------------------

def test_nao_sobrescreve_destino_existente(base_url, tmp_path):
    destino = tmp_path / "a.bin"
    destino.write_bytes(b"original")
    with pytest.raises(DestinoJaExiste):
        baixar_arquivo(f"{base_url}/ok", destino)
    assert destino.read_bytes() == b"original"
    assert _restos(tmp_path) == ["a.bin"]


def test_sobrescrever_explicito(base_url, tmp_path):
    destino = tmp_path / "a.bin"
    destino.write_bytes(b"original")
    baixar_arquivo(f"{base_url}/ok", destino, sobrescrever=True)
    assert destino.read_bytes() == CONTEUDO
    assert _restos(tmp_path) == ["a.bin"]


def test_destino_e_diretorio(base_url, tmp_path):
    pasta = tmp_path / "pasta"
    pasta.mkdir()
    with pytest.raises(ErroDeDownload):
        baixar_arquivo(f"{base_url}/ok", pasta)
    assert pasta.is_dir()


def test_destino_so_aparece_no_fim(base_url, tmp_path, monkeypatch):
    """Enquanto o corpo está sendo lido, o nome final não existe."""
    from fotoorganizer.security import http_seguro

    visto: list[bool] = []
    original = http_seguro._promover
    destino = tmp_path / "a.bin"

    def espiao(temporario, alvo, sobrescrever):
        visto.append(alvo.exists())  # antes da promoção
        return original(temporario, alvo, sobrescrever)

    monkeypatch.setattr(http_seguro, "_promover", espiao)
    http_seguro.baixar_arquivo(f"{base_url}/ok", destino)
    assert visto == [False]
    assert destino.exists()


# --- erros de filesystem continuam dentro do contrato ----------------------
#
# O docstring promete que tudo que sai de `baixar_arquivo` é `ErroDeDownload`.
# Isso vale também quando quem falha é o disco, não a rede.

def test_link_nao_suportado_vira_erro_do_modulo(base_url, tmp_path, monkeypatch):
    """`os.link` com EOPNOTSUPP — o que um destino em exFAT/SMB devolve.

    Antes escapava como `OSError` cru pelo meio do chamador.
    """
    from fotoorganizer.security import http_seguro

    def sem_link(origem, alvo):
        raise OSError(errno.EOPNOTSUPP, "Operation not supported")

    monkeypatch.setattr(http_seguro.os, "link", sem_link)
    destino = tmp_path / "a.bin"
    with pytest.raises(ErroDeArquivo) as info:
        baixar_arquivo(f"{base_url}/ok", destino)
    assert isinstance(info.value, ErroDeDownload)
    assert isinstance(info.value.__cause__, OSError)
    assert not destino.exists()
    assert _restos(tmp_path) == []  # o parcial saiu mesmo assim


@pytest.mark.skipif(
    hasattr(os, "geteuid") and os.geteuid() == 0,
    reason="root escreve em diretório sem permissão de escrita",
)
def test_diretorio_sem_escrita_vira_erro_do_modulo(base_url, tmp_path):
    """`mkstemp` com PermissionError — idem: erro do módulo, não cru."""
    pasta = tmp_path / "somente-leitura"
    pasta.mkdir()
    pasta.chmod(0o500)
    try:
        with pytest.raises(ErroDeArquivo) as info:
            baixar_arquivo(f"{base_url}/ok", pasta / "a.bin")
        assert isinstance(info.value, ErroDeDownload)
        assert isinstance(info.value.__cause__, PermissionError)
        assert _restos(pasta) == []
    finally:
        pasta.chmod(0o700)


def test_temporario_nasce_com_0600(base_url, tmp_path, monkeypatch):
    """A permissão restrita vale para o parcial também — o conteúdo
    baixado nunca fica legível para outros usuários, nem no meio."""
    from fotoorganizer.security import http_seguro

    modos: list[int] = []
    original = http_seguro._promover

    def espiao(temporario, alvo, sobrescrever):
        modos.append(os.stat(temporario).st_mode & 0o777)
        return original(temporario, alvo, sobrescrever)

    monkeypatch.setattr(http_seguro, "_promover", espiao)
    http_seguro.baixar_arquivo(f"{base_url}/ok", tmp_path / "a.bin")
    assert modos == [0o600]
