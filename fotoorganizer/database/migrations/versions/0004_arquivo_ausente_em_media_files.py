"""arquivo_ausente em media_files (referência sem arquivo local)

Fotos que só existem no iCloud não têm arquivo no disco, mas têm horário e
coordenada no banco da biblioteca do Fotos. Elas entram no catálogo como
REFERÊNCIA: doam GPS para a correlação entre fontes e nunca participam de
grade, miniatura, duplicata ou plano de cópia — não há arquivo para copiar.

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-26 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0004'
down_revision: Union[str, None] = '0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('media_files', schema=None) as batch_op:
        batch_op.add_column(sa.Column(
            'arquivo_ausente', sa.Boolean(), nullable=False,
            # Tudo que já está catalogado veio de um arquivo real.
            server_default=sa.false(),
        ))


def downgrade() -> None:
    with op.batch_alter_table('media_files', schema=None) as batch_op:
        batch_op.drop_column('arquivo_ausente')
