from datetime import date, time, timedelta

import pytest

from app.elexon.models import ForecastPoint
from app.services.align import HourlyComparison
from app.services.analysis import PlanningConfig, analyse_day, analyse_period
from app.services.planning import build_plan, plan_metrics, range_hits
from tests.factories import actual_day, run, utc

CUTOFF = time(9, 20)


def errors_history(errors: list[float]) -> list[HourlyComparison]:
    return [HourlyComparison(utc(2026, 1, 10, i % 24), 1000 + e, 1000) for i, e in enumerate(errors)]


def forecast(mw: list[float]) -> list[ForecastPoint]:
    return [ForecastPoint(utc(2026, 1, 14, 7, 30), utc(2026, 1, 15, h), v) for h, v in enumerate(mw)]


def test_build_plan_Should_ShiftForecastByMedianErrorAndBracketWithP10P90():
    history = errors_history([-200, -100, 0, 100, 200, 300, 400, 500, 600, 700, 800])

    plan = build_plan(forecast([5000]), history, history_days=3, min_history_days=3)

    assert (plan.p10_mw, plan.p50_mw, plan.p90_mw) == (pytest.approx(-100), pytest.approx(300), pytest.approx(700))
    hour = plan.hours[0]
    assert hour.plan_mw == pytest.approx(4700)
    assert hour.low_mw == pytest.approx(4300)
    assert hour.high_mw == pytest.approx(5100)


def test_build_plan_Should_ReturnNone_When_TooFewHistoryDays():
    assert build_plan(forecast([5000]), errors_history([100]), history_days=2, min_history_days=3) is None


def test_build_plan_Should_ReturnNone_When_NoHistoryOrNoForecast():
    assert build_plan(forecast([5000]), [], history_days=5, min_history_days=3) is None
    assert build_plan([], errors_history([100]), history_days=5, min_history_days=3) is None


def test_build_plan_Should_ClampAtZero_When_AdjustmentExceedsForecast():
    plan = build_plan(forecast([300]), errors_history([1000, 1000, 1000]), history_days=3, min_history_days=3)

    assert (plan.hours[0].plan_mw, plan.hours[0].low_mw, plan.hours[0].high_mw) == (0, 0, 0)


def test_build_plan_Should_WidenUpwards_When_PastErrorsNegative():
    plan = build_plan(forecast([5000]), errors_history([-500, -500, -500]), history_days=3, min_history_days=3)

    assert plan.hours[0].plan_mw == pytest.approx(5500)


def test_plan_metrics_and_range_hits_Should_ScorePlanAgainstOutturn():
    plan = build_plan(forecast([5000, 5000]), errors_history([0, 200, 400]), history_days=3, min_history_days=3)
    outturn = [HourlyComparison(utc(2026, 1, 15, 0), 5000, 4800), HourlyComparison(utc(2026, 1, 15, 1), 5000, 3000)]

    metrics = plan_metrics(plan, outturn)

    assert metrics.mae_mw == pytest.approx((0 + 1800) / 2)
    assert range_hits(plan, outturn) == (1, 2)
    assert plan_metrics(None, outturn) is None


def history_scenario(polluted_mw: float):
    """Decisions 10–13 Jan with +100 MW error; delivery date 14 Jan carries `polluted_mw` error."""
    forecasts, actuals = [], []
    for offset in range(5):
        decision = date(2026, 1, 10) + timedelta(days=offset)
        delivery = decision + timedelta(days=1)
        error = polluted_mw if delivery == date(2026, 1, 14) else 100
        forecasts += run(utc(decision.year, decision.month, decision.day, 7, 30),
                         (delivery.year, delivery.month, delivery.day), mw=1000 + error)
        actuals += actual_day((delivery.year, delivery.month, delivery.day), mw=1000)
    return forecasts, actuals


def test_analyse_day_Should_NotLearnFromDeliveryDateStillInProgress():
    # Deciding on 14 Jan at 09:20: delivery date 14 Jan is under way, so its outturn must not be used.
    forecasts, actuals = history_scenario(polluted_mw=5000)
    config = PlanningConfig(first_decision_date=date(2026, 1, 10), min_history_days=3)

    result = analyse_day(forecasts, actuals, date(2026, 1, 14), CUTOFF, config)

    assert result.history_days == 3
    assert result.plan.p50_mw == pytest.approx(100)
    assert result.plan.hours[0].plan_mw == pytest.approx(result.decision.points[0].generation_mw - 100)


def test_analyse_day_Should_SkipPlan_When_HistoryBelowMinimum():
    forecasts, actuals = history_scenario(polluted_mw=100)
    config = PlanningConfig(first_decision_date=date(2026, 1, 10), min_history_days=3)

    result = analyse_day(forecasts, actuals, date(2026, 1, 12), CUTOFF, config)

    assert result.history_days == 1
    assert result.plan is None
    assert result.plan_metrics is None


def test_analyse_period_Should_ScorePlanOnlyForDaysWithEnoughHistory():
    forecasts, actuals = history_scenario(polluted_mw=100)
    config = PlanningConfig(first_decision_date=date(2026, 1, 10), min_history_days=3)
    dates = [date(2026, 1, 10) + timedelta(days=i) for i in range(5)]

    result = analyse_period(forecasts, actuals, dates, CUTOFF, config)

    with_plan = [d.decision_date for d in result.days if d.plan_metrics]
    assert with_plan == [date(2026, 1, 14)]
    assert result.plan_overall.mae_mw == pytest.approx(0)
    assert result.plan_range_hit_pct == pytest.approx(100)
    assert result.overall.mae_mw == pytest.approx(100)
