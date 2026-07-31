"""referência é sempre testemunha, nunca acervo

`papel` (0008) e `arquivo_ausente` são ortogonais por desenho — uma miniatura
do Apple Fotos existe no disco e não é acervo —, mas há uma direção que não é
livre: quem não tem arquivo local não pode ser acervo, porque não há o que
mostrar na grade nem o que copiar no plano.

O importador de catálogo externo não sabia disso. Na primeira importação do
Lightroom, 54.086 referências entraram com `papel='ACERVO'` e
`arquivo_ausente=1` ao mesmo tempo. Nada quebrou — `organizavel` exige as duas
condições —, mas o registro passou a dizer duas coisas contraditórias, e é do
tipo de incoerência que uma consulta futura acerta por acidente ou erra em
silêncio.

Revision ID: 0010
Revises: 0009
Create Date: 2026-07-31 09:40:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = '0010'
down_revision: Union[str, None] = '0009'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "update media_files set papel='SINAL' "
        "where arquivo_ausente = 1 and papel <> 'SINAL'"
    )


def downgrade() -> None:
    # Sem volta: `papel` não guarda quem o alterou, e reverter devolveria ao
    # acervo também o que a 0008 e a 0009 rebaixaram por outros motivos.
    pass
