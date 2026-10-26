import logging
import threading
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import get_repository, router
from app.elexon.repository import WindDataRepository

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def warm_cache(repo: WindDataRepository) -> None:
    # Best effort: if Elexon is down at boot, requests will retry the fetch themselves.
    try:
        repo.forecasts()
        repo.actuals()
        logger.info("Elexon data cache warmed")
    except Exception:
        logger.exception("Cache warm-up failed; will fetch on first request")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    threading.Thread(target=warm_cache, args=(get_repository(),), daemon=True).start()
    yield


app = FastAPI(title="Wind Forecast API", lifespan=lifespan)
app.include_router(router)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
