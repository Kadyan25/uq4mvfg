from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from app.elexon.models import ActualPoint, ForecastPoint
from app.services.align import HourlyComparison, compare
from app.services.forecast import DecisionForecast, delivery_window, select_decision_forecast
from app.services.metrics import ErrorMetrics, LevelBucket, compute_metrics, error_by_forecast_level, error_percentiles
from app.services.planning import PlanningEstimate, build_plan, plan_comparisons, plan_metrics, range_hits


@dataclass(frozen=True)
class PlanningConfig:
    first_decision_date: date
    min_history_days: int


@dataclass(frozen=True)
class DayAnalysis:
    decision: DecisionForecast
    actuals: list[ActualPoint]
    hourly: list[HourlyComparison]
    metrics: ErrorMetrics | None
    history_days: int
    plan: PlanningEstimate | None
    plan_metrics: ErrorMetrics | None


@dataclass(frozen=True)
class DaySummary:
    decision_date: date
    delivery_date: date
    publish_time: datetime | None
    metrics: ErrorMetrics | None
    plan_metrics: ErrorMetrics | None


@dataclass(frozen=True)
class PeriodSummary:
    days: list[DaySummary]
    overall: ErrorMetrics | None
    percentiles: dict[float, float]
    by_forecast_level: list[LevelBucket]
    plan_overall: ErrorMetrics | None
    # Forecast scored on exactly the hours that had a plan, so the two are directly comparable.
    plan_baseline: ErrorMetrics | None
    plan_range_hit_pct: float | None


@dataclass(frozen=True)
class _DecisionDay:
    decision: DecisionForecast
    actuals: list[ActualPoint]
    hourly: list[HourlyComparison]


def _decision_day(forecasts: list[ForecastPoint], actuals: list[ActualPoint], decision_date: date, cutoff: time) -> _DecisionDay:
    decision = select_decision_forecast(forecasts, decision_date, cutoff)
    start, end = delivery_window(decision.delivery_date)
    day_actuals = [a for a in actuals if start <= a.start_time < end]
    return _DecisionDay(decision, day_actuals, compare(decision.points, day_actuals))


def _learnable(days: dict[date, _DecisionDay], decision_date: date) -> list[_DecisionDay]:
    # At the cutoff on decision date X, only delivery dates before X are fully measured.
    return [d for d in days.values() if d.decision.delivery_date < decision_date and d.hourly]


def _plan_for(day: _DecisionDay, history: list[_DecisionDay], config: PlanningConfig) -> PlanningEstimate | None:
    rows = [h for d in history for h in d.hourly]
    return build_plan(day.decision.points, rows, len(history), config.min_history_days)


def analyse_day(
    forecasts: list[ForecastPoint], actuals: list[ActualPoint], decision_date: date, cutoff: time,
    config: PlanningConfig,
) -> DayAnalysis:
    span = (decision_date - config.first_decision_date).days
    history_dates = [config.first_decision_date + timedelta(days=i) for i in range(max(span, 0))]
    history = {d: _decision_day(forecasts, actuals, d, cutoff) for d in history_dates}
    day = _decision_day(forecasts, actuals, decision_date, cutoff)
    learnable = _learnable(history, decision_date)
    plan = _plan_for(day, learnable, config)
    return DayAnalysis(day.decision, day.actuals, day.hourly, compute_metrics(day.hourly), len(learnable), plan,
                       plan_metrics(plan, day.hourly))


def analyse_period(
    forecasts: list[ForecastPoint], actuals: list[ActualPoint], decision_dates: list[date], cutoff: time,
    config: PlanningConfig,
) -> PeriodSummary:
    days = {d: _decision_day(forecasts, actuals, d, cutoff) for d in decision_dates}
    summaries: list[DaySummary] = []
    all_hours: list[HourlyComparison] = []
    plan_hours: list[HourlyComparison] = []
    baseline_hours: list[HourlyComparison] = []
    hits = checked = 0
    for decision_date, day in days.items():
        plan = _plan_for(day, _learnable(days, decision_date), config)
        summaries.append(DaySummary(decision_date, day.decision.delivery_date, day.decision.publish_time,
                                    compute_metrics(day.hourly), plan_metrics(plan, day.hourly)))
        all_hours.extend(day.hourly)
        if plan:
            plan_hours.extend(plan_comparisons(plan, day.hourly))
            baseline_hours.extend(day.hourly)
            day_hits, day_checked = range_hits(plan, day.hourly)
            hits, checked = hits + day_hits, checked + day_checked
    return PeriodSummary(
        summaries, compute_metrics(all_hours), error_percentiles(all_hours), error_by_forecast_level(all_hours),
        compute_metrics(plan_hours), compute_metrics(baseline_hours), (hits / checked * 100) if checked else None,
    )
