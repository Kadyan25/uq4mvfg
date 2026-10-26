import type { SummaryResponse } from '../api/client'
import { DEFINITIONS } from '../lib/definitions'
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
  if (!o) return <p className="empty">No data for this period.</p>

  return (
    <>
      <div className="kpis">
        <KpiCard label="MAE" value={formatGw(o.mae_mw, 2)} hint={`${o.count} hours`} info={DEFINITIONS.mae} />
        <KpiCard label="RMSE" value={formatGw(o.rmse_mw, 2)} info={DEFINITIONS.rmse} />
        <KpiCard label="Bias" value={formatSignedGw(o.bias_mw, 2)} info={DEFINITIONS.bias} />
        <KpiCard label="WAPE" value={formatPct(o.wape_pct)} info={DEFINITIONS.wape} />
      </div>
      <div className="grid-2">
        <div className="panel">
          <h3>MAE by delivery date</h3>
          <DailyErrorChart days={summary.days} selectedDecisionDate={selectedDecisionDate} onSelect={onSelectDay} />
        </div>
        {summary.error_percentiles && (
          <ErrorBand p10={summary.error_percentiles.p10_mw} p50={summary.error_percentiles.p50_mw}
            p90={summary.error_percentiles.p90_mw} />
        )}
      </div>
      <div className="panel">
        <h3>MAE by hour (UTC)</h3>
        <HourOfDayChart rows={summary.mae_by_hour} />
      </div>
    </>
  )
}
