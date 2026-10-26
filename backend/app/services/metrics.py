import math
from collections import defaultdict
from dataclasses import dataclass

from app.services.align import HourlyComparison


@dataclass(frozen=True)
class ErrorMetrics:
    count: int
    mae_mw: float
    rmse_mw: float
    bias_mw: float
    # Weighted absolute % error. Used instead of MAPE, which explodes in low-wind hours.
    wape_pct: float | None


def compute_metrics(rows: list[HourlyComparison]) -> ErrorMetrics | None:
    if not rows:
        return None
    errors = [r.error_mw for r in rows]
    n = len(errors)
    total_actual = sum(r.actual_mw for r in rows)
    abs_sum = sum(abs(e) for e in errors)
    return ErrorMetrics(
        count=n,
        mae_mw=abs_sum / n,
        rmse_mw=math.sqrt(sum(e * e for e in errors) / n),
        bias_mw=sum(errors) / n,
        wape_pct=(abs_sum / total_actual * 100) if total_actual > 0 else None,
    )


def percentile(values: list[float], pct: float) -> float:
    """Linear-interpolated percentile (same as numpy's default)."""
    if not values:
        raise ValueError("percentile of empty list")
    if not 0 <= pct <= 100:
        raise ValueError("pct must be within 0..100")
    ordered = sorted(values)
    rank = (len(ordered) - 1) * pct / 100
    low = math.floor(rank)
    high = math.ceil(rank)
    return ordered[low] + (ordered[high] - ordered[low]) * (rank - low)


def error_percentiles(rows: list[HourlyComparison], pcts: tuple[float, ...] = (10, 50, 90)) -> dict[float, float]:
    errors = [r.error_mw for r in rows]
    if not errors:
        return {}
    return {p: percentile(errors, p) for p in pcts}


def mae_by_hour(rows: list[HourlyComparison]) -> dict[int, float]:
    buckets: dict[int, list[float]] = defaultdict(list)
    for r in rows:
        buckets[r.start_time.hour].append(abs(r.error_mw))
    return {hour: sum(v) / len(v) for hour, v in sorted(buckets.items())}
