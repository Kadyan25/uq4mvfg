import { mergeSeries } from './series'

describe('mergeSeries', () => {
  it('joins hourly forecast and half-hourly actuals on one sorted time axis', () => {
    const rows = mergeSeries(
      [{ time: '2026-01-15T01:00:00Z', mw: 900 }, { time: '2026-01-15T00:00:00Z', mw: 1000 }],
      [
        { time: '2026-01-15T00:00:00Z', mw: 1100 },
        { time: '2026-01-15T00:30:00Z', mw: 1050 },
        { time: '2026-01-15T01:00:00Z', mw: 950 },
      ],
    )

    expect(rows).toEqual([
      { t: Date.parse('2026-01-15T00:00:00Z'), forecast: 1000, actual: 1100 },
      { t: Date.parse('2026-01-15T00:30:00Z'), actual: 1050 },
      { t: Date.parse('2026-01-15T01:00:00Z'), forecast: 900, actual: 950 },
    ])
  })

  it('adds plan value and P10–P90 range on the forecast hours', () => {
    const rows = mergeSeries(
      [{ time: '2026-01-15T00:00:00Z', mw: 1000 }],
      [{ time: '2026-01-15T00:30:00Z', mw: 950 }],
      [{ time: '2026-01-15T00:00:00Z', plan_mw: 900, low_mw: 600, high_mw: 1100 }],
    )

    expect(rows).toEqual([
      { t: Date.parse('2026-01-15T00:00:00Z'), forecast: 1000, plan: 900, range: [600, 1100] },
      { t: Date.parse('2026-01-15T00:30:00Z'), actual: 950 },
    ])
  })

  it('returns an empty list when there is no data', () => {
    expect(mergeSeries([], [])).toEqual([])
  })
})
