import os

import pytest

# UI em modo offscreen: testes rodam sem display (CI e sessões headless).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture()
def db_path(tmp_path):
    return tmp_path / "catalog.db"


@pytest.fixture()
def migrated_engine(db_path):
    from fotoorganizer.database import create_db_engine, upgrade_to_head

    upgrade_to_head(db_path)
    engine = create_db_engine(db_path)
    yield engine
    engine.dispose()
