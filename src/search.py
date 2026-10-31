"""Keyword search over the knowledge base using TF-IDF scoring. Pure Python, no models."""
import math
import re
from collections import Counter
from functools import lru_cache

from . import nlp
from .knowledge import glossary, topics

MIN_SCORE = 1.0
SUBJECT_WORDS = {"gendang", "beleq"}  # the subject of every topic, so they say nothing about what is being asked


def _tokens(text: str) -> list[str]:
    words = re.findall(r"[a-z]+", text.lower().replace("belek", "beleq"))
    return [nlp.stem(w) for w in words if w not in nlp.STOPWORDS and len(w) > 2]


@lru_cache(maxsize=1)
def _index():
    docs = []
    for t in topics():
        for fact in t["facts"]:
            docs.append({"topic": t["id"], "text": fact["text"], "sources": fact["sources"], "tokens": _tokens(fact["text"])})
    for term, entry in glossary().items():
        text = f"{term[0].upper()}{term[1:]} is {entry['meaning']}."
        docs.append({"topic": "glossary", "term": term, "text": text, "sources": entry["sources"], "tokens": _tokens(text)})
    df = Counter()
    for d in docs:
        df.update(set(d["tokens"]))
    n = len(docs)
    idf = {w: math.log((n + 1) / (c + 0.5)) for w, c in df.items()}
    return docs, idf


def keyword_hit(keyword: str, low: str) -> bool:
    # short keywords must match whole words, so 'war' does not fire on 'warm'
    return bool(re.search(rf"\b{re.escape(keyword)}{'' if len(keyword) >= 4 else r'\b'}", low))


def mentions_domain(text: str) -> bool:
    low = text.lower()
    return any(keyword_hit(kw, low) for t in topics() for kw in t["keywords"]) or any(w in low for w in SUBJECT_WORDS)


def search(query: str, k: int = 6, question: str | None = None) -> list[dict]:
    """Best-matching facts as {"topic", "text", "sources", "score"}, strongest first, weak matches dropped.

    `query` is the expanded search text. `question` is what the user actually typed: a glossary definition
    is only offered when the user named that term, because short definitions otherwise outrank real answers.
    """
    docs, idf = _index()
    q = set(_tokens(query))
    low = query.lower()
    asked = (question if question is not None else query).lower().replace("belek", "beleq")
    boosted = {t["id"] for t in topics() if any(keyword_hit(kw, low) for kw in t["keywords"])}
    scored = []
    for d in docs:
        if "term" in d and not keyword_hit(d["term"], asked):
            continue
        tf = Counter(d["tokens"])
        score = sum(idf[w] * (1 + math.log(tf[w])) for w in q if w in tf)
        if score:
            score = score / len(d["tokens"]) ** 0.25 + (1.5 if d["topic"] in boosted or "term" in d else 0)
            scored.append({"topic": d["topic"], "text": d["text"], "sources": d["sources"], "score": score})
    scored.sort(key=lambda h: h["score"], reverse=True)
    return [h for h in scored if h["score"] >= MIN_SCORE][:k]


def coverage(question: str, text: str) -> float:
    """Share of the question's meaningful words that the answer contains. Low means only a partial match."""
    wanted = set(_tokens(question)) - SUBJECT_WORDS
    return len(wanted & set(_tokens(text))) / len(wanted) if wanted else 1.0
