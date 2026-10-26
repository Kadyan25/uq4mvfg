import type { MetaResponse } from '../api/client'
import { DEFINITIONS } from '../lib/definitions'
import { formatDateLong, nextDate } from '../lib/format'
import { InfoTip } from './InfoTip'

interface Props {
  meta: MetaResponse
  decisionDate: string
  cutoff: string
  onDecisionDateChange: (value: string) => void
  onCutoffChange: (value: string) => void
}

export function Controls({ meta, decisionDate, cutoff, onDecisionDateChange, onCutoffChange }: Props) {
  return (
    <section className="controls" aria-label="Filters">
      <label className="field">
        <span className="field-label">Decision date</span>
        <input
          type="date"
          value={decisionDate}
          min={meta.first_decision_date}
          max={meta.last_decision_date}
          required
          onChange={(e) => e.target.value && onDecisionDateChange(e.target.value)}
        />
      </label>
      <div className="field">
        <span className="field-label">
          <label htmlFor="gate-closure">Gate closure (UTC)</label>
          <InfoTip text={DEFINITIONS.gateClosure} />
        </span>
        <input
          id="gate-closure"
          type="time"
          value={cutoff}
          step={60}
          required
          onChange={(e) => e.target.value && onCutoffChange(e.target.value.slice(0, 5))}
        />
      </div>
      <div className="field">
        <span className="field-label">Delivery date</span>
        <span className="field-static">{formatDateLong(nextDate(decisionDate))}</span>
      </div>
      {cutoff !== meta.default_cutoff && (
        <button type="button" className="secondary-button" onClick={() => onCutoffChange(meta.default_cutoff)}>
          Reset to {meta.default_cutoff}
        </button>
      )}
    </section>
  )
}
