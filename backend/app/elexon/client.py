from datetime import date, datetime, timezone
from typing import Any

import httpx

from app.elexon.models import ActualPoint, ForecastPoint


class ElexonError(Exception):
    """Raised when Elexon is unreachable or returns data we can't trust."""


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class ElexonClient:
    def __init__(self, base_url: str, timeout_s: float, http: httpx.Client | None = None):
        self._base_url = base_url.rstrip("/")
        self._http = http or httpx.Client(timeout=timeout_s)

    def fetch_wind_actuals(self, settlement_from: date, settlement_to: date) -> list[ActualPoint]:
        rows = self._get_stream("FUELHH", {
            "settlementDateFrom": settlement_from.isoformat(),
            "settlementDateTo": settlement_to.isoformat(),
            "fuelType": "WIND",
        })
        latest: dict[datetime, tuple[datetime, float]] = {}
        for row in rows:
            if row.get("fuelType") != "WIND":
                continue
            start, published, mw = self._parse_row(row)
            # Outturn can be republished; keep the most recent revision per period.
            if start not in latest or published >= latest[start][0]:
                latest[start] = (published, mw)
        return sorted(
            (ActualPoint(start, mw) for start, (_, mw) in latest.items()),
            key=lambda p: p.start_time,
        )

    def fetch_wind_forecasts(self, publish_from: datetime, publish_to: datetime) -> list[ForecastPoint]:
        rows = self._get_stream("WINDFOR", {
            "publishDateTimeFrom": _iso(publish_from),
            "publishDateTimeTo": _iso(publish_to),
        })
        unique: dict[tuple[datetime, datetime], float] = {}
        for row in rows:
            start, published, mw = self._parse_row(row)
            unique[(published, start)] = mw
        return sorted(
            (ForecastPoint(pub, start, mw) for (pub, start), mw in unique.items()),
            key=lambda p: (p.publish_time, p.start_time),
        )

    def _get_stream(self, dataset: str, params: dict[str, str]) -> list[dict[str, Any]]:
        url = f"{self._base_url}/datasets/{dataset}/stream"
        try:
            response = self._http.get(url, params=params)
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ElexonError(f"{dataset} request failed: {exc}") from exc
        if not isinstance(payload, list):
            raise ElexonError(f"{dataset} returned an unexpected payload shape")
        return payload

    @staticmethod
    def _parse_row(row: dict[str, Any]) -> tuple[datetime, datetime, float]:
        try:
            return (
                _parse_time(row["startTime"]),
                _parse_time(row["publishTime"]),
                float(row["generation"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ElexonError(f"malformed row: {row!r}") from exc
