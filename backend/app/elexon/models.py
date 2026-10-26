from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ActualPoint:
    start_time: datetime
    generation_mw: float


@dataclass(frozen=True)
class ForecastPoint:
    publish_time: datetime
    start_time: datetime
    generation_mw: float
