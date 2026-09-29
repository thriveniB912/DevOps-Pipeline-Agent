import { useEffect, useState } from 'react'
import Dashboard from './pages/Dashboard.jsx'
import Incidents from './pages/Incidents.jsx'
import IncidentDetail from './pages/IncidentDetail.jsx'
import Similar from './pages/Similar.jsx'
import Memory from './pages/Memory.jsx'
import { api } from './api.js'

const NAV = [['dashboard', 'Dashboard'], ['incidents', 'Incidents'], ['similar', 'Similar incidents'], ['memory', 'Memory']]

export default function App() {
  const [view, setView] = useState({ name: 'dashboard' })
  const [useMemory, setUseMemory] = useState(true)
  const [backend, setBackend] = useState(null)
  useEffect(() => { api.dashboard().then((d) => setBackend(d.memory_backend)).catch(() => setBackend(false)) }, [view])
  const go = (name, id) => setView({ name, id })
  const open = (id) => go('incident', id)

  return (
    <div className="shell">
      <aside className="side">
        <div className="brand">OpsMemory</div>
        <nav>
          {NAV.map(([k, label]) => (
            <button key={k} className={view.name === k || (k === 'incidents' && view.name === 'incident') ? 'on' : ''} onClick={() => go(k)}>{label}</button>
          ))}
        </nav>
        <div className="side-foot">
          <label className="toggle">
            <input type="checkbox" checked={useMemory} onChange={(e) => setUseMemory(e.target.checked)} />
            <span>Memory recall {useMemory ? 'on' : 'off'}</span>
          </label>
          <p className="hint">Switch off to show the agent without memory, then on to show the difference.</p>
          <p className="hint">{backend === false ? 'API not reachable' : backend ? `Storage: Postgres${backend.hindsight ? ' + Hindsight' : ''}` : ''}</p>
        </div>
      </aside>
      <main className="main">
        {view.name === 'dashboard' && <Dashboard open={open} go={go} />}
        {view.name === 'incidents' && <Incidents open={open} useMemory={useMemory} />}
        {view.name === 'incident' && <IncidentDetail id={view.id} useMemory={useMemory} open={open} />}
        {view.name === 'similar' && <Similar open={open} />}
        {view.name === 'memory' && <Memory open={open} />}
      </main>
    </div>
  )
}
