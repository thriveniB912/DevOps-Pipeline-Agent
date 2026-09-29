import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { Sev } from '../components.jsx'

export default function Dashboard({ open, go }) {
  const [d, setD] = useState(null)
  const load = () => api.dashboard().then(setD).catch(() => setD(false))
  useEffect(() => { load() }, [])
  if (d === false) return <p className="empty">Cannot reach the API. Start the backend on port 8000.</p>
  if (!d) return <p className="empty">Loading…</p>
  const stat = (n, l) => <div className="stat"><div className="num">{n ?? '–'}</div><div className="lbl">{l}</div></div>
  return (
    <>
      <h1>Dashboard</h1>
      {d.total === 0 && (
        <div className="callout">
          <p>No incident history yet. Load three past incidents so the agent has something to remember.</p>
          <button className="btn" onClick={() => api.seed().then(load)}>Load demo history</button>
        </div>
      )}
      <div className="stats">
        {stat(d.total, 'Incidents')}{stat(d.open, 'Open')}{stat(d.memories, 'Memories stored')}
        {stat(d.recalls, 'Times memory was recalled')}
      </div>
      <section className="panel">
        <h2>Minutes to resolve</h2>
        <div className="mttr">
          <div><b>{d.mttr_without_memory ?? '–'}</b><span>without memory</span></div>
          <div className="mem"><b>{d.mttr_with_memory ?? '–'}</b><span>with memory recall</span></div>
        </div>
        <p className="hint">Averages over resolved incidents. Resolve incidents that used recall to fill in the second number.</p>
      </section>
      <section className="panel">
        <h2>Recent incidents</h2>
        {d.recent.length === 0 ? <p className="empty">Nothing yet. <button className="link" onClick={() => go('incidents')}>Report an incident</button></p> :
          <table><tbody>{d.recent.map((i) => (
            <tr key={i.id} onClick={() => open(i.id)}>
              <td className="mono">#{i.id}</td><td>{i.title}</td><td>{i.service}</td><td><Sev v={i.severity} /></td>
              <td>{i.status}{i.memory_assisted ? ' · memory used' : ''}</td>
            </tr>))}</tbody></table>}
      </section>
    </>
  )
}
