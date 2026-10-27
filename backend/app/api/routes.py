import logging
from dataclasses import asdict
from datetime import date, time, timedelta
from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api import schemas
from app.config import Settings, get_settings
from app.elexon.client import ElexonClient, ElexonError
from app.elexon.repository import WindDataRepository
from app.services.analysis import DayAnalysis, PeriodSummary, PlanningConfig, analyse_day, analyse_period
from app.services.forecast import decision_cutoff, runs_for_delivery, select_decision_forecast
from app.services.metrics import ErrorMetrics
from app.services.planning import PlanningEstimate

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

CUTOFF_PATTERN = r"^([01]\d|2[0-3]):[0-5]\d$"
CutoffParam = Annotated[str | None, Query(pattern=CUTOFF_PATTERN, description="HH:MM UTC on the decision day")]


@lru_cache
def get_repository() -> WindDataRepository:
    settings = get_settings()
    return WindDataRepository(ElexonClient(settings.elexon_base_url, settings.http_timeout_s), settings)


Repo = Annotated[WindDataRepository, Depends(get_repository)]
Config = Annotated[Settings, Depends(get_settings)]


@router.get("/meta", response_model=schemas.MetaResponse)
def meta(settings: Config) -> schemas.MetaResponse:
    return schemas.MetaResponse(
        first_decision_date=settings.first_decision_date,
        last_decision_date=settings.last_decision_date,
        default_cutoff=settings.default_cutoff.strftime("%H:%M"),
        min_history_days=settings.min_history_days,
    )


@router.get("/day", response_model=schemas.DayResponse)
def day(decision_date: date, repo: Repo, settings: Config, cutoff: CutoffParam = None) -> schemas.DayResponse:
    _check_in_scope(decision_date, settings)
    cutoff_time = _resolve_cutoff(cutoff, settings)
    forecasts, actuals = _load(repo)
    return _day_response(analyse_day(forecasts, actuals, decision_date, cutoff_time, _planning(settings)))


@router.get("/runs", response_model=schemas.RunsResponse)
def runs(decision_date: date, repo: Repo, settings: Config, cutoff: CutoffParam = None) -> schemas.RunsResponse:
    _check_in_scope(decision_date, settings)
    cutoff_time = _resolve_cutoff(cutoff, settings)
    forecasts, _ = _load(repo)
    cutoff_at = decision_cutoff(decision_date, cutoff_time)
    chosen = select_decision_forecast(forecasts, decision_date, cutoff_time).publish_time
    delivery_date = decision_date + timedelta(days=1)
    return schemas.RunsResponse(
        decision_date=decision_date,
        delivery_date=delivery_date,
        cutoff=cutoff_at,
        runs=[
            schemas.ForecastRunRow(
                publish_time=r.publish_time,
                after_cutoff=r.publish_time > cutoff_at,
                is_decision_run=r.publish_time == chosen,
                points=[schemas.SeriesPoint(time=p.start_time, mw=p.generation_mw) for p in r.points],
            )
            for r in runs_for_delivery(forecasts, delivery_date)
        ],
    )


@router.get("/summary", response_model=schemas.SummaryResponse)
def summary(repo: Repo, settings: Config, cutoff: CutoffParam = None) -> schemas.SummaryResponse:
    cutoff_time = _resolve_cutoff(cutoff, settings)
    span = (settings.last_decision_date - settings.first_decision_date).days
    dates = [settings.first_decision_date + timedelta(days=i) for i in range(span + 1)]
    forecasts, actuals = _load(repo)
    return _summary_response(analyse_period(forecasts, actuals, dates, cutoff_time, _planning(settings)), cutoff_time)


def _check_in_scope(decision_date: date, settings: Settings) -> None:
    if not settings.first_decision_date <= decision_date <= settings.last_decision_date:
        raise HTTPException(422, "decision_date is outside the supported range")


def _planning(settings: Settings) -> PlanningConfig:
    return PlanningConfig(settings.first_decision_date, settings.min_history_days)


def _resolve_cutoff(cutoff: str | None, settings: Settings) -> time:
    return time.fromisoformat(cutoff) if cutoff else settings.default_cutoff


def _load(repo: WindDataRepository):
    try:
        return repo.forecasts(), repo.actuals()
    except ElexonError:
        logger.exception("Elexon fetch failed")
        raise HTTPException(502, "Upstream data source is unavailable, please retry shortly")


def _metrics(m: ErrorMetrics | None) -> schemas.Metrics | None:
    return schemas.Metrics(**asdict(m)) if m else None


def _plan(plan: PlanningEstimate | None) -> schemas.Plan | None:
    if not plan:
        return None
    return schemas.Plan(
        history_days=plan.history_days,
        p10_error_mw=plan.p10_mw,
        p50_error_mw=plan.p50_mw,
        p90_error_mw=plan.p90_mw,
        hours=[schemas.PlanHourRow(time=h.start_time, plan_mw=h.plan_mw, low_mw=h.low_mw, high_mw=h.high_mw)
               for h in plan.hours],
    )


def _day_response(result: DayAnalysis) -> schemas.DayResponse:
    d = result.decision
    lead = None
    if d.publish_time and d.points:
        lead = (d.points[0].start_time - d.publish_time).total_seconds() / 3600
    return schemas.DayResponse(
        decision_date=d.decision_date,
        delivery_date=d.delivery_date,
        cutoff=d.cutoff,
        forecast_publish_time=d.publish_time,
        lead_time_hours=lead,
        forecast=[schemas.SeriesPoint(time=p.start_time, mw=p.generation_mw) for p in d.points],
        actuals=[schemas.SeriesPoint(time=a.start_time, mw=a.generation_mw) for a in result.actuals],
        hourly=[
            schemas.HourlyRow(time=h.start_time, forecast_mw=h.forecast_mw, actual_mw=h.actual_mw, error_mw=h.error_mw)
            for h in result.hourly
        ],
        metrics=_metrics(result.metrics),
        history_days=result.history_days,
        plan=_plan(result.plan),
        plan_metrics=_metrics(result.plan_metrics),
    )


def _summary_response(result: PeriodSummary, cutoff: time) -> schemas.SummaryResponse:
    pct = result.percentiles
    return schemas.SummaryResponse(
        cutoff=cutoff.strftime("%H:%M"),
        days=[
            schemas.DaySummaryRow(
                decision_date=d.decision_date,
                delivery_date=d.delivery_date,
                forecast_publish_time=d.publish_time,
                metrics=_metrics(d.metrics),
                plan_metrics=_metrics(d.plan_metrics),
            )
            for d in result.days
        ],
        overall=_metrics(result.overall),
        error_percentiles=schemas.Percentiles(p10_mw=pct[10], p50_mw=pct[50], p90_mw=pct[90]) if pct else None,
        mae_by_hour=[schemas.HourOfDayError(hour=h, mae_mw=v) for h, v in result.mae_by_hour.items()],
        plan_overall=_metrics(result.plan_overall),
        plan_range_hit_pct=result.plan_range_hit_pct,
    )
