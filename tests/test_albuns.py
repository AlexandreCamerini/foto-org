"""Que álbum nomeia um acontecimento e qual é nome de aparelho ou de app."""

import pytest

from fotoorganizer.grouping.albuns import album_nomeia, cameras_do_catalogo


@pytest.mark.parametrize("nome", [
    "Portugal e Italia com as Meninas",
    "Peru - Julho de 2026",
    "Jalapão",
    "Nosso Casamento",
    "Joanna 4 Anos",
    "Chapada dos Veadeiros Dez/22",
    "Férias",
    "Family",
    "Família",          # o filtro de PASTA rejeitava; álbum não é prateleira
    "Aiuruoca e Tiradentes",
])
def test_nomes_que_o_dono_escreveu_nomeiam(nome):
    assert album_nomeia(nome) is True


@pytest.mark.parametrize("nome", [
    "WhatsApp", "Instagram", "Twitter", "𝕏", "Salvo do Flickr",
    "GoPro Album", "Drone", "Recentes", "Favoritos", "Sem título",
    "Screenshots", "Downloads",
])
def test_app_e_servico_nao_nomeiam(nome):
    assert album_nomeia(nome) is False


@pytest.mark.parametrize("nome", [
    "Canon EOS R6m2", "Canon EOS 5D Mark IV", "iPhone 15 Pro",
    "Fotos da Nikon D850", "Lumix GH5", "DJI Mavic 3",
])
def test_nome_de_aparelho_nao_nomeia(nome):
    """O maior álbum de um acervo real era "Canon EOS 5D Mark IV", com 4.887
    fotos. Sem este corte, o evento do dono se chamaria assim."""
    assert album_nomeia(nome) is False


def test_camera_do_proprio_acervo_e_reconhecida_sem_estar_na_lista():
    """Marca desconhecida hoje sai pelo catálogo — é o que impede o filtro
    de envelhecer quando o dono compra outra câmera."""
    cameras = cameras_do_catalogo([("Blackmagic", "Pocket 6K"), (None, None)])
    assert album_nomeia("Pocket 6K", cameras) is False
    assert album_nomeia("Blackmagic Pocket 6K", cameras) is False
    # E o acervo não fica refém: nome de viagem continua passando.
    assert album_nomeia("Patagônia 2020", cameras) is True


def test_camera_fora_do_alcance_ainda_e_barrada_pela_marca():
    """A câmera antiga está no HD na gaveta, então não aparece no catálogo
    alcançável — foi exatamente o caso que passou na primeira versão."""
    assert album_nomeia("Canon EOS 5D Mark IV", frozenset()) is False


@pytest.mark.parametrize("nome", ["", "  ", "20", "2019", "01", "-", None])
def test_nome_vazio_ou_so_numero_nao_nomeia(nome):
    """Data já é tratada noutro passo da cascata; "2019" descreve quando,
    não o quê."""
    assert album_nomeia(nome) is False


def test_cameras_do_catalogo_ignora_o_que_nao_identifica():
    """Linha sem modelo não descreve câmera nenhuma; modelo curto demais
    casaria com qualquer palavra."""
    achadas = cameras_do_catalogo([
        (None, None), ("Canon", None), ("x", "a"), ("Canon", "EOS R6m2"),
    ])
    assert "a" not in achadas                 # curto demais para comparar
    assert "eos r6m2" in achadas
    assert "canon eos r6m2" in achadas
