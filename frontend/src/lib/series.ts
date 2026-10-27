import type { PlanHour, SeriesPoint } from '../api/client'

export interface ChartRow {
  t: number
  forecast?: number
  actual?: number
  plan?: number
  range?: [number, number]
}

/** Puts hourly forecast/plan and half-hourly outturn on one time axis; gaps are bridged by the chart. */
export function mergeSeries(forecast: SeriesPoint[], actuals: SeriesPoint[], plan: PlanHour[] = []): ChartRow[] {
  const rows = new Map<number, ChartRow>()
  const at = (iso: string) => {
    const t = Date.parse(iso)
    if (!rows.has(t)) rows.set(t, { t })
    return rows.get(t)!
  }
  forecast.forEach((p) => { at(p.time).forecast = p.mw })
  actuals.forEach((p) => { at(p.time).actual = p.mw })
  plan.forEach((p) => {
    const row = at(p.time)
    row.plan = p.plan_mw
    row.range = [p.low_mw, p.high_mw]
  })
  return [...rows.values()].sort((a, b) => a.t - b.t)
}
