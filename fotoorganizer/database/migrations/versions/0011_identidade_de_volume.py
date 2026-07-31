"""identidade de volume na fonte

O macOS não promete o ponto de montagem: um disco "photo" monta em
`/Volumes/photo` hoje e em `/Volumes/photo 1` amanhã, se o nome colidir. Com o
caminho como identidade da fonte, essa remontagem vira "disco novo" — e num
acervo real seriam 45.397 fotos recatalogadas do zero.

`volume_id` guarda o que sobrevive: UUID do volume quando existe, servidor e
compartilhamento para NAS, ponto de montagem como último recurso.

`visto_em` registra quando a fonte esteve alcançável pela última vez. É o que
separa "está na gaveta" de "sumiu" — e sem essa distinção o app só sabe dizer
que o arquivo não está lá.

Revision ID: 0011
Revises: 0010
Create Date: 2026-07-31 10:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0011'
down_revision: Union[str, None] = '0010'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('sources', schema=None) as batch_op:
        batch_op.add_column(sa.Column('volume_id', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('volume_nome', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('visto_em', sa.DateTime(), nullable=True))
        batch_op.create_index('ix_sources_volume_id', ['volume_id'],
                              unique=False)


def downgrade() -> None:
    with op.batch_alter_table('sources', schema=None) as batch_op:
        batch_op.drop_index('ix_sources_volume_id')
        batch_op.drop_column('visto_em')
        batch_op.drop_column('volume_nome')
        batch_op.drop_column('volume_id')
