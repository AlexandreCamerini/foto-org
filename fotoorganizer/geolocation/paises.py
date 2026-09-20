"""Nome canônico de país, em português, a partir de qualquer entrada.

Duas fontes dão país ao catálogo e cada uma falava uma língua: o dataset
offline devolve "Thailand"/"France" (GeoNames, em inglês) e o nome da
pasta devolvia o que estivesse escrito — "França" numa foto, "France" na
seguinte. Duas grafias do mesmo país viram duas pastas no destino.

Aqui existe um nome só por país, em português, e o código ISO 3166-1
alfa-2 é a chave. O dataset offline já entrega esse código; para nome de
pasta, os apelidos (inglês, siglas, variantes) resolvem para o mesmo.

Nenhuma rede: é tabela estática, como manda o invariante 4.
"""

from __future__ import annotations

import re
import unicodedata

# Vocabulário de evento vem do módulo folha `grouping/segmentos.py` — sentido
# único geolocation → grouping.segmentos; `grouping/__init__` não importa
# geolocation, então não há ciclo.
from fotoorganizer.grouping.segmentos import keyword_de_evento

# ISO 3166-1 alfa-2 → nome em português do Brasil.
PAISES_PT: dict[str, str] = {
    "AD": "Andorra", "AE": "Emirados Árabes Unidos", "AF": "Afeganistão",
    "AG": "Antígua e Barbuda", "AI": "Anguilla", "AL": "Albânia",
    "AM": "Armênia", "AO": "Angola", "AQ": "Antártida", "AR": "Argentina",
    "AS": "Samoa Americana", "AT": "Áustria", "AU": "Austrália",
    "AW": "Aruba", "AX": "Ilhas Åland", "AZ": "Azerbaijão",
    "BA": "Bósnia e Herzegovina", "BB": "Barbados", "BD": "Bangladesh",
    "BE": "Bélgica", "BF": "Burkina Faso", "BG": "Bulgária",
    "BH": "Bahrein", "BI": "Burundi", "BJ": "Benin",
    "BL": "São Bartolomeu", "BM": "Bermudas", "BN": "Brunei",
    "BO": "Bolívia", "BQ": "Países Baixos Caribenhos", "BR": "Brasil",
    "BS": "Bahamas", "BT": "Butão", "BV": "Ilha Bouvet", "BW": "Botsuana",
    "BY": "Belarus", "BZ": "Belize", "CA": "Canadá", "CC": "Ilhas Cocos",
    "CD": "República Democrática do Congo",
    "CF": "República Centro-Africana", "CG": "República do Congo",
    "CH": "Suíça", "CI": "Costa do Marfim", "CK": "Ilhas Cook",
    "CL": "Chile", "CM": "Camarões", "CN": "China", "CO": "Colômbia",
    "CR": "Costa Rica", "CU": "Cuba", "CV": "Cabo Verde", "CW": "Curaçao",
    "CX": "Ilha Christmas", "CY": "Chipre", "CZ": "Tchéquia",
    "DE": "Alemanha", "DJ": "Djibuti", "DK": "Dinamarca", "DM": "Dominica",
    "DO": "República Dominicana", "DZ": "Argélia", "EC": "Equador",
    "EE": "Estônia", "EG": "Egito", "EH": "Saara Ocidental",
    "ER": "Eritreia", "ES": "Espanha", "ET": "Etiópia", "FI": "Finlândia",
    "FJ": "Fiji", "FK": "Ilhas Malvinas", "FM": "Micronésia",
    "FO": "Ilhas Faroe", "FR": "França", "GA": "Gabão",
    "GB": "Reino Unido", "GD": "Granada", "GE": "Geórgia",
    "GF": "Guiana Francesa", "GG": "Guernsey", "GH": "Gana",
    "GI": "Gibraltar", "GL": "Groenlândia", "GM": "Gâmbia", "GN": "Guiné",
    "GP": "Guadalupe", "GQ": "Guiné Equatorial", "GR": "Grécia",
    "GS": "Geórgia do Sul e Sandwich do Sul", "GT": "Guatemala",
    "GU": "Guam", "GW": "Guiné-Bissau", "GY": "Guiana", "HK": "Hong Kong",
    "HM": "Ilha Heard e Ilhas McDonald", "HN": "Honduras", "HR": "Croácia",
    "HT": "Haiti", "HU": "Hungria", "ID": "Indonésia", "IE": "Irlanda",
    "IL": "Israel", "IM": "Ilha de Man", "IN": "Índia",
    "IO": "Território Britânico do Oceano Índico", "IQ": "Iraque",
    "IR": "Irã", "IS": "Islândia", "IT": "Itália", "JE": "Jersey",
    "JM": "Jamaica", "JO": "Jordânia", "JP": "Japão", "KE": "Quênia",
    "KG": "Quirguistão", "KH": "Camboja", "KI": "Kiribati",
    "KM": "Comores", "KN": "São Cristóvão e Névis", "KP": "Coreia do Norte",
    "KR": "Coreia do Sul", "KW": "Kuwait", "KY": "Ilhas Cayman",
    "KZ": "Cazaquistão", "LA": "Laos", "LB": "Líbano", "LC": "Santa Lúcia",
    "LI": "Liechtenstein", "LK": "Sri Lanka", "LR": "Libéria",
    "LS": "Lesoto", "LT": "Lituânia", "LU": "Luxemburgo", "LV": "Letônia",
    "LY": "Líbia", "MA": "Marrocos", "MC": "Mônaco", "MD": "Moldávia",
    "ME": "Montenegro", "MF": "São Martinho", "MG": "Madagascar",
    "MH": "Ilhas Marshall", "MK": "Macedônia do Norte", "ML": "Mali",
    "MM": "Mianmar", "MN": "Mongólia", "MO": "Macau",
    "MP": "Ilhas Marianas do Norte", "MQ": "Martinica",
    "MR": "Mauritânia", "MS": "Montserrat", "MT": "Malta",
    "MU": "Maurício", "MV": "Maldivas", "MW": "Malaui", "MX": "México",
    "MY": "Malásia", "MZ": "Moçambique", "NA": "Namíbia",
    "NC": "Nova Caledônia", "NE": "Níger", "NF": "Ilha Norfolk",
    "NG": "Nigéria", "NI": "Nicarágua", "NL": "Países Baixos",
    "NO": "Noruega", "NP": "Nepal", "NR": "Nauru", "NU": "Niue",
    "NZ": "Nova Zelândia", "OM": "Omã", "PA": "Panamá", "PE": "Peru",
    "PF": "Polinésia Francesa", "PG": "Papua-Nova Guiné", "PH": "Filipinas",
    "PK": "Paquistão", "PL": "Polônia", "PM": "São Pedro e Miquelão",
    "PN": "Ilhas Pitcairn", "PR": "Porto Rico", "PS": "Palestina",
    "PT": "Portugal", "PW": "Palau", "PY": "Paraguai", "QA": "Catar",
    "RE": "Reunião", "RO": "Romênia", "RS": "Sérvia", "RU": "Rússia",
    "RW": "Ruanda", "SA": "Arábia Saudita", "SB": "Ilhas Salomão",
    "SC": "Seicheles", "SD": "Sudão", "SE": "Suécia", "SG": "Singapura",
    "SH": "Santa Helena", "SI": "Eslovênia", "SJ": "Svalbard e Jan Mayen",
    "SK": "Eslováquia", "SL": "Serra Leoa", "SM": "San Marino",
    "SN": "Senegal", "SO": "Somália", "SR": "Suriname",
    "SS": "Sudão do Sul", "ST": "São Tomé e Príncipe", "SV": "El Salvador",
    "SX": "Sint Maarten", "SY": "Síria", "SZ": "Essuatíni",
    "TC": "Ilhas Turks e Caicos", "TD": "Chade",
    "TF": "Terras Austrais Francesas", "TG": "Togo", "TH": "Tailândia",
    "TJ": "Tajiquistão", "TK": "Toquelau", "TL": "Timor-Leste",
    "TM": "Turcomenistão", "TN": "Tunísia", "TO": "Tonga", "TR": "Turquia",
    "TT": "Trinidad e Tobago", "TV": "Tuvalu", "TW": "Taiwan",
    "TZ": "Tanzânia", "UA": "Ucrânia", "UG": "Uganda",
    "UM": "Ilhas Menores Distantes dos EUA", "US": "Estados Unidos",
    "UY": "Uruguai", "UZ": "Uzbequistão", "VA": "Vaticano",
    "VC": "São Vicente e Granadinas", "VE": "Venezuela",
    "VG": "Ilhas Virgens Britânicas", "VI": "Ilhas Virgens Americanas",
    "VN": "Vietnã", "VU": "Vanuatu", "WF": "Wallis e Futuna",
    "WS": "Samoa", "XK": "Kosovo", "YE": "Iêmen", "YT": "Mayotte",
    "ZA": "África do Sul", "ZM": "Zâmbia", "ZW": "Zimbábue",
}

# Como o país aparece escrito em nome de pasta ou no dataset em inglês.
# Só o que de fato ocorre: o nome em português já entra automaticamente.
_APELIDOS: dict[str, str] = {
    "AE": ["United Arab Emirates", "UAE", "Dubai", "Abu Dhabi"],
    "AR": ["Argentina"], "AT": ["Austria"], "AU": ["Australia"],
    "BE": ["Belgium"], "BO": ["Bolivia"], "BR": ["Brazil"],
    "CA": ["Canada"], "CH": ["Switzerland"], "CL": ["Chile"],
    "CN": ["China"], "CO": ["Colombia"], "CZ": ["Czech Republic",
                                                "Czechia",
                                                "República Tcheca"],
    "DE": ["Germany"], "DK": ["Denmark"], "EC": ["Ecuador"],
    "EG": ["Egypt"], "ES": ["Spain"], "FI": ["Finland"], "FR": ["France"],
    "GB": ["United Kingdom", "UK", "England", "Inglaterra", "Scotland",
           "Escócia", "Wales", "País de Gales"],
    "GR": ["Greece"], "HR": ["Croatia"], "HU": ["Hungary"],
    "ID": ["Indonesia"], "IE": ["Ireland"], "IN": ["India"],
    "IS": ["Iceland"], "IT": ["Italy"], "JP": ["Japan"],
    "KR": ["South Korea", "Korea"], "MA": ["Morocco"], "MX": ["Mexico"],
    "MY": ["Malaysia"], "NL": ["Netherlands", "Holanda", "Holland"],
    "NO": ["Norway"], "NZ": ["New Zealand"], "PE": ["Peru"],
    "PH": ["Philippines"], "PL": ["Poland"], "PT": ["Portugal"],
    "PY": ["Paraguay"], "SE": ["Sweden"], "SG": ["Singapore"],
    "TH": ["Thailand"], "TR": ["Turkey", "Türkiye"], "US": ["United States",
                                                            "USA", "EUA",
                                                            "U.S.A."],
    "UY": ["Uruguay"], "VN": ["Vietnam", "Viet Nam", "Vietname"],
    "ZA": ["South Africa"],
}


def _normalizar(texto: str) -> str:
    sem_acento = (
        unicodedata.normalize("NFKD", texto)
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    return re.sub(r"[^a-z0-9]+", " ", sem_acento.lower()).strip()


# alias normalizado → nome canônico em português.
_CANONICO: dict[str, str] = {}
for _codigo, _nome in PAISES_PT.items():
    _CANONICO[_normalizar(_nome)] = _nome
for _codigo, _lista in _APELIDOS.items():
    for _alias in _lista:
        _CANONICO[_normalizar(_alias)] = PAISES_PT[_codigo]


def pais_por_codigo(codigo: str | None) -> str | None:
    """"TH" → "Tailândia". Chave preferida: não depende de grafia."""
    if not codigo:
        return None
    return PAISES_PT.get(codigo.strip().upper())


def canonizar_pais(nome: str | None) -> str | None:
    """"France", "França", "FRANCE" → "França". None quando não é país."""
    if not nome:
        return None
    return _CANONICO.get(_normalizar(nome))


# Abreviação só vale a partir daqui: "Viet" identifica, "Ma" não.
_MIN_PREFIXO = 4


def _por_prefixo(chave: str) -> str | None:
    """"thai" → "Tailândia". Só quando UM país responde ao prefixo.

    Nome de pasta abrevia ("Thai", "Viet"); exigir a grafia inteira
    perderia a informação. A exigência de resposta única é o que impede
    o palpite: se duas nações começam igual, nenhuma é escolhida.
    """
    if len(chave) < _MIN_PREFIXO:
        return None
    achados = {
        pais for alias, pais in _CANONICO.items() if alias.startswith(chave)
    }
    return achados.pop() if len(achados) == 1 else None


# O que sobra numa parte depois de tirar data e conector: "Franca 2013" →
# "franca", "Do Peru" → "peru", "Atacama Abr.18" → "atacama". Só ano e
# mês abreviado/por extenso com número ao lado; "15 anos" não é data.
_RE_DATA_SOLTA = re.compile(
    r"\b(?:19|20)\d{2}\b"
    r"|\b(?:jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)[a-z]*\.?\s*\d{2,4}\b",
    re.IGNORECASE,
)
_RE_CONECTOR_INICIAL = re.compile(
    r"^(?:do|da|de|dos|das|ao|aos|a|para|pelo|pela)\s+", re.IGNORECASE
)
# Separadores de lista de destinos. " - " com espaços separa ("Carnaval
# 2016 - Portugal e Espanha"); o hífen colado é outra história, tratada
# em _paises_da_parte. Hífen colado fica de fora de propósito —
# "Guiné-Bissau" e "Timor-Leste" o usam dentro do próprio nome.
_RE_LISTA = re.compile(
    r"\s*(?:,|&|\+|/|\se\s|\sao\s|\s-\s)\s*", re.IGNORECASE
)
_RE_HIFEN = re.compile(r"\s*-\s*")
# Sigla de estado brasileiro numa das partes ("Guadalupe - RJ", "Franca -
# SP"): endereço no Brasil, e o homônimo de país que estiver ali é bairro
# ou cidade. Caso real do acervo: "Guadalupe, RJ" com GPS no Rio.
_RE_UF = re.compile(
    r"^(?:AC|AL|AP|AM|BA|CE|DF|ES|GO|MA|MT|MS|MG|PA|PB|PR|PE|PI|RJ|RN|RS"
    r"|RO|RR|SC|SP|SE|TO)$"
)


def _chave_da_parte(parte: str) -> str:
    return _normalizar(_RE_DATA_SOLTA.sub(" ", _RE_CONECTOR_INICIAL.sub("", parte)))


def _pais_exato(parte: str) -> str | None:
    """A parte, tirando data e conector, É um país: "Chile", "Franca 2013",
    "Do Peru", "Guiné-Bissau"."""
    chave = _chave_da_parte(parte)
    return _CANONICO.get(chave) if chave else None


def _pais_tolerante(parte: str) -> str | None:
    """Abreviação ("Thai") ou país seguido de palavra ("Espanha Carnaval").

    Só vale dentro de uma lista onde OUTRA parte já é país exato — solta,
    esta tolerância inventa país: "Serra - ES" viraria Serra Leoa, "Cabo"
    viraria Cabo Verde, "Georgia 15 Anos" viraria Geórgia.
    """
    chave = _chave_da_parte(parte)
    if not chave:
        return None
    pais = _por_prefixo(chave)
    if pais is not None:
        return pais
    palavras = chave.split()
    for n in range(len(palavras) - 1, 0, -1):
        pais = _CANONICO.get(" ".join(palavras[:n]))
        if pais is not None:
            return pais
    return None


def _paises_da_parte(parte: str, tolerante: bool) -> tuple[str, ...]:
    """Parte → países: um, ou vários quando o hífen colado separa destinos
    ("Peru-Bolivia-Chile"). Hífen só conta como separador se TODOS os
    pedaços forem país — "Provence-Alpes-Côte d'Azur" continua sendo um
    lugar só, e "Guiné-Bissau" resolve inteiro."""
    reconhecer = (lambda x: _pais_exato(x) or _pais_tolerante(x)) if tolerante \
        else _pais_exato
    pedacos = [x for x in _RE_HIFEN.split(parte) if x.strip()]
    if len(pedacos) >= 2:
        achados = [reconhecer(x) for x in pedacos]
        if all(a is not None for a in achados):
            return tuple(dict.fromkeys(achados))
    pais = reconhecer(parte)
    return (pais,) if pais is not None else ()


def paises_no_segmento(segmento: str | None) -> tuple[str, ...]:
    """Países que um segmento de pasta nomeia, na ordem — ou () quando o
    segmento não é sobre países.

    Medido no acervo real (2026-09-20, D-082): 8.690 fotos em cinco pastas
    como "Peru-Bolivia-Chile", "Italia e Franca 2013" e "Do Peru ao Chile",
    mais 880 em "Chile e Atacama Abr.18", não ganhavam lugar nenhum porque
    o reconhecedor exigia o segmento inteiro igual ao nome do país.

    As regras, todas contra o palpite:
    - Uma parte só conta como país se for país EXATO (tirando data e
      conector). Abreviação e "país + palavra" só valem quando outra parte
      do mesmo segmento já é país exato ("Dubai, Thai & Viet";
      "Portugal e Espanha Carnaval").
    - Dois ou mais países no segmento é sinal forte — valem onde
      estiverem ("Carnaval 2016 - Portugal e Espanha").
    - Um país só vale se for a PRIMEIRA parte ("Chile e Atacama" sim;
      "Estádio Nilton Santos - Guadalupe, RJ" não), sem sigla de estado
      brasileiro em nenhuma parte ("Guadalupe - RJ" — a sigla barra até
      a lista) e sem palavra de evento no segmento ("Israel e Maria
      Casamento", "Georgia 15 Anos").
    Fica de fora, por enquanto: cidade homônima de país na primeira parte
    ("Granada e Sevilha") e país + nome de pessoa sem palavra de festa
    ("Israel e Maria 2019") — precisam do dataset de cidades para
    desempatar (fatia 2 de D-082).
    """
    if not segmento:
        return ()
    partes = [x for x in _RE_LISTA.split(segmento) if x.strip()]
    if not partes:
        return ()
    exatos = [_paises_da_parte(x, tolerante=False) for x in partes]
    if not any(exatos):
        return ()
    if len(partes) >= 2:
        por_parte = [
            grupo or _paises_da_parte(parte, tolerante=True)
            for parte, grupo in zip(partes, exatos)
        ]
    else:
        por_parte = exatos
    paises = tuple(dict.fromkeys(p for grupo in por_parte for p in grupo))
    # Sigla de UF desqualifica o segmento inteiro, lista ou não: "Brasil e
    # Portugal - RJ" é endereço, não roteiro.
    if any(_RE_UF.match(x.strip().upper()) for x in partes):
        return ()
    if len(paises) >= 2:
        return paises
    if not exatos[0]:
        return ()
    # Palavra de evento só barra o país ÚNICO: "Portugal e Espanha - Natal
    # 2015" continua sendo dois países.
    if keyword_de_evento(segmento):
        return ()
    return paises


def identificar_paises(texto: str | None) -> tuple[str, ...]:
    """Países listados num único segmento, na ordem em que aparecem.

    "Dubai, Thai & Viet" → ("Emirados Árabes Unidos", "Tailândia",
    "Vietnã"). Devolve () quando o segmento nomeia menos de dois países:
    "França" sozinha não é lista, e "Serena 15 Anos" não é destino.
    """
    paises = paises_no_segmento(texto)
    return paises if len(paises) >= 2 else ()


# Sufixos e prefixos administrativos em inglês que o GeoNames anexa à
# região ("Quảng Nam Province"). O nome próprio é o que interessa; o
# rótulo administrativo em inglês só polui o destino. Não traduzimos o
# nome em si — endônimo é o nome certo do lugar.
_RE_ADMIN_SUFIXO = re.compile(
    r"\s+(province|state|region|prefecture|county|district|governorate"
    r"|municipality|oblast|territory|department|canton|emirate"
    r"|autonomous region|metropolitan city|federal district)$",
    re.IGNORECASE,
)
_RE_ADMIN_PREFIXO = re.compile(
    r"^(province|state|region|prefecture|governorate|department)\s+of\s+",
    re.IGNORECASE,
)


def limpar_regiao(nome: str | None) -> str | None:
    """"Quảng Nam Province" → "Quảng Nam"; "Province of X" → "X"."""
    if not nome:
        return None
    limpo = _RE_ADMIN_PREFIXO.sub("", nome).strip()
    limpo = _RE_ADMIN_SUFIXO.sub("", limpo).strip()
    return limpo or None
