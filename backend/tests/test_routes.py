import pytest
from fastapi.testclient import TestClient

from app.api.routes import get_repository
from app.elexon.client import ElexonError
from app.main import app
from tests.factories import actual_day, run, utc


class FakeRepository:
    def __init__(self, forecasts=None, actuals=None, error: Exception | None = None):
        self._forecasts = forecasts or []
        self._actuals = actuals or []
        self._error = error

    def forecasts(self):
        if self._error:
            raise self._error
        return self._forecasts

    def actuals(self):
        return self._actuals


def sample_repository() -> FakeRepository:
    forecasts = (
        run(utc(2026, 1, 14, 4, 30), (2026, 1, 15), mw=900)
        + run(utc(2026, 1, 14, 7, 30), (2026, 1, 15), mw=1100)
        + run(utc(2026, 1, 14, 9, 30), (2026, 1, 15), mw=5000)
    )
    return FakeRepository(forecasts, actual_day((2026, 1, 15), 1000))


@pytest.fixture
def client():
    app.dependency_overrides[get_repository] = sample_repository
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_meta_Should_ReturnScopeAndDefaultCutoff(client):
    body = client.get("/api/meta").json()

    assert body == {"first_decision_date": "2026-01-01", "last_decision_date": "2026-01-31", "default_cutoff": "09:20", "min_history_days": 3}


def test_day_Should_UseDefaultCutoff_When_NoneGiven(client):
    response = client.get("/api/day", params={"decision_date": "2026-01-14"})

    body = response.json()
    assert response.status_code == 200
    assert body["delivery_date"] == "2026-01-15"
    assert body["cutoff"] == "2026-01-14T09:20:00Z"
    assert body["forecast_publish_time"] == "2026-01-14T07:30:00Z"
    assert body["lead_time_hours"] == pytest.approx(16.5)
    assert len(body["forecast"]) == 24
    assert len(body["actuals"]) == 48
    assert len(body["hourly"]) == 24
    assert body["hourly"][0] == {
        "time": "2026-01-15T00:00:00Z", "forecast_mw": 1100.0, "actual_mw": 1000.0, "error_mw": 100.0,
    }
    assert body["metrics"]["mae_mw"] == pytest.approx(100)
    assert body["history_days"] == 0
    assert body["plan"] is None
    assert body["plan_metrics"] is None


def test_day_Should_PickEarlierRun_When_CutoffMovedEarlier(client):
    body = client.get("/api/day", params={"decision_date": "2026-01-14", "cutoff": "06:00"}).json()

    assert body["forecast_publish_time"] == "2026-01-14T04:30:00Z"
    assert body["metrics"]["bias_mw"] == pytest.approx(-100)


def test_day_Should_ReturnEmptyForecast_When_NoRunBeforeCutoff(client):
    body = client.get("/api/day", params={"decision_date": "2026-01-14", "cutoff": "01:00"}).json()

    assert body["forecast_publish_time"] is None
    assert body["lead_time_hours"] is None
    assert body["forecast"] == []
    assert body["metrics"] is None


@pytest.mark.parametrize("decision_date", ["2025-12-31", "2026-02-01"])
def test_day_Should_Reject_When_DateOutsideScope(client, decision_date):
    response = client.get("/api/day", params={"decision_date": decision_date})

    assert response.status_code == 422


@pytest.mark.parametrize("cutoff", ["24:00", "9:20", "09:60", "abc", "09:20:00"])
def test_day_Should_Reject_When_CutoffMalformed(client, cutoff):
    response = client.get("/api/day", params={"decision_date": "2026-01-14", "cutoff": cutoff})

    assert response.status_code == 422


def test_day_Should_Reject_When_DateMissingOrInvalid(client):
    assert client.get("/api/day").status_code == 422
    assert client.get("/api/day", params={"decision_date": "not-a-date"}).status_code == 422


def test_runs_Should_FlagDecisionRunAndRunsAfterCutoff(client):
    body = client.get("/api/runs", params={"decision_date": "2026-01-14"}).json()

    assert body["delivery_date"] == "2026-01-15"
    assert body["cutoff"] == "2026-01-14T09:20:00Z"
    flags = [(r["publish_time"], r["after_cutoff"], r["is_decision_run"]) for r in body["runs"]]
    assert flags == [
        ("2026-01-14T04:30:00Z", False, False),
        ("2026-01-14T07:30:00Z", False, True),
        ("2026-01-14T09:30:00Z", True, False),
    ]
    assert len(body["runs"][0]["points"]) == 24


def test_runs_Should_Reject_When_DateOutsideScope(client):
    assert client.get("/api/runs", params={"decision_date": "2026-02-01"}).status_code == 422
    assert client.get("/api/runs", params={"decision_date": "2026-01-14", "cutoff": "25:00"}).status_code == 422


def test_summary_Should_CoverEveryDecisionDayInScope(client):
    body = client.get("/api/summary").json()

    assert body["cutoff"] == "09:20"
    assert len(body["days"]) == 31
    assert body["days"][0]["decision_date"] == "2026-01-01"
    assert body["days"][-1]["delivery_date"] == "2026-02-01"
    day14 = next(d for d in body["days"] if d["decision_date"] == "2026-01-14")
    assert day14["metrics"]["mae_mw"] == pytest.approx(100)
    assert body["overall"]["count"] == 24
    assert body["error_percentiles"]["p50_mw"] == pytest.approx(100)
    assert body["by_forecast_level"] == [
        {"low_mw": 0.0, "high_mw": 5000.0, "count": 24, "mae_mw": pytest.approx(100), "bias_mw": pytest.approx(100)}
    ]


def test_summary_Should_ReturnNullAggregates_When_NoData():
    app.dependency_overrides[get_repository] = lambda: FakeRepository()
    try:
        body = TestClient(app).get("/api/summary").json()
    finally:
        app.dependency_overrides.clear()

    assert body["overall"] is None
    assert body["error_percentiles"] is None
    assert body["by_forecast_level"] == []


def test_routes_Should_Return502WithGenericMessage_When_ElexonFails():
    app.dependency_overrides[get_repository] = lambda: FakeRepository(error=ElexonError("secret upstream detail"))
    try:
        response = TestClient(app).get("/api/day", params={"decision_date": "2026-01-14"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    assert "secret" not in response.text
