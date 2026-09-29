"""Dependency-free hashed bag-of-words embeddings (words + bigrams, synonym-normalised).
Good enough for a prototype; swap embed() for OpenAI embeddings or pgvector later."""
import hashlib
import math
import re

DIM = 384
STOP = {"the", "a", "an", "is", "are", "and", "or", "to", "of", "in", "on", "for", "with", "we", "it",
        "was", "our", "this", "that", "again", "after", "by", "at", "from", "as", "be", "has", "have"}
SYN = {"db": "database", "postgres": "database", "postgresql": "database", "mysql": "database",
       "lag": "latency", "slow": "latency", "slowness": "latency", "timeouts": "timeout",
       "oom": "memory", "ram": "memory", "oomkilled": "memory", "conns": "connection",
       "connections": "connection", "pgbouncer": "pool", "pooling": "pool", "503": "error",
       "500": "error", "5xx": "error", "dropping": "drop", "dropped": "drop", "leaks": "leak"}


def tokens(text: str) -> list[str]:
    words = [w for w in re.findall(r"[a-z0-9_]+", text.lower()) if w not in STOP]
    out = []
    for w in words:
        out.append(w)
        if w in SYN:
            out.append(SYN[w])
    out += [f"{a}_{b}" for a, b in zip(words, words[1:])]
    return out


def embed(text: str) -> list[float]:
    vec = [0.0] * DIM
    for t in tokens(text):
        h = int(hashlib.md5(t.encode()).hexdigest(), 16)
        vec[h % DIM] += 1.0 if (h >> 40) & 1 else -1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))
