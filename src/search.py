"""Keyword search over the knowledge base using TF-IDF scoring. Pure Python, no models."""
import math
import re
from collections import Counter
from functools import lru_cache

from . import nlp
from .knowledge import glossary, topics

MIN_SCORE = 1.0


def _tokens(text: str) -> list[str]:
    return [nlp.stem(w) for w in re.findall(r"[a-z]+", text.lower()) if w not in nlp.STOPWORDS and len(w) > 2]


@lru_cache(maxsize=1)
def _index():
    docs = []
    for t in topics():
        for text in (t["summary"], *t.get("facts", [])):
            docs.append({"topic": t["id"], "text": text, "tokens": _tokens(text)})
    for term, meaning in glossary().items():
        text = f"'{term}' means {meaning}."
        docs.append({"topic": "glossary", "text": text, "tokens": _tokens(text)})
    df = Counter()
    for d in docs:
        df.update(set(d["tokens"]))
    n = len(docs)
    idf = {w: math.log((n + 1) / (c + 0.5)) for w, c in df.items()}
    return docs, idf


def search(query: str, k: int = 3) -> list[dict]:
    """Best-matching facts as {"topic", "text", "score"}, strongest first, weak matches dropped."""
    docs, idf = _index()
    q = set(_tokens(query))
    low = query.lower()
    boosted = {t["id"] for t in topics() if any(re.search(rf"\b{re.escape(k_)}", low) for k_ in t["keywords"])}
    scored = []
    for d in docs:
        tf = Counter(d["tokens"])
        score = sum(idf[w] * (1 + math.log(tf[w])) for w in q if w in tf)
        if score:
            score = score / len(d["tokens"]) ** 0.25 + (1.2 if d["topic"] in boosted else 0)
            scored.append({**{x: d[x] for x in ("topic", "text")}, "score": score})
    scored.sort(key=lambda h: h["score"], reverse=True)
    seen, out = set(), []
    for h in scored:
        if h["score"] >= MIN_SCORE and h["text"] not in seen:
            seen.add(h["text"])
            out.append(h)
    return out[:k]
