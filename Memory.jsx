import { useEffect, useState } from 'react'
import { api } from '../api.js'

export default function Memory({ open }) {
  const [m, setM] = useState(null)
  useEffect(() => { api.memories().then(setM).catch(() => setM([])) }, [])
  if (!m) return <p className="empty">Loading…</p>
  return (
    <>
      <h1>Memory</h1>
      <p className="desc">Every resolved incident becomes a memory. This is what the agent can recall.</p>
      {m.length === 0 ? <p className="empty">No memories yet. Resolve an incident to create the first one.</p> :
        m.map((x) => (
          <article className="panel memory" key={x.id}>
            <div className="recalled-meta">
              <button className="link" onClick={() => open(x.incident_id)}>Incident #{x.incident_id}</button>
              <span>{x.service}</span><span>recalled {x.times_recalled}×</span>{x.in_hindsight && <span className="match">in Hindsight</span>}
            </div>
            <p><b>Cause:</b> {x.root_cause}</p><p><b>Fix:</b> {x.fix}</p>
          </article>))}
    </>
  )
}
