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
        <h2 id="day-title">Forecast vs outturn</h2>
        {day.status === 'success' ? <DayView day={day.data} minHistoryDays={meta.min_history_days} /> : <Status state={day} />}
      </section>

      <section className="section" aria-labelledby="period-title">
        <h2 id="period-title">Forecast accuracy · January 2026</h2>
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
        <h1>UK Wind Forecast Monitor</h1>
        <p>National wind · Elexon BMRS · UTC</p>
      </header>
      <main>
        {meta.status === 'success' ? <Dashboard meta={meta.data} /> : <Status state={meta} />}
      </main>
      <footer className="footer">Source: Elexon BMRS (WINDFOR, FUELHH)</footer>
    </div>
  )
}
