from fastapi import FastAPI

app = FastAPI(title="Wind Forecast API")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
