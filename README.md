# UK Wind Forecast Monitor

A web app for a GB day-ahead power buying team. It shows the national wind forecast that was actually available at the day-ahead auction deadline, measures how accurate that forecast turned out to be, and turns the measured error into a planning estimate with a range.

**Live app:** https://gb-wind-forecast-monitor.vercel.app

Data comes only from Elexon BMRS:
- **WINDFOR**: national wind generation forecast (hourly, published about 8 times a day)
- **FUELHH**: generation outturn by fuel type, filtered to `WIND` (half-hourly)

Scope is purchase decisions made in January 2026 (decision dates 1–31 Jan, delivery dates 2 Jan – 1 Feb).

---

## What the app shows

**For a chosen decision date and gate closure time**
- The forecast run in force at gate closure, its lead time, forecast vs outturn energy, MAE and bias.
- A chart of forecast vs half-hourly outturn, with a **planning estimate** line and a **P10–P90 range**.
- A planning card: wind to plan for (GWh) with its range, and an optional expected-demand input that turns it into a suggested purchase range.
- Every forecast run published in the two days before delivery, with the one used at gate closure highlighted.

**For the whole month (at the same gate closure)**
- MAE, RMSE, bias and WAPE across all 744 hours.
- Planning estimate vs raw forecast, scored on the same hours, plus how often outturn landed inside the P10–P90 range.
- MAE per delivery date (click a bar to open that date), the error distribution (P10 / P50 / P90), and bias by forecast level.

---

## Repository layout

```
.
├── api/
│   └── index.py               Vercel entrypoint: exposes the FastAPI app as a serverless function
├── backend/                   Python API (FastAPI)
│   ├── app/
│   │   ├── main.py            App setup, /api/health, cache warm-up on startup
│   │   ├── config.py          Settings: scope dates, default gate closure, cache TTL, DATABASE_URL
│   │   ├── api/
│   │   │   ├── routes.py      /api/meta, /api/day, /api/runs, /api/summary (input validation, error handling)
│   │   │   └── schemas.py     Pydantic response models
│   │   ├── elexon/
│   │   │   ├── client.py      Fetches and parses WINDFOR and FUELHH streams
│   │   │   ├── models.py      ActualPoint, ForecastPoint
│   │   │   ├── repository.py  In-memory cache, serve-stale-while-refreshing, optional snapshot store
│   │   │   └── store.py       Postgres snapshot store and compact JSON codecs
│   │   └── services/
│   │       ├── forecast.py    Picks the latest run published at or before gate closure; lists all runs
│   │       ├── align.py       Averages half-hourly outturn into hours and joins it to the forecast
│   │       ├── metrics.py     MAE, RMSE, bias, WAPE, percentiles, error by forecast level
│   │       ├── planning.py    Planning estimate and P10–P90 range from past errors
│   │       └── analysis.py    Per-day and per-month analysis that ties the services together
│   ├── tests/                 pytest suite (unit, API and optional Postgres integration tests)
│   ├── pyproject.toml         Dependencies (managed with uv)
│   └── Dockerfile
├── frontend/                  React + TypeScript (Vite, Recharts)
│   ├── src/
│   │   ├── App.tsx            Page layout and data loading
│   │   ├── api/client.ts      Typed API client
│   │   ├── components/        Controls, KPI cards, charts, planning card, tooltips
│   │   ├── hooks/useAsync.ts  Request state with cancellation
│   │   ├── lib/               Formatting, chart data shaping, planning maths, metric definitions
│   │   └── *.test.ts(x)       vitest + Testing Library tests
│   ├── nginx.conf             Serves the build and proxies /api to the backend (Docker)
│   └── Dockerfile
├── scripts/
│   └── verify_against_elexon.py   Independent end-to-end check against raw Elexon data
├── docker-compose.yml         Runs backend + frontend locally
├── vercel.json                Vercel build, function and routing config
├── requirements.txt           Python dependencies for the Vercel function
└── .vercelignore              Allowlist of files uploaded to Vercel
```

---

## Running locally

### With Docker (recommended)

Requires Docker with Compose.

```bash
docker compose up -d --build
```

Open http://localhost:8080. The frontend container serves the React build and proxies `/api` to the backend container. The first request after startup loads January's data from Elexon (a few seconds); after that, everything is served from memory.

Stop it with:

```bash
docker compose down
```

### Without Docker

Requires Python 3.12+ with [uv](https://docs.astral.sh/uv/), and Node.js 22+.

Backend (terminal 1):

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

Frontend (terminal 2):

```bash
cd frontend
npm ci
npm run dev
```

Open http://localhost:5173. Vite proxies `/api` to `http://localhost:8000`.

### Configuration

All optional, set as environment variables on the backend:

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | unset | Postgres URL. When set, fetched data is saved as snapshots so new instances skip the Elexon fetch |
| `CACHE_TTL_S` | `21600` | Age in seconds after which data is refreshed in the background (stale data is still served meanwhile) |
| `ELEXON_BASE_URL` | `https://data.elexon.co.uk/bmrs/api/v1` | Elexon API base URL |
| `ELEXON_TIMEOUT_S` | `60` | Elexon request timeout |

No API keys are needed. Elexon BMRS is public.

---

## Tests

Backend:

```bash
cd backend
uv run pytest
```

The Postgres store test runs only when a disposable database is provided:

```bash
docker run -d --rm --name wf-test-pg -e POSTGRES_PASSWORD=localtest -p 55432:5432 postgres:17-alpine
```

```bash
cd backend
TEST_DATABASE_URL=postgresql://postgres:localtest@localhost:55432/postgres uv run pytest tests/test_store.py
```

Frontend (tests, type check, lint):

```bash
cd frontend
npm test
npx tsc -b
npx oxlint src
```

---

## Independent verification

`scripts/verify_against_elexon.py` recomputes the results from raw Elexon data, using only the Python standard library and sharing no code with the backend, then compares them with a running instance of the app. It checks:

- the forecast run chosen for every decision date at five gate closure times (09:20, 12:00, 05:00, 00:00, 23:59)
- hours counted, MAE and bias for every day, and the monthly MAE
- raw forecast and outturn values for a sample hour
- planning estimate percentiles for every day, plan MAE and range hit rate
- the list of forecast runs and the gate-closure run for a delivery date

Run it against the local Docker app:

```bash
python scripts/verify_against_elexon.py
```

Or against the live app:

```bash
APP_URL=https://gb-wind-forecast-monitor.vercel.app python scripts/verify_against_elexon.py
```

It exits non-zero on any mismatch. I checked that it fails when a deliberate 1 MW error or a look-ahead leak is introduced.

---

## Deployment

The app runs on Vercel: the React build is served as static files and the FastAPI app runs as a Python serverless function (`api/index.py`). A free Neon Postgres database, connected through the Vercel integration, provides `DATABASE_URL` for the snapshot store, so a new function instance loads the month from the database in about a second instead of calling Elexon.

```bash
vercel deploy --prod
```

---

## Assumptions and design decisions

- **Decision window.** The brief scopes the product to purchase decisions made in January 2026. A decision on date D-1 is for delivery date D, so decision dates are 1–31 Jan and delivery dates are 2 Jan – 1 Feb.
- **Gate closure.** The brief says decisions are made the day before delivery but gives no time. I default to **09:20 UTC**, the EPEX GB day-ahead auction gate closure. That selects the 07:30 forecast run. N2EX closes at 09:50, which would allow the 09:30 run, so the gate closure time is adjustable in the UI to compare the two. In January, UK time equals UTC.
- **Which forecast counts.** For each delivery date, the app uses the WINDFOR run with the latest `publishTime` at or before gate closure that covers that date. Runs published later are never used for scoring, even if they were more accurate.
- **Aligning resolutions.** WINDFOR is hourly and FUELHH is half-hourly. Hourly outturn is the mean of the two half-hours in each hour. Hours missing either half are dropped, never filled in.
- **Metrics.** Error is forecast − outturn, so positive means the forecast was too high. I report MAE, RMSE, bias and WAPE (total absolute error ÷ total outturn). I don't use MAPE because it blows up in low-wind hours.
- **Planning estimate.** For each decision date, the app takes the hourly errors from delivery dates that had **fully finished** before the decision date (the delivery date in progress at gate closure is excluded), shifts the new forecast by their median, and brackets it with their P10–P90. It needs at least 3 completed dates, so it starts from decision date 5 Jan. The daily range is the sum of the hourly bounds, which is slightly conservative. It is an indicative statistical correction, not a weather forecast, and the UI says so.
- **Demand input.** There is no demand data in scope, so the app reports wind to plan for. The optional demand box is user input, used only in the browser to show demand minus planned wind, and is never sent to the server.
- **Month summary.** The monthly accuracy figures use the whole of January. They describe the pilot period; they are not information a buyer would have had on a given day. The planning estimate is the part that uses past data only.
- **Data coverage.** Both datasets cover transmission-metered wind farms only, so totals are lower than headline "all GB wind" figures that include embedded generation. The consistent over-forecast in January is likely linked in part to curtailment on high-wind days; that can't be confirmed with these two datasets alone.
- **Caching.** January 2026 data is historical, so the app serves cached data immediately and refreshes it in the background after `CACHE_TTL_S`. If Elexon is unavailable, the API returns a 502 with a generic message, and cached data keeps being served when available.

---

## Use of AI tools

I used AI tools while building this project, mainly Claude Code (Anthropic). I used it to help with:

- researching the GB day-ahead market, Elexon datasets and January 2026 context
- writing and refactoring backend and frontend code
- writing unit, API and frontend tests, and the independent verification script
- Docker and Vercel configuration
- drafting this README

I made the product and design decisions (scope, gate closure default, metrics, the planning estimate and its no-look-ahead rule), reviewed the code, and checked the results against raw Elexon data with the verification script.
