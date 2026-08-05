"""o que uma palavra é: lugar, ocasião, pessoa ou ruído

A cascata determinística sabe medir duração e distância; não tem como saber
que "Pantanal" é um lugar aonde se viaja e "Quizomba" é uma festa. Medido no
acervo real: a regra 6 de `docs/AGRUPAMENTO.md` classificou Pantanal (1d23h)
e Visconde de Mauá (18 fotos) como eventos — os dois são destino de viagem.

A chave é o NOME, não a foto: um acervo inteiro tem uma centena de nomes
distintos de pasta e álbum, então classificá-los uma vez resolve todas as
sessões e todas as regenerações futuras.

Revision ID: 0012
Revises: 0011
Create Date: 2026-08-04 23:40:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = '0012'
down_revision: Union[str, None] = '0011'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'nomes_classificados',
        sa.Column('nome', sa.String(), nullable=False),
        sa.Column('categoria', sa.String(), nullable=False),
        sa.Column('justificativa', sa.String(), nullable=True),
        sa.Column('origem', sa.String(), nullable=False),
        sa.Column('classificado_em', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('nome'),
    )


def downgrade() -> None:
    op.drop_table('nomes_classificados')
