import type { DayResponse } from '../api/client'
import { formatGw, formatGwh, formatPct, formatPublished, formatSignedGw } from '../lib/format'
import { ForecastChart } from './ForecastChart'
import { KpiCard } from './KpiCard'

interface Props {
  day: DayResponse
}

export function DayView({ day }: Props) {
  if (!day.forecast_publish_time) {
    return (
      <p className="empty">
        No wind forecast had been published by {day.cutoff.slice(11, 16)} UTC on this decision day. Try a later cutoff.
      </p>
    )
  }

  // Each hourly value is an average MW over the hour, so summing gives MWh.
  const forecastEnergy = day.hourly.reduce((sum, h) => sum + h.forecast_mw, 0)
  const actualEnergy = day.hourly.reduce((sum, h) => sum + h.actual_mw, 0)
  const m = day.metrics

  return (
    <>
      <div className="kpis">
        <KpiCard label="Forecast used" value={formatPublished(day.forecast_publish_time)}
          hint={`Latest run before cutoff · ${day.lead_time_hours?.toFixed(1)} h before delivery starts`} />
        <KpiCard label="Forecast wind energy" value={formatGwh(forecastEnergy)}
          hint={`Actual: ${day.hourly.length ? formatGwh(actualEnergy) : '—'}`} />
        <KpiCard label="Mean absolute error" value={formatGw(m?.mae_mw, 2)} hint={`WAPE ${formatPct(m?.wape_pct)}`} />
        <KpiCard label="Bias" value={formatSignedGw(m?.bias_mw, 2)}
          hint={m ? (m.bias_mw > 0 ? 'Forecast too high: buy shortfall' : 'Forecast too low: surplus wind') : 'No actuals yet'} />
      </div>
      <ForecastChart forecast={day.forecast} actuals={day.actuals} />
    </>
  )
}
