from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone

from app.elexon.models import ForecastPoint


@dataclass(frozen=True)
class DecisionForecast:
    decision_date: date
    delivery_date: date
    cutoff: datetime
    publish_time: datetime | None
    points: list[ForecastPoint]


@dataclass(frozen=True)
class ForecastRun:
    publish_time: datetime
    points: list[ForecastPoint]


def runs_for_delivery(forecasts: list[ForecastPoint], delivery_date: date, lookback_days: int = 2) -> list[ForecastRun]:
    """Every run published in the `lookback_days` before delivery starts, clipped to the delivery date."""
    day_start, day_end = delivery_window(delivery_date)
    earliest = day_start - timedelta(days=lookback_days)
    by_run: dict[datetime, list[ForecastPoint]] = {}
    for p in forecasts:
        if earliest <= p.publish_time < day_start and day_start <= p.start_time < day_end:
            by_run.setdefault(p.publish_time, []).append(p)
    return [
        ForecastRun(published, sorted(points, key=lambda p: p.start_time))
        for published, points in sorted(by_run.items())
    ]


def decision_cutoff(decision_date: date, cutoff: time) -> datetime:
    return datetime.combine(decision_date, cutoff, timezone.utc)


def delivery_window(delivery_date: date) -> tuple[datetime, datetime]:
    start = datetime.combine(delivery_date, time(0, 0), timezone.utc)
    return start, start + timedelta(days=1)


def select_decision_forecast(
    forecasts: list[ForecastPoint], decision_date: date, cutoff: time
) -> DecisionForecast:
    """Pick the most recent forecast run a buyer could actually have seen at the cutoff.

    Runs published after the cutoff are excluded even if they're more accurate —
    using them would overstate the accuracy available at decision time.
    """
    delivery_date = decision_date + timedelta(days=1)
    cutoff_at = decision_cutoff(decision_date, cutoff)
    day_start, day_end = delivery_window(delivery_date)
    eligible = [
        p for p in forecasts
        if p.publish_time <= cutoff_at and day_start <= p.start_time < day_end
    ]
    if not eligible:
        return DecisionForecast(decision_date, delivery_date, cutoff_at, None, [])
    latest = max(p.publish_time for p in eligible)
    points = sorted((p for p in eligible if p.publish_time == latest), key=lambda p: p.start_time)
    return DecisionForecast(decision_date, delivery_date, cutoff_at, latest, points)
