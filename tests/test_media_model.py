from datetime import datetime, timedelta

import pytest
from PySide6.QtCore import Qt

from fotoorganizer.database import create_session_factory
from fotoorganizer.models import MediaFile, Source
from fotoorganizer.repositories import MediaFilters, MediaRepository
from fotoorganizer.thumbnails import ThumbnailCache
from fotoorganizer.ui.media_model import PAGE_SIZE, MediaListModel
from fotoorganizer.workers import ThumbnailService
from tests.fixtures import make_jpeg

TOTAL = 600  # > 2 páginas


@pytest.fixture()
def ambiente(migrated_engine, tmp_path, qtbot):
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        fonte = Source(caminho=str(tmp_path))
        session.add(fonte)
        session.flush()
        base = datetime(2024, 1, 1)
        for i in range(TOTAL):
            session.add(
                MediaFile(
                    source_id=fonte.id, caminho=f"{tmp_path}/img_{i:04d}.jpg",
                    pasta=str(tmp_path), nome=f"img_{i:04d}.jpg", extensao="jpg",
                    tamanho=1000 + i, data_capturada=base + timedelta(minutes=i),
                    hash_rapido=f"xxh3:{i:016x}",
                )
            )
        session.commit()

    repo = MediaRepository(factory)
    service = ThumbnailService(ThumbnailCache(tmp_path / "cache"), workers=1)
    model = MediaListModel(repo, service)
    return model, repo, service, factory


def test_carregamento_e_paginado(ambiente):
    model, *_ = ambiente
    model.set_filters(MediaFilters())

    # Nada carregado até a view pedir — memória proporcional ao visível.
    assert model.total == TOTAL
    assert model.rowCount() == 0
    assert model.canFetchMore()

    model.fetchMore()
    assert model.rowCount() == PAGE_SIZE

    while model.canFetchMore():
        model.fetchMore()
    assert model.rowCount() == TOTAL
    assert not model.canFetchMore()


def test_dados_das_celulas(ambiente):
    model, *_ = ambiente
    model.set_filters(MediaFilters())
    model.fetchMore()
    # Ordenação padrão: mais recentes primeiro.
    index = model.index(0)
    assert model.data(index, Qt.ItemDataRole.DisplayRole) == f"img_{TOTAL-1:04d}.jpg"
    assert "img_" in model.data(index, Qt.ItemDataRole.ToolTipRole)


def test_reset_com_filtro(ambiente):
    model, *_ = ambiente
    model.set_filters(MediaFilters(busca="img_0001"))
    assert model.total == 1
    model.fetchMore()
    assert model.rowCount() == 1


def test_miniatura_assincrona(ambiente, tmp_path, qtbot):
    model, repo, service, factory = ambiente
    # Dá um arquivo real à primeira foto do modelo (as demais não existem).
    make_jpeg(tmp_path / f"img_{TOTAL-1:04d}.jpg", size=(640, 480))

    model.set_filters(MediaFilters())
    model.fetchMore()
    index = model.index(0)

    # Primeiro acesso: placeholder na hora + geração agendada.
    placeholder = model.data(index, Qt.ItemDataRole.DecorationRole)
    assert placeholder.width() == 1

    with qtbot.waitSignal(service.pronta, timeout=5000):
        pass
    pronto = model.data(index, Qt.ItemDataRole.DecorationRole)
    assert pronto.width() > 1  # miniatura real, não placeholder
