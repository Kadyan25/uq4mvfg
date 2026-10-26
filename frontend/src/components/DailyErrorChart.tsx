import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { DaySummaryRow } from '../api/client'
import { formatDateShort, formatGw, formatSignedGw } from '../lib/format'

interface Props {
  days: DaySummaryRow[]
  selectedDecisionDate: string
  onSelect: (decisionDate: string) => void
}

export function DailyErrorChart({ days, selectedDecisionDate, onSelect }: Props) {
  const data = days.map((d) => ({
    decision: d.decision_date,
    label: formatDateShort(d.delivery_date),
    mae: d.metrics?.mae_mw ?? null,
    bias: d.metrics?.bias_mw ?? null,
  }))

  return (
    <div className="chart" role="img" aria-label="MAE by delivery date">
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <XAxis dataKey="label" stroke="var(--muted)" fontSize={11} interval="preserveStartEnd" minTickGap={12} />
          <YAxis tickFormatter={(v: number) => (v / 1000).toFixed(1)} stroke="var(--muted)" fontSize={12} width={40}
            label={{ value: 'GW', angle: -90, position: 'insideLeft', fill: 'var(--muted)', fontSize: 12 }} />
          <Tooltip
            cursor={{ fill: 'var(--hover)' }}
            contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8 }}
            formatter={(v, _name, item) => [
              `${formatGw(Number(v), 2)} (bias ${formatSignedGw(item.payload.bias, 2)})`,
              'MAE',
            ]}
            labelFormatter={(label) => `Delivery ${label}`}
          />
          <Bar dataKey="mae" radius={[3, 3, 0, 0]} cursor="pointer"
            onClick={(entry) => onSelect((entry.payload as { decision: string }).decision)}>
            {data.map((d) => (
              <Cell key={d.decision} fill={d.decision === selectedDecisionDate ? 'var(--accent)' : 'var(--bar)'} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
