import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Callable, TypeVar

from app.config import Settings
from app.elexon.client import ElexonClient
from app.elexon.models import ActualPoint, ForecastPoint

T = TypeVar("T")


class WindDataRepository:
    """Fetches the full in-scope window once and serves it from memory.

    January 2026 is historical, so the data barely changes; one fetch per TTL keeps
    requests fast and avoids hammering Elexon.
    """

    def __init__(self, client: ElexonClient, settings: Settings, clock: Callable[[], float] = time.monotonic):
        self._client = client
        self._settings = settings
        self._clock = clock
        self._lock = threading.Lock()
        self._cache: dict[str, tuple[float, object]] = {}

    def actuals(self) -> list[ActualPoint]:
        s = self._settings
        return self._cached("actuals", lambda: self._client.fetch_wind_actuals(
            s.first_decision_date + timedelta(days=1),
            s.last_decision_date + timedelta(days=1),
        ))

    def forecasts(self) -> list[ForecastPoint]:
        s = self._settings
        # Any cutoff on the decision day can only see runs published from the day before onwards.
        start = datetime.combine(s.first_decision_date - timedelta(days=1), datetime.min.time(), timezone.utc)
        end = datetime.combine(s.last_decision_date + timedelta(days=1), datetime.min.time(), timezone.utc)
        return self._cached("forecasts", lambda: self._client.fetch_wind_forecasts(start, end))

    def _cached(self, key: str, load: Callable[[], T]) -> T:
        with self._lock:
            hit = self._cache.get(key)
            if hit and self._clock() - hit[0] < self._settings.cache_ttl_s:
                return hit[1]  # type: ignore[return-value]
            value = load()
            self._cache[key] = (self._clock(), value)
            return value
