import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

from app.elexon.models import ActualPoint, ForecastPoint

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Snapshot:
    fetched_at: float  # unix seconds, comparable across processes
    payload: str


class SnapshotStore(Protocol):
    def load(self, key: str) -> Snapshot | None: ...

    def save(self, key: str, snapshot: Snapshot) -> None: ...


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


# Compact row arrays keep a month of forecasts around 1 MB instead of ~3 MB of keyed objects.
def encode_actuals(points: list[ActualPoint]) -> str:
    return json.dumps([[_iso(p.start_time), p.generation_mw] for p in points], separators=(",", ":"))


def decode_actuals(payload: str) -> list[ActualPoint]:
    return [ActualPoint(_parse(t), float(mw)) for t, mw in json.loads(payload)]


def encode_forecasts(points: list[ForecastPoint]) -> str:
    rows = [[_iso(p.publish_time), _iso(p.start_time), p.generation_mw] for p in points]
    return json.dumps(rows, separators=(",", ":"))


def decode_forecasts(payload: str) -> list[ForecastPoint]:
    return [ForecastPoint(_parse(pub), _parse(start), float(mw)) for pub, start, mw in json.loads(payload)]


class PostgresStore:
    """Persists dataset snapshots so a fresh serverless instance skips the slow Elexon fetch."""

    _CREATE = """
        CREATE TABLE IF NOT EXISTS dataset_snapshots (
            key TEXT PRIMARY KEY,
            fetched_at DOUBLE PRECISION NOT NULL,
            payload TEXT NOT NULL
        )
    """

    def __init__(self, database_url: str):
        self._url = database_url
        self._ready = False

    def load(self, key: str) -> Snapshot | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT fetched_at, payload FROM dataset_snapshots WHERE key = %s", (key,)
            ).fetchone()
        return Snapshot(row[0], row[1]) if row else None

    def save(self, key: str, snapshot: Snapshot) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO dataset_snapshots (key, fetched_at, payload) VALUES (%s, %s, %s)
                ON CONFLICT (key) DO UPDATE SET fetched_at = EXCLUDED.fetched_at, payload = EXCLUDED.payload
                """,
                (key, snapshot.fetched_at, snapshot.payload),
            )

    def _connect(self):
        import psycopg  # imported lazily so local runs without a database don't need the driver

        conn = psycopg.connect(self._url, autocommit=True, connect_timeout=5)
        if not self._ready:
            conn.execute(self._CREATE)
            self._ready = True
        return conn
