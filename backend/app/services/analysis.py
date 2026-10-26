from dataclasses import dataclass
from datetime import date, datetime, time

from app.elexon.models import ActualPoint, ForecastPoint
from app.services.align import HourlyComparison, compare
from app.services.forecast import DecisionForecast, delivery_window, select_decision_forecast
from app.services.metrics import ErrorMetrics, compute_metrics, error_percentiles, mae_by_hour


@dataclass(frozen=True)
class DayAnalysis:
    decision: DecisionForecast
    actuals: list[ActualPoint]
    hourly: list[HourlyComparison]
    metrics: ErrorMetrics | None


@dataclass(frozen=True)
class DaySummary:
    decision_date: date
    delivery_date: date
    publish_time: datetime | None
    metrics: ErrorMetrics | None


@dataclass(frozen=True)
class PeriodSummary:
    days: list[DaySummary]
    overall: ErrorMetrics | None
    percentiles: dict[float, float]
    mae_by_hour: dict[int, float]


def analyse_day(
    forecasts: list[ForecastPoint], actuals: list[ActualPoint], decision_date: date, cutoff: time
) -> DayAnalysis:
    decision = select_decision_forecast(forecasts, decision_date, cutoff)
    start, end = delivery_window(decision.delivery_date)
    day_actuals = [a for a in actuals if start <= a.start_time < end]
    hourly = compare(decision.points, day_actuals)
    return DayAnalysis(decision, day_actuals, hourly, compute_metrics(hourly))


def analyse_period(
    forecasts: list[ForecastPoint], actuals: list[ActualPoint], decision_dates: list[date], cutoff: time
) -> PeriodSummary:
    days: list[DaySummary] = []
    all_hours: list[HourlyComparison] = []
    for decision_date in decision_dates:
        day = analyse_day(forecasts, actuals, decision_date, cutoff)
        days.append(DaySummary(decision_date, day.decision.delivery_date, day.decision.publish_time, day.metrics))
        all_hours.extend(day.hourly)
    return PeriodSummary(days, compute_metrics(all_hours), error_percentiles(all_hours), mae_by_hour(all_hours))
