from datetime import datetime

import pytest
from sqlalchemy import select

from fotoorganizer.database import create_session_factory
from fotoorganizer.models import (
    ConfidenceLevel,
    MediaFile,
    Source,
    Suggestion,
    SuggestionStatus,
)
from fotoorganizer.repositories import SuggestionFilters, SuggestionRepository


@pytest.fixture()
def repo(migrated_engine):
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        fonte = Source(caminho="/fotos")
        session.add(fonte)
        session.flush()
        niveis = [ConfidenceLevel.ALTA, ConfidenceLevel.ALTA,
                  ConfidenceLevel.MEDIA, ConfidenceLevel.BAIXA]
        for i, nivel in enumerate(niveis):
            media = MediaFile(
                source_id=fonte.id, caminho=f"/fotos/f{i}.jpg", pasta="/fotos",
                nome=f"f{i}.jpg", extensao="jpg", tamanho=1,
                data_capturada=datetime(2024, 1, 1 + i),
            )
            session.add(media)
            session.flush()
            session.add(Suggestion(
                media_id=media.id, destino_sugerido=f"Destino/{i}",
                template="t", nivel=nivel, versao_logica="test",
            ))
        session.commit()
    return SuggestionRepository(factory)


def test_listar_e_contar_pendentes(repo):
    filtros = SuggestionFilters()
    assert repo.contar(filtros) == 4
    linhas = repo.listar(filtros, limit=10, offset=0)
    assert len(linhas) == 4
    assert all(l.status == SuggestionStatus.PENDENTE for l in linhas)


def test_filtro_por_confianca(repo):
    assert repo.contar(SuggestionFilters(nivel=ConfidenceLevel.ALTA)) == 2
    assert repo.contar(SuggestionFilters(nivel=ConfidenceLevel.BAIXA)) == 1


def test_aprovar_em_lote_e_desfazer(repo):
    linhas = repo.listar(SuggestionFilters(), 10, 0)
    ids = [l.id for l in linhas[:2]]

    assert repo.aprovar(ids) == 2
    assert repo.contar(SuggestionFilters()) == 2  # pendentes restantes
    assert repo.contar(SuggestionFilters(status=SuggestionStatus.APROVADA)) == 2

    assert repo.desfazer(ids) == 2
    assert repo.contar(SuggestionFilters()) == 4


def test_rejeitar(repo):
    linha = repo.listar(SuggestionFilters(), 10, 0)[0]
    repo.rejeitar([linha.id])
    rejeitadas = repo.listar(
        SuggestionFilters(status=SuggestionStatus.REJEITADA), 10, 0
    )
    assert [l.id for l in rejeitadas] == [linha.id]


def test_editar_destino(repo):
    linha = repo.listar(SuggestionFilters(), 10, 0)[0]
    atualizada = repo.editar_destino(linha.id, "Novo/Caminho")
    assert atualizada.destino == "Novo/Caminho"
    assert atualizada.status == SuggestionStatus.EDITADA
    editadas = repo.listar(SuggestionFilters(status=SuggestionStatus.EDITADA), 10, 0)
    assert editadas[0].destino == "Novo/Caminho"


def test_editar_destino_de_sugestao_ja_aprovada(repo):
    """O PySide6 não trava edição por status anterior — o plano só olha o
    destino no momento em que é criado. Manter a mesma semântica: aprovar
    e depois editar substitui o destino e vira EDITADA."""
    linha = repo.listar(SuggestionFilters(), 10, 0)[0]
    repo.aprovar([linha.id])
    atualizada = repo.editar_destino(linha.id, "Outro/Destino")
    assert atualizada.status == SuggestionStatus.EDITADA
    assert atualizada.destino == "Outro/Destino"


def test_editar_destino_inexistente_devolve_none(repo):
    assert repo.editar_destino(99999, "Novo/Caminho") is None


def test_contagens_por_status(repo):
    linhas = repo.listar(SuggestionFilters(), 10, 0)
    repo.aprovar([linhas[0].id])
    repo.rejeitar([linhas[1].id])
    contagens = repo.contagens_por_status()
    assert contagens[SuggestionStatus.PENDENTE] == 2
    assert contagens[SuggestionStatus.APROVADA] == 1
    assert contagens[SuggestionStatus.REJEITADA] == 1


def test_filtro_status_none_lista_todas(repo):
    linhas = repo.listar(SuggestionFilters(), 10, 0)
    repo.aprovar([linhas[0].id])
    assert repo.contar(SuggestionFilters(status=None)) == 4
