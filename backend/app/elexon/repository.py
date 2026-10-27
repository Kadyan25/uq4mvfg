import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Generic, TypeVar

from app.config import Settings
from app.elexon.client import ElexonClient
from app.elexon.models import ActualPoint, ForecastPoint
from app.elexon.store import (
    Snapshot,
    SnapshotStore,
    decode_actuals,
    decode_forecasts,
    encode_actuals,
    encode_forecasts,
)

logger = logging.getLogger(__name__)
T = TypeVar("T")


def _in_thread(task: Callable[[], None]) -> None:
    threading.Thread(target=task, daemon=True).start()


@dataclass(frozen=True)
class _Dataset(Generic[T]):
    key: str
    fetch: Callable[[], T]
    encode: Callable[[T], str]
    decode: Callable[[str], T]


class WindDataRepository:
    """Serves the in-scope window from memory, falling back to a persisted snapshot, then Elexon.

    Stale data is returned immediately and refreshed in the background, so after the first
    load no request ever waits on Elexon. January 2026 is historical, so stale data is safe.
    """

    def __init__(
        self,
        client: ElexonClient,
        settings: Settings,
        store: SnapshotStore | None = None,
        clock: Callable[[], float] = time.time,
        run_in_background: Callable[[Callable[[], None]], None] = _in_thread,
    ):
        self._client = client
        self._settings = settings
        self._store = store
        self._clock = clock
        self._background = run_in_background
        self._lock = threading.Lock()
        self._memory: dict[str, tuple[float, object]] = {}
        self._refreshing: set[str] = set()
        self._cold_locks = {"actuals": threading.Lock(), "forecasts": threading.Lock()}

    def actuals(self) -> list[ActualPoint]:
        return self._get(self._actuals_dataset())

    def forecasts(self) -> list[ForecastPoint]:
        return self._get(self._forecasts_dataset())

    def both(self) -> tuple[list[ForecastPoint], list[ActualPoint]]:
        """Load both datasets concurrently; on a cold start this halves the wait."""
        with ThreadPoolExecutor(max_workers=2) as pool:
            forecasts = pool.submit(self.forecasts)
            actuals = pool.submit(self.actuals)
            return forecasts.result(), actuals.result()

    def _actuals_dataset(self) -> _Dataset[list[ActualPoint]]:
        s = self._settings
        fetch = lambda: self._client.fetch_wind_actuals(  # noqa: E731
            s.first_decision_date + timedelta(days=1), s.last_decision_date + timedelta(days=1)
        )
        return _Dataset("actuals", fetch, encode_actuals, decode_actuals)

    def _forecasts_dataset(self) -> _Dataset[list[ForecastPoint]]:
        s = self._settings
        # Any cutoff on the decision day can only see runs published from the day before onwards.
        start = datetime.combine(s.first_decision_date - timedelta(days=1), datetime.min.time(), timezone.utc)
        end = datetime.combine(s.last_decision_date + timedelta(days=1), datetime.min.time(), timezone.utc)
        fetch = lambda: self._client.fetch_wind_forecasts(start, end)  # noqa: E731
        return _Dataset("forecasts", fetch, encode_forecasts, decode_forecasts)

    def _get(self, ds: _Dataset[T]) -> T:
        hit = self._from_memory(ds.key)
        if hit is None:
            # One cold load per dataset at a time, so concurrent requests don't all hit Elexon.
            with self._cold_locks[ds.key]:
                hit = self._from_memory(ds.key) or self._load_cold(ds)
        if self._clock() - hit[0] >= self._settings.cache_ttl_s:
            self._schedule_refresh(ds)
        return hit[1]  # type: ignore[return-value]

    def _from_memory(self, key: str) -> tuple[float, object] | None:
        with self._lock:
            return self._memory.get(key)

    def _load_cold(self, ds: _Dataset[T]) -> tuple[float, object]:
        snapshot = self._read_store(ds.key)
        if snapshot is not None:
            hit: tuple[float, object] = (snapshot.fetched_at, ds.decode(snapshot.payload))
        else:
            hit = self._fetch_and_store(ds)
        with self._lock:
            # Another thread may have loaded meanwhile; keep whichever is newer.
            current = self._memory.get(ds.key)
            if current is None or current[0] < hit[0]:
                self._memory[ds.key] = hit
            return self._memory[ds.key]

    def _fetch_and_store(self, ds: _Dataset[T]) -> tuple[float, object]:
        value = ds.fetch()
        fetched_at = self._clock()
        if self._store is not None:
            self._write_store(ds.key, lambda: Snapshot(fetched_at, ds.encode(value)))
        return fetched_at, value

    def _schedule_refresh(self, ds: _Dataset[T]) -> None:
        with self._lock:
            if ds.key in self._refreshing:
                return
            self._refreshing.add(ds.key)

        def refresh() -> None:
            try:
                hit = self._fetch_and_store(ds)
                with self._lock:
                    self._memory[ds.key] = hit
            except Exception:
                logger.exception("Background refresh of %s failed; serving previous data", ds.key)
            finally:
                with self._lock:
                    self._refreshing.discard(ds.key)

        self._background(refresh)

    def _read_store(self, key: str) -> Snapshot | None:
        if self._store is None:
            return None
        try:
            return self._store.load(key)
        except Exception:
            logger.exception("Snapshot store read failed for %s; falling back to Elexon", key)
            return None

    def _write_store(self, key: str, snapshot: Callable[[], Snapshot]) -> None:
        try:
            self._store.save(key, snapshot())  # type: ignore[union-attr]
        except Exception:
            logger.exception("Snapshot store write failed for %s", key)
