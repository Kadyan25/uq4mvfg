from datetime import datetime, timezone

from app.elexon.models import ActualPoint, ForecastPoint


def utc(*args: int) -> datetime:
    return datetime(*args, tzinfo=timezone.utc)


def run(publish: datetime, day: tuple[int, int, int], mw: float = 1000, hours: range = range(24)) -> list[ForecastPoint]:
    return [ForecastPoint(publish, utc(*day, h), mw + h) for h in hours]


def actual_day(day: tuple[int, int, int], mw: float = 1000) -> list[ActualPoint]:
    return [ActualPoint(utc(*day, h, m), mw + h) for h in range(24) for m in (0, 30)]
