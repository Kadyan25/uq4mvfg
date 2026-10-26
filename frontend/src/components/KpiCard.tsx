import { InfoTip } from './InfoTip'

interface Props {
  label: string
  value: string
  hint?: string
  info?: string
}

export function KpiCard({ label, value, hint, info }: Props) {
  return (
    <div className="kpi">
      <span className="kpi-label">
        {label}
        {info && <InfoTip text={info} />}
      </span>
      <span className="kpi-value">{value}</span>
      {hint && <span className="kpi-hint">{hint}</span>}
    </div>
  )
}
