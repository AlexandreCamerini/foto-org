"""resolvido_automaticamente em duplicate_groups

Marca se o papel dos membros de um grupo veio da regra determinística de
`duplicates/resolucao.py` (hoje, só grupos EXATO) em vez de decisão humana —
a UI usa isto para diferenciar "o algoritmo já decidiu, revise se quiser" de
"você decidiu". Nasce False para todo grupo já existente: nenhuma decisão
anterior foi tomada por essa regra, que só passa a existir a partir desta
fatia.

Revision ID: 0016
Revises: 0015
Create Date: 2026-08-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0016'
down_revision: Union[str, None] = '0015'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('duplicate_groups', schema=None) as batch_op:
        batch_op.add_column(sa.Column(
            'resolvido_automaticamente', sa.Boolean(), nullable=False,
            server_default='0',
        ))


def downgrade() -> None:
    with op.batch_alter_table('duplicate_groups', schema=None) as batch_op:
        batch_op.drop_column('resolvido_automaticamente')
