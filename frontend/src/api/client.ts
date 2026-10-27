export interface Metrics {
  count: number
  mae_mw: number
  rmse_mw: number
  bias_mw: number
  wape_pct: number | null
}

export interface SeriesPoint {
  time: string
  mw: number
}

export interface HourlyRow {
  time: string
  forecast_mw: number
  actual_mw: number
  error_mw: number
}

export interface PlanHour {
  time: string
  plan_mw: number
  low_mw: number
  high_mw: number
}

export interface Plan {
  history_days: number
  p10_error_mw: number
  p50_error_mw: number
  p90_error_mw: number
  hours: PlanHour[]
}

export interface DayResponse {
  decision_date: string
  delivery_date: string
  cutoff: string
  forecast_publish_time: string | null
  lead_time_hours: number | null
  forecast: SeriesPoint[]
  actuals: SeriesPoint[]
  hourly: HourlyRow[]
  metrics: Metrics | null
  history_days: number
  plan: Plan | null
  plan_metrics: Metrics | null
}

export interface ForecastRun {
  publish_time: string
  after_cutoff: boolean
  is_decision_run: boolean
  points: SeriesPoint[]
}

export interface RunsResponse {
  decision_date: string
  delivery_date: string
  cutoff: string
  runs: ForecastRun[]
}

export interface DaySummaryRow {
  decision_date: string
  delivery_date: string
  forecast_publish_time: string | null
  metrics: Metrics | null
  plan_metrics: Metrics | null
}

export interface SummaryResponse {
  cutoff: string
  days: DaySummaryRow[]
  overall: Metrics | null
  error_percentiles: { p10_mw: number; p50_mw: number; p90_mw: number } | null
  mae_by_hour: { hour: number; mae_mw: number }[]
  plan_overall: Metrics | null
  plan_range_hit_pct: number | null
}

export interface MetaResponse {
  first_decision_date: string
  last_decision_date: string
  default_cutoff: string
  min_history_days: number
}

export class ApiError extends Error {}

async function getJson<T>(path: string, params: Record<string, string> = {}, signal?: AbortSignal): Promise<T> {
  const query = new URLSearchParams(params).toString()
  const response = await fetch(query ? `${path}?${query}` : path, { signal })
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    const detail = typeof body?.detail === 'string' ? body.detail : `Request failed (${response.status})`
    throw new ApiError(detail)
  }
  return response.json() as Promise<T>
}

export const api = {
  meta: (signal?: AbortSignal) => getJson<MetaResponse>('/api/meta', {}, signal),
  day: (decisionDate: string, cutoff: string, signal?: AbortSignal) =>
    getJson<DayResponse>('/api/day', { decision_date: decisionDate, cutoff }, signal),
  runs: (decisionDate: string, cutoff: string, signal?: AbortSignal) =>
    getJson<RunsResponse>('/api/runs', { decision_date: decisionDate, cutoff }, signal),
  summary: (cutoff: string, signal?: AbortSignal) => getJson<SummaryResponse>('/api/summary', { cutoff }, signal),
}
