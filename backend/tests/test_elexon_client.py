from datetime import date, datetime, timezone

import httpx
import pytest
import respx

from app.elexon.client import ElexonClient, ElexonError

BASE = "https://elexon.test/api"
FUELHH = f"{BASE}/datasets/FUELHH/stream"
WINDFOR = f"{BASE}/datasets/WINDFOR/stream"


def utc(*args: int) -> datetime:
    return datetime(*args, tzinfo=timezone.utc)


@pytest.fixture
def client() -> ElexonClient:
    return ElexonClient(BASE, timeout_s=5)


@respx.mock
def test_fetch_wind_actuals_Should_SendWindFilterAndParseRows(client):
    route = respx.get(FUELHH).respond(json=[
        {"fuelType": "WIND", "startTime": "2026-01-02T00:30:00Z", "publishTime": "2026-01-02T01:00:00Z", "generation": 1200},
        {"fuelType": "WIND", "startTime": "2026-01-02T00:00:00Z", "publishTime": "2026-01-02T00:30:00Z", "generation": 1000},
    ])

    points = client.fetch_wind_actuals(date(2026, 1, 2), date(2026, 1, 3))

    params = route.calls.last.request.url.params
    assert params["fuelType"] == "WIND"
    assert params["settlementDateFrom"] == "2026-01-02"
    assert params["settlementDateTo"] == "2026-01-03"
    assert [p.start_time for p in points] == [utc(2026, 1, 2, 0, 0), utc(2026, 1, 2, 0, 30)]
    assert [p.generation_mw for p in points] == [1000.0, 1200.0]


@respx.mock
def test_fetch_wind_actuals_Should_DropNonWindRows_When_ServerReturnsOtherFuels(client):
    respx.get(FUELHH).respond(json=[
        {"fuelType": "CCGT", "startTime": "2026-01-02T00:00:00Z", "publishTime": "2026-01-02T00:30:00Z", "generation": 9999},
        {"fuelType": "WIND", "startTime": "2026-01-02T00:00:00Z", "publishTime": "2026-01-02T00:30:00Z", "generation": 1000},
    ])

    points = client.fetch_wind_actuals(date(2026, 1, 2), date(2026, 1, 2))

    assert [p.generation_mw for p in points] == [1000.0]


@respx.mock
def test_fetch_wind_actuals_Should_KeepLatestRevision_When_PeriodRepublished(client):
    respx.get(FUELHH).respond(json=[
        {"fuelType": "WIND", "startTime": "2026-01-02T00:00:00Z", "publishTime": "2026-01-02T05:00:00Z", "generation": 1100},
        {"fuelType": "WIND", "startTime": "2026-01-02T00:00:00Z", "publishTime": "2026-01-02T00:30:00Z", "generation": 1000},
    ])

    points = client.fetch_wind_actuals(date(2026, 1, 2), date(2026, 1, 2))

    assert len(points) == 1
    assert points[0].generation_mw == 1100.0


@respx.mock
def test_fetch_wind_forecasts_Should_SendPublishWindowAndSortByRun(client):
    route = respx.get(WINDFOR).respond(json=[
        {"publishTime": "2026-01-01T09:30:00Z", "startTime": "2026-01-02T00:00:00Z", "generation": 5000},
        {"publishTime": "2026-01-01T07:30:00Z", "startTime": "2026-01-02T01:00:00Z", "generation": 4100},
        {"publishTime": "2026-01-01T07:30:00Z", "startTime": "2026-01-02T00:00:00Z", "generation": 4000},
    ])

    points = client.fetch_wind_forecasts(utc(2025, 12, 31), utc(2026, 1, 2))

    params = route.calls.last.request.url.params
    assert params["publishDateTimeFrom"] == "2025-12-31T00:00:00Z"
    assert params["publishDateTimeTo"] == "2026-01-02T00:00:00Z"
    assert [(p.publish_time.hour, p.start_time.hour) for p in points] == [(7, 0), (7, 1), (9, 0)]


@respx.mock
def test_fetch_wind_forecasts_Should_ReturnEmpty_When_NoRows(client):
    respx.get(WINDFOR).respond(json=[])

    assert client.fetch_wind_forecasts(utc(2026, 1, 1), utc(2026, 1, 2)) == []


@respx.mock
def test_fetch_Should_RaiseElexonError_When_ServerErrors(client):
    respx.get(FUELHH).respond(status_code=503)

    with pytest.raises(ElexonError):
        client.fetch_wind_actuals(date(2026, 1, 2), date(2026, 1, 2))


@respx.mock
def test_fetch_Should_RaiseElexonError_When_NetworkFails(client):
    respx.get(WINDFOR).mock(side_effect=httpx.ConnectError("boom"))

    with pytest.raises(ElexonError):
        client.fetch_wind_forecasts(utc(2026, 1, 1), utc(2026, 1, 2))


@respx.mock
def test_fetch_Should_RaiseElexonError_When_PayloadIsNotAList(client):
    respx.get(WINDFOR).respond(json={"data": []})

    with pytest.raises(ElexonError):
        client.fetch_wind_forecasts(utc(2026, 1, 1), utc(2026, 1, 2))


@respx.mock
def test_fetch_Should_RaiseElexonError_When_RowMissingGeneration(client):
    respx.get(WINDFOR).respond(json=[{"publishTime": "2026-01-01T07:30:00Z", "startTime": "2026-01-02T00:00:00Z"}])

    with pytest.raises(ElexonError):
        client.fetch_wind_forecasts(utc(2026, 1, 1), utc(2026, 1, 2))
