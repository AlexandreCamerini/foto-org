"""Nome canônico de país: uma grafia só, venha de onde vier.

Duas fontes davam país ao catálogo em línguas diferentes — o dataset
offline em inglês ("Thailand") e o nome da pasta como estivesse escrito
("França" numa foto, "France" na seguinte). Cada grafia virava uma pasta
no destino.
"""

import pytest

from fotoorganizer.geolocation.folder_names import identificar_pais
from fotoorganizer.geolocation.paises import (
    PAISES_PT,
    canonizar_pais,
    limpar_regiao,
    pais_por_codigo,
)


@pytest.mark.parametrize(
    "codigo,nome",
    [("TH", "Tailândia"), ("VN", "Vietnã"), ("AE", "Emirados Árabes Unidos"),
     ("FR", "França"), ("JP", "Japão"), ("BR", "Brasil"),
     ("US", "Estados Unidos"), ("GB", "Reino Unido")],
)
def test_codigo_iso_da_nome_em_portugues(codigo, nome):
    assert pais_por_codigo(codigo) == nome


def test_codigo_desconhecido_ou_vazio_nao_explode():
    assert pais_por_codigo(None) is None
    assert pais_por_codigo("") is None
    assert pais_por_codigo("ZZ") is None


@pytest.mark.parametrize(
    "entrada,canonico",
    [
        ("France", "França"), ("França", "França"), ("FRANCE", "França"),
        ("Thailand", "Tailândia"), ("Vietnam", "Vietnã"),
        ("United Arab Emirates", "Emirados Árabes Unidos"),
        ("Dubai", "Emirados Árabes Unidos"),
        ("USA", "Estados Unidos"), ("EUA", "Estados Unidos"),
        ("Inglaterra", "Reino Unido"), ("Scotland", "Reino Unido"),
        ("Holanda", "Países Baixos"),
    ],
)
def test_apelidos_convergem_para_uma_grafia(entrada, canonico):
    assert canonizar_pais(entrada) == canonico


def test_o_que_nao_e_pais_continua_nao_sendo():
    for nome in ["Quizomba", "Teatro", "Visconde de Maua", "Provence", ""]:
        assert canonizar_pais(nome) is None


def test_nome_de_pasta_usa_a_mesma_grafia_do_geocoder():
    """O bug que motivou o módulo: duas pastas para o mesmo país."""
    assert identificar_pais("France") == identificar_pais("França") == "França"
    assert identificar_pais("Thailand") == pais_por_codigo("TH")


@pytest.mark.parametrize(
    "bruto,limpo",
    [
        ("Quảng Nam Province", "Quảng Nam"),
        ("Chiang Mai", "Chiang Mai"),
        ("Province of Ontario", "Ontario"),
        ("Tokyo Prefecture", "Tokyo"),
        ("Île-de-France", "Île-de-France"),
        (None, None),
    ],
)
def test_rotulo_administrativo_ingles_sai_da_regiao(bruto, limpo):
    assert limpar_regiao(bruto) == limpo


def test_tabela_iso_sem_nomes_repetidos():
    """Dois códigos com o mesmo nome fundiriam países distintos."""
    nomes = list(PAISES_PT.values())
    assert len(nomes) == len(set(nomes))
