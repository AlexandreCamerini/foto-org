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


# -- pasta que lista a viagem inteira -----------------------------------
@pytest.mark.parametrize(
    "segmento,paises",
    [
        ("Dubai, Thai & Viet",
         ("Emirados Árabes Unidos", "Tailândia", "Vietnã")),
        ("França e Itália", ("França", "Itália")),
        ("Peru + Bolivia", ("Peru", "Bolívia")),
        ("Argentina/Chile", ("Argentina", "Chile")),
        ("Portugal, Espanha", ("Portugal", "Espanha")),
        # Casos reais do acervo (D-082): 8.690 fotos sem lugar porque o
        # reconhecedor exigia o segmento inteiro igual ao nome do país.
        ("Peru-Bolivia-Chile", ("Peru", "Bolívia", "Chile")),
        ("Italia e Franca 2013", ("Itália", "França")),
        ("Do Peru ao Chile", ("Peru", "Chile")),
        ("Portugal e Espanha Carnaval Fev.16", ("Portugal", "Espanha")),
        ("Carnaval 2016 - Portugal e Espanha", ("Portugal", "Espanha")),
        ("Guiné-Bissau, Senegal", ("Guiné-Bissau", "Senegal")),  # hífen no nome
        # Palavra de festa não desfaz uma lista de dois países.
        ("Portugal e Espanha - Natal 2015", ("Portugal", "Espanha")),
    ],
)
def test_pasta_lista_os_destinos_da_viagem(segmento, paises):
    from fotoorganizer.geolocation.paises import identificar_paises

    assert identificar_paises(segmento) == paises


@pytest.mark.parametrize(
    "segmento",
    [
        "Serena 15 Anos",      # evento, não lista de destinos
        "Quizomba, Teatro",    # lista, mas de coisas que não são países
        "Estrada Real",
        "Guiné-Bissau",        # hífen faz parte do nome, não separa
        "França",              # um país só não é lista
        "Chile e Atacama Abr.18",  # um país + um lugar: não é lista
        "Provence-Alpes-Côte d'Azur",  # hífen entre pedaços que não são país
        "Festa do Papangu - Bezerros - PE",
        # Bairro homônimo de país, e não na primeira parte: caso real com
        # GPS no Rio — um país só nunca vale fora da primeira parte.
        "Estádio Nilton Santos - Guadalupe, RJ, 18 de agosto de 2016",
        # Abreviação/prefixo só vale ao lado de um país exato: sozinhos,
        # "Serra" (cidade do ES) viraria Serra Leoa e "Fran" viraria França.
        "Serra - ES",
        "Fran e Ze",
        # Sigla de UF barra até a lista: é endereço, não roteiro.
        "Brasil e Portugal - RJ",
        "",
    ],
)
def test_meia_lista_ou_nenhuma_nao_vira_viagem(segmento):
    from fotoorganizer.geolocation.paises import identificar_paises

    assert identificar_paises(segmento) == ()


def test_abreviacao_curta_demais_nao_chuta():
    """"Ma" poderia ser Marrocos, Malta, Mali… — nenhuma é escolhida."""
    from fotoorganizer.geolocation.paises import identificar_paises

    assert identificar_paises("Ma, Ind") == ()


# -- um país só, tolerando o que o dono escreve junto -----------------
@pytest.mark.parametrize(
    "segmento,pais",
    [
        ("Chile e Atacama Abr.18", "Chile"),   # 880 fotos reais sem lugar
        ("França 2016", "França"),
        ("Do Chile", "Chile"),
        ("Timor-Leste", "Timor-Leste"),
        # Lista de dois não tem UM país: é assunto de identificar_paises.
        ("Italia e Franca 2013", None),
        ("Peru-Bolivia-Chile", None),
        # Palavra que vem ANTES do país desqualifica: "Guadalupe" aqui é
        # bairro do Rio, e "Atacama" nunca foi país.
        ("Estádio Nilton Santos - Guadalupe, RJ, 18 de agosto de 2016", None),
        ("Atacama Abr.18", None),
        ("3 Picos", None),
        ("Mar del Plata", None),
        # Sigla de estado em qualquer parte: endereço no Brasil, o homônimo
        # é bairro ou cidade.
        ("Guadalupe - RJ", None),
        ("Franca - SP", None),
        # Palavra de evento no segmento: aniversário e casamento não são
        # viagem, por mais que o nome coincida com país.
        ("Georgia 15 Anos", None),
        ("Israel 50 anos", None),
        ("Israel e Maria Casamento", None),
        ("Cuba 60 anos", None),
        # País seguido de palavra só vale ao lado de outro país exato.
        ("Espanha Carnaval", None),
        ("China Town", None),
        ("Peru Beach", None),
        # Abreviação sozinha nunca vira país.
        ("Cabo", None),
        ("Serra - ES", None),
    ],
)
def test_um_pais_so_vale_na_primeira_parte(segmento, pais):
    assert identificar_pais(segmento) == pais


def test_aniversario_homonimo_de_pais_continua_evento():
    """"Georgia 15 Anos" tem de chegar à regra de keyword como nome de
    álbum — se o país tolerante o rejeitasse, viraria viagem 'Geórgia'."""
    from fotoorganizer.grouping.eventos import extrair_evento, nome_de_album

    assert nome_de_album("Georgia 15 Anos")
    assert extrair_evento(["/fotos/Georgia 15 Anos"]) == ("Georgia 15 Anos", True)
    # Um país só, exato, continua fora dos nomes de álbum.
    assert not nome_de_album("Chile e Atacama Abr.18")
