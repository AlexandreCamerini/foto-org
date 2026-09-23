"""exif_write_plans.status ganha INTERROMPIDA (plano órfão reconciliado no boot)

`status` foi criada em 0019 como `Enum(..., native_enum=False)`: um VARCHAR
do tamanho do nome mais longo ("EXECUTANDO", 10). SQLite não impõe o
tamanho, mas o schema declarado ficaria mentindo — e um Postgres futuro
recusaria "INTERROMPIDA" (12). Recria a coluna com o novo membro; os dados
existentes são copiados como estão (batch mode no SQLite).

Por que o status existe: só o fim feliz ou o cancelamento escrevem status.
Quando o processo morre no meio (app fechado, Mac desligado), o plano
ficava EXECUTANDO para sempre e a tela mentia sobre trabalho em curso. O
boot do servidor carimba INTERROMPIDA (D-095), mesmo padrão de
`ScanStatus.INTERROMPIDO`.

Revision ID: 0023
Revises: 0022
Create Date: 2026-09-23 02:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0023'
down_revision: Union[str, None] = '0022'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ANTIGO = sa.Enum(
    'PLANEJADA', 'EXECUTANDO', 'CONCLUIDA', 'CANCELADA', 'ERRO',
    name='exifwritestatus', native_enum=False,
)
_NOVO = sa.Enum(
    'PLANEJADA', 'EXECUTANDO', 'CONCLUIDA', 'CANCELADA', 'ERRO', 'INTERROMPIDA',
    name='exifwritestatus', native_enum=False,
)


def upgrade() -> None:
    with op.batch_alter_table('exif_write_plans', schema=None) as batch_op:
        batch_op.alter_column(
            'status', existing_type=_ANTIGO, type_=_NOVO, existing_nullable=False,
        )


def downgrade() -> None:
    # Linha já carimbada como INTERROMPIDA não cabe no enum antigo: vira
    # ERRO antes de estreitar, para o downgrade não quebrar no meio.
    op.execute(
        "UPDATE exif_write_plans SET status = 'ERRO' WHERE status = 'INTERROMPIDA'"
    )
    with op.batch_alter_table('exif_write_plans', schema=None) as batch_op:
        batch_op.alter_column(
            'status', existing_type=_NOVO, type_=_ANTIGO, existing_nullable=False,
        )
