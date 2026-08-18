"""Dump cru de tags, allowlist estrutural e diff — o único sinal confiável.

Verificado empiricamente nesta fase (RESEARCH.md Pitfall 2, exiftool 13.55):
o exit code do exiftool e a linha "N image files updated" **não** são sinal
de sucesso. `exiftool -GPSLatitude=notanumber -City="X" -Country="Y" <file>`
imprime um warning, **pula só a tag malformada**, escreve City e Country do
mesmo jeito, ainda reporta "1 image files updated" e ainda sai 0. Um design
que rume o exit code ou a mensagem-resumo como critério de EXIF-03 perde
exatamente o caso que EXIF-03 existe para pegar. O único sinal confiável é
o diff completo de tags antes/depois — é o que este módulo produz.
"""

from __future__ import annotations

import json
import logging
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)

_TIMEOUT_S = 30.0

# -- tags por campo, escrita direta -----------------------------------------
# Grupo explícito em toda tag (invariante desta fase, RESEARCH.md Pitfall 3):
# `-City`/`-Country` sem prefixo resolvem para grupos DIFERENTES e
# assimétricos (City cai em IPTC, Country cai em XMP-photoshop) — por isso
# o writer sempre grava os dois grupos, e a verificação sempre confere os
# dois grupos.
TAGS_POR_CAMPO: dict[str, tuple[str, ...]] = {
    "gps": (
        "GPS:GPSLatitude",
        "GPS:GPSLatitudeRef",
        "GPS:GPSLongitude",
        "GPS:GPSLongitudeRef",
    ),
    "cidade": ("IPTC:City", "XMP-photoshop:City"),
    "pais": ("IPTC:Country-PrimaryLocationName", "XMP-photoshop:Country"),
}

# -- tags por campo, sidecar .xmp autônomo -----------------------------------
# IPTC é formato de segmento binário de container de imagem — não existe
# num .xmp autônomo (verificado na pesquisa). Sidecar só grava o grupo XMP.
TAGS_POR_CAMPO_SIDECAR: dict[str, tuple[str, ...]] = {
    "gps": ("XMP-exif:GPSLatitude", "XMP-exif:GPSLongitude"),
    "cidade": ("XMP-photoshop:City",),
    "pais": ("XMP-photoshop:Country",),
}

TAGS_DE_LOCALIZACAO: frozenset[str] = frozenset(
    tag
    for mapa in (TAGS_POR_CAMPO, TAGS_POR_CAMPO_SIDECAR)
    for tags in mapa.values()
    for tag in tags
)

# Andaime inevitável: escrever um bloco GPS/IPTC/XMP pela primeira vez num
# arquivo que nunca teve nenhum dos três produz estas tags como efeito
# colateral obrigatório, não como localização em si (RESEARCH.md Pitfall 4,
# verificado duas vezes com fixtures diferentes). Isto é o caso NORMAL desta
# fase — todo arquivo que este módulo escreve começa sem GPS/IPTC/XMP, por
# construção (EXIF-02 só escreve em campo vazio).
#
# Proibido isentar o prefixo inteiro "IPTC:"/"XMP:" para "resolver" isto de
# uma vez: mascararia escrita real fora de escopo (EXIF-04). Cada entrada
# abaixo é justificada individualmente.
TAGS_ESTRUTURAIS_ESPERADAS: frozenset[str] = frozenset({
    # Tag de versão obrigatória do IFD GPS, sempre escrita ao criar um
    # bloco GPS novo — não é coordenada, é versão de formato do bloco.
    "GPS:GPSVersionID",
    # Versão obrigatória do registro IPTC, sempre escrita ao criar um
    # bloco IPTC novo — não é dado de localização.
    "IPTC:ApplicationRecordVersion",
    # Checksum do bloco IPTC inteiro, gerido pelo próprio exiftool a cada
    # escrita — muda porque o bloco mudou, não é em si um dado gravado.
    "File:CurrentIPTCDigest",
    # Identifica a ferramenta que escreveu o pacote XMP, sempre presente
    # num pacote XMP novo — metadado do pacote, não da foto.
    "XMP-x:XMPToolkit",
})

# O que muda incondicionalmente sem significar nada, presente ou ausente de
# qualquer escrita de localização. "File:" não entra como prefixo inteiro
# porque File:ImageWidth/File:ImageHeight mudando É sinal real de corrupção
# — cada entrada de File: aqui é individual e justificada.
TAGS_VOLATEIS: frozenset[str] = frozenset({
    "SourceFile",
    "File:FileSize",
    "File:FileModifyDate",
    "File:FileAccessDate",
    "File:FileInodeChangeDate",
    "File:FilePermissions",
    "File:Directory",
    "File:FileName",
    "ExifTool:ExifToolVersion",
    "ExifTool:Warning",
})

# Composite:* é derivado das tags GPS reais (re-renderização de leitura),
# não escrito de forma independente pelo exiftool.
PREFIXOS_VOLATEIS: tuple[str, ...] = ("System:", "Composite:")


def dump(caminho: Path, binario: str = "exiftool") -> dict[str, str]:
    """Dump cru de todas as tags de `caminho`, chave `Grupo:Tag` -> valor str.

    `-n`: sem isto o GPS volta formatado ("23 deg 33' 1.87\" S") e o diff
    vira comparação de string formatada; com `-n` volta decimal,
    determinístico. `-G1`: grupo de família 1, distingue `XMP-photoshop:City`
    de `IPTC:City` — exatamente a assimetria da Pitfall 3. `-a`: mostra tags
    duplicadas em grupos diferentes, o caso normal de cidade/país aqui.

    Nunca levanta: devolve `{}` se o processo falhar ou o JSON não parsear.
    """
    try:
        resultado = subprocess.run(
            [binario, "-j", "-G1", "-a", "-n", "-charset", "filename=utf8", str(caminho)],
            capture_output=True, text=True, check=False, timeout=_TIMEOUT_S,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        log.warning("exiftool -j falhou em %s (%s)", caminho, exc)
        return {}
    try:
        dados = json.loads(resultado.stdout)
    except json.JSONDecodeError:
        return {}
    if not dados:
        return {}
    return {chave: str(valor) for chave, valor in dados[0].items()}


def dump_lote(
    caminhos: Sequence[Path], binario: str = "exiftool", tamanho_lote: int = 200,
) -> dict[str, dict[str, str]]:
    """Mesma invocação de `dump`, N caminhos por chamada.

    1.400 invocações a ~200 ms cada seriam ~5 min de dry-run; em lote são
    segundos. Fatiar em `tamanho_lote` evita estourar `ARG_MAX` do shell.
    Caminho sem resposta entra com `{}`.
    """
    resultado: dict[str, dict[str, str]] = {}
    lista = list(caminhos)
    for inicio in range(0, len(lista), tamanho_lote):
        fatia = lista[inicio : inicio + tamanho_lote]
        try:
            processo = subprocess.run(
                [binario, "-j", "-G1", "-a", "-n", "-charset", "filename=utf8",
                 *[str(c) for c in fatia]],
                capture_output=True, text=True, check=False, timeout=_TIMEOUT_S,
            )
            dados = json.loads(processo.stdout)
        except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
            log.warning("exiftool -j em lote falhou (%s)", exc)
            dados = []
        vistos: set[str] = set()
        for item in dados:
            origem = item.get("SourceFile")
            if not origem:
                continue
            vistos.add(origem)
            resultado[origem] = {chave: str(valor) for chave, valor in item.items()}
        for caminho in fatia:
            chave = str(caminho)
            if chave not in vistos and chave not in resultado:
                resultado[chave] = {}
    return resultado


def avisos(caminho: Path, binario: str = "exiftool") -> set[str]:
    """Conjunto de strings de warning/error de `caminho`. Nunca levanta.

    O critério de D-04 é **delta** de avisos (nenhum aviso NOVO), não "zero
    avisos depois" — uma fixture sintética pode já carregar aviso
    pré-existente. Esta função só coleta o estado bruto; o delta é
    responsabilidade de quem chama, comparando duas chamadas.

    Texto plano, não `-j`: verificado empiricamente (plano 06-04, medição
    contra o acervo real) que a saída `-j` do exiftool **colapsa** tags
    `Warning`/`Error` repetidas em uma só — um TIFF com 6 warnings reais
    devolve só 1 no JSON, silenciando 5. Em texto plano cada ocorrência é
    uma linha própria. `Validate` (o resumo agregado, ex. "6 Warnings (3
    minor)") é descartado deste conjunto: não é warning nem error — é uma
    contagem derivada que muda de valor sempre que a contagem muda, inclusive
    quando ela MELHORA (uma reescrita que renormaliza o IFD e resolve um
    warning pré-existente também muda o texto de `Validate`, o que um diff
    ingênuo contaria como aviso "novo" — verificado num JPEG real: 3
    Warnings -> "OK" depois de uma escrita limpa). O conteúdo que interessa
    já está inteiro nas linhas `Warning:`/`Error:` individuais.
    """
    try:
        resultado = subprocess.run(
            [binario, "-validate", "-warning", "-error", "-a",
             "-charset", "filename=utf8", str(caminho)],
            capture_output=True, text=True, check=False, timeout=_TIMEOUT_S,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        log.warning("exiftool -validate falhou em %s (%s)", caminho, exc)
        return set()
    coletados: set[str] = set()
    for linha in resultado.stdout.splitlines():
        chave, separador, valor = linha.partition(":")
        if not separador:
            continue
        chave = chave.strip()
        if chave in ("Warning", "Error"):
            coletados.add(f"{chave}: {valor.strip()}")
    return coletados


@dataclass(frozen=True, slots=True)
class DiffTags:
    """Resultado de `diferenca()`: três dicionários, sem sobreposição."""

    esperadas: dict[str, str]
    estruturais: dict[str, str]
    inesperadas: dict[str, tuple[str | None, str | None]]


def diferenca(antes: dict[str, str], depois: dict[str, str]) -> DiffTags:
    """Classifica toda tag que mudou entre `antes` e `depois`.

    Ordem de classificação (importa): andaime estrutural primeiro, depois
    volátil, depois localização, e por fim o resto. Isto garante que uma
    tag de andaime (ex. `File:CurrentIPTCDigest`) seja sempre contabilizada
    em `estruturais`, mesmo describendo-se coloquialmente como "algo que
    muda sem significar nada" — ela tem endereço fixo em
    `TAGS_ESTRUTURAIS_ESPERADAS`, não é varrida pelo filtro de voláteis.

    Tag de localização que **sumiu** (estava em `antes`, ausente em
    `depois`) vai para `inesperadas` com `(valor, None)` — não para
    `esperadas`, porque "esperadas" significa "entrou", e sumir é o oposto.
    """
    esperadas: dict[str, str] = {}
    estruturais: dict[str, str] = {}
    inesperadas: dict[str, tuple[str | None, str | None]] = {}

    for chave in set(antes) | set(depois):
        valor_antes = antes.get(chave)
        valor_depois = depois.get(chave)
        if valor_antes == valor_depois:
            continue

        if chave in TAGS_ESTRUTURAIS_ESPERADAS:
            if valor_depois is not None:
                estruturais[chave] = valor_depois
            continue

        if chave in TAGS_VOLATEIS or chave.startswith(PREFIXOS_VOLATEIS):
            continue

        if chave in TAGS_DE_LOCALIZACAO and valor_depois is not None:
            esperadas[chave] = valor_depois
            continue

        inesperadas[chave] = (valor_antes, valor_depois)

    return DiffTags(esperadas=esperadas, estruturais=estruturais, inesperadas=inesperadas)


def campo_gravado(campo: str, diff: DiffTags, sidecar: bool = False) -> bool:
    """`True` só quando TODAS as tags do campo estão em `diff.esperadas`.

    O "todas" é o detector de falha parcial de EXIF-03: cidade que entrou
    no IPTC mas não no XMP é falha, não sucesso — metade dos consumidores
    de metadado continuaria sem enxergar o dado.
    """
    mapa = TAGS_POR_CAMPO_SIDECAR if sidecar else TAGS_POR_CAMPO
    tags = mapa.get(campo, ())
    if not tags:
        return False
    return all(tag in diff.esperadas for tag in tags)
