"""Incident-response agent. Uses an OpenAI-compatible LLM if a key is set, else a rule-based responder."""
from . import config

SYSTEM = ("You are OpsMemory, an expert SRE incident-response agent. Give concise, prioritised, actionable "
          "troubleshooting steps. If RECALLED MEMORY is provided, lead with it: cite the past incident number, "
          "its root cause and fix, then say what to verify first. Never invent incidents that are not in memory.")


def _memory_block(recalled: list[dict]) -> str:
    lines = []
    for r in recalled:
        if r["incident_id"]:
            lines.append(f"- Incident #{r['incident_id']} [{r['service']}] root cause: {r['root_cause']} | fix: {r['fix']}")
        else:
            lines.append(f"- {r['summary']}")
    return "\n".join(lines)


def _generic_steps(text: str) -> list[str]:
    t = text.lower()
    steps = []
    if any(k in t for k in ("postgres", "database", "db", "mysql", "connection")):
        steps += ["Compare active connections to max_connections (pg_stat_activity).",
                  "Look for long-running or idle-in-transaction queries.",
                  "Check pool saturation and any deploy in the last 24h."]
    if any(k in t for k in ("memory", "oom", "ram", "leak")):
        steps += ["Check memory trend and restart counts for the affected pods/hosts.",
                  "Compare resource limits with actual usage."]
    if any(k in t for k in ("cpu", "latency", "slow", "timeout")):
        steps += ["Check CPU saturation and top slow endpoints/queries.", "Inspect upstream dependency latency."]
    if any(k in t for k in ("500", "503", "5xx", "error")):
        steps += ["Check error-rate by endpoint and the latest deployment.", "Roll back if errors began with a release."]
    return steps or ["Confirm impact and scope.", "Check recent deploys and config changes.",
                     "Review logs and metrics for the first anomaly."]


def _fallback(inc, message: str, recalled: list[dict]) -> str:
    if recalled:
        top = recalled[0]
        head = (f"This matches a past incident. **Incident #{top['incident_id']}** ({top['service']}) had the same "
                f"pattern.\n\n**Root cause then:** {top['root_cause']}\n**Fix that worked:** {top['fix']}\n\n"
                if top["incident_id"] else f"Relevant history from Hindsight: {top['summary']}\n\n")
        return head + "**Verify first:**\n" + "\n".join(f"{i}. {s}" for i, s in enumerate(_generic_steps(inc.title + message)[:3], 1))
    steps = _generic_steps(f"{inc.title} {inc.description} {message}")
    return ("No similar incident in memory yet, so here is a generic checklist:\n\n"
            + "\n".join(f"{i}. {s}" for i, s in enumerate(steps, 1))
            + "\n\nWhen you find the fix, log it as a resolution so the next on-call engineer gets it instantly.")


def respond(inc, history: list[dict], message: str, recalled: list[dict]) -> str:
    if not config.OPENAI_API_KEY:
        return _fallback(inc, message, recalled)
    try:
        from openai import OpenAI
        sys = SYSTEM + f"\n\nCURRENT INCIDENT: {inc.title} ({inc.service}, {inc.severity}). {inc.description}"
        sys += ("\n\nRECALLED MEMORY:\n" + _memory_block(recalled)) if recalled else "\n\nNo relevant memory found."
        msgs = [{"role": "system", "content": sys}] + history[-8:] + [{"role": "user", "content": message}]
        out = OpenAI(api_key=config.OPENAI_API_KEY).chat.completions.create(
            model=config.LLM_MODEL, messages=msgs, temperature=0.2)
        return out.choices[0].message.content
    except Exception:
        return _fallback(inc, message, recalled)
