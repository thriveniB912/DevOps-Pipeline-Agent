# OpsMemory AI (prototype)

Incident-response agent that remembers how past incidents were fixed and recalls the fix when a similar one appears.

React (Vite) -> FastAPI -> PostgreSQL (+ optional Hindsight memory server, + optional OpenAI LLM)

## Run it

```bash
# 1. Database (optional; without it the backend uses a local SQLite file)
docker compose up -d db

# 2. Backend
cd backend
python -m venv venv && source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                   # add OPENAI_API_KEY if you have one
uvicorn app.main:app --reload --port 8000

# 3. Frontend (new terminal)
cd frontend && npm install && npm run dev              # http://localhost:5173
```

Open the dashboard and click **Load demo history**.

## Turn on real Hindsight (important for judging)

```bash
export OPENAI_API_KEY=sk-...
docker compose --profile hindsight up -d      # API :8888, UI :9999
# in backend/.env set HINDSIGHT_URL=http://localhost:8888
```
Resolved incidents are then sent to Hindsight with `retain`, and `recall` results appear in chat
next to the Postgres matches. The Hindsight UI (:9999) is your "memory inspector" for the demo video.

## Demo script (3 minutes)

1. Sidebar: memory **off**. Report "Postgres primary has high latency and connection timeouts". Generic checklist.
2. Memory **on**. Report the same incident. The reply leads with the teal "Recalled from memory" block: Incident #1, root cause, fix.
3. Log a resolution on the new incident. Open **Memory** to show it stored. Open **Similar incidents** and search an alert.
4. Dashboard: recalls count and minutes to resolve with vs without memory.

## Layout
- `backend/app/memory.py` - retain / recall (Postgres embeddings + Hindsight)
- `backend/app/agent.py` - LLM agent (OpenAI or rule-based fallback)
- `backend/app/embeddings.py` - dependency-free embeddings; swap for OpenAI embeddings or pgvector
- `backend/app/seed.py` - demo history
- `frontend/src/pages/` - Dashboard, Incidents, IncidentDetail (chat), Similar, Memory
