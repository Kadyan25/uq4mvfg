import { CartesianGrid, Line, LineChart, ResponsiveContainer, XAxis, YAxis } from 'recharts'
import type { RunsResponse, SeriesPoint } from '../api/client'
import { DEFINITIONS } from '../lib/definitions'
import { formatClock, formatPublished } from '../lib/format'
import { mergeRuns, runKey } from '../lib/series'
import { InfoTip } from './InfoTip'

const HOUR_MS = 3_600_000

interface Props {
  runs: RunsResponse
  actuals: SeriesPoint[]
}

function runStyle(run: RunsResponse['runs'][number]) {
  if (run.is_decision_run) return { stroke: 'var(--forecast)', strokeWidth: 2.5, strokeOpacity: 1 }
  if (run.after_cutoff) return { stroke: 'var(--muted)', strokeWidth: 1, strokeOpacity: 0.7, strokeDasharray: '4 4' }
  return { stroke: 'var(--bar)', strokeWidth: 1, strokeOpacity: 0.6 }
}

export function RunsChart({ runs, actuals }: Props) {
  const data = mergeRuns(runs.runs, actuals)
  const tick = (t: number) => formatClock(new Date(t).toISOString())
  const ticks = data.map((r) => r.t).filter((t) => t % (3 * HOUR_MS) === 0)
  const decision = runs.runs.find((r) => r.is_decision_run)

  return (
    <div className="panel">
      <h3>
        Forecast runs for this delivery date
        <InfoTip text={DEFINITIONS.runs} />
      </h3>
      <ul className="runs-legend">
        <li><span className="swatch swatch-decision" />Used at gate closure{decision && ` (${formatPublished(decision.publish_time)})`}</li>
        <li><span className="swatch swatch-earlier" />Earlier runs</li>
        <li><span className="swatch swatch-later" />Published after gate closure</li>
        <li><span className="swatch swatch-actual" />Outturn</li>
      </ul>
      <div className="chart chart-flat" role="img"
        aria-label={`${runs.runs.length} forecast runs for ${runs.delivery_date} compared with outturn`}>
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="t" type="number" scale="time" domain={['dataMin', 'dataMax']} ticks={ticks}
              tickFormatter={tick} stroke="var(--muted)" fontSize={12} />
            <YAxis tickFormatter={(v: number) => (v / 1000).toFixed(0)} stroke="var(--muted)" fontSize={12} width={40}
              label={{ value: 'GW', angle: -90, position: 'insideLeft', fill: 'var(--muted)', fontSize: 12 }} />
            {runs.runs.map((run, i) => (
              <Line key={run.publish_time} dataKey={runKey(i)} dot={false} connectNulls isAnimationActive={false}
                {...runStyle(run)} />
            ))}
            <Line dataKey="actual" stroke="var(--actual)" strokeWidth={2} dot={false} connectNulls
              isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
