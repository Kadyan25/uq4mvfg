from datetime import date, datetime, timezone
from unittest.mock import MagicMock

from app.config import Settings
from app.elexon.repository import WindDataRepository


def make_settings(ttl: int = 100) -> Settings:
    return Settings(elexon_base_url="x", http_timeout_s=1, cache_ttl_s=ttl)


def test_actuals_Should_RequestDeliveryDaysForWholeDecisionWindow():
    client = MagicMock()
    client.fetch_wind_actuals.return_value = []

    WindDataRepository(client, make_settings()).actuals()

    client.fetch_wind_actuals.assert_called_once_with(date(2026, 1, 2), date(2026, 2, 1))


def test_forecasts_Should_RequestRunsFromDayBeforeFirstDecision():
    client = MagicMock()
    client.fetch_wind_forecasts.return_value = []

    WindDataRepository(client, make_settings()).forecasts()

    client.fetch_wind_forecasts.assert_called_once_with(
        datetime(2025, 12, 31, tzinfo=timezone.utc), datetime(2026, 2, 1, tzinfo=timezone.utc)
    )


def test_actuals_Should_ServeFromCache_When_WithinTtl():
    client = MagicMock()
    client.fetch_wind_actuals.return_value = ["a"]
    now = [0.0]
    repo = WindDataRepository(client, make_settings(ttl=100), clock=lambda: now[0])

    repo.actuals()
    now[0] = 99
    result = repo.actuals()

    assert result == ["a"]
    assert client.fetch_wind_actuals.call_count == 1


def test_actuals_Should_Refetch_When_TtlExpired():
    client = MagicMock()
    client.fetch_wind_actuals.side_effect = [["old"], ["new"]]
    now = [0.0]
    repo = WindDataRepository(client, make_settings(ttl=100), clock=lambda: now[0])

    repo.actuals()
    now[0] = 100
    assert repo.actuals() == ["new"]


def test_actuals_Should_NotCacheFailure_When_FetchRaises():
    client = MagicMock()
    client.fetch_wind_actuals.side_effect = [RuntimeError("down"), ["ok"]]
    repo = WindDataRepository(client, make_settings())

    try:
        repo.actuals()
    except RuntimeError:
        pass
    assert repo.actuals() == ["ok"]
