import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { Sev } from '../components.jsx'

const EMPTY = { title: '', description: '', service: '', severity: 'sev2' }

export default function Incidents({ open, useMemory }) {
  const [list, setList] = useState([])
  const [f, setF] = useState(EMPTY)
  const [busy, setBusy] = useState(false)
  useEffect(() => { api.incidents().then(setList).catch(() => {}) }, [])
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })
  const submit = async (e) => {
    e.preventDefault(); setBusy(true)
    try { const inc = await api.createIncident({ ...f, service: f.service || 'general', use_memory: useMemory }); open(inc.id) }
    finally { setBusy(false) }
  }
  return (
    <>
      <h1>Incidents</h1>
      <form className="panel form" onSubmit={submit}>
        <h2>Report an incident</h2>
        <input required placeholder="What is happening? e.g. Postgres primary has high latency and timeouts" value={f.title} onChange={set('title')} />
        <textarea rows={3} placeholder="Symptoms, alerts, recent changes (optional)" value={f.description} onChange={set('description')} />
        <div className="row">
          <input placeholder="Service, e.g. PostgreSQL" value={f.service} onChange={set('service')} />
          <select value={f.severity} onChange={set('severity')}><option>sev1</option><option>sev2</option><option>sev3</option></select>
          <button className="btn" disabled={busy}>{busy ? 'Analysing…' : 'Open incident'}</button>
        </div>
      </form>
      <section className="panel">
        <h2>All incidents</h2>
        {list.length === 0 ? <p className="empty">No incidents yet. Report one above, or load demo history from the dashboard.</p> :
          <table><tbody>{list.map((i) => (
            <tr key={i.id} onClick={() => open(i.id)}>
              <td className="mono">#{i.id}</td><td>{i.title}</td><td>{i.service}</td><td><Sev v={i.severity} /></td>
              <td>{i.status}{i.minutes_to_resolve != null ? ` · ${i.minutes_to_resolve} min` : ''}</td>
            </tr>))}</tbody></table>}
      </section>
    </>
  )
}
