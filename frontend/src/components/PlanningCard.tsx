import { useState } from 'react'
import type { DayResponse } from '../api/client'
import { DEFINITIONS } from '../lib/definitions'
import { formatGw } from '../lib/format'
import { MAX_DEMAND_GWH, parseDemand, planTotals, purchaseRange } from '../lib/planning'
import { InfoTip } from './InfoTip'

interface Props {
  day: DayResponse
  minHistoryDays: number
}

const gwh = (v: number) => `${v.toFixed(0)} GWh`
const signedGwh = (v: number) => `${v > 0 ? '+' : v < 0 ? '−' : ''}${Math.abs(v).toFixed(0)} GWh`

export function PlanningCard({ day, minHistoryDays }: Props) {
  const [demandInput, setDemandInput] = useState('')

  if (!day.plan) {
    return (
      <div className="planning planning-empty">
        <h3>Planning estimate</h3>
        <p>Not enough history yet: needs {minHistoryDays} completed delivery dates, has {day.history_days}.</p>
      </div>
    )
  }

  const totals = planTotals(day.plan)
  const forecastGwh = day.forecast.reduce((s, p) => s + p.mw, 0) / 1000
  const outturnGwh = day.hourly.length === 24 ? day.hourly.reduce((s, h) => s + h.actual_mw, 0) / 1000 : null
  const demand = parseDemand(demandInput)
  const purchase = demand === null ? null : purchaseRange(demand, totals)

  return (
    <div className="planning">
      <h3>
        Planning estimate
        <InfoTip text={DEFINITIONS.plan} />
      </h3>
      <div className="planning-grid">
        <div className="planning-main">
          <span className="kpi-label">Wind to plan for</span>
          <span className="planning-value">{gwh(totals.planGwh)}</span>
          <span className="kpi-hint">Range {gwh(totals.lowGwh)} – {gwh(totals.highGwh)} (P10–P90)</span>
          <span className="kpi-hint">
            Forecast {gwh(forecastGwh)} · adjusted {signedGwh(totals.planGwh - forecastGwh)} from {day.plan.history_days} prior days
          </span>
          {outturnGwh !== null && day.plan_metrics && day.metrics && (
            <span className="kpi-hint">
              Outturn {gwh(outturnGwh)} · MAE plan {formatGw(day.plan_metrics.mae_mw, 2)} vs forecast {formatGw(day.metrics.mae_mw, 2)}
            </span>
          )}
        </div>
        <div className="planning-demand">
          <label className="field">
            <span className="field-label">Expected demand (GWh)</span>
            <input type="number" inputMode="decimal" min={0} max={MAX_DEMAND_GWH} step="any" placeholder="e.g. 750"
              value={demandInput} onChange={(e) => setDemandInput(e.target.value)}
              aria-invalid={demandInput !== '' && demand === null} />
          </label>
          {purchase && (
            <div className="planning-purchase" aria-live="polite">
              <span className="kpi-label">Suggested purchase</span>
              <span className="planning-value">{gwh(purchase.purchaseGwh)}</span>
              <span className="kpi-hint">Range {gwh(purchase.minGwh)} – {gwh(purchase.maxGwh)}</span>
            </div>
          )}
          {demandInput !== '' && demand === null && (
            <span className="field-error">Enter a demand between 0 and {MAX_DEMAND_GWH} GWh.</span>
          )}
        </div>
      </div>
      <p className="planning-caveat">
        Indicative only. Based on how the forecast performed on previous delivery dates; it cannot anticipate tomorrow&rsquo;s
        weather. Use alongside your own judgement.
      </p>
    </div>
  )
}
