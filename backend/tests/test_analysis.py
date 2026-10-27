from datetime import date, time

import pytest

from app.services.analysis import PlanningConfig, analyse_day, analyse_period
from tests.factories import actual_day, run, utc

CUTOFF = time(9, 20)
# History starts at the day under test, so these tests see no planning history.
NO_HISTORY = PlanningConfig(first_decision_date=date(2026, 1, 14), min_history_days=3)


def test_analyse_day_Should_CompareDecisionForecastAgainstDeliveryDayActuals():
    forecasts = run(utc(2026, 1, 14, 7, 30), (2026, 1, 15), mw=1100)
    actuals = actual_day((2026, 1, 14), 5000) + actual_day((2026, 1, 15), 1000) + actual_day((2026, 1, 16), 5000)

    result = analyse_day(forecasts, actuals, date(2026, 1, 14), CUTOFF, NO_HISTORY)

    assert len(result.actuals) == 48
    assert {a.start_time.date() for a in result.actuals} == {date(2026, 1, 15)}
    assert len(result.hourly) == 24
    assert result.metrics.mae_mw == pytest.approx(100)
    assert result.metrics.bias_mw == pytest.approx(100)


def test_analyse_day_Should_ReturnNoMetrics_When_NoForecastBeforeCutoff():
    forecasts = run(utc(2026, 1, 14, 9, 30), (2026, 1, 15))

    result = analyse_day(forecasts, actual_day((2026, 1, 15)), date(2026, 1, 14), CUTOFF, NO_HISTORY)

    assert result.hourly == []
    assert result.metrics is None
    assert len(result.actuals) == 48


def test_analyse_day_Should_ReturnNoMetrics_When_ActualsMissing():
    forecasts = run(utc(2026, 1, 14, 7, 30), (2026, 1, 15))

    result = analyse_day(forecasts, [], date(2026, 1, 14), CUTOFF, NO_HISTORY)

    assert len(result.decision.points) == 24
    assert result.metrics is None


def test_analyse_period_Should_AggregateAcrossAllDays():
    forecasts = run(utc(2026, 1, 14, 7, 30), (2026, 1, 15), mw=1100) + run(utc(2026, 1, 15, 7, 30), (2026, 1, 16), mw=700)
    actuals = actual_day((2026, 1, 15), 1000) + actual_day((2026, 1, 16), 1000)

    result = analyse_period(forecasts, actuals, [date(2026, 1, 14), date(2026, 1, 15)], CUTOFF, NO_HISTORY)

    assert [d.delivery_date for d in result.days] == [date(2026, 1, 15), date(2026, 1, 16)]
    assert [d.metrics.bias_mw for d in result.days] == [pytest.approx(100), pytest.approx(-300)]
    assert result.overall.count == 48
    assert result.overall.mae_mw == pytest.approx(200)
    assert result.overall.bias_mw == pytest.approx(-100)
    assert result.percentiles[50] == pytest.approx(-100)
    assert [(b.low_mw, b.count) for b in result.by_forecast_level] == [(0, 48)]


def test_analyse_period_Should_KeepDayWithNoData_When_ForecastMissing():
    forecasts = run(utc(2026, 1, 14, 7, 30), (2026, 1, 15))
    actuals = actual_day((2026, 1, 15)) + actual_day((2026, 1, 16))

    result = analyse_period(forecasts, actuals, [date(2026, 1, 14), date(2026, 1, 15)], CUTOFF, NO_HISTORY)

    assert result.days[1].publish_time is None
    assert result.days[1].metrics is None
    assert result.overall.count == 24


def test_analyse_period_Should_ReturnEmptyAggregates_When_NoData():
    result = analyse_period([], [], [date(2026, 1, 14)], CUTOFF, NO_HISTORY)

    assert result.overall is None
    assert result.percentiles == {}
    assert result.by_forecast_level == []
