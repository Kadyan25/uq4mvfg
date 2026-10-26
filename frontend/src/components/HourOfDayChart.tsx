import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { formatGw } from '../lib/format'

interface Props {
  rows: { hour: number; mae_mw: number }[]
}

export function HourOfDayChart({ rows }: Props) {
  const data = rows.map((r) => ({ label: `${String(r.hour).padStart(2, '0')}:00`, mae: r.mae_mw }))

  return (
    <div className="chart" role="img" aria-label="MAE by hour of day">
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <XAxis dataKey="label" stroke="var(--muted)" fontSize={11} interval={2} />
          <YAxis tickFormatter={(v: number) => (v / 1000).toFixed(1)} stroke="var(--muted)" fontSize={12} width={40} />
          <Tooltip
            cursor={{ fill: 'var(--hover)' }}
            contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8 }}
            formatter={(v) => [formatGw(Number(v), 2), 'MAE']}
            labelFormatter={(label) => `${label} UTC`}
          />
          <Bar dataKey="mae" fill="var(--bar)" radius={[3, 3, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
