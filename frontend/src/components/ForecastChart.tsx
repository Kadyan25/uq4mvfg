import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { SeriesPoint } from '../api/client'
import { formatClock, formatGw } from '../lib/format'
import { mergeSeries } from '../lib/series'

interface Props {
  forecast: SeriesPoint[]
  actuals: SeriesPoint[]
}

export function ForecastChart({ forecast, actuals }: Props) {
  const data = mergeSeries(forecast, actuals)
  const tick = (t: number) => formatClock(new Date(t).toISOString())

  return (
    <div className="chart" role="img" aria-label="Forecast versus actual wind generation for the delivery day">
      <ResponsiveContainer width="100%" height={320}>
        <LineChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <XAxis dataKey="t" type="number" scale="time" domain={['dataMin', 'dataMax']} tickFormatter={tick}
            stroke="var(--muted)" fontSize={12} />
          <YAxis tickFormatter={(v: number) => (v / 1000).toFixed(0)} stroke="var(--muted)" fontSize={12} width={40}
            label={{ value: 'GW', angle: -90, position: 'insideLeft', fill: 'var(--muted)', fontSize: 12 }} />
          <Tooltip
            labelFormatter={(t) => `${tick(Number(t))} UTC`}
            formatter={(v, name) => [formatGw(Number(v), 2), name]}
            contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8 }}
          />
          <Legend />
          <Line name="Actual (half-hourly)" dataKey="actual" stroke="var(--actual)" strokeWidth={2} dot={false}
            connectNulls isAnimationActive={false} />
          <Line name="Forecast at decision time (hourly)" dataKey="forecast" stroke="var(--forecast)" strokeWidth={2}
            strokeDasharray="6 4" dot={{ r: 2 }} connectNulls isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
