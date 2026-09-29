import { useEffect, useRef, useState } from 'react'
import { api } from '../api.js'
import { Md, Recalled, Sev } from '../components.jsx'

export default function IncidentDetail({ id, useMemory, open }) {
  const [inc, setInc] = useState(null)
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const [showResolve, setShowResolve] = useState(false)
  const [r, setR] = useState({ root_cause: '', fix: '', resolved_by: '' })
  const [saved, setSaved] = useState(false)
  const end = useRef(null)
  useEffect(() => { api.incident(id).then(setInc) }, [id])
  useEffect(() => { end.current?.scrollIntoView({ behavior: 'smooth' }) }, [inc?.messages?.length])
  if (!inc) return <p className="empty">Loading…</p>

  const send = async (e) => {
    e.preventDefault(); if (!text.trim()) return
    const msg = text; setText(''); setBusy(true)
    setInc({ ...inc, messages: [...inc.messages, { id: -1, role: 'user', content: msg, recalled: [] }] })
    try { setInc(await api.chat(id, { message: msg, use_memory: useMemory })) } finally { setBusy(false) }
  }
  const resolve = async (e) => {
    e.preventDefault()
    const out = await api.resolve(id, { ...r, resolved_by: r.resolved_by || 'on-call' })
    setInc(out.incident); setShowResolve(false); setSaved(true)
  }

  return (
    <>
      <div className="head">
        <div>
          <h1>#{inc.id} {inc.title}</h1>
          <p className="sub"><Sev v={inc.severity} /> {inc.service} · {inc.status}{inc.memory_assisted ? ' · memory was used' : ''}</p>
        </div>
        {inc.status === 'open' && <button className="btn" onClick={() => setShowResolve(!showResolve)}>Log resolution</button>}
      </div>
      {inc.description && <p className="desc">{inc.description}</p>}

      {showResolve && (
        <form className="panel form" onSubmit={resolve}>
          <h2>What fixed it?</h2>
          <textarea required rows={2} placeholder="Root cause" value={r.root_cause} onChange={(e) => setR({ ...r, root_cause: e.target.value })} />
          <textarea required rows={2} placeholder="Fix that worked" value={r.fix} onChange={(e) => setR({ ...r, fix: e.target.value })} />
          <div className="row"><input placeholder="Resolved by" value={r.resolved_by} onChange={(e) => setR({ ...r, resolved_by: e.target.value })} />
            <button className="btn">Resolve and save to memory</button></div>
        </form>
      )}
      {saved && <div className="callout mem">Saved to memory. The next similar incident will recall this fix.</div>}
      {inc.resolution && (
        <section className="panel"><h2>Resolution</h2>
          <p><b>Root cause:</b> {inc.resolution.root_cause}</p><p><b>Fix:</b> {inc.resolution.fix}</p>
          <p className="hint">Resolved by {inc.resolution.resolved_by}{inc.minutes_to_resolve != null ? ` in ${inc.minutes_to_resolve} min` : ''}</p>
        </section>
      )}

      <section className="chat">
        {inc.messages.map((m, i) => (
          <div key={i} className={`msg ${m.role}`}>
            {m.role === 'assistant' && <Recalled items={m.recalled} onOpen={open} />}
            <div className="bubble"><Md text={m.content} /></div>
          </div>
        ))}
        {busy && <div className="msg assistant"><div className="bubble">Searching memory…</div></div>}
        <div ref={end} />
      </section>
      <form className="composer" onSubmit={send}>
        <input value={text} onChange={(e) => setText(e.target.value)} placeholder={`Ask the agent (memory ${useMemory ? 'on' : 'off'})`} />
        <button className="btn" disabled={busy}>Send</button>
      </form>
    </>
  )
}
