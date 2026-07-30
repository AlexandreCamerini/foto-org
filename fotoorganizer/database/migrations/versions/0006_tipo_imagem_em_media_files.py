"""tipo_imagem em media_files (foto x captura x recebida x baixada)

Um acervo pessoal real não é só foto: tem captura de tela, imagem recebida no
WhatsApp e banner baixado do navegador. Elas entopem a grade, poluem o
agrupamento temporal e inflam qualquer contagem — e ninguém quer organizá-las
por viagem.

A coluna é nullable de propósito: NULL significa "ainda não avaliado", que é
o estado de todo arquivo já catalogado antes desta migração. O detector
(classification/tipo_imagem.py) preenche na próxima geração de sugestões.

Nada é excluído do catálogo: o arquivo entra, é marcado, e o usuário decide.
Marcar é reversível; ignorar no scan seria invisível.

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-30 03:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0006'
down_revision: Union[str, None] = '0005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('media_files', schema=None) as batch_op:
        batch_op.add_column(sa.Column('tipo_imagem', sa.String(), nullable=True))
        # A Biblioteca vai filtrar por isto e o Panorama vai contá-lo.
        batch_op.create_index(
            'ix_media_files_tipo_imagem', ['tipo_imagem'], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table('media_files', schema=None) as batch_op:
        batch_op.drop_index('ix_media_files_tipo_imagem')
        batch_op.drop_column('tipo_imagem')
