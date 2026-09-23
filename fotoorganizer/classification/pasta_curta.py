"""Nome curto de pasta para envio externo — o mesmo recorte que a tela mostra.

Só o que o dono vê na lista de candidatas (`pastaCurta` em
`ClassificacaoPasta.tsx`: as duas últimas pastas do caminho) sai da máquina.
Nunca o caminho absoluto — ele carrega nome de usuário (`/Users/fulano`),
nome de volume/NAS (`/Volumes/photo`) e a árvore inteira do acervo, e nada
disso é "nome da pasta", que é o que `docs/PRIVACIDADE.md` promete (M2 da
auditoria de 2026-09-19: a UI mostrava o nome curto e o payload levava o
caminho inteiro).
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable

# Mesmo número de `pastaCurta` na UI: o que é mostrado é o que é enviado.
SEGMENTOS = 2

# Raízes de infraestrutura do macOS: o segmento seguinte a elas é nome de
# usuário ou de volume, que nunca é "nome da pasta" do acervo. Cortados
# ANTES do recorte — senão um caminho raso (`/Volumes/Externo/Estrada Real`,
# caso real com 2.624 fotos) levaria o volume junto (achado da revisão
# com olhos frescos de D-094).
_RAIZES_INFRA = ("Users", "Volumes", "home")


def _segmentos(pasta: str) -> list[str]:
    # Só "/" separa pasta. Barra invertida é caractere VÁLIDO em nome de
    # pasta no macOS — normalizá-la fundiria `Fotos\2016` com `Fotos/2016`
    # numa colisão que não existe no disco (achado da revisão).
    return [s for s in pasta.split("/") if s]


def segmentos_uteis(pasta: str) -> list[str]:
    """Segmentos do caminho sem a raiz de infraestrutura e o nome de
    usuário/volume que a segue. `/Volumes/photo/Portfolio/Peru` →
    `["Portfolio", "Peru"]`; `/Volumes/photo` → `[]`."""
    partes = _segmentos(pasta)
    if len(partes) >= 2 and partes[0] in _RAIZES_INFRA:
        return partes[2:]
    return partes


def nome_curto(pasta: str, segmentos: int = SEGMENTOS) -> str:
    """As últimas `segmentos` pastas úteis do caminho, sem barra inicial.

    `/Users/eu/Pictures/Viagens/Peru 2023` → `Viagens/Peru 2023`;
    `/Volumes/Externo/Estrada Real` → `Estrada Real`; `Peru 2023` →
    `Peru 2023`; pasta que é só a raiz do volume → `""`.
    """
    uteis = segmentos_uteis(pasta)
    return "/".join(uteis[-segmentos:]) if uteis else ""


def nomes_curtos_unicos(pastas: Iterable[str]) -> dict[str, str]:
    """{caminho absoluto: nome curto}, um nome curto DISTINTO por pasta —
    garantido, não só tentado.

    Duas pastas diferentes podem ter as mesmas duas últimas partes
    (`/a/2015/Fotos` e `/b/2015/Fotos`). A resposta do modelo é casada de
    volta pelo nome enviado, então colisão viraria proposta atribuída à
    pasta errada. Quem colide ganha um segmento ÚTIL a mais até
    desempatar (nunca o usuário/volume cortado por `segmentos_uteis`); as
    demais continuam com o recorte padrão. Se ainda assim duas ficam
    iguais (só diferem em barra final, ou são a raiz de dois volumes),
    um sufixo ` (2)`, ` (3)`… fecha a injetividade — o mapa de volta
    nunca pode ter duas pastas na mesma chave.

    Só para o caminho que precisa de resposta casada (classificação de
    pasta por GenAI). O advisor de cluster não tem volta e usa
    `nome_curto` direto: escalar segmento lá seria dado a mais sem
    função (cópia local + NAS da mesma foto caem no mesmo cluster e
    subiriam até o caminho inteiro — achado da revisão).
    """
    absolutas = sorted(set(pastas))
    profundidade = {p: SEGMENTOS for p in absolutas}
    while True:
        curtos = {p: nome_curto(p, profundidade[p]) for p in absolutas}
        repetidos = {c for c, n in Counter(curtos.values()).items() if n > 1}
        if not repetidos:
            return curtos
        avancou = False
        for p in absolutas:
            if curtos[p] in repetidos and profundidade[p] < len(segmentos_uteis(p)):
                profundidade[p] += 1
                avancou = True
        if not avancou:
            break
    # Irredutível: desempata por sufixo, na ordem estável de `absolutas`.
    vistos: Counter[str] = Counter()
    unicos: dict[str, str] = {}
    for p in absolutas:
        base = curtos[p]
        vistos[base] += 1
        unicos[p] = base if vistos[base] == 1 else f"{base} ({vistos[base]})"
    return unicos
