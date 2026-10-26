// Built by hand rather than via Intl so output is identical across browsers and ICU versions.
const WEEKDAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

const pad = (n: number) => String(n).padStart(2, '0')
const utcDate = (isoDate: string) => new Date(`${isoDate.slice(0, 10)}T00:00:00Z`)

export function formatGw(mw: number | null | undefined, digits = 1): string {
  if (mw == null || Number.isNaN(mw)) return '—'
  return `${(mw / 1000).toFixed(digits)} GW`
}

export function formatSignedGw(mw: number | null | undefined, digits = 1): string {
  if (mw == null || Number.isNaN(mw)) return '—'
  const sign = mw > 0 ? '+' : mw < 0 ? '−' : ''
  return `${sign}${Math.abs(mw / 1000).toFixed(digits)} GW`
}

export function formatPct(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return '—'
  return `${value.toFixed(1)}%`
}

export function formatClock(iso: string): string {
  const d = new Date(iso)
  return `${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}`
}

export function formatDateLong(isoDate: string): string {
  const d = utcDate(isoDate)
  return `${WEEKDAYS[d.getUTCDay()]} ${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]} ${d.getUTCFullYear()}`
}

export function formatDateShort(isoDate: string): string {
  const d = utcDate(isoDate)
  return `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]}`
}

export function formatPublished(iso: string): string {
  return `${formatClock(iso)} UTC · ${formatDateShort(iso)}`
}

export function nextDate(isoDate: string): string {
  const d = utcDate(isoDate)
  d.setUTCDate(d.getUTCDate() + 1)
  return d.toISOString().slice(0, 10)
}
