"""
DevOps Pipeline Agent: a CI/CD failure triage agent that gets better with every incident.

Workflow (the ONE thing it does):
  failed pipeline log -> recall similar past incidents -> propose root cause + fix
  -> engineer outcome is fed back into memory -> next similar failure is solved faster.

Run:  python pipeline_agent.py            # demo: 8 incidents, watch hit-rate climb
      ANTHROPIC_API_KEY=... python pipeline_agent.py   # LLM handles first-seen failures
      HINDSIGHT_URL=http://localhost:8888 python pipeline_agent.py   # use Hindsight memory
"""
import json, os, random, re
from pathlib import Path

# ---------------------------------------------------------------- synthetic data
# Each scenario: a realistic log template + the true root cause and fix (ground truth
# used only by the simulated on-call engineer to close the feedback loop).
SCENARIOS = {
    "docker_rate_limit": dict(
        log="""[{ts}] Step 4/9 : FROM node:18-alpine
[{ts}] toomanyrequests: You have reached your pull rate limit. You may increase the limit by authenticating and upgrading: https://www.docker.com/increase-rate-limit
[{ts}] ERROR: failed to solve: node:18-alpine: failed to authorize
[{ts}] Pipeline {svc}#{build} FAILED (exit code 1)""",
        cause="Docker Hub anonymous pull rate limit on shared CI runner IP",
        fix="Add docker login with a service account in the build job, or mirror base images to ECR"),
    "oom_test_runner": dict(
        log="""[{ts}] > jest --runInBand --coverage
[{ts}] <--- Last few GCs --->
[{ts}] FATAL ERROR: Reached heap limit Allocation failed - JavaScript heap out of memory
[{ts}] Killed
[{ts}] Pipeline {svc}#{build} FAILED (exit code 137)""",
        cause="Jest with coverage exceeds Node default heap on the 4GB runner",
        fix="Set NODE_OPTIONS=--max-old-space-size=3072 and drop --runInBand for shards"),
    "terraform_state_lock": dict(
        log="""[{ts}] Error: Error acquiring the state lock
[{ts}] Lock Info:  ID: 8f2c1d9e-{build}  Path: s3://acme-tfstate/{svc}/terraform.tfstate  Who: runner@ci-{build}
[{ts}] ConditionalCheckFailedException: The conditional request failed (DynamoDB)
[{ts}] Pipeline {svc}#{build} FAILED (exit code 1)""",
        cause="Stale DynamoDB lock left by a cancelled earlier apply",
        fix="Confirm no apply is running, then terraform force-unlock <ID>; add concurrency group to the job"),
    "flaky_postgres_health": dict(
        log="""[{ts}] Waiting for postgres:5432 ...
[{ts}] psycopg2.OperationalError: connection to server at "postgres" (172.18.0.3), port 5432 failed: Connection refused
[{ts}] pytest tests/integration -x  ->  1 error in 31.20s
[{ts}] Pipeline {svc}#{build} FAILED (exit code 1)""",
        cause="Tests start before the Postgres service container is healthy",
        fix="Add a healthcheck (pg_isready) to the service and use depends_on: condition: service_healthy"),
}
SERVICES = ["payments-api", "checkout-web", "inventory-svc", "auth-gateway", "ml-scoring"]

def make_incident(kind, rng):
    s = SCENARIOS[kind]
    log = s["log"].format(ts=f"2026-09-{rng.randint(1,28):02d}T{rng.randint(0,23):02d}:{rng.randint(0,59):02d}:{rng.randint(0,59):02d}Z",
                          svc=rng.choice(SERVICES), build=rng.randint(1200, 9800))
    return dict(kind=kind, log=log, cause=s["cause"], fix=s["fix"])

# ---------------------------------------------------------------- memory layer
def tokens(log):
    """Normalise a log so different builds of the same failure look alike."""
    log = re.sub(r"\[[^\]]*\]|\d+|[0-9a-f]{8}-\S*|\S+@\S+", " ", log.lower())
    return set(re.findall(r"[a-z_]{4,}", log))

def sim(a, b):
    return len(a & b) / max(1, len(a | b))

class LocalMemory:
    """Persistent JSON memory: every resolved incident is retained, recall = similarity search."""
    def __init__(self, path="incident_memory.json"):
        self.path = Path(path)
        self.items = json.loads(self.path.read_text()) if self.path.exists() else []

    def retain(self, log, cause, fix, worked):
        self.items.append(dict(log=log, cause=cause, fix=fix, worked=worked))
        self.path.write_text(json.dumps(self.items, indent=2))

    def recall(self, log, k=3):
        q = tokens(log)
        scored = sorted(((sim(q, tokens(i["log"])), i) for i in self.items), key=lambda x: -x[0])
        return [(s, i) for s, i in scored[:k] if s > 0.2]

class HindsightMemory:
    """Adapter for Hindsight (vectorize-io). Check the client docs; method names may differ by version."""
    def __init__(self, url, bank="devops-pipeline-agent"):
        from hindsight_client import Hindsight
        self.c, self.bank = Hindsight(base_url=url), bank

    def retain(self, log, cause, fix, worked):
        self.c.retain(bank_id=self.bank, content=json.dumps(dict(log=log, cause=cause, fix=fix, worked=worked)))

    def recall(self, log, k=3):
        out = []
        for r in self.c.recall(bank_id=self.bank, query=log[:500]).results[:k]:
            try: out.append((0.9, json.loads(r.text)))
            except Exception: pass
        return out

def get_memory():
    if os.getenv("HINDSIGHT_URL"):
        return HindsightMemory(os.environ["HINDSIGHT_URL"])
    Path("incident_memory.json").unlink(missing_ok=True)  # fresh start so the demo shows learning
    return LocalMemory()

# ---------------------------------------------------------------- the agent
def ask_llm(log):
    """Cold-start path: no relevant memory, so ask an LLM (if a key is set)."""
    if not os.getenv("ANTHROPIC_API_KEY"):
        return None
    import anthropic
    msg = anthropic.Anthropic().messages.create(
        model="claude-sonnet-5-5", max_tokens=300,
        messages=[{"role": "user", "content": "CI failure log:\n" + log +
                   '\nReply ONLY JSON: {"cause": "...", "fix": "..."}'}])
    try: return json.loads(msg.content[0].text)
    except Exception: return None

def triage(memory, log):
    hits = memory.recall(log)
    good = [(s, i) for s, i in hits if i["worked"]]
    if good:
        s, best = good[0]
        wins = sum(1 for _, i in hits if i["fix"] == best["fix"] and i["worked"])
        return dict(source="MEMORY", cause=best["cause"], fix=best["fix"],
                    confidence=round(min(0.97, 0.55 + 0.15 * wins + 0.3 * s), 2))
    guess = ask_llm(log)
    if guess:
        return dict(source="LLM", cause=guess["cause"], fix=guess["fix"], confidence=0.4)
    return dict(source="NONE", cause="Unknown failure pattern", fix="Escalate to on-call", confidence=0.0)

# ---------------------------------------------------------------- demo
def main():
    rng, memory = random.Random(7), get_memory()
    kinds = list(SCENARIOS)
    schedule = kinds + [rng.choice(kinds) for _ in range(8)]   # first-seen, then repeats
    solved_by_memory = 0
    print(f"{'#':>2}  {'failure':<22} {'source':<7} {'conf':>5}  outcome")
    for n, kind in enumerate(schedule, 1):
        inc = make_incident(kind, rng)
        plan = triage(memory, inc["log"])
        worked = plan["fix"] == inc["fix"]                       # simulated engineer applies the fix
        memory.retain(inc["log"], inc["cause"], inc["fix"], True)  # true resolution always learned
        solved_by_memory += plan["source"] == "MEMORY" and worked
        print(f"{n:>2}  {kind:<22} {plan['source']:<7} {plan['confidence']:>5}  "
              f"{'auto-resolved' if worked else 'manual fix, now remembered'}")
    print(f"\nSolved instantly from memory: {solved_by_memory}/{len(schedule)} incidents "
          f"(every first-seen failure was learned after one occurrence).")

if __name__ == "__main__":
    main()
