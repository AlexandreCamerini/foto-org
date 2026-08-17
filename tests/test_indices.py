"""Índices de FK ausentes (fase 5, LANC-02) — plano de consulta, não schema.

Por que a asserção principal é sobre `EXPLAIN QUERY PLAN` e não sobre
`sqlite_master` conter o nome do índice: RESEARCH.md Pitfall 3 mostrou,
verificado empiricamente, que um `Index()` sozinho em `MediaFile.pasta` NÃO
basta para o SQLite reescrever `pasta LIKE 'prefixo/%'` num range scan sobre
o índice — o planner só faz isso com `PRAGMA case_sensitive_like=ON`
habilitado na conexão (ou índice `COLLATE NOCASE`, que não é o caso aqui).
Um teste que só checasse "o índice existe em sqlite_master" passaria mesmo
com o `SCAN media_files` ainda acontecendo — exatamente o jeito silencioso
de o critério de aceite #2 da fase falhar sem nenhum teste denunciar.
"""

from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy import select, text
from sqlalchemy.dialects import sqlite

from fotoorganizer.database import create_session_factory
from fotoorganizer.models import MediaFile, Source
from fotoorganizer.repositories import MediaFilters, MediaRepository
from fotoorganizer.repositories.media import _sob_a_pasta

# Os 9 índices novos da migração 0018 (consumidor real citado na migração e
# no modelo) mais os 4 que já existem no banco desde 0005/0006/0007/0011 e
# que a Task 2 só espelha em __table_args__ — nenhuma migração nova para
# estes últimos (RESEARCH.md Pitfall 2).
INDICES_ESPERADOS = [
    "ix_media_files_pasta",
    "ix_media_files_location_id",
    "ix_suggestions_media_id",
    "ix_operation_items_plan_id",
    "ix_operation_items_media_id",
    "ix_audit_log_plan_id",
    "ix_duplicate_members_media_id",
    "ix_face_occurrences_media_id",
    "ix_face_occurrences_person_id",
    "ix_media_files_gps_estimado_de_id",
    "ix_media_files_tipo_imagem",
    "ix_media_files_tipo_confirmado",
    "ix_sources_volume_id",
]


@pytest.fixture()
def catalogo_com_pastas(migrated_engine):
    """Semeia `/fotos/a` (2x), `/fotos/a/sub` e `/fotos/ab` — a pasta irmã
    que só um `LIKE` com barra explícita no prefixo (não um `LIKE` cru)
    consegue não confundir com `/fotos/a`."""
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        fonte = Source(caminho="/fotos")
        session.add(fonte)
        session.flush()
        linhas = [
            ("praia.jpg", "jpg", "/fotos/a", "PRAIA.JPG"),
            ("segunda.jpg", "jpg", "/fotos/a", None),
            ("sub.jpg", "jpg", "/fotos/a/sub", None),
            ("irma.jpg", "jpg", "/fotos/ab", None),
        ]
        for nome_padrao, ext, pasta, nome_real in linhas:
            nome = nome_real or nome_padrao
            session.add(
                MediaFile(
                    source_id=fonte.id,
                    caminho=f"{pasta}/{nome}",
                    pasta=pasta,
                    nome=nome,
                    extensao=ext,
                    tamanho=100,
                    data_capturada=datetime(2024, 1, 1),
                )
            )
        session.commit()
    return MediaRepository(factory), factory


def test_prefixo_de_pasta_usa_indice_nao_scan(migrated_engine, catalogo_com_pastas):
    """Critério 2 da fase: SEARCH sobre `ix_media_files_pasta`, nunca SCAN.

    Compila a consulta REAL de `_sob_a_pasta` (não SQL reescrito à mão) —
    é um `or_` de igualdade e prefixo, então o plano esperado é
    `MULTI-INDEX OR` com dois ramos `SEARCH` sobre o mesmo índice; a
    asserção procura substring, não a linha inteira, para tolerar isso.
    """
    consulta_compilada = (
        select(MediaFile)
        .where(_sob_a_pasta("/fotos/a"))
        .compile(dialect=sqlite.dialect(), compile_kwargs={"literal_binds": True})
    )
    stmt = text("EXPLAIN QUERY PLAN " + str(consulta_compilada))
    with migrated_engine.connect() as conn:
        plano = conn.execute(stmt).fetchall()
    detalhe = " ".join(row[3] for row in plano)
    assert "SEARCH" in detalhe
    assert "ix_media_files_pasta" in detalhe
    assert "SCAN media_files" not in detalhe


@pytest.mark.parametrize("nome_indice", INDICES_ESPERADOS)
def test_indices_declarados_existem_no_schema(migrated_engine, nome_indice):
    """Os 13 índices (9 novos + 4 de drift) existem num catálogo migrado do
    zero — schema só nasce de `upgrade_to_head()`, nunca `create_all()`."""
    with migrated_engine.connect() as conn:
        nomes = {
            linha[0]
            for linha in conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='index'")
            )
        }
    assert nome_indice in nomes


def test_busca_textual_continua_insensivel_a_maiusculas(catalogo_com_pastas):
    """Guarda permanente (T-05-02): `PRAGMA case_sensitive_like=ON` da Task 3
    não pode afetar `.ilike()`, que no SQLite compila para
    `lower(x) LIKE lower(y)` — independente do PRAGMA. `PRAIA.JPG` gravado
    em caixa alta continua achável buscando em minúsculas."""
    repo, _ = catalogo_com_pastas
    achados = repo.listar(MediaFilters(busca="prai"), limit=10, offset=0)
    assert "PRAIA.JPG" in {m.nome for m in achados}


def test_prefixo_de_pasta_nao_vaza_pasta_irma(catalogo_com_pastas):
    """`/fotos/a` devolve ele mesmo e `/fotos/a/sub`, nunca `/fotos/ab` —
    a barra explícita no segundo termo de `_sob_a_pasta` é o que evita a
    pasta irmã de nome parecido colar no prefixo."""
    repo, _ = catalogo_com_pastas
    achados = repo.listar(MediaFilters(pasta="/fotos/a"), limit=10, offset=0)
    pastas = {m.pasta for m in achados}
    assert pastas == {"/fotos/a", "/fotos/a/sub"}
