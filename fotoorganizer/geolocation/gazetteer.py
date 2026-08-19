"""Gazetteer local estático de marcos conhecidos (D-082/Gazetteer).

Reconhece o NOME de um marco no caminho da pasta — não a coordenada.
Extensão do mesmo princípio de `folder_names.py`: ".../Cristo Redentor"
já diz onde a foto foi tirada, sem precisar de GPS nem de geocodificação
nenhuma. É o equivalente offline e determinístico do que
`classification/location_advisor.py` (GenAI, opt-in) faz por inferência —
aqui não há inferência, só um dicionário; o que não está na lista não
bate, ponto.

Por que não é coordenada: o geocoder offline (`geolocation/offline.py`)
já resolve QUALQUER coordenada pela cidade mais próxima — nunca devolve
None por "não conhecer" o lugar, só por exceção. Um gazetteer de pontos
geográficos entraria morto: o passo de GPS já teria retornado antes dele
ser alcançado. O ganho real está no nome, não na coordenada.

Por que não por substring: reconhecer "Cristo Redentor" dentro de "Rio -
Cristo Redentor 2019" pegaria também falsos positivos incidentais (um
marco cujo nome aparece dentro de uma palavra maior, sem ser o assunto da
pasta). Bate o SEGMENTO INTEIRO do caminho, normalizado — mesmo critério
de `identificar_pais`.

Lista PEQUENA e curada de propósito: cada marco aqui é uma decisão
editorial do dono, não uma tentativa de cobrir o globo. Adicionar uma
entrada errada é pior que não ter nenhuma — vira sugestão de alta
confiança em cima de uma coincidência de nome. Os marcos abaixo são só um
conjunto inicial de exemplo (lugares inequívocos, fáceis de conferir num
mapa); estender a lista com os marcos que realmente aparecem no acervo é
trabalho do dono, não algo que dá para inventar por fora do catálogo real.
"""

from __future__ import annotations

from dataclasses import dataclass

from fotoorganizer.geolocation.folder_names import _normalizar


@dataclass(frozen=True, slots=True)
class Marco:
    nome: str  # grafia canônica, para a justificativa
    cidade: str
    regiao: str | None
    pais: str


# Conjunto inicial de exemplo — ver docstring do módulo.
_MARCOS_RAW: tuple[Marco, ...] = (
    Marco("Cristo Redentor", "Rio de Janeiro", "Rio de Janeiro", "Brasil"),
    Marco("Corcovado", "Rio de Janeiro", "Rio de Janeiro", "Brasil"),
    Marco("Pão de Açúcar", "Rio de Janeiro", "Rio de Janeiro", "Brasil"),
    Marco("Torre Eiffel", "Paris", "Île-de-France", "França"),
    Marco("Eiffel Tower", "Paris", "Île-de-France", "França"),
    Marco("Coliseu", "Roma", "Lácio", "Itália"),
    Marco("Colosseum", "Roma", "Lácio", "Itália"),
    Marco("Sagrada Família", "Barcelona", "Catalunha", "Espanha"),
    Marco("Machu Picchu", "Cusco", "Cusco", "Peru"),
    Marco("Estátua da Liberdade", "Nova York", "Nova York", "Estados Unidos"),
    Marco("Statue of Liberty", "Nova York", "Nova York", "Estados Unidos"),
)

MARCOS_NORMALIZADOS: dict[str, Marco] = {
    _normalizar(m.nome): m for m in _MARCOS_RAW
}


def identificar_marco(segmento: str) -> Marco | None:
    """O marco cujo nome bate EXATAMENTE (normalizado) com `segmento`,
    ou None. Nunca por substring — ver docstring do módulo."""
    return MARCOS_NORMALIZADOS.get(_normalizar(segmento))
