from datetime import date, datetime, timezone
from unittest.mock import MagicMock

import pytest

from app.config import Settings
from app.elexon.models import ActualPoint
from app.elexon.repository import WindDataRepository
from app.elexon.store import Snapshot, encode_actuals

POINT = ActualPoint(datetime(2026, 1, 2, tzinfo=timezone.utc), 1000.0)


def make_settings(ttl: int = 100) -> Settings:
    return Settings(elexon_base_url="x", http_timeout_s=1, cache_ttl_s=ttl, database_url=None)


class MemoryStore:
    def __init__(self, snapshots: dict[str, Snapshot] | None = None, fail: bool = False):
        self.snapshots = snapshots or {}
        self.fail = fail
        self.saved: list[str] = []

    def load(self, key):
        if self.fail:
            raise RuntimeError("db down")
        return self.snapshots.get(key)

    def save(self, key, snapshot):
        if self.fail:
            raise RuntimeError("db down")
        self.saved.append(key)
        self.snapshots[key] = snapshot


class Clock:
    def __init__(self, now: float = 1000.0):
        self.now = now

    def __call__(self) -> float:
        return self.now


def make_repo(client, store=None, ttl=100, clock=None, background=None):
    deferred: list = []
    run = background if background is not None else deferred.append
    repo = WindDataRepository(client, make_settings(ttl), store, clock or Clock(), run)
    return repo, deferred


def test_actuals_Should_RequestDeliveryDaysForWholeDecisionWindow():
    client = MagicMock()
    client.fetch_wind_actuals.return_value = []

    make_repo(client)[0].actuals()

    client.fetch_wind_actuals.assert_called_once_with(date(2026, 1, 2), date(2026, 2, 1))


def test_forecasts_Should_RequestRunsFromDayBeforeFirstDecision():
    client = MagicMock()
    client.fetch_wind_forecasts.return_value = []

    make_repo(client)[0].forecasts()

    client.fetch_wind_forecasts.assert_called_once_with(
        datetime(2025, 12, 31, tzinfo=timezone.utc), datetime(2026, 2, 1, tzinfo=timezone.utc)
    )


def test_actuals_Should_ServeFromMemory_When_WithinTtl():
    client = MagicMock()
    client.fetch_wind_actuals.return_value = [POINT]
    clock = Clock()
    repo, deferred = make_repo(client, clock=clock)

    repo.actuals()
    clock.now += 99
    assert repo.actuals() == [POINT]

    assert client.fetch_wind_actuals.call_count == 1
    assert deferred == []


def test_actuals_Should_ServeStaleImmediatelyAndRefreshInBackground_When_TtlExpired():
    client = MagicMock()
    client.fetch_wind_actuals.side_effect = [["old"], ["new"]]
    clock = Clock()
    repo, deferred = make_repo(client, clock=clock)

    repo.actuals()
    clock.now += 100
    assert repo.actuals() == ["old"]  # no waiting on Elexon
    assert len(deferred) == 1

    deferred[0]()
    assert repo.actuals() == ["new"]


def test_refresh_Should_BeScheduledOnce_When_ManyRequestsSeeStaleData():
    client = MagicMock()
    client.fetch_wind_actuals.return_value = ["x"]
    clock = Clock()
    repo, deferred = make_repo(client, clock=clock)

    repo.actuals()
    clock.now += 500
    repo.actuals()
    repo.actuals()

    assert len(deferred) == 1


def test_refresh_Should_KeepServingOldData_When_ElexonFails():
    client = MagicMock()
    client.fetch_wind_actuals.side_effect = [["old"], RuntimeError("elexon down"), ["new"]]
    clock = Clock()
    repo, deferred = make_repo(client, clock=clock)

    repo.actuals()
    clock.now += 100
    repo.actuals()
    deferred.pop()()  # fails, logged

    assert repo.actuals() == ["old"]
    assert len(deferred) == 1  # a new refresh can be scheduled after the failure


def test_actuals_Should_NotCacheFailure_When_ColdFetchRaises():
    client = MagicMock()
    client.fetch_wind_actuals.side_effect = [RuntimeError("down"), ["ok"]]
    repo, _ = make_repo(client)

    with pytest.raises(RuntimeError):
        repo.actuals()
    assert repo.actuals() == ["ok"]


def test_cold_load_Should_UseStoredSnapshot_InsteadOfElexon():
    client = MagicMock()
    store = MemoryStore({"actuals": Snapshot(990.0, encode_actuals([POINT]))})
    repo, deferred = make_repo(client, store=store, clock=Clock(1000.0))

    assert repo.actuals() == [POINT]
    client.fetch_wind_actuals.assert_not_called()
    assert deferred == []


def test_cold_load_Should_RefreshInBackground_When_StoredSnapshotIsStale():
    client = MagicMock()
    fresh = ActualPoint(POINT.start_time, 2000.0)
    client.fetch_wind_actuals.return_value = [fresh]
    store = MemoryStore({"actuals": Snapshot(0.0, encode_actuals([POINT]))})
    repo, deferred = make_repo(client, store=store, clock=Clock(1000.0))

    assert repo.actuals() == [POINT]
    deferred[0]()

    assert repo.actuals() == [fresh]
    assert store.saved == ["actuals"]


def test_cold_fetch_Should_SaveSnapshotToStore():
    client = MagicMock()
    client.fetch_wind_actuals.return_value = [POINT]
    store = MemoryStore()

    make_repo(client, store=store)[0].actuals()

    assert store.saved == ["actuals"]
    assert store.snapshots["actuals"].fetched_at == 1000.0


def test_store_failures_Should_FallBackToElexon():
    client = MagicMock()
    client.fetch_wind_actuals.return_value = [POINT]

    repo, _ = make_repo(client, store=MemoryStore(fail=True))

    assert repo.actuals() == [POINT]


def test_both_Should_ReturnForecastsAndActuals():
    client = MagicMock()
    client.fetch_wind_forecasts.return_value = ["f"]
    client.fetch_wind_actuals.return_value = ["a"]

    assert make_repo(client)[0].both() == (["f"], ["a"])
