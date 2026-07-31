"""rebaixa a acervo→sinal o que mora em pasta de trabalho de programação

A fonte de um acervo real apontava para a pasta pessoal inteira, e o scanner
desceu em `node_modules`, `Assets.xcassets` e afins: 499 ícones de app,
splash screens e skins de emulador entraram como se fossem fotos.

O estrago maior não foi a contagem. `BoraChurrascoRio.imageset` — uma pasta de
asset catalog — passou pelo teste de "nome de álbum" e batizou um evento com
1.314 fotos de verdade dentro, incluindo uma noite de teatro.

O scanner passou a não entrar nessas pastas (`discovery.PASTAS_DE_CODIGO` e
`SUFIXOS_DE_CODIGO`) e o nomeador de eventos passou a recusá-las. Esta
migração cuida do que já está gravado: rebaixa a `papel='SINAL'`, sai da
grade, da revisão e do plano. Nada é removido — invariante 8.

Diferente das miniaturas do Apple Fotos (0008), estas não são testemunha de
coisa alguma: um ícone de app não tem data de captura nem GPS para doar. Ficam
como sinal por consistência com o invariante, não por utilidade.

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-31 06:30:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = '0009'
down_revision: Union[str, None] = '0008'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Espelham discovery.PASTAS_DE_CODIGO e SUFIXOS_DE_CODIGO. Ficam copiadas
# aqui de propósito: migração é histórico e não pode mudar de efeito quando
# a lista do código crescer.
PASTAS = (
    "node_modules", "bower_components", "__pycache__", "site-packages",
    "DerivedData", "Pods", "venv", "vendor", "target",
)
SUFIXOS = (
    ".xcassets", ".imageset", ".appiconset", ".colorset", ".dataset",
    ".xcodeproj", ".xcworkspace", ".playground", ".lproj",
    ".framework", ".bundle", ".app",
)


def upgrade() -> None:
    for pasta in PASTAS:
        op.execute(
            "update media_files set papel='SINAL' "
            f"where instr(lower(caminho), '/{pasta.lower()}/') > 0"
        )
    for sufixo in SUFIXOS:
        op.execute(
            "update media_files set papel='SINAL' "
            f"where instr(lower(caminho), '{sufixo}/') > 0"
        )


def downgrade() -> None:
    # Sem volta possível: `papel` não guarda por que foi rebaixado, e desfazer
    # devolveria ao acervo também o que a 0008 rebaixou. Rodar de novo a 0008
    # e esta reconstrói o estado — nenhuma linha foi perdida no caminho.
    pass
