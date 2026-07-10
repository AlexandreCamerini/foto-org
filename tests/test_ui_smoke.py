"""Smoke tests da janela completa em plataforma offscreen (sem display)."""

import pytest

from fotoorganizer.config.settings import Settings
from fotoorganizer.database import create_session_factory
from tests.fixtures import make_jpeg


@pytest.fixture()
def window(migrated_engine, tmp_path, qtbot):
    from fotoorganizer.ui.main_window import MainWindow
    from fotoorganizer.ui.theme import QSS

    settings = Settings(data_dir=tmp_path / "dados", cache_dir=tmp_path / "cache")
    factory = create_session_factory(migrated_engine)
    win = MainWindow(settings, factory)
    win.setStyleSheet(QSS)
    qtbot.addWidget(win)
    return win


def test_janela_constroi_vazia(window):
    assert window.windowTitle() == "Foto Organizer"
    assert window.splitter.count() == 3
    assert window.model.total == 0


def test_atalhos_alternam_paineis(window):
    window._toggle_sidebar()
    assert not window.sidebar.isVisibleTo(window)
    window._toggle_sidebar()
    assert window.sidebar.isVisibleTo(window)
    window._toggle_inspector()
    assert not window.inspector.isVisibleTo(window)


def _start_scan(window, pasta):
    window._iniciar_scan(pasta)
    return window._scan_worker.terminado


def test_scan_ponta_a_ponta_atualiza_grade(window, tmp_path, qtbot):
    fotos = tmp_path / "biblioteca"
    for i in range(8):
        make_jpeg(fotos / f"img_{i}.jpg", seed=i)

    with qtbot.waitSignal(_start_scan(window, fotos), timeout=15000):
        pass

    assert window.model.total == 8
    window.model.fetchMore()
    assert window.model.rowCount() == 8
    # Sidebar recarregada com a fonte nova.
    assert "8" in window.sidebar._stats.text()


def test_selecao_preenche_inspetor(window, tmp_path, qtbot):
    fotos = tmp_path / "biblioteca"
    make_jpeg(fotos / "unica.jpg", gps=(43.95, 4.81), make="Canon", model="R6")

    with qtbot.waitSignal(_start_scan(window, fotos), timeout=15000):
        pass
    window.model.fetchMore()

    index = window.model.index(0)
    window.grid.setCurrentIndex(index)

    assert window.inspector._nome.text() == "unica.jpg"
    assert "Canon" in window.inspector._camera.text()
    assert "43.95" in window.inspector._gps.text()
