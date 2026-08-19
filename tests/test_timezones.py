"""TZ_POR_PAIS cobre todo país de PAISES_PT, todo valor é IANA válido.

Rede de segurança contra dois jeitos de errar: um país esquecido por
acidente (cobertura parcial) e um identificador digitado errado (não
existe no fuso horário real).
"""

import zoneinfo

from fotoorganizer.geolocation.paises import PAISES_PT
from fotoorganizer.geolocation.timezones import TZ_POR_PAIS


def test_cobre_todos_os_paises_de_paises_pt():
    assert set(TZ_POR_PAIS) == set(PAISES_PT.values())


def test_todo_valor_e_identificador_iana_valido():
    disponiveis = zoneinfo.available_timezones()
    for pais, fuso in TZ_POR_PAIS.items():
        assert fuso in disponiveis, f"{pais}: {fuso!r} não é IANA válido"
