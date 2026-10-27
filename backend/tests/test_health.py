from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.main import app, warm_cache


def test_health_returns_ok():
    response = TestClient(app).get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_warm_cache_Should_LoadBothDatasets():
    repo = MagicMock()

    warm_cache(repo)

    repo.both.assert_called_once()


def test_warm_cache_Should_NotRaise_When_FetchFails():
    repo = MagicMock()
    repo.both.side_effect = RuntimeError("elexon down")

    warm_cache(repo)  # must not raise
