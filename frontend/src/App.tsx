import { useState } from 'react'
import { api } from './api/client'
import type { MetaResponse } from './api/client'
import { Controls } from './components/Controls'
import { DayView } from './components/DayView'
import { PeriodView } from './components/PeriodView'
import { useAsync } from './hooks/useAsync'

function Status({ state }: { state: { status: string; error?: string } }) {
  if (state.status === 'loading') return <p className="status" role="status">Loading…</p>
  if (state.status === 'error') return <p className="status status-error" role="alert">{state.error}</p>
  return null
}

function Dashboard({ meta }: { meta: MetaResponse }) {
  const [decisionDate, setDecisionDate] = useState(meta.first_decision_date)
  const [cutoff, setCutoff] = useState(meta.default_cutoff)
  const day = useAsync((signal) => api.day(decisionDate, cutoff, signal), [decisionDate, cutoff])
  const summary = useAsync((signal) => api.summary(cutoff, signal), [cutoff])

  return (
    <>
      <Controls meta={meta} decisionDate={decisionDate} cutoff={cutoff}
        onDecisionDateChange={setDecisionDate} onCutoffChange={setCutoff} />

      <section className="section" aria-labelledby="day-title">
        <h2 id="day-title">What the buying desk would have seen</h2>
        <p className="section-lead">The latest wind forecast published before the cutoff, against what the wind actually did.</p>
        {day.status === 'success' ? <DayView day={day.data} /> : <Status state={day} />}
      </section>

      <section className="section" aria-labelledby="period-title">
        <h2 id="period-title">How far can you trust it? January 2026</h2>
        <p className="section-lead">Forecast accuracy at the same cutoff, across every decision day in the month.</p>
        {summary.status === 'success'
          ? <PeriodView summary={summary.data} selectedDecisionDate={decisionDate} onSelectDay={setDecisionDate} />
          : <Status state={summary} />}
      </section>
    </>
  )
}

export default function App() {
  const meta = useAsync((signal) => api.meta(signal), [])

  return (
    <div className="page">
      <header className="header">
        <h1>UK Wind: Day-Ahead Forecast Check</h1>
        <p>National wind generation forecasts vs. outturn, from Elexon BMRS. All times UTC.</p>
      </header>
      <main>
        {meta.status === 'success' ? <Dashboard meta={meta.data} /> : <Status state={meta} />}
      </main>
      <footer className="footer">Data: Elexon BMRS (WINDFOR forecasts, FUELHH outturn).</footer>
    </div>
  )
}
