"""pais_confirmado/regiao_confirmado/cidade_confirmado em media_files

Mesmo padrão de tipo_confirmado (0007): a cascata geo (`_evidencias_geo`)
é reescrita a cada geração de sugestões — GPS herdado pode mudar de
doadora, um álbum pode ser reclassificado, o dataset offline de
geocodificação pode revisar um nome. Uma correção manual do usuário seria
silenciosamente desfeita na próxima rodada sem um campo que o motor nunca
sobrescreve.

Três colunas, não uma: o usuário pode corrigir só a cidade e deixar
país/região virem da cascata normalmente. Não entra em `locations` — essa
tabela é cache POR COORDENADA (~110m), compartilhada por todas as fotos
que caem no mesmo bucket; gravar a correção lá vazaria para fotos de
outro momento que só coincidem no mesmo lugar.

Revision ID: 0022
Revises: 0021
Create Date: 2026-09-22 03:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0022'
down_revision: Union[str, None] = '0021'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('media_files', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('pais_confirmado', sa.String(), nullable=True)
        )
        batch_op.add_column(
            sa.Column('regiao_confirmado', sa.String(), nullable=True)
        )
        batch_op.add_column(
            sa.Column('cidade_confirmado', sa.String(), nullable=True)
        )
        batch_op.add_column(
            sa.Column('local_confirmado_em', sa.DateTime(), nullable=True)
        )
        batch_op.create_index(
            'ix_media_files_pais_confirmado', ['pais_confirmado'], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table('media_files', schema=None) as batch_op:
        batch_op.drop_index('ix_media_files_pais_confirmado')
        batch_op.drop_column('local_confirmado_em')
        batch_op.drop_column('cidade_confirmado')
        batch_op.drop_column('regiao_confirmado')
        batch_op.drop_column('pais_confirmado')
