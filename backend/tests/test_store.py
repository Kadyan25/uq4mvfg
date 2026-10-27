import os
import uuid
from datetime import datetime, timezone

import pytest

from app.elexon.models import ActualPoint, ForecastPoint
from app.elexon.store import (
    PostgresStore,
    Snapshot,
    decode_actuals,
    decode_forecasts,
    encode_actuals,
    encode_forecasts,
)


def utc(*args: int) -> datetime:
    return datetime(*args, tzinfo=timezone.utc)


def test_actuals_codec_Should_RoundTrip():
    points = [ActualPoint(utc(2026, 1, 2, 0, 30), 1234.5), ActualPoint(utc(2026, 1, 2, 1), 0.0)]

    assert decode_actuals(encode_actuals(points)) == points


def test_forecasts_codec_Should_RoundTrip():
    points = [ForecastPoint(utc(2026, 1, 1, 7, 30), utc(2026, 1, 2), 15834.0)]

    assert decode_forecasts(encode_forecasts(points)) == points


def test_codecs_Should_HandleEmptyLists():
    assert decode_actuals(encode_actuals([])) == []
    assert decode_forecasts(encode_forecasts([])) == []


# Runs only when a disposable Postgres is provided, e.g. the docker one in the README.
TEST_DB = os.getenv("TEST_DATABASE_URL")


@pytest.mark.skipif(not TEST_DB, reason="TEST_DATABASE_URL not set")
def test_postgres_store_Should_SaveLoadAndOverwrite():
    store = PostgresStore(TEST_DB)
    key = f"test-{uuid.uuid4()}"

    assert store.load(key) is None
    store.save(key, Snapshot(1.0, "first"))
    store.save(key, Snapshot(2.0, "second"))

    assert store.load(key) == Snapshot(2.0, "second")
