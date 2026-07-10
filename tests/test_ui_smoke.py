"""Smoke test da UI em plataforma offscreen (sem display)."""


def test_main_window_constroi(qtbot):
    from fotoorganizer.ui.main_window import MainWindow
    from fotoorganizer.ui.theme import QSS

    window = MainWindow()
    qtbot.addWidget(window)
    window.setStyleSheet(QSS)

    assert window.windowTitle() == "Foto Organizer"
    assert window.splitter.count() == 3
    assert window.sidebar.isVisibleTo(window)
    assert window.inspector.isVisibleTo(window)


def test_atalhos_alternam_paineis(qtbot):
    from fotoorganizer.ui.main_window import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)

    window._toggle_sidebar()
    assert not window.sidebar.isVisibleTo(window)
    window._toggle_sidebar()
    assert window.sidebar.isVisibleTo(window)

    window._toggle_inspector()
    assert not window.inspector.isVisibleTo(window)
