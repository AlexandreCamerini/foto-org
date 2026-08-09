"""O que conta como "caminho de arquivo de verdade" para decidir alcance.

Referência de catálogo externo (`apple://uuid`, `lightroom://uuid`,
`takeout://id`) não é um caminho de filesystem — `Path.exists()`/`stat()`
nela não têm sentido, e tratá-la como se tivesse já causou um bug real: o
scan normal marcava essas linhas como `arquivo_offline=True` sempre que a
`Source` de um catálogo externo era reaproveitada por um scan de pasta comum
apontando para o mesmo caminho (`_get_or_create_source` funde as duas).

Este módulo é a ÚNICA fonte de verdade para essa pergunta, compartilhada
entre o scan normal (`scanner.py`, ao decidir o que marcar como sumido) e o
laço de reconciliação (`reconciliacao.py`, ao decidir o que vale a pena
perguntar ao filesystem) — os dois nunca podem divergir sobre isto.
"""

from __future__ import annotations

# O mesmo marcador usado nos dois lados: aqui em Python (substring), e em
# `reconciliacao.py` dentro de um `NOT LIKE '%://%'` no SQL. Um só símbolo
# para as duas expressões nunca saírem de sincronia.
MARCADOR_REFERENCIA_EXTERNA = "://"
PADRAO_SQL_REFERENCIA_EXTERNA = f"%{MARCADOR_REFERENCIA_EXTERNA}%"


def eh_caminho_de_filesystem(caminho: str) -> bool:
    """False para referência de catálogo externo — não é um caminho real."""
    return MARCADOR_REFERENCIA_EXTERNA not in caminho


def elegivel_para_verificacao_de_alcance(
    caminho: str, arquivo_ausente: bool
) -> bool:
    """Vale a pena perguntar ao filesystem sobre esta linha?

    Não, se ela já é uma referência sem arquivo local (`arquivo_ausente`) —
    nunca teve o que verificar — ou se o caminho não é de filesystem. Hoje
    uma condição sempre implica a outra (toda referência externa nasce com
    `arquivo_ausente=True` — ver `sources/importer.py:_gravar_referencia`),
    mas checar as duas é a defesa contra as duas divergirem no futuro sem
    que ninguém perceba.
    """
    return not arquivo_ausente and eh_caminho_de_filesystem(caminho)
