import math

import pytest

from app.services.align import HourlyComparison
from app.services.metrics import LevelBucket, compute_metrics, error_by_forecast_level, error_percentiles, percentile
from tests.factories import utc


def row(hour: int, forecast: float, actual: float) -> HourlyComparison:
    return HourlyComparison(utc(2026, 1, 15, hour), forecast, actual)


def test_compute_metrics_Should_CalculateAllMetrics():
    rows = [row(0, 1100, 1000), row(1, 900, 1000), row(2, 1300, 1000)]  # errors +100, -100, +300

    m = compute_metrics(rows)

    assert m.count == 3
    assert m.mae_mw == pytest.approx(500 / 3)
    assert m.rmse_mw == pytest.approx(math.sqrt((100**2 + 100**2 + 300**2) / 3))
    assert m.bias_mw == pytest.approx(100)
    assert m.wape_pct == pytest.approx(500 / 3000 * 100)


def test_compute_metrics_Should_ReturnNone_When_NoRows():
    assert compute_metrics([]) is None


def test_compute_metrics_Should_ReturnNoneWape_When_ActualsSumToZero():
    m = compute_metrics([row(0, 50, 0)])

    assert m.wape_pct is None
    assert m.mae_mw == 50


def test_compute_metrics_Should_ReportZeroError_When_ForecastPerfect():
    m = compute_metrics([row(0, 1000, 1000), row(1, 2000, 2000)])

    assert (m.mae_mw, m.rmse_mw, m.bias_mw, m.wape_pct) == (0, 0, 0, 0)


def test_percentile_Should_InterpolateLinearly():
    values = [10.0, 20.0, 30.0, 40.0, 50.0]

    assert percentile(values, 0) == 10
    assert percentile(values, 50) == 30
    assert percentile(values, 100) == 50
    assert percentile(values, 90) == pytest.approx(46)
    assert percentile([40.0, 10.0, 30.0, 20.0], 50) == pytest.approx(25)


def test_percentile_Should_ReturnValue_When_SingleElement():
    assert percentile([7.0], 90) == 7


def test_percentile_Should_Raise_When_EmptyOrOutOfRange():
    with pytest.raises(ValueError):
        percentile([], 50)
    with pytest.raises(ValueError):
        percentile([1.0], 101)


def test_error_percentiles_Should_UseSignedErrors():
    rows = [row(h, 1000 + e, 1000) for h, e in enumerate([-200, -100, 0, 100, 200])]

    assert error_percentiles(rows) == {10: pytest.approx(-160), 50: 0, 90: pytest.approx(160)}


def test_error_percentiles_Should_ReturnEmpty_When_NoRows():
    assert error_percentiles([]) == {}


def test_error_by_forecast_level_Should_BucketByForecastAndReportBiasAndMae():
    rows = [
        HourlyComparison(utc(2026, 1, 15, 0), 3000, 2800),     # 0–5 GW, +200
        HourlyComparison(utc(2026, 1, 15, 1), 4999, 5199),     # 0–5 GW, −200
        HourlyComparison(utc(2026, 1, 15, 2), 21000, 17000),   # 20–25 GW, +4000
    ]

    assert error_by_forecast_level(rows) == [
        LevelBucket(0, 5000, 2, 200, 0),
        LevelBucket(20000, 25000, 1, 4000, 4000),
    ]


def test_error_by_forecast_level_Should_PutBoundaryValueInUpperBucket():
    rows = [HourlyComparison(utc(2026, 1, 15, 0), 5000, 4000)]

    assert error_by_forecast_level(rows)[0].low_mw == 5000


def test_error_by_forecast_level_Should_ReturnEmpty_When_NoRows():
    assert error_by_forecast_level([]) == []
