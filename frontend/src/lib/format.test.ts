import { formatClock, formatDateLong, formatGw, formatGwh, formatPct, formatPublished, formatSignedGw } from './format'

describe('format helpers', () => {
  it('formats megawatts as gigawatts', () => {
    expect(formatGw(12345)).toBe('12.3 GW')
    expect(formatGw(12345, 2)).toBe('12.35 GW')
  })

  it('shows a dash for missing values', () => {
    expect(formatGw(null)).toBe('—')
    expect(formatSignedGw(undefined)).toBe('—')
    expect(formatPct(null)).toBe('—')
  })

  it('signs positive and negative errors explicitly', () => {
    expect(formatSignedGw(1500)).toBe('+1.5 GW')
    expect(formatSignedGw(-1500)).toBe('−1.5 GW')
    expect(formatSignedGw(0)).toBe('0.0 GW')
  })

  it('formats percentages and energy', () => {
    expect(formatPct(9.8586)).toBe('9.9%')
    expect(formatGwh(254300)).toBe('254 GWh')
  })

  it('renders times and dates in UTC regardless of local zone', () => {
    expect(formatClock('2026-01-14T07:30:00Z')).toBe('07:30')
    expect(formatDateLong('2026-01-15')).toBe('Thu 15 Jan 2026')
    expect(formatPublished('2026-01-14T07:30:00Z')).toBe('07:30 UTC, 14 Jan')
  })
})
