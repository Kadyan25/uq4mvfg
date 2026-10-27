import os
from dataclasses import dataclass
from datetime import date, time
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    elexon_base_url: str
    http_timeout_s: float
    cache_ttl_s: int
    # The brief scopes the product to purchase decisions made in January 2026;
    # each decision on day D-1 is for delivery day D.
    first_decision_date: date = date(2026, 1, 1)
    last_decision_date: date = date(2026, 1, 31)
    # GB day-ahead auction (EPEX) gate closure is 09:20 UK time; UK time == UTC in January.
    default_cutoff: time = time(9, 20)
    # Completed delivery dates needed before the planning estimate is shown; fewer is too noisy to trust.
    min_history_days: int = 3


@lru_cache
def get_settings() -> Settings:
    return Settings(
        elexon_base_url=os.getenv("ELEXON_BASE_URL", "https://data.elexon.co.uk/bmrs/api/v1"),
        http_timeout_s=float(os.getenv("ELEXON_TIMEOUT_S", "60")),
        cache_ttl_s=int(os.getenv("CACHE_TTL_S", "21600")),
    )
