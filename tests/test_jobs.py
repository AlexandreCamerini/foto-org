"""Curadoria da mensagem de erro de importação (fotoorganizer/server/jobs.py).

A biblioteca do Apple Fotos falhando por falta de permissão precisa dizer
o que fazer no macOS (Ajustes -> Privacidade e Segurança -> Acesso Total
ao Disco), como o PySide6 antecipa — sem depender de casar substring
frágil na mensagem de uma exceção de terceiros.
"""

from pathlib import Path

from fotoorganizer.server.jobs import _erro_de_permissao, _mensagem_falha_import
from fotoorganizer.sources import (
    ApplePhotosError,
    ApplePhotosProvider,
    GoogleTakeoutProvider,
)


def test_permissao_detectada_na_causa_direta():
    assert _erro_de_permissao(PermissionError(1, "Operation not permitted"))


def test_permissao_detectada_na_cadeia_de_causas():
    """`raise ... from origem` preserva `__cause__` — o sinal precisa
    atravessar o encadeamento, não só olhar a exceção mais externa."""
    try:
        try:
            raise PermissionError(13, "Permission denied")
        except PermissionError as origem:
            raise RuntimeError("falhou ao iterar a biblioteca") from origem
    except RuntimeError as encadeada:
        assert _erro_de_permissao(encadeada)


def test_erro_sem_permissao_nao_e_detectado():
    assert not _erro_de_permissao(RuntimeError("qualquer coisa"))
    assert not _erro_de_permissao(FileNotFoundError("sumiu"))
    assert not _erro_de_permissao(None)


def test_apple_photos_error_mantem_a_propria_mensagem():
    """ApplePhotosError já inclui o app responsável pelo TCC e o caminho
    dos Ajustes — reescrevê-la aqui jogaria fora esse detalhe mais
    específico que a curadoria genérica não tem como reconstruir."""
    provider = ApplePhotosProvider()
    exc = ApplePhotosError(
        "não consegui ler a biblioteca. Acesso Total ao Disco: o app "
        "«Fotos de Teste» precisa estar marcado."
    )
    assert _mensagem_falha_import(provider, exc) == str(exc)


def test_permissao_crua_do_apple_photos_ganha_orientacao():
    """O buraco real: uma PermissionError levantada durante a iteração da
    biblioteca (não na abertura), que hoje chega crua ao usuário."""
    provider = ApplePhotosProvider()
    exc = PermissionError(1, "Operation not permitted")
    mensagem = _mensagem_falha_import(provider, exc)
    assert "Acesso Total ao Disco" in mensagem
    assert "Ajustes" in mensagem


def test_permissao_do_takeout_nao_ganha_orientacao_do_apple():
    """A curadoria é específica do Apple Fotos — erro de permissão numa
    pasta de Takeout é outro problema (permissão do arquivo local), não
    o TCC do macOS para o Fotos."""
    provider = GoogleTakeoutProvider(Path("/tmp/nao-importa"))
    exc = PermissionError(13, "Permission denied")
    assert _mensagem_falha_import(provider, exc) == str(exc)


def test_erro_generico_do_apple_photos_nao_ganha_orientacao():
    provider = ApplePhotosProvider()
    exc = RuntimeError("algo inesperado, sem relação com permissão")
    assert _mensagem_falha_import(provider, exc) == str(exc)
