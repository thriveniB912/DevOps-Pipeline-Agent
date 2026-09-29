const j = async (r) => { if (!r.ok) throw new Error(await r.text()); return r.json() }
const post = (url, body) => fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body || {}) }).then(j)
export const api = {
  dashboard: () => fetch('/api/dashboard').then(j),
  incidents: () => fetch('/api/incidents').then(j),
  incident: (id) => fetch(`/api/incidents/${id}`).then(j),
  createIncident: (b) => post('/api/incidents', b),
  chat: (id, b) => post(`/api/incidents/${id}/chat`, b),
  resolve: (id, b) => post(`/api/incidents/${id}/resolve`, b),
  memories: () => fetch('/api/memories').then(j),
  similar: (q) => fetch(`/api/similar?q=${encodeURIComponent(q)}`).then(j),
  seed: () => post('/api/seed'),
}
