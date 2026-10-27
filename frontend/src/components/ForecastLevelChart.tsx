import { Bar, BarChart, CartesianGrid, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { LevelBucket } from '../api/client'
import { formatGw, formatSignedGw } from '../lib/format'

interface Props {
  buckets: LevelBucket[]
}

export function ForecastLevelChart({ buckets }: Props) {
  const data = buckets.map((b) => ({
    label: `${b.low_mw / 1000}–${b.high_mw / 1000}`,
    bias: b.bias_mw,
    mae: b.mae_mw,
    count: b.count,
  }))

  return (
    <div className="chart chart-flat" role="img" aria-label="Forecast bias by forecast level">
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} margin={{ top: 8, right: 16, bottom: 12, left: 0 }}>
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <XAxis dataKey="label" stroke="var(--muted)" fontSize={12}
            label={{ value: 'Forecast level (GW)', position: 'insideBottom', offset: -6, fill: 'var(--muted)', fontSize: 12 }} />
          <YAxis tickFormatter={(v: number) => (v / 1000).toFixed(1)} stroke="var(--muted)" fontSize={12} width={40}
            label={{ value: 'GW', angle: -90, position: 'insideLeft', fill: 'var(--muted)', fontSize: 12 }} />
          <ReferenceLine y={0} stroke="var(--muted)" />
          <Tooltip
            cursor={{ fill: 'var(--hover)' }}
            contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8 }}
            formatter={(v, _name, item) => [
              `${formatSignedGw(Number(v), 2)} (MAE ${formatGw(item.payload.mae, 2)}, ${item.payload.count} h)`,
              'Bias',
            ]}
            labelFormatter={(label) => `Forecast ${label} GW`}
          />
          <Bar dataKey="bias" fill="var(--forecast)" radius={[3, 3, 0, 0]} isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
