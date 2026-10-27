from datetime import date, datetime

from pydantic import BaseModel


class Metrics(BaseModel):
    count: int
    mae_mw: float
    rmse_mw: float
    bias_mw: float
    wape_pct: float | None


class SeriesPoint(BaseModel):
    time: datetime
    mw: float


class HourlyRow(BaseModel):
    time: datetime
    forecast_mw: float
    actual_mw: float
    error_mw: float


class PlanHourRow(BaseModel):
    time: datetime
    plan_mw: float
    low_mw: float
    high_mw: float


class Plan(BaseModel):
    history_days: int
    p10_error_mw: float
    p50_error_mw: float
    p90_error_mw: float
    hours: list[PlanHourRow]


class DayResponse(BaseModel):
    decision_date: date
    delivery_date: date
    cutoff: datetime
    forecast_publish_time: datetime | None
    lead_time_hours: float | None
    forecast: list[SeriesPoint]
    actuals: list[SeriesPoint]
    hourly: list[HourlyRow]
    metrics: Metrics | None
    history_days: int
    plan: Plan | None
    plan_metrics: Metrics | None


class DaySummaryRow(BaseModel):
    decision_date: date
    delivery_date: date
    forecast_publish_time: datetime | None
    metrics: Metrics | None
    plan_metrics: Metrics | None


class Percentiles(BaseModel):
    p10_mw: float
    p50_mw: float
    p90_mw: float


class HourOfDayError(BaseModel):
    hour: int
    mae_mw: float


class SummaryResponse(BaseModel):
    cutoff: str
    days: list[DaySummaryRow]
    overall: Metrics | None
    error_percentiles: Percentiles | None
    mae_by_hour: list[HourOfDayError]
    plan_overall: Metrics | None
    plan_range_hit_pct: float | None


class MetaResponse(BaseModel):
    first_decision_date: date
    last_decision_date: date
    default_cutoff: str
    min_history_days: int
