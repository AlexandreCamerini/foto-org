"""local estimado em media_files (coordenada herdada de outro dispositivo)

A câmera boa não grava GPS; o telefone grava. Quando as duas fotografam a
mesma cena com minutos de diferença, a foto da câmera pode HERDAR a
coordenada — e até agora essa herança vivia só em memória, durante a geração
de sugestões: o lugar resolvido virava `location_id`, mas a coordenada em si
se perdia e a foto continuava contando como "sem coordenada".

As colunas ficam SEPARADAS de gps_lat/gps_lon de propósito. Coordenada lida
do arquivo e coordenada estimada não são a mesma coisa, e qualquer consulta
que as misture perde a distinção que o usuário precisa ver. Quem quiser as
duas usa COALESCE explicitamente.

`gps_estimado_de_id` aponta a foto doadora e `gps_estimado_delta_s` guarda o
Δt já corrigido de deriva de relógio — os dois em coluna, não só dentro do
texto da justificativa, para que dê para filtrar "estimativas com mais de N
minutos de distância" sem interpretar prosa.

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-30 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0005'
down_revision: Union[str, None] = '0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('media_files', schema=None) as batch_op:
        batch_op.add_column(sa.Column('gps_lat_estimado', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('gps_lon_estimado', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column(
            'gps_estimado_de_id', sa.Integer(), nullable=True
        ))
        batch_op.add_column(sa.Column(
            'gps_estimado_delta_s', sa.Integer(), nullable=True
        ))
        batch_op.create_foreign_key(
            'fk_media_files_gps_estimado_de_id_media_files',
            'media_files', ['gps_estimado_de_id'], ['id'],
        )
        # SQLite não indexa FK sozinho, e a UI vai perguntar "quem herdou
        # desta foto?" ao abrir a doadora.
        batch_op.create_index(
            'ix_media_files_gps_estimado_de_id', ['gps_estimado_de_id'],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table('media_files', schema=None) as batch_op:
        batch_op.drop_index('ix_media_files_gps_estimado_de_id')
        batch_op.drop_constraint(
            'fk_media_files_gps_estimado_de_id_media_files', type_='foreignkey'
        )
        batch_op.drop_column('gps_estimado_delta_s')
        batch_op.drop_column('gps_estimado_de_id')
        batch_op.drop_column('gps_lon_estimado')
        batch_op.drop_column('gps_lat_estimado')
