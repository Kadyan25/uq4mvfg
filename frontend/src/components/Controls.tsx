import type { MetaResponse } from '../api/client'
import { formatDateLong } from '../lib/format'

interface Props {
  meta: MetaResponse
  decisionDate: string
  cutoff: string
  onDecisionDateChange: (value: string) => void
  onCutoffChange: (value: string) => void
}

function addDay(isoDate: string): string {
  const d = new Date(`${isoDate}T00:00:00Z`)
  d.setUTCDate(d.getUTCDate() + 1)
  return d.toISOString().slice(0, 10)
}

export function Controls({ meta, decisionDate, cutoff, onDecisionDateChange, onCutoffChange }: Props) {
  const isDefaultCutoff = cutoff === meta.default_cutoff

  return (
    <section className="controls" aria-label="Decision settings">
      <label className="field">
        <span className="field-label">Decision day</span>
        <input
          type="date"
          value={decisionDate}
          min={meta.first_decision_date}
          max={meta.last_decision_date}
          required
          onChange={(e) => e.target.value && onDecisionDateChange(e.target.value)}
        />
      </label>
      <label className="field">
        <span className="field-label">Decision cutoff (UTC)</span>
        <input
          type="time"
          value={cutoff}
          step={60}
          required
          onChange={(e) => e.target.value && onCutoffChange(e.target.value.slice(0, 5))}
        />
      </label>
      <div className="field">
        <span className="field-label">Delivery day</span>
        <span className="field-static">{formatDateLong(addDay(decisionDate))}</span>
      </div>
      <p className="controls-note">
        {isDefaultCutoff ? (
          <>Default cutoff {meta.default_cutoff} UTC matches GB day-ahead auction gate closure.</>
        ) : (
          <>
            Custom cutoff.{' '}
            <button type="button" className="link-button" onClick={() => onCutoffChange(meta.default_cutoff)}>
              Reset to {meta.default_cutoff} gate closure
            </button>
          </>
        )}
      </p>
    </section>
  )
}
