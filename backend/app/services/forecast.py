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
