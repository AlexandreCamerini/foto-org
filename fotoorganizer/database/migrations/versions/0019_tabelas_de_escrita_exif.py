"""tabelas de escrita EXIF de localização (D-075, Fase 6)

Duas tabelas novas, paralelas a `operation_plans`/`operation_items` mas
**sem relação** com elas — domínio de escrita de localização, não de cópia
física:

- `exif_write_plans` — plano de escrita EXIF (dry-run → aprovação →
  execução), consumido por `exif_write/planner.py` e `exif_write/
  executor.py`.
- `exif_write_items` — um item por mídia, com **status e motivo
  independentes por campo** (`status_gps`/`status_cidade`/`status_pais`),
  não um status único: exiftool não é atômico por tag dentro de uma
  invocação (RESEARCH.md Pitfall 2), então falha parcial (ex.: gravou
  cidade e país, falhou o GPS) é resultado real e frequente (EXIF-03).
  Consumido por `repositories/exif_write.py` (lista de itens de um plano)
  e `exif_write/planner.py` (checa escrita pendente por mídia) — índices
  `ix_exif_write_items_plan_id` e `ix_exif_write_items_media_id`.

**Nenhuma coluna é adicionada a `audit_log`.** A trilha de auditoria da
escrita EXIF reusa `AuditLog` como está, sempre com `plan_id=None` — aquela
coluna tem FK real para `operation_plans.id`, e usar ali o id de um
`ExifWritePlan` (sequência de PK independente) quebra o insert com
`PRAGMA foreign_keys=ON` (RESEARCH.md Pitfall 5). O id do plano EXIF viaja
em `AuditLog.detalhe` (JSON), como `{"exif_plan_id": ...}` — deliberado,
para não precisar de mudança de esquema em `audit_log`.

Revision ID: 0019
Revises: 0018
Create Date: 2026-08-18 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = '0019'
down_revision: Union[str, None] = '0018'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'exif_write_plans',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(), nullable=False),
        sa.Column(
            'status',
            sa.Enum(
                'PLANEJADA', 'EXECUTANDO', 'CONCLUIDA', 'CANCELADA', 'ERRO',
                name='exifwritestatus', native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column('dry_run_em', sa.DateTime(), nullable=True),
        sa.Column('criado_em', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_exif_write_plans')),
    )
    op.create_table(
        'exif_write_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('plan_id', sa.Integer(), nullable=False),
        sa.Column('media_id', sa.Integer(), nullable=False),
        sa.Column('origem', sa.Text(), nullable=False),
        sa.Column('valor_gps_lat', sa.Float(), nullable=True),
        sa.Column('valor_gps_lon', sa.Float(), nullable=True),
        sa.Column('valor_cidade', sa.String(), nullable=True),
        sa.Column('valor_pais', sa.String(), nullable=True),
        sa.Column(
            'status_gps',
            sa.Enum(
                'PENDENTE', 'PRONTO', 'PULADO', 'SEM_VALOR', 'GRAVADO', 'FALHA',
                name='campostatus', native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column(
            'status_cidade',
            sa.Enum(
                'PENDENTE', 'PRONTO', 'PULADO', 'SEM_VALOR', 'GRAVADO', 'FALHA',
                name='campostatus', native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column(
            'status_pais',
            sa.Enum(
                'PENDENTE', 'PRONTO', 'PULADO', 'SEM_VALOR', 'GRAVADO', 'FALHA',
                name='campostatus', native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column('motivo_gps', sa.Text(), nullable=True),
        sa.Column('motivo_cidade', sa.Text(), nullable=True),
        sa.Column('motivo_pais', sa.Text(), nullable=True),
        sa.Column('formato_suportado', sa.Boolean(), nullable=False),
        sa.Column('motivo_nao_suportado', sa.Text(), nullable=True),
        sa.Column('sidecar_destino', sa.Text(), nullable=True),
        sa.Column('pasta_sincronizada', sa.String(), nullable=True),
        sa.Column('incluido', sa.Boolean(), nullable=False),
        sa.Column('hash_pre', sa.String(), nullable=True),
        sa.Column('hash_pos', sa.String(), nullable=True),
        sa.Column('backup_original', sa.Text(), nullable=True),
        sa.Column('erro', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ['media_id'], ['media_files.id'],
            name=op.f('fk_exif_write_items_media_id_media_files'),
        ),
        sa.ForeignKeyConstraint(
            ['plan_id'], ['exif_write_plans.id'],
            name=op.f('fk_exif_write_items_plan_id_exif_write_plans'),
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_exif_write_items')),
    )
    with op.batch_alter_table('exif_write_items', schema=None) as batch_op:
        batch_op.create_index(
            'ix_exif_write_items_plan_id', ['plan_id'], unique=False
        )
        batch_op.create_index(
            'ix_exif_write_items_media_id', ['media_id'], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table('exif_write_items', schema=None) as batch_op:
        batch_op.drop_index('ix_exif_write_items_media_id')
        batch_op.drop_index('ix_exif_write_items_plan_id')
    op.drop_table('exif_write_items')
    op.drop_table('exif_write_plans')
