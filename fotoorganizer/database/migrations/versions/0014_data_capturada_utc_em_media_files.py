"""data_capturada_utc em media_files (o segundo instante)

Uma foto tem dois instantes, e até aqui o catálogo guardava um só.
`data_capturada` sempre foi a hora de PAREDE — a que o relógio marcava no
lugar da captura. Isso não é acidente: `metadata/exiftool.py:_data()` e
`sources/apple_photos.py:_asset_de()` descartam o fuso de propósito, este
último com o comentário "coerente com EXIF no resto do catálogo". É a hora
certa para ordenar a grade e agrupar evento e viagem, e continua sendo.

Falta o outro: o instante ABSOLUTO. Sem ele não existe ordem verdadeira
entre fotos de fusos diferentes, e `tz_estimado` (fase 11) viraria um campo
cujo significado depende de outro estar preenchido — receita de bug
silencioso num acervo de 25 anos com viagens (D-029).

Backfill aqui dentro, em SQL, e não em script separado: é uma sentença só
para as 219 mil linhas com data, sem processo à parte que alguém possa
esquecer de rodar. A regra do backfill é a mesma que vale para linha nova —
sem fuso conhecido, os dois instantes são iguais (o `keepLocalTime` do
Immich, `metadata.service.ts:1023`). Igualdade quer dizer "fuso
desconhecido", nunca "tirada em UTC".

**Isto não é atômico, e o `upgrade()` é escrito sabendo disso.** Sob pysqlite
o `ADD COLUMN` provoca commit implícito, então uma interrupção entre ele e o
`UPDATE` (app morto, disco cheio) deixaria a coluna criada com
`alembic_version` ainda em 0013 — e a tentativa seguinte quebraria em
`duplicate column name`, travando a abertura do app. O que se garante é
outra coisa, e é suficiente: **o upgrade é seguro para retomar**. A coluna só
é adicionada se ainda não existir, e o backfill é idempotente por natureza
(reafirmar `utc = local` em quem já está assim não muda nada), então roda
sempre, sem guarda. Uma segunda tentativa termina o serviço em vez de travar.

O backfill iguala inclusive as linhas do Apple Fotos que TINHAM fuso real e
o perderam antes desta fatia existir. Reimportar a biblioteca corrige as que
entraram como REFERÊNCIA — reescritas a cada import, e são as 44.661 do
acervo real, que roda em "Otimizar armazenamento". Asset com arquivo local
não: o importador o pula por assinatura (tamanho+mtime) inalterada, então só
volta a ganhar o fuso quando o arquivo mudar. Nada se perde no meio-tempo —
igualdade já era o que estava implícito antes desta coluna existir.

Sem índice: ordenação e recortes continuam na coluna local, e não há
consulta que filtre por esta. Ver o comentário em `models/catalog.py`.

Revision ID: 0014
Revises: 0013
Create Date: 2026-08-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0014'
down_revision: Union[str, None] = '0013'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Retomada depois de uma interrupção entre o ADD COLUMN (que comita
    # sozinho sob pysqlite) e o UPDATE: a coluna já existe e `alembic_version`
    # ainda diz 0013. Sem esta checagem, a segunda tentativa morre em
    # "duplicate column name" e o app deixa de abrir.
    colunas = {
        c["name"] for c in sa.inspect(op.get_bind()).get_columns("media_files")
    }
    if "data_capturada_utc" not in colunas:
        with op.batch_alter_table('media_files', schema=None) as batch_op:
            batch_op.add_column(
                sa.Column('data_capturada_utc', sa.DateTime(), nullable=True)
            )
    # Roda sempre — é o que faz a retomada terminar o serviço em vez de
    # deixar metade das linhas para trás. `data_capturada_utc is null` não é
    # otimização: numa retomada, alguém pode ter reimportado o Apple Fotos no
    # meio-tempo e escrito um fuso de verdade, e o backfill não pode apagá-lo
    # por cima. Quem não tem hora local não ganha instante absoluto — um sem
    # o outro seria uma linha afirmando que sabe quando a foto foi tirada sem
    # saber que horas eram.
    op.execute(
        "update media_files set data_capturada_utc = data_capturada "
        "where data_capturada is not null and data_capturada_utc is null"
    )


def downgrade() -> None:
    with op.batch_alter_table('media_files', schema=None) as batch_op:
        batch_op.drop_column('data_capturada_utc')
