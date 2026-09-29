from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from . import agent
from .db import Base, ChatMessage, Incident, IncidentMemory, Resolution, engine, get_db, now
from .memory import memory

Base.metadata.create_all(engine)
app = FastAPI(title="OpsMemory AI")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["*"], allow_headers=["*"])


class IncidentIn(BaseModel):
    title: str
    description: str = ""
    service: str = "general"
    severity: str = "sev3"
    use_memory: bool = True


class ChatIn(BaseModel):
    message: str
    use_memory: bool = True


class ResolveIn(BaseModel):
    root_cause: str
    fix: str
    resolved_by: str = "on-call"


def iso(d):
    return d.isoformat() if d else None


def mins(inc):
    return round((inc.resolved_at - inc.created_at).total_seconds() / 60) if inc.resolved_at else None


def inc_out(i: Incident, detail=False):
    out = {"id": i.id, "title": i.title, "description": i.description, "service": i.service,
           "severity": i.severity, "status": i.status, "memory_assisted": i.memory_assisted,
           "created_at": iso(i.created_at), "resolved_at": iso(i.resolved_at), "minutes_to_resolve": mins(i)}
    if detail:
        r = i.resolution
        out["resolution"] = r and {"root_cause": r.root_cause, "fix": r.fix, "resolved_by": r.resolved_by}
        out["messages"] = [{"id": m.id, "role": m.role, "content": m.content, "recalled": m.recalled or [],
                            "created_at": iso(m.created_at)} for m in i.messages]
    return out


def mem_out(m: IncidentMemory):
    return {"id": m.id, "incident_id": m.incident_id, "service": m.service, "summary": m.summary,
            "root_cause": m.root_cause, "fix": m.fix, "in_hindsight": m.in_hindsight,
            "times_recalled": m.times_recalled, "created_at": iso(m.created_at)}


def get_inc(db: Session, iid: int) -> Incident:
    inc = db.get(Incident, iid)
    if not inc:
        raise HTTPException(404, "Incident not found")
    return inc


def agent_turn(db: Session, inc: Incident, message: str, use_memory: bool):
    recalled = memory.recall(db, f"{inc.title}. {inc.description}. {message}", exclude_incident_id=inc.id) if use_memory else []
    history = [{"role": m.role, "content": m.content} for m in inc.messages]
    reply = agent.respond(inc, history, message, recalled)
    if recalled:
        inc.memory_assisted = True
    db.add(ChatMessage(incident_id=inc.id, role="assistant", content=reply, recalled=recalled))
    db.commit()
    db.expire(inc)


@app.get("/api/dashboard")
def dashboard(db: Session = Depends(get_db)):
    incs = db.query(Incident).all()
    resolved = [i for i in incs if i.status == "resolved" and i.resolved_at]
    avg = lambda xs: round(sum(xs) / len(xs)) if xs else None
    assisted = [mins(i) for i in resolved if i.memory_assisted]
    plain = [mins(i) for i in resolved if not i.memory_assisted]
    return {"total": len(incs), "open": sum(i.status == "open" for i in incs), "resolved": len(resolved),
            "memories": db.query(func.count(IncidentMemory.id)).scalar(),
            "recalls": db.query(func.coalesce(func.sum(IncidentMemory.times_recalled), 0)).scalar(),
            "mttr_with_memory": avg(assisted), "mttr_without_memory": avg(plain),
            "memory_backend": memory.status,
            "recent": [inc_out(i) for i in sorted(incs, key=lambda i: i.id, reverse=True)[:5]]}


@app.get("/api/incidents")
def list_incidents(db: Session = Depends(get_db)):
    return [inc_out(i) for i in db.query(Incident).order_by(Incident.id.desc()).all()]


@app.post("/api/incidents")
def create_incident(body: IncidentIn, db: Session = Depends(get_db)):
    inc = Incident(title=body.title, description=body.description, service=body.service, severity=body.severity)
    db.add(inc)
    db.commit()
    agent_turn(db, inc, "New incident reported. What should I check first?", body.use_memory)
    return inc_out(db.get(Incident, inc.id), detail=True)


@app.get("/api/incidents/{iid}")
def get_incident(iid: int, db: Session = Depends(get_db)):
    return inc_out(get_inc(db, iid), detail=True)


@app.post("/api/incidents/{iid}/chat")
def chat(iid: int, body: ChatIn, db: Session = Depends(get_db)):
    inc = get_inc(db, iid)
    db.add(ChatMessage(incident_id=iid, role="user", content=body.message))
    db.commit()
    db.refresh(inc)
    agent_turn(db, inc, body.message, body.use_memory)
    return inc_out(db.get(Incident, iid), detail=True)


@app.post("/api/incidents/{iid}/resolve")
def resolve(iid: int, body: ResolveIn, db: Session = Depends(get_db)):
    inc = get_inc(db, iid)
    if inc.resolution:
        raise HTTPException(400, "Already resolved")
    res = Resolution(incident_id=iid, root_cause=body.root_cause, fix=body.fix, resolved_by=body.resolved_by)
    inc.status, inc.resolved_at = "resolved", now()
    db.add(res)
    db.commit()
    db.refresh(inc)
    mem = memory.retain(db, inc, res)
    return {"incident": inc_out(inc, detail=True), "memory": mem_out(mem)}


@app.get("/api/similar")
def similar(q: str, exclude: int | None = None, db: Session = Depends(get_db)):
    return memory.recall(db, q, exclude_incident_id=exclude, top_k=5, threshold=0.15)


@app.get("/api/memories")
def memories(db: Session = Depends(get_db)):
    return [mem_out(m) for m in db.query(IncidentMemory).order_by(IncidentMemory.id.desc()).all()]


@app.post("/api/seed")
def seed_endpoint(db: Session = Depends(get_db)):
    from .seed import seed
    return {"seeded": seed(db)}
