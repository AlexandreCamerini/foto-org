"""papel em media_files (acervo x fonte de sinal)

O scanner entrou no pacote `Photos Library.photoslibrary` e catalogou as
miniaturas internas do Apple Fotos — 540×360, 360×640 — como se fossem fotos.
Num acervo real medido em 2026-07-31 elas eram 45.822 de 51.423 arquivos
locais: 89%. A revisão recebeu 45.822 sugestões sobre miniatura e ficou
inutilizável.

Apagá-las seria pior. Elas carregam o GPS que as referências do `osxphotos`
não reportam, e nenhum dos 5.601 arquivos reais do acervo tem coordenada
própria: sem as miniaturas, as fotos com lugar estimado caem de 2.117 para
162. O invariante 8 do CLAUDE.md fecha a porta — nada que possa ser a
referência real de uma foto é apagado.

Daí `papel`: quem não é acervo é rebaixado a testemunha. Sai da grade, da
revisão e do plano; continua doando data, GPS e correlação.

O backfill classifica o que já está catalogado, para o catálogo existente
não precisar de nova varredura. Nenhuma linha é removida.

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-31 05:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0008'
down_revision: Union[str, None] = '0007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Pacotes de biblioteca de foto do macOS: por dentro são cache de app, não
# acervo. Casados por sufixo — o nome real é "<Qualquer Nome>.photoslibrary".
SUFIXOS_DE_PACOTE = (
    ".photoslibrary",
    ".photolibrary",
    ".migratedphotolibrary",
    ".aplibrary",
)


def upgrade() -> None:
    with op.batch_alter_table('media_files', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('papel', sa.String(), nullable=False,
                      server_default='ACERVO')
        )
        batch_op.create_index('ix_media_files_papel', ['papel'], unique=False)

    # Referência de catálogo externo já era testemunha na prática; agora diz.
    op.execute(
        "update media_files set papel='SINAL' where arquivo_ausente = 1"
    )
    # E o que mora dentro de um pacote de biblioteca de foto.
    for sufixo in SUFIXOS_DE_PACOTE:
        op.execute(
            "update media_files set papel='SINAL' "
            f"where instr(lower(caminho), '{sufixo}/') > 0"
        )


def downgrade() -> None:
    with op.batch_alter_table('media_files', schema=None) as batch_op:
        batch_op.drop_index('ix_media_files_papel')
        batch_op.drop_column('papel')
