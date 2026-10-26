from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime

from app.elexon.models import ActualPoint, ForecastPoint


@dataclass(frozen=True)
class HourlyComparison:
    start_time: datetime
    forecast_mw: float
    actual_mw: float

    @property
    def error_mw(self) -> float:
        # Positive = forecast was too high = less wind than planned for = buy-side shortfall.
        return self.forecast_mw - self.actual_mw


def hourly_actuals(actuals: list[ActualPoint]) -> dict[datetime, float]:
    """Average the two half-hourly settlement periods into the hour WINDFOR forecasts.

    Hours missing either half are dropped rather than guessed, so metrics never
    rest on fabricated actuals.
    """
    halves: dict[datetime, list[float]] = defaultdict(list)
    for point in actuals:
        hour = point.start_time.replace(minute=0, second=0, microsecond=0)
        halves[hour].append(point.generation_mw)
    return {hour: sum(v) / 2 for hour, v in halves.items() if len(v) == 2}


def compare(forecast: list[ForecastPoint], actuals: list[ActualPoint]) -> list[HourlyComparison]:
    by_hour = hourly_actuals(actuals)
    return [
        HourlyComparison(p.start_time, p.generation_mw, by_hour[p.start_time])
        for p in forecast
        if p.start_time in by_hour
    ]
