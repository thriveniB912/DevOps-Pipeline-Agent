"""Seed past incidents so the demo has 'history'. Run: python -m app.seed"""
from datetime import timedelta
from sqlalchemy.orm import Session
from .db import Base, Incident, Resolution, SessionLocal, engine, now
from .memory import memory

PAST = [
    dict(title="Postgres RAM at 98% and dropped connections", service="PostgreSQL", severity="sev1", minutes=45,
         description="Primary database memory near 98%, clients getting connection errors and timeouts.",
         root_cause="Connection leak in the web service exhausted the connection pool.",
         fix="Capped max_connections to 200, set PgBouncer pool_mode=transaction, patched the leaking web client.",
         by="Ravi", days=21),
    dict(title="Redis latency spike and evicted keys", service="Redis", severity="sev2", minutes=35,
         description="Cache latency up 10x, hit rate dropped, sessions logged out.",
         root_cause="maxmemory reached with allkeys-lru evicting session keys.",
         fix="Moved sessions to a dedicated Redis instance and raised maxmemory to 4GB.", by="Anita", days=14),
    dict(title="Checkout pods OOMKilled after release", service="Kubernetes", severity="sev2", minutes=50,
         description="Checkout pods restarting repeatedly with OOMKilled after the v2.4 deploy.",
         root_cause="New image cache had no size limit and pod memory limit was 512Mi.",
         fix="Bounded the cache to 128MB and raised the memory limit to 1Gi; rolled out v2.4.1.", by="Sam", days=9),
]


def seed(db: Session) -> int:
    if db.query(Incident).count():
        return 0
    for p in PAST:
        created = now() - timedelta(days=p["days"])
        inc = Incident(title=p["title"], description=p["description"], service=p["service"], severity=p["severity"],
                       status="resolved", created_at=created, resolved_at=created + timedelta(minutes=p["minutes"]))
        db.add(inc)
        db.commit()
        res = Resolution(incident_id=inc.id, root_cause=p["root_cause"], fix=p["fix"], resolved_by=p["by"])
        db.add(res)
        db.commit()
        memory.retain(db, inc, res)
    return len(PAST)


if __name__ == "__main__":
    Base.metadata.create_all(engine)
    with SessionLocal() as s:
        print("seeded", seed(s))
