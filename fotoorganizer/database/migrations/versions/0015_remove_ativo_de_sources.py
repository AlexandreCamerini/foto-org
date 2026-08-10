"""remove ativo de sources (nunca lida nem escrita)

`ativo` existe desde a migração inicial e nunca foi lida nem escrita por
código de produção (auditoria em 2026-08-09). Nenhum find-or-create de fonte
(`scanner/scanner.py:_get_or_create_source`, `sources/importer.py:_obter_source`)
filtra por ela — os dois já fazem busca não escopada por `caminho`, então a
coluna não protegia nada. Mantê-la seria terreno fértil para alguém escopar um
find por `ativo=True` no futuro sem ver que o create seguinte esbarraria na
constraint única de `caminho` sem nunca reencontrar a linha (o bug que o
PhotoPrism corrige com "find precisa enxergar soft-deleted antes de criar").
Mais simples remover agora do que documentar um risco que não precisa existir.

Revision ID: 0015
Revises: 0014
Create Date: 2026-08-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0015'
down_revision: Union[str, None] = '0014'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('sources', schema=None) as batch_op:
        batch_op.drop_column('ativo')


def downgrade() -> None:
    with op.batch_alter_table('sources', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('ativo', sa.Boolean(), nullable=False, server_default='1')
        )
