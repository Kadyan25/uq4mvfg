from app.elexon.models import ActualPoint, ForecastPoint
from app.services.align import HourlyComparison, compare, hourly_actuals
from tests.factories import utc


def test_hourly_actuals_Should_AverageBothHalfHours():
    actuals = [ActualPoint(utc(2026, 1, 15, 3, 0), 1000), ActualPoint(utc(2026, 1, 15, 3, 30), 1400)]

    assert hourly_actuals(actuals) == {utc(2026, 1, 15, 3): 1200}


def test_hourly_actuals_Should_DropHour_When_HalfHourMissing():
    actuals = [
        ActualPoint(utc(2026, 1, 15, 3, 0), 1000),
        ActualPoint(utc(2026, 1, 15, 4, 0), 1000),
        ActualPoint(utc(2026, 1, 15, 4, 30), 2000),
    ]

    assert hourly_actuals(actuals) == {utc(2026, 1, 15, 4): 1500}


def test_hourly_actuals_Should_ReturnEmpty_When_NoActuals():
    assert hourly_actuals([]) == {}


def test_compare_Should_JoinForecastToHourlyActual():
    publish = utc(2026, 1, 14, 7, 30)
    forecast = [ForecastPoint(publish, utc(2026, 1, 15, 3), 1500)]
    actuals = [ActualPoint(utc(2026, 1, 15, 3, 0), 1000), ActualPoint(utc(2026, 1, 15, 3, 30), 1400)]

    rows = compare(forecast, actuals)

    assert rows == [HourlyComparison(utc(2026, 1, 15, 3), 1500, 1200)]
    assert rows[0].error_mw == 300


def test_compare_Should_SkipForecastHours_When_NoMatchingActual():
    publish = utc(2026, 1, 14, 7, 30)
    forecast = [
        ForecastPoint(publish, utc(2026, 1, 15, 3), 1500),
        ForecastPoint(publish, utc(2026, 1, 15, 4), 1500),
    ]
    actuals = [ActualPoint(utc(2026, 1, 15, 3, 0), 1000), ActualPoint(utc(2026, 1, 15, 3, 30), 1000)]

    assert [r.start_time.hour for r in compare(forecast, actuals)] == [3]


def test_error_Should_BeNegative_When_ForecastUnderestimates():
    assert HourlyComparison(utc(2026, 1, 15), 800, 1000).error_mw == -200
