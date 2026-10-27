import { Area, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { PlanHour, SeriesPoint } from '../api/client'
import { formatClock, formatGw } from '../lib/format'
import { mergeSeries } from '../lib/series'

const HOUR_MS = 3_600_000

interface Props {
  forecast: SeriesPoint[]
  actuals: SeriesPoint[]
  plan?: PlanHour[]
}

function formatValue(value: unknown): string {
  if (Array.isArray(value)) return `${formatGw(Number(value[0]), 2)} – ${formatGw(Number(value[1]), 2)}`
  return formatGw(Number(value), 2)
}

export function ForecastChart({ forecast, actuals, plan = [] }: Props) {
  const data = mergeSeries(forecast, actuals, plan)
  const tick = (t: number) => formatClock(new Date(t).toISOString())
  const ticks = data.map((r) => r.t).filter((t) => t % (3 * HOUR_MS) === 0)
  const hasPlan = plan.length > 0

  return (
    <div className="chart" role="img" aria-label="Forecast, planning range and outturn for the delivery date">
      <ResponsiveContainer width="100%" height={340}>
        <ComposedChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <XAxis dataKey="t" type="number" scale="time" domain={['dataMin', 'dataMax']} ticks={ticks} tickFormatter={tick}
            stroke="var(--muted)" fontSize={12} />
          <YAxis tickFormatter={(v: number) => (v / 1000).toFixed(0)} stroke="var(--muted)" fontSize={12} width={40}
            label={{ value: 'GW', angle: -90, position: 'insideLeft', fill: 'var(--muted)', fontSize: 12 }} />
          <Tooltip
            labelFormatter={(t) => `${tick(Number(t))} UTC`}
            formatter={(v, name) => [formatValue(v), name]}
            contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8 }}
          />
          <Legend />
          {hasPlan && (
            <Area name="Plan range (P10–P90)" dataKey="range" stroke="none" fill="var(--plan)" fillOpacity={0.16}
              connectNulls isAnimationActive={false} />
          )}
          <Line name="Outturn (30 min)" dataKey="actual" stroke="var(--actual)" strokeWidth={2} dot={false}
            connectNulls isAnimationActive={false} />
          <Line name="Forecast (hourly)" dataKey="forecast" stroke="var(--forecast)" strokeWidth={2}
            strokeDasharray="6 4" dot={{ r: 2 }} connectNulls isAnimationActive={false} />
          {hasPlan && (
            <Line name="Plan" dataKey="plan" stroke="var(--plan)" strokeWidth={2} dot={false}
              connectNulls isAnimationActive={false} />
          )}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}
