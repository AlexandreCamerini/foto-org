"""Timezone estimado a partir do país herdado — item 5 do backlog
(`docs/ROADMAP.md`), 100% foto-organizer, sem restrição de licença.
Especificado em `docs/prompts/fase-11-timezone-estimado.md`; a nota de
2026-08-09 no topo daquele arquivo (o modelo de dois instantes de D-038)
já está incorporada abaixo.

Staging fora de `fotoorganizer/**` (protocolo em `docs/prompts/00-protocolo.md`).

Reaproveita o DADO que a herança de país já produz (não a lógica de
escrita, que continua em `classification/engine.py`): quando
`Evidence(campo="pais", ...)` existe para uma mídia — vinda de GPS próprio,
de herança temporal (D-025) ou de nome de pasta — este módulo resolve um
fuso plausível para aquele país, via `zoneinfo`/IANA tzdata (biblioteca
padrão, sem rede, coerente com o invariante 4 do `CLAUDE.md`).
"""

from __future__ import annotations

import zoneinfo
from dataclasses import dataclass

# Chave = MESMO nome em português que `geolocation/paises.py::PAISES_PT`
# produz (não o código ISO): `Evidence.valor` já chega como nome de país em
# PT-BR, e recodificar de volta para ISO só para procurar aqui seria
# trabalho e uma fonte de bug a mais (fase-11, §1). Gerado a partir da
# leitura de `fotoorganizer/geolocation/paises.py::PAISES_PT` nesta sessão
# (250 países — a tabela real do projeto, não os "98" citados na estimativa
# original do prompt de fase, que estava desatualizada).
#
# Países com mais de um fuso (Brasil, EUA, Rússia, Canadá, Austrália,
# México, Indonésia, ...): fuso da CAPITAL ou do local de maior população,
# como aproximação deliberada — coerente com o resto do campo ser
# "estimado", não um substituto de `timezonefinder` (fora de escopo,
# fase-11 "Fora de escopo"). Territórios não habitados sem entrada IANA
# própria (Ilha Bouvet, Ilha Heard) usam o offset fixo `Etc/GMT[+-]N`
# correspondente à longitude aproximada — também documentado caso a caso
# abaixo onde a escolha não é óbvia.
TZ_POR_PAIS: dict[str, str] = {
    "Afeganistão": "Asia/Kabul",
    "Albânia": "Europe/Tirane",
    "Alemanha": "Europe/Berlin",
    "Andorra": "Europe/Andorra",
    "Angola": "Africa/Luanda",
    "Anguilla": "America/Anguilla",
    "Antártida": "Antarctica/McMurdo",  # estação McMurdo, a mais populosa
    "Antígua e Barbuda": "America/Antigua",
    "Argentina": "America/Argentina/Buenos_Aires",
    "Argélia": "Africa/Algiers",
    "Armênia": "Asia/Yerevan",
    "Aruba": "America/Aruba",
    "Arábia Saudita": "Asia/Riyadh",
    "Austrália": "Australia/Sydney",  # maior população, não a capital
    "Azerbaijão": "Asia/Baku",
    "Bahamas": "America/Nassau",
    "Bahrein": "Asia/Bahrain",
    "Bangladesh": "Asia/Dhaka",
    "Barbados": "America/Barbados",
    "Belarus": "Europe/Minsk",
    "Belize": "America/Belize",
    "Benin": "Africa/Porto-Novo",
    "Bermudas": "Atlantic/Bermuda",
    "Bolívia": "America/La_Paz",
    "Botsuana": "Africa/Gaborone",
    "Brasil": "America/Sao_Paulo",  # maior população, não a capital
    "Brunei": "Asia/Brunei",
    "Bulgária": "Europe/Sofia",
    "Burkina Faso": "Africa/Ouagadougou",
    "Burundi": "Africa/Bujumbura",
    "Butão": "Asia/Thimphu",
    "Bélgica": "Europe/Brussels",
    "Bósnia e Herzegovina": "Europe/Sarajevo",
    "Cabo Verde": "Atlantic/Cape_Verde",
    "Camarões": "Africa/Douala",
    "Camboja": "Asia/Phnom_Penh",
    "Canadá": "America/Toronto",  # maior população, não a capital (Ottawa)
    "Catar": "Asia/Qatar",
    "Cazaquistão": "Asia/Almaty",
    "Chade": "Africa/Ndjamena",
    "Chile": "America/Santiago",
    "China": "Asia/Shanghai",  # fuso único oficial do país inteiro
    "Chipre": "Asia/Nicosia",
    "Colômbia": "America/Bogota",
    "Comores": "Indian/Comoro",
    "Coreia do Norte": "Asia/Pyongyang",
    "Coreia do Sul": "Asia/Seoul",
    "Costa Rica": "America/Costa_Rica",
    "Costa do Marfim": "Africa/Abidjan",
    "Croácia": "Europe/Zagreb",
    "Cuba": "America/Havana",
    "Curaçao": "America/Curacao",
    "Dinamarca": "Europe/Copenhagen",
    "Djibuti": "Africa/Djibouti",
    "Dominica": "America/Dominica",
    "Egito": "Africa/Cairo",
    "El Salvador": "America/El_Salvador",
    "Emirados Árabes Unidos": "Asia/Dubai",
    "Equador": "America/Guayaquil",  # inclui o continental (Quito no mesmo fuso)
    "Eritreia": "Africa/Asmara",
    "Eslováquia": "Europe/Bratislava",
    "Eslovênia": "Europe/Ljubljana",
    "Espanha": "Europe/Madrid",
    "Essuatíni": "Africa/Mbabane",
    "Estados Unidos": "America/New_York",  # maior população, não a capital
    "Estônia": "Europe/Tallinn",
    "Etiópia": "Africa/Addis_Ababa",
    "Fiji": "Pacific/Fiji",
    "Filipinas": "Asia/Manila",
    "Finlândia": "Europe/Helsinki",
    "França": "Europe/Paris",
    "Gabão": "Africa/Libreville",
    "Gana": "Africa/Accra",
    "Geórgia": "Asia/Tbilisi",
    "Geórgia do Sul e Sandwich do Sul": "Atlantic/South_Georgia",
    "Gibraltar": "Europe/Gibraltar",
    "Granada": "America/Grenada",
    "Groenlândia": "America/Nuuk",
    "Grécia": "Europe/Athens",
    "Guadalupe": "America/Guadeloupe",
    "Guam": "Pacific/Guam",
    "Guatemala": "America/Guatemala",
    "Guernsey": "Europe/Guernsey",
    "Guiana": "America/Guyana",
    "Guiana Francesa": "America/Cayenne",
    "Guiné": "Africa/Conakry",
    "Guiné Equatorial": "Africa/Malabo",
    "Guiné-Bissau": "Africa/Bissau",
    "Gâmbia": "Africa/Banjul",
    "Haiti": "America/Port-au-Prince",
    "Honduras": "America/Tegucigalpa",
    "Hong Kong": "Asia/Hong_Kong",
    "Hungria": "Europe/Budapest",
    "Ilha Bouvet": "Etc/GMT",  # não habitada, sem zona IANA própria; ~UTC+0 pela longitude
    "Ilha Christmas": "Indian/Christmas",
    "Ilha Heard e Ilhas McDonald": "Etc/GMT-5",  # não habitada, sem zona IANA própria; ~UTC+5
    "Ilha Norfolk": "Pacific/Norfolk",
    "Ilha de Man": "Europe/Isle_of_Man",
    "Ilhas Cayman": "America/Cayman",
    "Ilhas Cocos": "Indian/Cocos",
    "Ilhas Cook": "Pacific/Rarotonga",
    "Ilhas Faroe": "Atlantic/Faroe",
    "Ilhas Malvinas": "Atlantic/Stanley",
    "Ilhas Marianas do Norte": "Pacific/Saipan",
    "Ilhas Marshall": "Pacific/Majuro",
    "Ilhas Menores Distantes dos EUA": "Pacific/Wake",  # território disperso; Wake como representante
    "Ilhas Pitcairn": "Pacific/Pitcairn",
    "Ilhas Salomão": "Pacific/Guadalcanal",
    "Ilhas Turks e Caicos": "America/Grand_Turk",
    "Ilhas Virgens Americanas": "America/St_Thomas",
    "Ilhas Virgens Britânicas": "America/Tortola",
    "Ilhas Åland": "Europe/Mariehamn",
    "Indonésia": "Asia/Jakarta",  # maior população, não geográfico central
    "Iraque": "Asia/Baghdad",
    "Irlanda": "Europe/Dublin",
    "Irã": "Asia/Tehran",
    "Islândia": "Atlantic/Reykjavik",
    "Israel": "Asia/Jerusalem",
    "Itália": "Europe/Rome",
    "Iêmen": "Asia/Aden",
    "Jamaica": "America/Jamaica",
    "Japão": "Asia/Tokyo",
    "Jersey": "Europe/Jersey",
    "Jordânia": "Asia/Amman",
    "Kiribati": "Pacific/Tarawa",
    "Kosovo": "Europe/Belgrade",  # sem zona IANA própria; mesmas regras de Belgrado
    "Kuwait": "Asia/Kuwait",
    "Laos": "Asia/Vientiane",
    "Lesoto": "Africa/Maseru",
    "Letônia": "Europe/Riga",
    "Libéria": "Africa/Monrovia",
    "Liechtenstein": "Europe/Vaduz",
    "Lituânia": "Europe/Vilnius",
    "Luxemburgo": "Europe/Luxembourg",
    "Líbano": "Asia/Beirut",
    "Líbia": "Africa/Tripoli",
    "Macau": "Asia/Macau",
    "Macedônia do Norte": "Europe/Skopje",
    "Madagascar": "Indian/Antananarivo",
    "Malaui": "Africa/Blantyre",
    "Maldivas": "Indian/Maldives",
    "Mali": "Africa/Bamako",
    "Malta": "Europe/Malta",
    "Malásia": "Asia/Kuala_Lumpur",
    "Marrocos": "Africa/Casablanca",
    "Martinica": "America/Martinique",
    "Mauritânia": "Africa/Nouakchott",
    "Maurício": "Indian/Mauritius",
    "Mayotte": "Indian/Mayotte",
    "Mianmar": "Asia/Yangon",
    "Micronésia": "Pacific/Pohnpei",  # capital Palikir fica em Pohnpei
    "Moldávia": "Europe/Chisinau",
    "Mongólia": "Asia/Ulaanbaatar",
    "Montenegro": "Europe/Podgorica",
    "Montserrat": "America/Montserrat",
    "Moçambique": "Africa/Maputo",
    "México": "America/Mexico_City",
    "Mônaco": "Europe/Monaco",
    "Namíbia": "Africa/Windhoek",
    "Nauru": "Pacific/Nauru",
    "Nepal": "Asia/Kathmandu",
    "Nicarágua": "America/Managua",
    "Nigéria": "Africa/Lagos",
    "Niue": "Pacific/Niue",
    "Noruega": "Europe/Oslo",
    "Nova Caledônia": "Pacific/Noumea",
    "Nova Zelândia": "Pacific/Auckland",  # maior população, não a capital (Wellington)
    "Níger": "Africa/Niamey",
    "Omã": "Asia/Muscat",
    "Palau": "Pacific/Palau",
    "Palestina": "Asia/Gaza",
    "Panamá": "America/Panama",
    "Papua-Nova Guiné": "Pacific/Port_Moresby",
    "Paquistão": "Asia/Karachi",
    "Paraguai": "America/Asuncion",
    "Países Baixos": "Europe/Amsterdam",
    "Países Baixos Caribenhos": "America/Kralendijk",
    "Peru": "America/Lima",
    "Polinésia Francesa": "Pacific/Tahiti",  # maior população (Taiti), não a capital administrativa
    "Polônia": "Europe/Warsaw",
    "Porto Rico": "America/Puerto_Rico",
    "Portugal": "Europe/Lisbon",  # continente; Açores e Madeira têm fuso próprio, ignorado por aproximação
    "Quirguistão": "Asia/Bishkek",
    "Quênia": "Africa/Nairobi",
    "Reino Unido": "Europe/London",
    "República Centro-Africana": "Africa/Bangui",
    "República Democrática do Congo": "Africa/Kinshasa",
    "República Dominicana": "America/Santo_Domingo",
    "República do Congo": "Africa/Brazzaville",
    "Reunião": "Indian/Reunion",
    "Romênia": "Europe/Bucharest",
    "Ruanda": "Africa/Kigali",
    "Rússia": "Europe/Moscow",  # maior população, não geográfico central
    "Saara Ocidental": "Africa/El_Aaiun",
    "Samoa": "Pacific/Apia",
    "Samoa Americana": "Pacific/Pago_Pago",
    "San Marino": "Europe/San_Marino",
    "Santa Helena": "Atlantic/St_Helena",
    "Santa Lúcia": "America/St_Lucia",
    "Seicheles": "Indian/Mahe",
    "Senegal": "Africa/Dakar",
    "Serra Leoa": "Africa/Freetown",
    "Singapura": "Asia/Singapore",
    "Sint Maarten": "America/Lower_Princes",
    "Somália": "Africa/Mogadishu",
    "Sri Lanka": "Asia/Colombo",
    "Sudão": "Africa/Khartoum",
    "Sudão do Sul": "Africa/Juba",
    "Suriname": "America/Paramaribo",
    "Suécia": "Europe/Stockholm",
    "Suíça": "Europe/Zurich",
    "Svalbard e Jan Mayen": "Arctic/Longyearbyen",
    "São Bartolomeu": "America/St_Barthelemy",
    "São Cristóvão e Névis": "America/St_Kitts",
    "São Martinho": "America/Marigot",
    "São Pedro e Miquelão": "America/Miquelon",
    "São Tomé e Príncipe": "Africa/Sao_Tome",
    "São Vicente e Granadinas": "America/St_Vincent",
    "Sérvia": "Europe/Belgrade",
    "Síria": "Asia/Damascus",
    "Tailândia": "Asia/Bangkok",
    "Taiwan": "Asia/Taipei",
    "Tajiquistão": "Asia/Dushanbe",
    "Tanzânia": "Africa/Dar_es_Salaam",
    "Tchéquia": "Europe/Prague",
    "Terras Austrais Francesas": "Indian/Kerguelen",
    "Território Britânico do Oceano Índico": "Indian/Chagos",
    "Timor-Leste": "Asia/Dili",
    "Togo": "Africa/Lome",
    "Tonga": "Pacific/Tongatapu",
    "Toquelau": "Pacific/Fakaofo",
    "Trinidad e Tobago": "America/Port_of_Spain",
    "Tunísia": "Africa/Tunis",
    "Turcomenistão": "Asia/Ashgabat",
    "Turquia": "Europe/Istanbul",
    "Tuvalu": "Pacific/Funafuti",
    "Ucrânia": "Europe/Kyiv",
    "Uganda": "Africa/Kampala",
    "Uruguai": "America/Montevideo",
    "Uzbequistão": "Asia/Tashkent",
    "Vanuatu": "Pacific/Efate",
    "Vaticano": "Europe/Vatican",
    "Venezuela": "America/Caracas",
    "Vietnã": "Asia/Ho_Chi_Minh",
    "Wallis e Futuna": "Pacific/Wallis",
    "Zimbábue": "Africa/Harare",
    "Zâmbia": "Africa/Lusaka",
    "África do Sul": "Africa/Johannesburg",
    "Áustria": "Europe/Vienna",
    "Índia": "Asia/Kolkata",
}


def tz_estimado_para_pais(pais: str | None) -> str | None:
    """`pais` já resolvido (de `Evidence(campo="pais").valor`, vindo de GPS
    próprio, herança D-025 ou nome de pasta — não importa a origem, é o
    mesmo nível de granularidade grosseira que o resto do app assume para
    país estimado). Sem país conhecido ou país fora da tabela (não deveria
    acontecer, dado que a tabela cobre os 250 valores de `PAISES_PT`, mas a
    tabela pode ficar desatualizada se `paises.py` ganhar um país novo):
    `None`, nunca inventa — mesma filosofia de "erro de leitura não derruba
    o resto" do resto do projeto.
    """
    if not pais:
        return None
    return TZ_POR_PAIS.get(pais)


@dataclass(frozen=True)
class ResultadoTzEstimado:
    """Para os testes/medição pedirem "quantas vieram por herança" sem
    reimplementar a leitura de `Evidence.origem` — só descreve o resultado
    de uma decisão já tomada por quem chama."""

    tz_estimado: str | None
    veio_de_heranca: bool


# Origens de país que fase-11 §"O que já existe" documenta como HERANÇA —
# não GPS próprio da mídia. Espelha os três valores que
# `classification/engine.py:736-781` (`_evidencias_geo`) já produz para
# `Evidence(campo="pais").origem`: `geocoding_offline` é GPS da própria
# foto (não é herança); `vizinhanca_temporal` é herança temporal (D-025);
# `pasta` é nome de diretório (também não é GPS próprio, mas o prompt de
# origem só cita "vizinhança" como herança propriamente dita — pasta é uma
# terceira fonte, nem medida nem própria; ver README para a leitura exata
# usada nesta contagem).
_ORIGEM_HERANCA = "vizinhanca_temporal"


def calcular_tz_estimado(pais: str | None, origem_pais: str | None) -> ResultadoTzEstimado:
    """Junta a resolução de fuso com a informação de proveniência, para
    quem for medir no catálogo real (aceite da fase-11: "quantas fotos
    ganhariam tz_estimado hoje, e quantas só por herança") ter os dois
    números de uma função só, sem duplicar a lista de origens em dois
    lugares do código de medição.
    """
    tz = tz_estimado_para_pais(pais)
    return ResultadoTzEstimado(
        tz_estimado=tz,
        veio_de_heranca=(tz is not None and origem_pais == _ORIGEM_HERANCA),
    )
