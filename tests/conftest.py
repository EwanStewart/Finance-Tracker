import pytest

from app import main
from app.main import app


@pytest.fixture(autouse=True)
def isolate_app_state(monkeypatch, tmp_path):
    """Keep every test away from the live database.

    A test that forgets to override get_db would otherwise read and write
    the real data/finance.db. Overrides are cleared afterwards so one module
    cannot leak its database into the next.
    """
    monkeypatch.setattr(main, "DEFAULT_DB_PATH", tmp_path / "test.db")
    yield
    app.dependency_overrides.clear()
