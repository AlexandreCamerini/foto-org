"""tipo em sources (pasta | apple_photos | google_takeout)

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-24 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0003'
down_revision: Union[str, None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('sources', schema=None) as batch_op:
        batch_op.add_column(sa.Column(
            'tipo',
            sa.Enum('PASTA', 'APPLE_PHOTOS', 'GOOGLE_TAKEOUT',
                    name='sourcetype', native_enum=False),
            nullable=False,
            # Fontes existentes são todas pastas varridas.
            server_default='PASTA',
        ))


def downgrade() -> None:
    with op.batch_alter_table('sources', schema=None) as batch_op:
        batch_op.drop_column('tipo')
