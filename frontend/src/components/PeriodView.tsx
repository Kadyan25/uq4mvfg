import type { SummaryResponse } from '../api/client'
import { formatGw, formatPct, formatSignedGw } from '../lib/format'
import { DailyErrorChart } from './DailyErrorChart'
import { ErrorBand } from './ErrorBand'
import { HourOfDayChart } from './HourOfDayChart'
import { KpiCard } from './KpiCard'

interface Props {
  summary: SummaryResponse
  selectedDecisionDate: string
  onSelectDay: (decisionDate: string) => void
}

export function PeriodView({ summary, selectedDecisionDate, onSelectDay }: Props) {
  const o = summary.overall
  if (!o) return <p className="empty">No overlapping forecast and actual data for this period.</p>

  return (
    <>
      <div className="kpis">
        <KpiCard label="Mean absolute error" value={formatGw(o.mae_mw, 2)} hint={`Across ${o.count} hours`} />
        <KpiCard label="RMSE" value={formatGw(o.rmse_mw, 2)} hint="Penalises large misses" />
        <KpiCard label="Bias" value={formatSignedGw(o.bias_mw, 2)}
          hint={o.bias_mw > 0 ? 'Forecast ran high on average' : 'Forecast ran low on average'} />
        <KpiCard label="WAPE" value={formatPct(o.wape_pct)} hint="Total error ÷ total wind" />
      </div>
      <div className="grid-2">
        <div className="panel">
          <h3>Error by delivery day</h3>
          <p className="panel-hint">Click a bar to inspect that day above.</p>
          <DailyErrorChart days={summary.days} selectedDecisionDate={selectedDecisionDate} onSelect={onSelectDay} />
        </div>
        {summary.error_percentiles && (
          <ErrorBand p10={summary.error_percentiles.p10_mw} p50={summary.error_percentiles.p50_mw}
            p90={summary.error_percentiles.p90_mw} />
        )}
      </div>
      <div className="panel">
        <h3>Error by hour of day</h3>
        <HourOfDayChart rows={summary.mae_by_hour} />
      </div>
    </>
  )
}
