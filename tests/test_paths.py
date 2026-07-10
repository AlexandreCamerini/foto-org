import pytest

from fotoorganizer.security.paths import (
    CaminhoInvalido,
    caminho_relativo_seguro,
    destino_recursivo,
    resolver_destino,
)


def test_caminho_relativo_normal():
    assert str(caminho_relativo_seguro("Viagens/2024 - França/Avignon")) == \
        "Viagens/2024 - França/Avignon"


def test_path_traversal_bloqueado():
    with pytest.raises(CaminhoInvalido):
        caminho_relativo_seguro("../../../etc")
    with pytest.raises(CaminhoInvalido):
        caminho_relativo_seguro("Viagens/../../fora")
    with pytest.raises(CaminhoInvalido):
        caminho_relativo_seguro("~/casa")
    with pytest.raises(CaminhoInvalido):
        caminho_relativo_seguro("///")


def test_resolver_destino_fica_na_raiz(tmp_path):
    destino = resolver_destino(tmp_path, "a/b")
    assert destino == tmp_path.resolve() / "a" / "b"
    assert destino.is_relative_to(tmp_path.resolve())


def test_barras_invertidas_e_segmentos_sujos(tmp_path):
    destino = resolver_destino(tmp_path, "a\\b: c?/  d  ")
    assert destino.is_relative_to(tmp_path.resolve())
    assert ":" not in destino.name and "?" not in str(destino)


def test_destino_recursivo(tmp_path):
    arvore = tmp_path / "fotos"
    arvore.mkdir()
    assert destino_recursivo(arvore, arvore / "organizadas") is True
    assert destino_recursivo(arvore, arvore) is True
    assert destino_recursivo(arvore, tmp_path / "destino") is False
