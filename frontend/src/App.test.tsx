import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'
import App from './App'
import type { DayResponse, SummaryResponse } from './api/client'

const meta = { first_decision_date: '2026-01-01', last_decision_date: '2026-01-31', default_cutoff: '09:20' }

const day: DayResponse = {
  decision_date: '2026-01-01',
  delivery_date: '2026-01-02',
  cutoff: '2026-01-01T09:20:00Z',
  forecast_publish_time: '2026-01-01T07:30:00Z',
  lead_time_hours: 16.5,
  forecast: [{ time: '2026-01-02T00:00:00Z', mw: 11000 }],
  actuals: [{ time: '2026-01-02T00:00:00Z', mw: 10000 }, { time: '2026-01-02T00:30:00Z', mw: 10000 }],
  hourly: [{ time: '2026-01-02T00:00:00Z', forecast_mw: 11000, actual_mw: 10000, error_mw: 1000 }],
  metrics: { count: 1, mae_mw: 1000, rmse_mw: 1000, bias_mw: 1000, wape_pct: 10 },
}

const summary: SummaryResponse = {
  cutoff: '09:20',
  days: [{ decision_date: '2026-01-01', delivery_date: '2026-01-02', forecast_publish_time: '2026-01-01T07:30:00Z', metrics: day.metrics }],
  overall: { count: 744, mae_mw: 2040, rmse_mw: 2500, bias_mw: 1750, wape_pct: 18.1 },
  error_percentiles: { p10_mw: -550, p50_mw: 1590, p90_mw: 4100 },
  mae_by_hour: [{ hour: 0, mae_mw: 1900 }],
}

function json(body: unknown, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }))
}

function mockApi(overrides: { day?: () => Promise<Response> } = {}) {
  const fetchMock = vi.fn((input: RequestInfo | URL) => {
    const url = String(input)
    if (url.startsWith('/api/meta')) return json(meta)
    if (url.startsWith('/api/day')) return overrides.day ? overrides.day() : json(day)
    if (url.startsWith('/api/summary')) return json(summary)
    return json({ detail: 'not found' }, 404)
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

afterEach(() => vi.unstubAllGlobals())

describe('App', () => {
  it('shows which forecast run was used and its accuracy', async () => {
    mockApi()
    render(<App />)

    expect(await screen.findByText('07:30 UTC, 1 Jan')).toBeInTheDocument()
    expect(screen.getByText(/16\.5 h before delivery/)).toBeInTheDocument()
    expect(screen.getByText('Fri 2 Jan 2026')).toBeInTheDocument()
    expect(screen.getByText('+1.00 GW')).toBeInTheDocument()
  })

  it('shows the month summary and buying guidance', async () => {
    mockApi()
    render(<App />)

    expect(await screen.findByText('How much wind to hold back on')).toBeInTheDocument()
    expect(screen.getByText('4.1 GW')).toBeInTheDocument()
    expect(screen.getByText('Across 744 hours')).toBeInTheDocument()
  })

  it('requests the default gate-closure cutoff', async () => {
    const fetchMock = mockApi()
    render(<App />)

    await screen.findByText('07:30 UTC, 1 Jan')
    const dayCall = fetchMock.mock.calls.map(([u]) => String(u)).find((u) => u.startsWith('/api/day'))
    expect(dayCall).toBe('/api/day?decision_date=2026-01-01&cutoff=09%3A20')
  })

  it('surfaces a readable error when the API fails', async () => {
    mockApi({ day: () => json({ detail: 'Upstream data source is unavailable, please retry shortly' }, 502) })
    render(<App />)

    expect(await screen.findByRole('alert')).toHaveTextContent('Upstream data source is unavailable')
  })

  it('explains when no forecast existed before the cutoff', async () => {
    mockApi({ day: () => json({ ...day, forecast_publish_time: null, forecast: [], hourly: [], metrics: null, cutoff: '2026-01-01T01:00:00Z' }) })
    render(<App />)

    expect(await screen.findByText(/No wind forecast had been published by 01:00 UTC/)).toBeInTheDocument()
  })

  it('offers a reset after changing the cutoff', async () => {
    const fetchMock = mockApi()
    render(<App />)
    const input = await screen.findByLabelText('Decision cutoff (UTC)')

    // jsdom can't type into time inputs, so set the value the way the browser would.
    fireEvent.change(input, { target: { value: '06:00' } })

    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([u]) => String(u))).toContain('/api/summary?cutoff=06%3A00'),
    )
    await userEvent.click(screen.getByRole('button', { name: /Reset to 09:20/ }))
    expect(input).toHaveValue('09:20')
    expect(screen.queryByRole('button', { name: /Reset to/ })).not.toBeInTheDocument()
  })
})
