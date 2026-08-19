"""pasta_classificacoes_genai — persistência do GenAI de pasta (D-07, Fase 7)

Uma tabela nova, chaveada pelo CAMINHO DA PASTA (string), não por
`media_id`: uma linha classifica a pasta inteira, servindo todas as fotos
dela — mesmo padrão de `nomes_classificados` (0012), aplicado a caminho em
vez de nome de segmento.

Por que a tabela existe em vez de escrever direto em `Evidence`:
`SuggestionEngine._persistir_sugestao()` apaga e reconstrói `Evidence` a
cada `gerar()` para mídia ainda pendente — gravar o resultado do Claude só
em `Evidence` faria ele sumir na próxima regeneração e obrigaria a pagar de
novo pela mesma chamada. Esta tabela sobrevive à regeneração; a evidência é
reconstruída a partir dela sem nova chamada à API.

`status` (proposta/aprovada/descartada) é um eixo separado de `origem`
(llm/manual) — `origem` diz quem produziu o valor, `status` diz se o dono
aceitou. Só `status == 'aprovada'` é lido pela cascata (T-07-01-02);
`descartar()` nunca remove a linha, ela continua no banco como fonte de
sinal e auditoria (invariante 8 do CLAUDE.md).

Sem FK e sem índice adicional: a PK (`pasta`) é o único caminho de acesso
usado pelo repositório, e a tabela tem uma linha por pasta candidata —
escala de dezenas/centenas, não milhões. Mesmo raciocínio de escala que já
levou `nomes_classificados` a não ter índice além da PK.

Revision ID: 0020
Revises: 0019
Create Date: 2026-08-18 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = '0020'
down_revision: Union[str, None] = '0019'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'pasta_classificacoes_genai',
        sa.Column('pasta', sa.String(), nullable=False),
        sa.Column('cidade', sa.String(), nullable=True),
        sa.Column('pais', sa.String(), nullable=True),
        sa.Column('categoria', sa.String(), nullable=True),
        sa.Column('evento', sa.String(), nullable=True),
        sa.Column('justificativa', sa.Text(), nullable=False),
        sa.Column('origem', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('sessao', sa.String(), nullable=False),
        sa.Column('classificado_em', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint(
            'pasta', name=op.f('pk_pasta_classificacoes_genai')
        ),
    )


def downgrade() -> None:
    op.drop_table('pasta_classificacoes_genai')
