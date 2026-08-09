"""arquivo_offline em media_files (o terceiro estado de alcance)

Hoje o app distingue dois estados: `arquivo_ausente` (referência de catálogo
externo — iCloud —, nunca teve arquivo local) e `Source.disponivel` (a fonte
INTEIRA não responde agora — HD na gaveta). Falta o do meio: um arquivo que
sumiu de uma fonte que CONTINUA montada — apagado, movido para fora,
renomeado por outro programa. Sem uma coluna própria isso era indistinguível
de "sempre esteve lá": a linha ficava no catálogo com metadados obsoletos e
ninguém percebia até tentar abrir.

`arquivo_offline` fecha essa lacuna. É mantida por dois mecanismos
complementares: o scan normal marca quem não apareceu no walk desta passada
(`scanner/scanner.py`), e o laço de reconciliação confere periodicamente sem
esperar um scan manual (`scanner/reconciliacao.py`), com checkpoint em
`application_settings` — de propósito NÃO em `ScanSession`, para não fazer
uma reconciliação pausada aparecer na tela de "retomar scan" do webapp
(`RetomarScan.tsx`) como se fosse uma varredura de pasta interrompida.

Revision ID: 0013
Revises: 0012
Create Date: 2026-08-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0013'
down_revision: Union[str, None] = '0012'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('media_files', schema=None) as batch_op:
        batch_op.add_column(sa.Column(
            'arquivo_offline', sa.Boolean(), nullable=False,
            # Tudo que já está catalogado foi visto pelo menos uma vez —
            # ninguém nasce sumido; a reconciliação decide daqui pra frente.
            server_default=sa.false(),
        ))
        batch_op.create_index(
            'ix_media_files_arquivo_offline', ['arquivo_offline'],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table('media_files', schema=None) as batch_op:
        batch_op.drop_index('ix_media_files_arquivo_offline')
        batch_op.drop_column('arquivo_offline')
