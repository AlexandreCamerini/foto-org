"""índices de FK ausentes (fase 5, LANC-02)

9 índices novos, cada um com consumidor real citado no `Index()` espelhado
em `fotoorganizer/models/*.py`:

- `ix_media_files_pasta` — `_sob_a_pasta` (repositories/media.py:171) faz
  SCAN completo de `media_files` a cada filtro de pasta na grade e a cada
  clique na árvore de `/api/pastas`. NECESSÁRIO MAS NÃO SUFICIENTE: o
  planner do SQLite só usa este índice para `LIKE 'prefixo/%'` com
  `PRAGMA case_sensitive_like=ON` também habilitado (database/engine.py,
  fatia separada desta migração) — ver RESEARCH.md Pitfall 3.
- `ix_media_files_location_id` — repositories/media.py:278,356, filtro/join
  de país e cidade.
- `ix_suggestions_media_id` — engine.py:1042,1083,1106; server/app.py:724;
  repositories/media.py:118,149; repositories/suggestions.py:119,296;
  operations/planner.py:60; operations/inventario.py:161. A busca por
  media_id mais consultada do catálogo (Inspetor, filtro "sem_sugestao",
  join do planejador).
- `ix_operation_items_plan_id` — repositories/operations.py:71,141 (lista de
  itens de um plano, consulta central da tela de Operações);
  operations/executor.py:272.
- `ix_operation_items_media_id` — operations/planner.py:68 (operações
  pendentes por mídia).
- `ix_audit_log_plan_id` — repositories/operations.py:95,128;
  operations/executor.py:131,163 (trilha de auditoria por plano).
- `ix_duplicate_members_media_id` — operations/planner.py:79;
  duplicates/detector.py:302 ("em qual grupo está esta mídia"). NÃO coberto
  pelo `UniqueConstraint(group_id, media_id)` já existente: media_id é a
  segunda coluna ali, não utilizável como índice de coluna líder para um
  filtro só por media_id.
- `ix_face_occurrences_media_id` / `ix_face_occurrences_person_id` —
  repositories/people.py:42,108,109.

Exclusão deliberada (não é omissão): `FaceEmbedding.person_id`,
`MediaTag.tag_id` e `Trip.location_id` NÃO entram nesta migração. Grep de
uso não achou nenhuma cláusula WHERE/join filtrando por essas três colunas
hoje — só travessia de relacionamento (`relationship()`, cascade delete).
Mesmo precedente já documentado em `fotoorganizer/models/catalog.py`:
"índice quando o custo de escrita se justifica por um consumidor real e
mensurável" (D-072). Ver RESEARCH.md Open Question 1 (RESOLVED).

Reconciliação de drift (SEM criar índice novo aqui — o índice já existe no
banco desde migrações anteriores, recriá-lo aborta `upgrade_to_head()` com
erro de índice duplicado): `ix_media_files_gps_estimado_de_id` (migração 0005),
`ix_media_files_tipo_imagem` (0006), `ix_media_files_tipo_confirmado`
(0007), `ix_sources_volume_id` (0011) — as quatro só ganharam o `Index(...)`
espelhado no modelo, nesta mesma fatia (RESEARCH.md Pitfall 2).

Revision ID: 0018
Revises: 0017
Create Date: 2026-08-17 18:26:17.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = '0018'
down_revision: Union[str, None] = '0017'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('media_files', schema=None) as batch_op:
        batch_op.create_index('ix_media_files_pasta', ['pasta'], unique=False)
        batch_op.create_index(
            'ix_media_files_location_id', ['location_id'], unique=False
        )
    with op.batch_alter_table('suggestions', schema=None) as batch_op:
        batch_op.create_index(
            'ix_suggestions_media_id', ['media_id'], unique=False
        )
    with op.batch_alter_table('operation_items', schema=None) as batch_op:
        batch_op.create_index(
            'ix_operation_items_plan_id', ['plan_id'], unique=False
        )
        batch_op.create_index(
            'ix_operation_items_media_id', ['media_id'], unique=False
        )
    with op.batch_alter_table('audit_log', schema=None) as batch_op:
        batch_op.create_index('ix_audit_log_plan_id', ['plan_id'], unique=False)
    with op.batch_alter_table('duplicate_members', schema=None) as batch_op:
        batch_op.create_index(
            'ix_duplicate_members_media_id', ['media_id'], unique=False
        )
    with op.batch_alter_table('face_occurrences', schema=None) as batch_op:
        batch_op.create_index(
            'ix_face_occurrences_media_id', ['media_id'], unique=False
        )
        batch_op.create_index(
            'ix_face_occurrences_person_id', ['person_id'], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table('face_occurrences', schema=None) as batch_op:
        batch_op.drop_index('ix_face_occurrences_person_id')
        batch_op.drop_index('ix_face_occurrences_media_id')
    with op.batch_alter_table('duplicate_members', schema=None) as batch_op:
        batch_op.drop_index('ix_duplicate_members_media_id')
    with op.batch_alter_table('audit_log', schema=None) as batch_op:
        batch_op.drop_index('ix_audit_log_plan_id')
    with op.batch_alter_table('operation_items', schema=None) as batch_op:
        batch_op.drop_index('ix_operation_items_media_id')
        batch_op.drop_index('ix_operation_items_plan_id')
    with op.batch_alter_table('suggestions', schema=None) as batch_op:
        batch_op.drop_index('ix_suggestions_media_id')
    with op.batch_alter_table('media_files', schema=None) as batch_op:
        batch_op.drop_index('ix_media_files_location_id')
        batch_op.drop_index('ix_media_files_pasta')
