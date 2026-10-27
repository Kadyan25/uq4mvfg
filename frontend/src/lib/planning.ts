import type { Plan } from '../api/client'

export interface PlanTotals {
  planGwh: number
  lowGwh: number
  highGwh: number
}

export interface PurchaseRange {
  purchaseGwh: number
  minGwh: number
  maxGwh: number
}

// Hourly values are average MW over the hour, so summing gives MWh.
export function planTotals(plan: Plan): PlanTotals {
  const sum = (pick: (h: Plan['hours'][number]) => number) => plan.hours.reduce((s, h) => s + pick(h), 0) / 1000
  return { planGwh: sum((h) => h.plan_mw), lowGwh: sum((h) => h.low_mw), highGwh: sum((h) => h.high_mw) }
}

/** Demand minus wind. More wind means less to buy, so the wind range flips into the purchase range. */
export function purchaseRange(demandGwh: number, totals: PlanTotals): PurchaseRange {
  const buy = (wind: number) => Math.max(demandGwh - wind, 0)
  return { purchaseGwh: buy(totals.planGwh), minGwh: buy(totals.highGwh), maxGwh: buy(totals.lowGwh) }
}

export const MAX_DEMAND_GWH = 5000

/** Parses the demand box; returns null for empty, non-numeric, negative or implausibly large input. */
export function parseDemand(raw: string): number | null {
  if (raw.trim() === '') return null
  const value = Number(raw)
  if (!Number.isFinite(value) || value < 0 || value > MAX_DEMAND_GWH) return null
  return value
}
