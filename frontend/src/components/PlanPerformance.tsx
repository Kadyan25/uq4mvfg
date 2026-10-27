import type { Metrics } from '../api/client'
import { DEFINITIONS } from '../lib/definitions'
import { formatGw, formatPct, formatSignedGw } from '../lib/format'
import { InfoTip } from './InfoTip'

interface Props {
  plan: Metrics
  baseline: Metrics
  rangeHitPct: number | null
  planDays: number
}

export function PlanPerformance({ plan, baseline, rangeHitPct, planDays }: Props) {
  const improvement = baseline.mae_mw > 0 ? (1 - plan.mae_mw / baseline.mae_mw) * 100 : null

  return (
    <div className="panel">
      <h3>
        Planning estimate vs forecast
        <InfoTip text={DEFINITIONS.planPerformance} />
      </h3>
      <dl className="compare-grid">
        <div>
          <dt>MAE</dt>
          <dd>{formatGw(plan.mae_mw, 2)} <span className="vs">vs {formatGw(baseline.mae_mw, 2)}</span></dd>
          {improvement !== null && <span className="kpi-hint">{improvement.toFixed(0)}% lower</span>}
        </div>
        <div>
          <dt>Bias</dt>
          <dd>{formatSignedGw(plan.bias_mw, 2)} <span className="vs">vs {formatSignedGw(baseline.bias_mw, 2)}</span></dd>
        </div>
        <div>
          <dt>Outturn inside P10–P90</dt>
          <dd>{formatPct(rangeHitPct)}</dd>
          <span className="kpi-hint">Target 80%</span>
        </div>
        <div>
          <dt>Evaluated</dt>
          <dd>{planDays} {planDays === 1 ? 'date' : 'dates'}</dd>
          <span className="kpi-hint">{plan.count} hours</span>
        </div>
      </dl>
    </div>
  )
}
