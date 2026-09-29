export const matchLabel = (s) => (s == null ? 'Hindsight' : s >= 0.4 ? 'Strong match' : s >= 0.25 ? 'Likely match' : 'Possible match')

export function Sev({ v }) { return <span className={`sev ${v}`}>{v}</span> }

export function Recalled({ items, onOpen }) {
  if (!items?.length) return null
  return (
    <div className="recalled">
      <div className="recalled-head">Recalled from memory</div>
      {items.map((r, i) => (
        <div className="recalled-item" key={i}>
          <div className="recalled-meta">
            {r.incident_id
              ? <button className="link" onClick={() => onOpen?.(r.incident_id)}>Incident #{r.incident_id}</button>
              : <span>Hindsight</span>}
            {r.service && <span>{r.service}</span>}
            <span className="match">{matchLabel(r.score)}</span>
          </div>
          {r.incident_id
            ? <><p><b>Cause:</b> {r.root_cause}</p><p><b>Fix:</b> {r.fix}</p></>
            : <p>{r.summary}</p>}
        </div>
      ))}
    </div>
  )
}

export function Md({ text }) {
  // tiny renderer: **bold** and line breaks
  return <div className="md">{text.split('\n').map((l, i) => (
    <p key={i}>{l.split(/(\*\*[^*]+\*\*)/g).map((p, k) => p.startsWith('**') ? <b key={k}>{p.slice(2, -2)}</b> : p)}</p>
  ))}</div>
}
