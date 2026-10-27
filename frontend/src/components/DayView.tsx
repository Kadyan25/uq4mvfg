import type { DayResponse } from '../api/client'
import { DEFINITIONS } from '../lib/definitions'
import { formatGw, formatPct, formatPublished, formatSignedGw } from '../lib/format'
import { ForecastChart } from './ForecastChart'
import { KpiCard } from './KpiCard'

interface Props {
  day: DayResponse
}

function biasLabel(bias: number): string {
  if (bias > 0) return 'Over-forecast'
  if (bias < 0) return 'Under-forecast'
  return 'Unbiased'
}

export function DayView({ day }: Props) {
  if (!day.forecast_publish_time) {
    return <p className="empty">No forecast published before {day.cutoff.slice(11, 16)} UTC.</p>
  }

  // Each hourly value is an average MW over the hour, so summing gives MWh.
  const forecastGwh = day.hourly.reduce((sum, h) => sum + h.forecast_mw, 0) / 1000
  const outturnGwh = day.hourly.reduce((sum, h) => sum + h.actual_mw, 0) / 1000
  const m = day.metrics

  return (
    <>
      <div className="kpis">
        <KpiCard label="Forecast run" value={formatPublished(day.forecast_publish_time)}
          hint={`Lead time ${day.lead_time_hours?.toFixed(1)} h`} info={DEFINITIONS.forecastRun} />
        <KpiCard label="Energy (fcst / outturn)"
          value={day.hourly.length ? `${forecastGwh.toFixed(0)} / ${outturnGwh.toFixed(0)} GWh` : '—'} />
        <KpiCard label="MAE" value={formatGw(m?.mae_mw, 2)} hint={`WAPE ${formatPct(m?.wape_pct)}`} info={DEFINITIONS.mae} />
        <KpiCard label="Bias" value={formatSignedGw(m?.bias_mw, 2)} hint={m ? biasLabel(m.bias_mw) : 'No outturn'}
          info={DEFINITIONS.bias} />
      </div>
      <ForecastChart forecast={day.forecast} actuals={day.actuals} plan={day.plan?.hours} />
    </>
  )
}
