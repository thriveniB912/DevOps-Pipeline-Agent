import { useState } from 'react'
import { api } from '../api.js'
import { Recalled } from '../components.jsx'

export default function Similar({ open }) {
  const [q, setQ] = useState('')
  const [res, setRes] = useState(null)
  const go = async (e) => { e.preventDefault(); setRes(await api.similar(q)) }
  return (
    <>
      <h1>Similar incidents</h1>
      <form className="panel form" onSubmit={go}>
        <textarea rows={3} required placeholder="Paste an alert or describe symptoms, e.g. pods restarting with OOMKilled" value={q} onChange={(e) => setQ(e.target.value)} />
        <div className="row"><button className="btn">Search memory</button></div>
      </form>
      {res && (res.length ? <Recalled items={res} onOpen={open} /> : <p className="empty">No similar past incident found. This looks new.</p>)}
    </>
  )
}
