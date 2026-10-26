import { formatGw, formatSignedGw } from '../lib/format'

interface Props {
  p10: number
  p50: number
  p90: number
}

/** Turns signed error percentiles (forecast − actual) into plain buying guidance. */
export function ErrorBand({ p10, p50, p90 }: Props) {
  return (
    <div className="band">
      <h3>How much wind to hold back on</h3>
      <p className="band-lead">
        In 9 out of 10 hours, actual wind came in no more than <strong>{formatGw(Math.max(p90, 0))}</strong> below
        the decision-time forecast.
      </p>
      <dl className="band-grid">
        <div>
          <dt>P10 error</dt>
          <dd>{formatSignedGw(p10)}</dd>
        </div>
        <div>
          <dt>Median error</dt>
          <dd>{formatSignedGw(p50)}</dd>
        </div>
        <div>
          <dt>P90 error</dt>
          <dd>{formatSignedGw(p90)}</dd>
        </div>
      </dl>
      <p className="band-note">
        Error = forecast − actual. Positive means the forecast promised more wind than arrived, so extra power had to
        be bought.
      </p>
    </div>
  )
}
