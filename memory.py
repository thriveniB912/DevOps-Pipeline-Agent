"""Memory service: Postgres-backed incident memory + optional Hindsight (retain / recall)."""
import logging
from sqlalchemy.orm import Session
from . import config
from .db import Incident, IncidentMemory, Resolution
from .embeddings import embed, cosine

log = logging.getLogger("opsmemory.memory")


class MemoryService:
    def __init__(self):
        self.hindsight = None
        if config.HINDSIGHT_URL:
            try:
                from hindsight_client import Hindsight
                self.hindsight = Hindsight(base_url=config.HINDSIGHT_URL)
            except Exception as e:  # missing package or server
                log.warning("Hindsight disabled: %s", e)

    @property
    def status(self) -> dict:
        return {"local": True, "hindsight": self.hindsight is not None, "bank": config.HINDSIGHT_BANK}

    # ---- retain ---------------------------------------------------------
    def retain(self, db: Session, inc: Incident, res: Resolution) -> IncidentMemory:
        summary = (f"Incident #{inc.id} [{inc.service}] {inc.title}. Symptoms: {inc.description} "
                   f"Root cause: {res.root_cause} Fix: {res.fix}")
        mem = IncidentMemory(incident_id=inc.id, service=inc.service, summary=summary,
                             root_cause=res.root_cause, fix=res.fix, embedding=embed(summary))
        if self.hindsight:
            try:
                self.hindsight.retain(bank_id=config.HINDSIGHT_BANK, content=summary,
                                      context="production incident post-mortem")
                mem.in_hindsight = True
            except Exception as e:
                log.warning("Hindsight retain failed: %s", e)
        db.add(mem)
        db.commit()
        return mem

    # ---- recall ---------------------------------------------------------
    def recall(self, db: Session, query: str, exclude_incident_id: int | None = None,
               top_k: int = 3, threshold: float = 0.2) -> list[dict]:
        q = embed(query)
        scored = []
        for m in db.query(IncidentMemory).all():
            if m.incident_id == exclude_incident_id:
                continue
            s = cosine(q, m.embedding)
            if s >= threshold:
                scored.append((s, m))
        scored.sort(key=lambda x: x[0], reverse=True)
        results = []
        for s, m in scored[:top_k]:
            m.times_recalled += 1
            results.append({"source": "postgres", "memory_id": m.id, "incident_id": m.incident_id,
                            "service": m.service, "score": round(s, 3), "root_cause": m.root_cause,
                            "fix": m.fix, "summary": m.summary})
        db.commit()
        results += self._hindsight_recall(query, have=len(results))
        return results

    def _hindsight_recall(self, query: str, have: int) -> list[dict]:
        if not self.hindsight:
            return []
        try:
            resp = self.hindsight.recall(bank_id=config.HINDSIGHT_BANK, query=query)
            items = getattr(resp, "results", resp) or []
            out = []
            for it in list(items)[:2]:
                text = getattr(it, "text", None) or str(it)
                out.append({"source": "hindsight", "memory_id": None, "incident_id": None,
                            "service": "", "score": None, "root_cause": "", "fix": "", "summary": text})
            return out
        except Exception as e:
            log.warning("Hindsight recall failed: %s", e)
            return []


memory = MemoryService()
