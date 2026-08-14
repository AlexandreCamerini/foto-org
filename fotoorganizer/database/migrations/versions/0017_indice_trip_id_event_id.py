"""índice em trip_id e event_id de media_files

`_agrupamentos` (server/app.py, /api/viagens e /api/eventos) filtra
`media_files` por `trip_id`/`event_id` uma vez por grupo — sem índice, cada
consulta é um SCAN completo da tabela (medido: 477 mil linhas), e o endpoint
faz ~190×2 dessas consultas numa carga só. Medido no catálogo real: aba
Viagens levava 50-120+ segundos para responder, tempo suficiente para a UI
mostrar "nenhuma viagem" antes da resposta chegar (D-066 achado 3, D-069).

Revision ID: 0017
Revises: 0016
Create Date: 2026-08-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = '0017'
down_revision: Union[str, None] = '0016'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('media_files', schema=None) as batch_op:
        batch_op.create_index(
            'ix_media_files_trip_id', ['trip_id'], unique=False
        )
        batch_op.create_index(
            'ix_media_files_event_id', ['event_id'], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table('media_files', schema=None) as batch_op:
        batch_op.drop_index('ix_media_files_event_id')
        batch_op.drop_index('ix_media_files_trip_id')
