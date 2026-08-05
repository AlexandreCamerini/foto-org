"""Nome legível da câmera a partir de `make` + `model`.

O EXIF grava fabricante e modelo em campos separados, e uma parte dos
fabricantes repete o próprio nome dentro do modelo: a Canon grava
`Make="Canon"` e `Model="Canon EOS 5D Mark III"`. Concatenar os dois às
cegas produz "Canon Canon EOS 5D Mark III", que apareceu em todas as
linhas da Revisão de um acervo real.

A regra é uma só e vale para qualquer fabricante: se o modelo já começa
pelo fabricante, o modelo basta. Nunca se remove pedaço do meio nem se
tenta adivinhar abreviação ("NIKON" vs "Nikon Corporation") — cortar
demais inventaria um nome que a câmera não gravou.
"""

from __future__ import annotations


def nome_da_camera(make: str | None, model: str | None) -> str | None:
    """`("Canon", "Canon EOS 5D Mark III")` → `"Canon EOS 5D Mark III"`.

    Devolve `None` quando não há nada a dizer — o chamador decide se
    esconde a linha ou mostra outra coisa no lugar.
    """
    fabricante = (make or "").strip()
    modelo = (model or "").strip()
    if not modelo:
        return fabricante or None
    if not fabricante:
        return modelo
    # Comparação por prefixo de palavra: "Canon" casa com "Canon EOS",
    # e "Canonical" não casaria com "Canon" por acidente.
    inicio = modelo[: len(fabricante)]
    resto = modelo[len(fabricante) :]
    if inicio.casefold() == fabricante.casefold() and (
        not resto or not resto[0].isalnum()
    ):
        return modelo
    return f"{fabricante} {modelo}"
