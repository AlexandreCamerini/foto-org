"""Cidade no nome da pasta só vale confirmada no dataset offline (D-083).

Casos reais do acervo: "Amsterdam 2016", "Paris 2016/Aquitânia…",
"Teatro Municipal - Rio de Janeiro, RJ, …", "Nazare da Mata - PE",
"Guadalupe - RJ", "3 Picos".
"""

import pytest

from fotoorganizer.geolocation import cidades
from fotoorganizer.geolocation.cidades import lugar_da_pasta, resolver_cidade


@pytest.fixture(autouse=True)
def dataset_pequeno(monkeypatch):
    """Índice sintético no formato interno (tuplas do GeoNames já filtradas)
    — o teste não depende do arquivo de 155 mil cidades nem de rede."""
    def reg(city, cc, state, pop, lat, lon):
        return (city, cc, cidades.normalizar(state), pop, lat, lon, state)
    indice = {}
    for r in [
        reg("Paris", "FR", "Île-de-France", 2_138_551, 48.85, 2.35),
        reg("Paris", "US", "Texas", 24_782, 33.66, -95.55),
        reg("Amsterdam", "NL", "North Holland", 741_636, 52.37, 4.89),
        reg("Rio de Janeiro", "BR", "Rio de Janeiro", 6_747_815, -22.90, -43.20),
        reg("Niterói", "BR", "Rio de Janeiro", 456_456, -22.88, -43.10),
        reg("Nazaré da Mata", "BR", "Pernambuco", 26_485, -7.74, -35.23),
        reg("Guadalupe", "BR", "Piauí", 10_500, -6.79, -43.56),
        reg("Guadalupe", "MX", "Nuevo León", 673_616, 25.68, -100.26),
        reg("Picos", "BR", "Piauí", 78_431, -7.08, -41.47),
        reg("Lapa", "BR", "São Paulo", 75_533, -23.52, -46.70),
        reg("Centro", "IT", "Lazio", 43_456, 41.9, 12.5),
        reg("Tokyo", "JP", "Tokyo", 9_733_276, 35.69, 139.69),
        reg("Genève", "CH", "Geneva", 183_981, 46.20, 6.14),
        reg("Serra", "BR", "Espírito Santo", 394_153, -20.13, -40.31),
        reg("Trindade", "BR", "Goiás", 97_521, -16.65, -49.49),
        reg("Trindade", "BR", "Pernambuco", 19_000, -7.76, -40.27),
    ]:
        indice.setdefault(r[0] and cidades.normalizar(r[0]), []).append(r)
    monkeypatch.setattr(cidades, "_indice", indice)


def test_homonimo_e_desempatado_pela_populacao():
    assert resolver_cidade("Paris").codigo == "FR"


def test_pais_do_caminho_desempata_o_homonimo():
    assert resolver_cidade("Paris", pais="Estados Unidos") is None  # 24k < piso
    assert resolver_cidade("Guadalupe", pais="México").codigo == "MX"


def test_abaixo_do_piso_nao_e_cidade():
    """"Centro" existe como cidade na Itália; como nome de pasta é bairro."""
    assert resolver_cidade("Centro") is None


def test_sigla_de_estado_baixa_o_piso_e_exige_o_estado():
    assert resolver_cidade("Nazare da Mata", uf="PE").populacao == 26_485
    assert resolver_cidade("Nazare da Mata") is None          # sem UF, < piso
    assert resolver_cidade("Guadalupe", uf="RJ") is None      # a do PI não é do RJ
    assert resolver_cidade("Guadalupe", uf="PI").codigo == "BR"
    # Homônimas no mesmo país: a UF escolhe e a chave de cache separa.
    go, pe = resolver_cidade("Trindade", uf="GO"), resolver_cidade("Trindade", uf="PE")
    assert (go.regiao, pe.regiao) == ("Goiás", "Pernambuco")
    assert go.chave_de_cache != pe.chave_de_cache


def test_nome_solto_exige_cidade_grande():
    """"Lapa" e "Niterói" são bairro do Rio e cidade vizinha; soltos num
    nome de pasta, não valem. Com o país no caminho, Niterói vale."""
    assert resolver_cidade("Lapa") is None
    assert resolver_cidade("Niterói") is None
    assert resolver_cidade("Niterói", pais="Brasil").nome == "Niterói"
    assert resolver_cidade("Serra") is None
    assert resolver_cidade("Serra", uf="ES").nome == "Serra"


def test_nome_em_portugues_encontra_a_grafia_do_dataset():
    assert resolver_cidade("Tóquio").nome == "Tokyo"
    # O apelido em português é contexto: o dono está falando de um lugar.
    assert resolver_cidade("Genebra").nome == "Genève"


@pytest.mark.parametrize(
    "pasta,cidade,texto",
    [
        ("/fotos/Amsterdam 2016/15 de outubro de 2016", "Amsterdam", "Amsterdam"),
        ("/fotos/Paris 2016", "Paris", "Paris"),
        ("/fotos/Disney 2015/Rio de Janeiro", "Rio de Janeiro", "Rio de Janeiro"),
        ("/fotos/Teatro Municipal - Rio de Janeiro, RJ, 1 de outubro de 2015",
         "Rio de Janeiro", "Rio de Janeiro"),
        ("/fotos/Maracatu Rural - Nazare da Mata - PE", "Nazaré da Mata", "Nazare da Mata"),
        ("/fotos/Serra - ES", "Serra", "Serra"),
        ("/fotos/Japão/Tóquio/[Developed]", "Tokyo", "Tóquio"),
        ("/fotos/Brasil/Niterói", "Niterói", "Niterói"),
    ],
)
def test_cidade_e_o_segmento_nomeador_mais_fundo(pasta, cidade, texto):
    lugar = lugar_da_pasta(pasta)
    assert lugar is not None
    assert (lugar.cidade.nome, lugar.texto) == (cidade, texto)


@pytest.mark.parametrize(
    "pasta",
    [
        # A subpasta nomeia outro lugar: a cidade da pasta-mãe não vale
        # (medido: 450-600 km de erro em "Paris 2016/Aquitânia…").
        "/fotos/Paris 2016/Aquitânia - Quai Salvette, 7 de outubro de 2016",
        "/fotos/3 Picos",              # "3 Picos" não é Picos (PI)
        "/fotos/Guadalupe - RJ",       # não há Guadalupe no RJ
        "/fotos/Centro - Praça Cardeal Câmara, 3 de julho de 2015",
        "/fotos/Serena 15 Anos",
        "/fotos/2009/junho 29",        # só datas
        "/fotos/Chile e Atacama Abr.18",  # país + lugar que o dataset não tem
        "/fotos/Lapa",                 # bairro do Rio, cidade de SP (75k): solto não vale
        "/fotos/Niterói 2016",         # cidade vizinha, 456k: solta não vale
    ],
)
def test_sem_cidade_confirmada_nao_inventa(pasta):
    assert lugar_da_pasta(pasta) is None
