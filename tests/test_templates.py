from fotoorganizer.classification import (
    normalizar_segmento,
    render_destino,
    resolver_colisao,
)
from fotoorganizer.classification.templates import DESTINO_NAO_CLASSIFICADO


def test_render_completo():
    campos = {"categoria": "Viagens", "ano": "2024", "viagem": "2024 - França",
              "pais": "França", "regiao": "Provence", "cidade": "Avignon"}
    destino = render_destino(
        "{categoria}/{ano} - {viagem}/{regiao}/{cidade}", campos
    )
    assert destino == "Viagens/2024 - 2024 - França/Provence/Avignon"


def test_segmento_vazio_cai_fora():
    campos = {"categoria": "Viagens", "ano": "2024", "pais": "Japão",
              "viagem": None, "regiao": None, "cidade": None}
    destino = render_destino(
        "{categoria}/{ano} - {viagem}/{pais}/{regiao}/{cidade}", campos
    )
    # {viagem} vazio some do segmento misto; {regiao}/{cidade} caem inteiros.
    assert destino == "Viagens/2024/Japão"


def test_tudo_vazio_nao_inventa():
    assert render_destino("{pais}/{cidade}", {}) == DESTINO_NAO_CLASSIFICADO


def test_normalizacao_remove_invalidos():
    assert normalizar_segmento('Fotos: "melhores" <2024>?') == "Fotos_ _melhores_ _2024__"
    assert "/" not in normalizar_segmento("a/b\\c")
    assert normalizar_segmento("  espaços   demais  ") == "espaços demais"
    assert normalizar_segmento("nome final com pontos...") == "nome final com pontos"


def test_normalizacao_limita_comprimento():
    longo = "x" * 300
    assert len(normalizar_segmento(longo)) <= 80


def test_unicode_preservado():
    assert normalizar_segmento("日本 – Tóquio") == "日本 – Tóquio"


def test_colisao_recebe_sufixo():
    existentes = {"IMG_001.jpg", "IMG_001.jpg (2)"}
    assert resolver_colisao("IMG_001.jpg", existentes) == "IMG_001.jpg (3)"
    assert resolver_colisao("nova.jpg", existentes) == "nova.jpg"
