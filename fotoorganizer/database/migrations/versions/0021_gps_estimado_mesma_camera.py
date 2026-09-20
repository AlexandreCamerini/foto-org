"""gps_estimado_mesma_camera em media_files (D-086, regra 1 da herança)

A herança same-câmera (câmera com receptor GPS confirmado, D-029/D-086)
tem o mesmo Δt confiável de qualquer outra herança, mas NENHUMA amostra
medida de acurácia — só o mecanismo do receptor sustenta. `gps_estimado_delta_s`
sozinho não distingue os dois casos: uma revisão adversarial encontrou que,
sem esta coluna, o plano de escrita EXIF (`exif_write/planner.py`) oferecia
GPS exato/cidade para escrita no arquivo original a partir de uma doação sem
amostra, só porque o Δt (agora mais curto, doadora do mesmo rolo) cabia na
mesma janela usada para heranças medidas. A coluna dá ao planner e ao mapa
(`server/app.py`) um jeito de distinguir e não prometer o que não foi medido.

Revision ID: 0021
Revises: 0020
Create Date: 2026-09-20 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0021'
down_revision: Union[str, None] = '0020'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('media_files', schema=None) as batch_op:
        batch_op.add_column(sa.Column(
            'gps_estimado_mesma_camera', sa.Boolean(), nullable=False,
            server_default=sa.false(),
        ))


def downgrade() -> None:
    with op.batch_alter_table('media_files', schema=None) as batch_op:
        batch_op.drop_column('gps_estimado_mesma_camera')
