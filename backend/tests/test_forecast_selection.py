from datetime import date, time

from app.services.forecast import decision_cutoff, runs_for_delivery, select_decision_forecast
from tests.factories import run, utc

DECISION = date(2026, 1, 14)
DELIVERY = (2026, 1, 15)
CUTOFF = time(9, 20)


def test_select_Should_PickLatestRunBeforeCutoff():
    forecasts = run(utc(2026, 1, 14, 4, 30), DELIVERY, 100) + run(utc(2026, 1, 14, 7, 30), DELIVERY, 200)

    result = select_decision_forecast(forecasts, DECISION, CUTOFF)

    assert result.publish_time == utc(2026, 1, 14, 7, 30)
    assert result.delivery_date == date(2026, 1, 15)
    assert len(result.points) == 24
    assert all(p.publish_time == utc(2026, 1, 14, 7, 30) for p in result.points)


def test_select_Should_ExcludeRunPublishedAfterCutoff():
    forecasts = run(utc(2026, 1, 14, 7, 30), DELIVERY) + run(utc(2026, 1, 14, 9, 30), DELIVERY)

    result = select_decision_forecast(forecasts, DECISION, CUTOFF)

    assert result.publish_time == utc(2026, 1, 14, 7, 30)


def test_select_Should_IncludeRun_When_PublishedExactlyAtCutoff():
    forecasts = run(utc(2026, 1, 14, 7, 30), DELIVERY) + run(utc(2026, 1, 14, 9, 20), DELIVERY)

    result = select_decision_forecast(forecasts, DECISION, CUTOFF)

    assert result.publish_time == utc(2026, 1, 14, 9, 20)


def test_select_Should_PickOffCycleReissue_When_ItIsLatestBeforeCutoff():
    forecasts = run(utc(2026, 1, 14, 7, 30), DELIVERY) + run(utc(2026, 1, 14, 8, 55), DELIVERY)

    result = select_decision_forecast(forecasts, DECISION, CUTOFF)

    assert result.publish_time == utc(2026, 1, 14, 8, 55)


def test_select_Should_FallBackToPreviousDayRun_When_CutoffBeforeFirstDailyRun():
    forecasts = run(utc(2026, 1, 13, 22, 30), DELIVERY) + run(utc(2026, 1, 14, 2, 30), DELIVERY)

    result = select_decision_forecast(forecasts, DECISION, time(1, 0))

    assert result.publish_time == utc(2026, 1, 13, 22, 30)


def test_select_Should_OnlyReturnPointsInsideDeliveryDay():
    publish = utc(2026, 1, 14, 7, 30)
    forecasts = run(publish, (2026, 1, 14)) + run(publish, DELIVERY) + run(publish, (2026, 1, 16))

    result = select_decision_forecast(forecasts, DECISION, CUTOFF)

    assert {p.start_time.date() for p in result.points} == {date(2026, 1, 15)}
    assert [p.start_time.hour for p in result.points] == list(range(24))


def test_select_Should_IgnoreRunsThatDontCoverDeliveryDay():
    # A later run that only covers the decision day itself must not win.
    forecasts = run(utc(2026, 1, 14, 4, 30), DELIVERY) + run(utc(2026, 1, 14, 7, 30), (2026, 1, 14))

    result = select_decision_forecast(forecasts, DECISION, CUTOFF)

    assert result.publish_time == utc(2026, 1, 14, 4, 30)


def test_select_Should_ReturnEmpty_When_NoRunBeforeCutoff():
    forecasts = run(utc(2026, 1, 14, 9, 30), DELIVERY)

    result = select_decision_forecast(forecasts, DECISION, CUTOFF)

    assert result.publish_time is None
    assert result.points == []
    assert result.cutoff == utc(2026, 1, 14, 9, 20)


def test_select_Should_ReturnEmpty_When_NoForecasts():
    assert select_decision_forecast([], DECISION, CUTOFF).points == []


def test_select_Should_SortPoints_When_InputUnordered():
    points = run(utc(2026, 1, 14, 7, 30), DELIVERY)

    result = select_decision_forecast(list(reversed(points)), DECISION, CUTOFF)

    assert [p.start_time.hour for p in result.points] == list(range(24))


def test_runs_for_delivery_Should_ReturnRunsPublishedInLookbackBeforeDeliveryStarts():
    forecasts = (
        run(utc(2026, 1, 12, 22, 30), DELIVERY)  # before the 2-day lookback
        + run(utc(2026, 1, 13, 2, 30), DELIVERY)
        + run(utc(2026, 1, 14, 22, 30), DELIVERY)
        + run(utc(2026, 1, 15, 2, 30), DELIVERY)  # published during delivery: excluded
    )

    runs = runs_for_delivery(forecasts, date(2026, 1, 15))

    assert [r.publish_time for r in runs] == [utc(2026, 1, 13, 2, 30), utc(2026, 1, 14, 22, 30)]
    assert all(len(r.points) == 24 for r in runs)


def test_runs_for_delivery_Should_ClipPointsToDeliveryDateAndSort():
    publish = utc(2026, 1, 14, 7, 30)
    forecasts = list(reversed(run(publish, (2026, 1, 14)) + run(publish, DELIVERY, hours=range(20))))

    runs = runs_for_delivery(forecasts, date(2026, 1, 15))

    assert len(runs) == 1
    assert [p.start_time.hour for p in runs[0].points] == list(range(20))


def test_runs_for_delivery_Should_ReturnEmpty_When_NoRuns():
    assert runs_for_delivery([], date(2026, 1, 15)) == []


def test_decision_cutoff_Should_CombineDecisionDateAndTimeInUtc():
    assert decision_cutoff(DECISION, CUTOFF) == utc(2026, 1, 14, 9, 20)
