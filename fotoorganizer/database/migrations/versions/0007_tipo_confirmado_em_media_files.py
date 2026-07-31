"""tipo_confirmado em media_files (o veredito do detector é provisório)

`tipo_imagem` é o que o detector concluiu, e é reescrito a cada geração de
sugestões — como tem de ser: um arquivo reprocessado pode ganhar EXIF, uma
foto nova pode mudar o contexto. Mas isso significa que uma correção do
usuário seria silenciosamente desfeita na próxima passagem.

`tipo_confirmado` é a palavra do usuário. Nada no motor a sobrescreve, e o
tipo que vale em qualquer decisão é `COALESCE(tipo_confirmado, tipo_imagem)`.

A separação também dá à interface o que ela precisa para pedir ajuda sem
atrapalhar: enquanto `tipo_confirmado` for NULL, a classificação é
explicitamente provisória e pode ser mostrada como pergunta, não como fato.

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-30 04:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0007'
down_revision: Union[str, None] = '0006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('media_files', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('tipo_confirmado', sa.String(), nullable=True)
        )
        batch_op.add_column(
            sa.Column('tipo_confirmado_em', sa.DateTime(), nullable=True)
        )
        batch_op.create_index(
            'ix_media_files_tipo_confirmado', ['tipo_confirmado'], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table('media_files', schema=None) as batch_op:
        batch_op.drop_index('ix_media_files_tipo_confirmado')
        batch_op.drop_column('tipo_confirmado_em')
        batch_op.drop_column('tipo_confirmado')
