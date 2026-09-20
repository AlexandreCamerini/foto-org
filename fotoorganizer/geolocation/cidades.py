"""Cidade escrita no nome da pasta, confirmada no dataset offline — e a
coordenada dela.

Fatia 2 de localização estimada (D-083). Uma pasta "Amsterdam 2016" diz
onde a foto foi tirada, mas dizer "cidade = Amsterdam" só pelo texto seria
inventar lugar: "3 Picos" não é Picos (PI), "Guadalupe - RJ" não é a ilha,
"Lapa" e "Grajaú" são bairros do Rio e cidades de São Paulo, e "Sofia",
"Salvador" e "Victoria" são nomes de gente antes de serem capitais. Aqui o nome
só vale quando o dataset local de cidades (GeoNames, o mesmo do geocoding
reverso — nenhum dado sai da máquina) o confirma como cidade de tamanho
reconhecível, e então a foto ganha o centroide dela como lugar, com um
raio do tamanho de uma cidade, não de um bairro.

O centroide NÃO entra em `gps_*_estimado`: esses campos são a herança de
doadora real (centenas de metros) e alimentam o plano de escrita EXIF no
arquivo original — um ponto com 15 km de dúvida nunca pode ir parar lá. O
lugar da pasta vive só em `locations` (fonte `pasta:`), de onde o mapa e o
Inspector o leem.

Medido no acervo real (2026-09-20) contra pastas cujas fotos têm GPS
próprio: quando a pasta é a própria cidade, o centroide fica a 0-12 km da
foto (Rio 1 km, Paris 2 km, Amsterdam 2 km, Niterói 12 km). Quando a
cidade é só uma pasta-mãe e a subpasta nomeia outro lugar ("Paris 2016/
Aquitânia - Quai Salvette"), o erro passa de 450 km — por isso a
coordenada só vale quando a cidade é o segmento nomeador mais fundo.
"""

from __future__ import annotations

import gzip
import json
import logging
import re
import threading
from dataclasses import dataclass
from pathlib import Path

from fotoorganizer.geolocation.folder_names import identificar_pais
from fotoorganizer.geolocation.paises import (
    PAISES_PT,
    canonizar_pais,
    limpar_regiao,
    pais_por_codigo,
)
from fotoorganizer.grouping.datas import separar_data
from fotoorganizer.grouping.segmentos import (
    keyword_de_evento,
    normalizar,
    segmento_tecnico,
)

log = logging.getLogger(__name__)

# Versão da fonte gravada em `locations.fonte` para lugares vindos daqui.
# Bump a cada mudança de regra: é o que distingue, no mapa e no Inspector,
# "centroide da cidade da pasta" de "coordenada herdada de outra foto".
FONTE_PASTA = "pasta:cidades/1"

# O tamanho da dúvida quando só se sabe a cidade. Calibrado em
# `scripts/calibrar_raio_cidade.py` (D-083) com os pisos abaixo: 10 pastas
# / 58 fotos do acervo cujo nome é cidade confirmada e cujas fotos têm GPS
# — erro máximo 4,2 km (Paris), mediana 1,4 km. Niterói, que entra só com
# contexto, fica a 12 km do centro. 15 km cobre todos os casos medidos e
# ainda é "uma cidade", não "uma região".
RAIO_CIDADE_M = 15_000.0
NOTA_RAIO_CIDADE = (
    "Só o nome da pasta diz o lugar: a foto está em algum ponto da cidade. "
    "Nas cidades deste acervo com GPS próprio, o centro fica a poucos km "
    "das fotos (12 km no pior caso medido); o círculo de 15 km cobre todas."
)

# Pisos de população, do mais exigente ao mais brando. Um nome solto de
# pasta coincide com bairro do Rio, distrito de São Paulo e cidade pequena
# de qualquer país ("Lapa", "Grajaú", "Aurora", "Praia", "Santa Cruz"):
# sem nada em volta só vale cidade grande. Com o país escrito no caminho,
# ou com a grafia em português da tabela abaixo, o dono está falando de
# um lugar. Com sigla de estado brasileiro ele está sendo específico.
POPULACAO_MINIMA_SEM_CONTEXTO = 500_000
POPULACAO_MINIMA_COM_CONTEXTO = 50_000
POPULACAO_MINIMA_COM_UF = 10_000

_UF_PARA_ESTADO = {
    "AC": "acre", "AL": "alagoas", "AP": "amapa", "AM": "amazonas",
    "BA": "bahia", "CE": "ceara", "DF": "federal district",
    "ES": "espirito santo", "GO": "goias", "MA": "maranhao",
    "MT": "mato grosso", "MS": "mato grosso do sul", "MG": "minas gerais",
    "PA": "para", "PB": "paraiba", "PR": "parana", "PE": "pernambuco",
    "PI": "piaui", "RJ": "rio de janeiro", "RN": "rio grande do norte",
    "RS": "rio grande do sul", "RO": "rondonia", "RR": "roraima",
    "SC": "santa catarina", "SP": "sao paulo", "SE": "sergipe",
    "TO": "tocantins",
}

# Como o dono escreve a cidade em português → como o GeoNames a grava
# (exônimo inglês na maioria; endônimo em Köln, Genève, Antwerpen, Sevilla).
# Só o que não bate depois de tirar acento; nomes iguais (Paris, Madrid,
# Cusco, Lima, Santiago, Cairo) não precisam entrar.
CIDADES_PT: dict[str, str] = {
    "toquio": "tokyo", "quioto": "kyoto", "lisboa": "lisbon",
    "londres": "london", "sevilha": "sevilla", "florenca": "florence",
    "veneza": "venice", "milao": "milan", "napoles": "naples",
    "roma": "rome", "turim": "turin", "bolonha": "bologna",
    "munique": "munich", "colonia": "koln", "genebra": "geneve",
    "zurique": "zurich", "bruxelas": "brussels", "antuerpia": "antwerpen",
    "amsterda": "amsterdam", "roterda": "rotterdam", "haia": "the hague",
    "copenhague": "copenhagen", "estocolmo": "stockholm",
    "moscou": "moscow", "pequim": "beijing", "xangai": "shanghai",
    "nova york": "new york city", "nova iorque": "new york city",
    "cidade do mexico": "mexico city", "atenas": "athens",
    "praga": "prague", "viena": "vienna", "varsovia": "warsaw",
    "cracovia": "krakow", "edimburgo": "edinburgh", "marselha": "marseille",
    "bordeus": "bordeaux", "cidade do cabo": "cape town",
    "joanesburgo": "johannesburg", "assuncao": "asuncion",
    "montevideu": "montevideo", "cuzco": "cusco", "istambul": "istanbul",
    "bangcoc": "bangkok", "seul": "seoul", "singapura": "singapore",
    "nova deli": "new delhi", "madri": "madrid", "bilbau": "bilbao",
}

# Um segmento lista lugares como o dono escreve: "Teatro Municipal - Rio
# de Janeiro, RJ, 1 de outubro de 2015", "Nazaré da Mata - PE".
_RE_PARTES = re.compile(r"\s*(?:,|/|\s-\s|\se\s)\s*", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class CidadeDoDataset:
    nome: str          # como o GeoNames grava ("Tokyo")
    pais: str          # canônico em português
    codigo: str        # ISO 3166-1 alfa-2
    regiao: str | None
    lat: float
    lon: float
    populacao: int

    @property
    def chave_de_cache(self) -> str:
        """Chave de `locations.cache_key`. Leva o estado: "Trindade" em GO
        e em PE são cidades diferentes com o mesmo nome e o mesmo país."""
        return f"pasta:{self.codigo}:{normalizar(self.regiao or '')}:{normalizar(self.nome)}"


@dataclass(frozen=True, slots=True)
class LugarDaPasta:
    cidade: CidadeDoDataset
    segmento: str      # segmento original que nomeou a cidade
    texto: str         # o que o dono escreveu ("Nazare da Mata")


# nome normalizado → (cidade, país, estado normalizado, população, lat, lon, estado)
_Registro = tuple[str, str, str, int, float, float, str]
_indice: dict[str, list[_Registro]] | None = None
_lock = threading.Lock()


def _caminho_dataset() -> Path:
    import reverse_geocode

    return Path(reverse_geocode.__file__).with_name("geocode.gz")


def _carregar() -> dict[str, list[_Registro]]:
    """Índice nome normalizado → registros, uma vez por processo.

    Guarda só o que a consulta usa e só cidades acima do menor piso
    (10 mil): das 155 mil linhas do GeoNames sobram ~50 mil tuplas curtas,
    não 155 mil dicionários — o `reverse_geocode` já paga o arquivo inteiro
    em memória para a busca inversa, e não há por que pagar duas vezes.
    Com lock: dois jobs no mesmo instante não constroem o índice em dobro.
    """
    global _indice
    if _indice is not None:
        return _indice
    with _lock:
        if _indice is None:
            log.info("cidades: carregando dataset local…")
            with gzip.open(_caminho_dataset(), "rt", encoding="utf-8") as f:
                registros = json.load(f)
            indice: dict[str, list[_Registro]] = {}
            for r in registros:
                populacao = _populacao(r)
                if populacao < POPULACAO_MINIMA_COM_UF:
                    continue
                indice.setdefault(normalizar(r["city"]), []).append((
                    r["city"], r["country_code"], normalizar(r.get("state") or ""),
                    populacao, float(r["latitude"]), float(r["longitude"]),
                    r.get("state") or "",
                ))
            _indice = indice
    return _indice


def _populacao(registro: dict) -> int:
    try:
        return int(registro.get("population") or 0)
    except (TypeError, ValueError):
        return 0


def resolver_cidade(
    nome: str, *, pais: str | None = None, uf: str | None = None
) -> CidadeDoDataset | None:
    """"Amsterdam" → a cidade do dataset, ou None.

    Homônimos são desempatados pelo país (quando o caminho o diz), pela
    sigla de estado brasileiro (quando o segmento a traz) e, por último,
    pela população — "Paris" é a da França, não a do Texas. Abaixo do
    piso de população o nome não vale, e o piso depende do contexto: nome
    solto exige cidade grande (500 mil); país no caminho ou grafia em
    português da tabela baixa para 50 mil; sigla de UF, para 10 mil com o
    estado obrigatório.
    """
    chave = normalizar(nome)
    apelido = chave in CIDADES_PT
    chave = CIDADES_PT.get(chave, chave)
    if len(chave) < 3:
        return None
    candidatos = _carregar().get(chave, [])
    codigo = next((c for c, n in PAISES_PT.items() if n == pais), None) if pais else None
    if codigo:
        candidatos = [r for r in candidatos if r[1] == codigo]
    if uf and uf.upper() in _UF_PARA_ESTADO:
        estado = _UF_PARA_ESTADO[uf.upper()]
        candidatos = [r for r in candidatos if r[1] == "BR" and r[2] == estado]
        minimo = POPULACAO_MINIMA_COM_UF
    elif codigo or apelido:
        minimo = POPULACAO_MINIMA_COM_CONTEXTO
    else:
        minimo = POPULACAO_MINIMA_SEM_CONTEXTO
    candidatos = [r for r in candidatos if r[3] >= minimo]
    if not candidatos:
        return None
    cidade, cc, _, populacao, lat, lon, estado = max(candidatos, key=lambda r: r[3])
    return CidadeDoDataset(
        nome=cidade,
        pais=pais_por_codigo(cc) or cc,
        codigo=cc,
        regiao=limpar_regiao(estado) if estado else None,
        lat=lat,
        lon=lon,
        populacao=populacao,
    )


def _partes(segmento: str) -> list[str]:
    nome, _ = separar_data(segmento)
    return [p.strip() for p in _RE_PARTES.split(nome) if p.strip()]


def lugar_da_pasta(pasta: str) -> LugarDaPasta | None:
    """A cidade que o caminho nomeia, quando é o lugar mais específico
    que ele nomeia — senão None.

    Anda do segmento mais fundo para o mais raso, pulando pasta técnica e
    pasta que é só data. O primeiro segmento que NOMEIA algo decide: se
    nomeia uma cidade conhecida, é ela; se nomeia outra coisa ("Aquitânia
    - Quai Salvette"), nenhum ancestral vale — a foto está onde a subpasta
    diz, e o dataset não sabe onde é isso. País escrito em qualquer
    segmento ("França/Paris") desempata homônimos e baixa o piso.
    """
    segmentos = [s for s in Path(pasta).parts if s not in ("/", "\\")]
    pais_contexto = next(
        (p for p in (identificar_pais(s) for s in segmentos) if p), None
    )
    for segmento in reversed(segmentos):
        if segmento_tecnico(segmento):
            continue
        nome, _ = separar_data(segmento)
        if not nome:
            continue  # só data: não nomeia lugar, sobe um nível
        partes = _partes(segmento)
        uf = next((p.upper() for p in partes if p.upper() in _UF_PARA_ESTADO), None)
        for parte in partes:
            if parte.upper() in _UF_PARA_ESTADO or canonizar_pais(parte):
                continue
            if keyword_de_evento(parte):
                continue
            cidade = resolver_cidade(parte, pais=pais_contexto, uf=uf)
            if cidade is not None:
                return LugarDaPasta(cidade=cidade, segmento=segmento, texto=parte)
        return None  # nomeia algo que não é cidade conhecida
    return None
