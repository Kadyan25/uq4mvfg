import { DEFINITIONS } from '../lib/definitions'
import { formatGw, formatSignedGw } from '../lib/format'
import { InfoTip } from './InfoTip'

interface Props {
  p10: number
  p50: number
  p90: number
}

export function ErrorBand({ p10, p50, p90 }: Props) {
  return (
    <div className="band">
      <h3>
        Error distribution
        <InfoTip text={DEFINITIONS.distribution} />
      </h3>
      <dl className="band-grid">
        <div>
          <dt>P10</dt>
          <dd>{formatSignedGw(p10)}</dd>
        </div>
        <div>
          <dt>P50</dt>
          <dd>{formatSignedGw(p50)}</dd>
        </div>
        <div>
          <dt>P90</dt>
          <dd>{formatSignedGw(p90)}</dd>
        </div>
      </dl>
      <p className="band-lead">
        P90 over-forecast <strong>{formatGw(Math.max(p90, 0))}</strong>
      </p>
      <p className="band-note">Error = forecast − outturn</p>
    </div>
  )
}
