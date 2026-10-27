import type { Plan } from '../api/client'
import { parseDemand, planTotals, purchaseRange } from './planning'

const plan: Plan = {
  history_days: 5,
  p10_error_mw: -500,
  p50_error_mw: 1000,
  p90_error_mw: 3000,
  hours: [
    { time: '2026-01-15T00:00:00Z', plan_mw: 9000, low_mw: 7000, high_mw: 10500 },
    { time: '2026-01-15T01:00:00Z', plan_mw: 11000, low_mw: 9000, high_mw: 12500 },
  ],
}

describe('planTotals', () => {
  it('sums hourly MW into GWh for plan, low and high', () => {
    expect(planTotals(plan)).toEqual({ planGwh: 20, lowGwh: 16, highGwh: 23 })
  })
})

describe('purchaseRange', () => {
  it('subtracts planned wind from demand and flips the range', () => {
    expect(purchaseRange(100, { planGwh: 20, lowGwh: 16, highGwh: 23 })).toEqual({ purchaseGwh: 80, minGwh: 77, maxGwh: 84 })
  })

  it('never suggests a negative purchase', () => {
    expect(purchaseRange(18, { planGwh: 20, lowGwh: 16, highGwh: 23 })).toEqual({ purchaseGwh: 0, minGwh: 0, maxGwh: 2 })
  })
})

describe('parseDemand', () => {
  it('accepts plausible positive numbers', () => {
    expect(parseDemand('750')).toBe(750)
    expect(parseDemand('0')).toBe(0)
    expect(parseDemand(' 812.5 ')).toBe(812.5)
  })

  it('rejects empty, invalid, negative and implausible input', () => {
    expect(parseDemand('')).toBeNull()
    expect(parseDemand('abc')).toBeNull()
    expect(parseDemand('-5')).toBeNull()
    expect(parseDemand('5001')).toBeNull()
    expect(parseDemand('Infinity')).toBeNull()
  })
})
