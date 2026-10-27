"""End-to-end correctness check: recompute every result from raw Elexon data and compare with the app.

Deliberately shares no code with the backend (stdlib only), so a bug in the app's logic
can't be hidden by the same bug in the check. Run it against a live stack:

    docker compose up -d
    python scripts/verify_against_elexon.py            # defaults to http://localhost:8080
    APP_URL=https://example.app python scripts/verify_against_elexon.py
"""
import json
import os
import sys
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta

ELEXON = "https://data.elexon.co.uk/bmrs/api/v1/datasets"
APP = os.getenv("APP_URL", "http://localhost:8080").rstrip("/") + "/api"
FIRST_DECISION = datetime(2026, 1, 1)
DAYS = 31
CUTOFFS = ["09:20", "12:00", "05:00", "00:00", "23:59"]
TOLERANCE = 1e-6
MIN_HISTORY_DAYS = 3


def get(url):
    with urllib.request.urlopen(url, timeout=120) as response:
        return json.load(response)


def ts(value):
    return datetime.strptime(value[:19], "%Y-%m-%dT%H:%M:%S")


def load_raw():
    windfor = get(f"{ELEXON}/WINDFOR/stream?publishDateTimeFrom=2025-12-31T00:00:00Z&publishDateTimeTo=2026-02-01T00:00:00Z")
    fuelhh = get(f"{ELEXON}/FUELHH/stream?settlementDateFrom=2026-01-02&settlementDateTo=2026-02-01&fuelType=WIND")
    runs = defaultdict(dict)
    for row in windfor:
        runs[ts(row["publishTime"])][ts(row["startTime"])] = row["generation"]
    halfhours = {ts(row["startTime"]): row["generation"] for row in fuelhh if row["fuelType"] == "WIND"}
    return runs, halfhours


def expected_day(runs, halfhours, decision, cutoff):
    hour, minute = map(int, cutoff.split(":"))
    cutoff_at = decision.replace(hour=hour, minute=minute)
    delivery_hours = [decision + timedelta(days=1, hours=h) for h in range(24)]
    candidates = [p for p in runs if p <= cutoff_at and any(h in runs[p] for h in delivery_hours)]
    run = max(candidates)
    errors = []
    for h in delivery_hours:
        first, second = halfhours.get(h), halfhours.get(h + timedelta(minutes=30))
        if h in runs[run] and first is not None and second is not None:
            errors.append(runs[run][h] - (first + second) / 2)
    return run, errors


def check_cutoff(runs, halfhours, cutoff):
    summary = get(f"{APP}/summary?cutoff={cutoff}")
    failures, all_errors = 0, []
    for i, row in enumerate(summary["days"]):
        decision = FIRST_DECISION + timedelta(days=i)
        run, errors = expected_day(runs, halfhours, decision, cutoff)
        all_errors += errors
        mae = sum(abs(e) for e in errors) / len(errors)
        bias = sum(errors) / len(errors)
        m = row["metrics"]
        if (ts(row["forecast_publish_time"]) != run or m["count"] != len(errors)
                or abs(m["mae_mw"] - mae) > TOLERANCE or abs(m["bias_mw"] - bias) > TOLERANCE):
            failures += 1
            print(f"  MISMATCH {decision.date()}: app run {row['forecast_publish_time']} {m}; expected run {run} mae={mae:.3f}")
    overall = sum(abs(e) for e in all_errors) / len(all_errors)
    if len(summary["days"]) != DAYS or abs(summary["overall"]["mae_mw"] - overall) > TOLERANCE:
        failures += 1
    print(f"cutoff {cutoff}: {len(summary['days'])} days, overall MAE app={summary['overall']['mae_mw']:.2f} "
          f"independent={overall:.2f} -> {'OK' if failures == 0 else 'FAIL'}")
    return failures


def check_raw_values(runs, halfhours):
    day = get(f"{APP}/day?decision_date=2026-01-14&cutoff=09:20")
    first = day["hourly"][0]
    raw_forecast = runs[datetime(2026, 1, 14, 7, 30)][datetime(2026, 1, 15)]
    raw_actual = (halfhours[datetime(2026, 1, 15, 0, 0)] + halfhours[datetime(2026, 1, 15, 0, 30)]) / 2
    ok = first["forecast_mw"] == raw_forecast and first["actual_mw"] == raw_actual and len(day["actuals"]) == 48
    print(f"raw values 15 Jan 00:00: forecast {first['forecast_mw']} vs {raw_forecast}, "
          f"actual {first['actual_mw']} vs {raw_actual} -> {'OK' if ok else 'FAIL'}")
    return 0 if ok else 1


def pct(values, p):
    ordered = sorted(values)
    k = (len(ordered) - 1) * p / 100
    low = int(k)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (k - low)


def expected_plan(runs, halfhours, i, cutoff):
    """History = delivery dates that ended before decision date i (decisions 0..i-2)."""
    history = [expected_day(runs, halfhours, FIRST_DECISION + timedelta(days=j), cutoff)[1] for j in range(max(i - 1, 0))]
    history = [errors for errors in history if errors]
    if len(history) < MIN_HISTORY_DAYS:
        return len(history), None
    flat = [e for errors in history for e in errors]
    return len(history), (pct(flat, 10), pct(flat, 50), pct(flat, 90))


def check_planning(runs, halfhours, cutoff="09:20"):
    failures, plan_errors, hits, checked = 0, [], 0, 0
    for i in range(DAYS):
        decision = FIRST_DECISION + timedelta(days=i)
        day = get(f"{APP}/day?decision_date={decision.date()}&cutoff={cutoff}")
        history_days, p = expected_plan(runs, halfhours, i, cutoff)
        app_plan = day["plan"]
        if day["history_days"] != history_days or (p is None) != (app_plan is None):
            failures += 1
            print(f"  MISMATCH plan presence {decision.date()}: app {day['history_days']} vs {history_days}")
            continue
        if p is None:
            continue
        app_p = (app_plan["p10_error_mw"], app_plan["p50_error_mw"], app_plan["p90_error_mw"])
        if any(abs(a - b) > TOLERANCE for a, b in zip(app_p, p)):
            failures += 1
            print(f"  MISMATCH plan percentiles {decision.date()}: app {app_p} vs {p}")
        for h in day["hourly"]:
            plan_mw, low, high = max(h["forecast_mw"] - p[1], 0), max(h["forecast_mw"] - p[2], 0), max(h["forecast_mw"] - p[0], 0)
            plan_errors.append(plan_mw - h["actual_mw"])
            hits, checked = hits + (low <= h["actual_mw"] <= high), checked + 1
    return failures, plan_errors, hits, checked


def check_planning_summary(runs, halfhours):
    failures, plan_errors, hits, checked = check_planning(runs, halfhours)
    summary = get(f"{APP}/summary?cutoff=09:20")
    mae = sum(abs(e) for e in plan_errors) / len(plan_errors)
    hit_pct = hits / checked * 100
    ok = abs(summary["plan_overall"]["mae_mw"] - mae) < TOLERANCE and abs(summary["plan_range_hit_pct"] - hit_pct) < TOLERANCE
    failures += 0 if ok else 1
    print(f"planning: plan MAE app={summary['plan_overall']['mae_mw']:.2f} independent={mae:.2f}, "
          f"range hit app={summary['plan_range_hit_pct']:.1f}% independent={hit_pct:.1f}% -> {'OK' if failures == 0 else 'FAIL'}")
    return failures


def check_runs(runs, decision=datetime(2026, 1, 27), cutoff="09:20"):
    body = get(f"{APP}/runs?decision_date={decision.date()}&cutoff={cutoff}")
    delivery = decision + timedelta(days=1)
    expected = sorted(p for p in runs if delivery - timedelta(days=2) <= p < delivery
                      and any(delivery + timedelta(hours=h) in runs[p] for h in range(24)))
    chosen = expected_day(runs, {}, decision, cutoff)[0]
    app_runs = [ts(r["publish_time"]) for r in body["runs"]]
    app_chosen = [ts(r["publish_time"]) for r in body["runs"] if r["is_decision_run"]]
    ok = app_runs == expected and app_chosen == [chosen]
    print(f"runs {delivery.date()}: {len(app_runs)} runs, decision run {app_chosen} -> {'OK' if ok else 'FAIL'}")
    return 0 if ok else 1


def main():
    print(f"Checking {APP} against raw Elexon data...")
    runs, halfhours = load_raw()
    failures = sum(check_cutoff(runs, halfhours, c) for c in CUTOFFS) + check_raw_values(runs, halfhours)
    failures += check_planning_summary(runs, halfhours) + check_runs(runs)
    print("ALL CHECKS PASSED" if failures == 0 else f"{failures} FAILURE(S)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
