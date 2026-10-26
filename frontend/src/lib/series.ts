import type { SeriesPoint } from '../api/client'

export interface ChartRow {
  t: number
  forecast?: number
  actual?: number
}

/** Puts hourly forecasts and half-hourly actuals on one time axis; gaps are bridged by the chart. */
export function mergeSeries(forecast: SeriesPoint[], actuals: SeriesPoint[]): ChartRow[] {
  const rows = new Map<number, ChartRow>()
  const at = (iso: string) => {
    const t = Date.parse(iso)
    if (!rows.has(t)) rows.set(t, { t })
    return rows.get(t)!
  }
  forecast.forEach((p) => { at(p.time).forecast = p.mw })
  actuals.forEach((p) => { at(p.time).actual = p.mw })
  return [...rows.values()].sort((a, b) => a.t - b.t)
}
