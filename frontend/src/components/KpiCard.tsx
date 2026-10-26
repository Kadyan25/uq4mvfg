interface Props {
  label: string
  value: string
  hint?: string
}

export function KpiCard({ label, value, hint }: Props) {
  return (
    <div className="kpi">
      <span className="kpi-label">{label}</span>
      <span className="kpi-value">{value}</span>
      {hint && <span className="kpi-hint">{hint}</span>}
    </div>
  )
}
