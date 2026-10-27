from dataclasses import dataclass
from datetime import datetime

from app.elexon.models import ForecastPoint
from app.services.align import HourlyComparison
from app.services.metrics import ErrorMetrics, compute_metrics, percentile


@dataclass(frozen=True)
class PlanHour:
    start_time: datetime
    plan_mw: float
    low_mw: float
    high_mw: float


@dataclass(frozen=True)
class PlanningEstimate:
    history_days: int
    # Percentiles of past hourly error (forecast − outturn) used to adjust this forecast.
    p10_mw: float
    p50_mw: float
    p90_mw: float
    hours: list[PlanHour]


def build_plan(
    forecast: list[ForecastPoint], history: list[HourlyComparison], history_days: int, min_history_days: int
) -> PlanningEstimate | None:
    """Shift the forecast by its typical past error and bracket it with the P10–P90 error range.

    `history` must only contain delivery dates that finished before the decision was made;
    the caller owns that rule so this stays a pure transformation.
    """
    if history_days < min_history_days or not history or not forecast:
        return None
    errors = [h.error_mw for h in history]
    p10, p50, p90 = percentile(errors, 10), percentile(errors, 50), percentile(errors, 90)
    # Wind output can't be negative, so clamp the adjusted values at zero.
    hours = [
        PlanHour(
            start_time=p.start_time,
            plan_mw=max(p.generation_mw - p50, 0.0),
            low_mw=max(p.generation_mw - p90, 0.0),
            high_mw=max(p.generation_mw - p10, 0.0),
        )
        for p in forecast
    ]
    return PlanningEstimate(history_days, p10, p50, p90, hours)


def plan_comparisons(plan: PlanningEstimate, outturn: list[HourlyComparison]) -> list[HourlyComparison]:
    """Re-express outturn rows against the plan so the same metrics can score both."""
    by_hour = {h.start_time: h for h in plan.hours}
    return [
        HourlyComparison(o.start_time, by_hour[o.start_time].plan_mw, o.actual_mw)
        for o in outturn
        if o.start_time in by_hour
    ]


def plan_metrics(plan: PlanningEstimate | None, outturn: list[HourlyComparison]) -> ErrorMetrics | None:
    return compute_metrics(plan_comparisons(plan, outturn)) if plan else None


def range_hits(plan: PlanningEstimate, outturn: list[HourlyComparison]) -> tuple[int, int]:
    """(hours where outturn fell inside the P10–P90 range, hours checked)."""
    by_hour = {h.start_time: h for h in plan.hours}
    checked = [(by_hour[o.start_time], o.actual_mw) for o in outturn if o.start_time in by_hour]
    return sum(h.low_mw <= a <= h.high_mw for h, a in checked), len(checked)
