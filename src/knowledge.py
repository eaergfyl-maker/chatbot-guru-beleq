"""Knowledge base: lessons, quiz questions, facts and glossary stored in data/knowledge/topics.json.

Check it with:  python -m src.knowledge
"""
import json
import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KB_FILE = ROOT / "data" / "knowledge" / "topics.json"


@lru_cache(maxsize=1)
def load_kb() -> dict:
    return json.loads(KB_FILE.read_text(encoding="utf-8"))


def topics() -> list[dict]:
    return load_kb()["topics"]


def get_topic(topic_id: str) -> dict:
    return next(t for t in topics() if t["id"] == topic_id)


def glossary() -> dict:
    return load_kb().get("glossary", {})


def quiz_items() -> list[dict]:
    """Every lesson check question plus the extra quiz questions, in one pool."""
    items = []
    for t in topics():
        for i, s in enumerate(t.get("lesson", [])):
            items.append({"key": f"{t['id']}:lesson:{i}", "topic": t["id"], "level": 1,
                          "question": s["question"], "answer": s["answer"], "hint": s["hint"], "explain": s["explain"]})
        for i, q in enumerate(t.get("quiz", [])):
            items.append({"key": f"{t['id']}:quiz:{i}", "topic": t["id"], "level": q.get("level", 1),
                          "question": q["question"], "answer": q["answer"], "hint": q["hint"], "explain": q["explain"]})
    return items


def vocabulary() -> set[str]:
    """Words in the knowledge base, used by the spelling corrector."""
    text = []
    for t in topics():
        text += [t["title"], t["summary"], *t["keywords"], *t.get("facts", [])]
    for term, meaning in glossary().items():
        text += [term, meaning]
    return {w for w in re.findall(r"[a-z]{4,}", " ".join(text).lower())}


def validate() -> list[str]:
    problems = []
    ids = {t["id"] for t in topics()}
    for t in topics():
        for field in ("id", "title", "keywords", "summary", "facts", "lesson", "source"):
            if not t.get(field):
                problems.append(f"{t.get('id', '?')}: missing {field}")
        for r in t.get("related", []):
            if r not in ids:
                problems.append(f"{t['id']}: related topic '{r}' does not exist")
        for s in t.get("lesson", []):
            for field in ("teach", "question", "answer", "hint", "explain"):
                if not s.get(field):
                    problems.append(f"{t['id']}: lesson step missing {field}")
    return problems


if __name__ == "__main__":
    print(f"{len(topics())} topics, {len(quiz_items())} quiz questions, {len(glossary())} glossary terms")
    unverified = [t["id"] for t in topics() if not t.get("verified")]
    print("Not yet verified against sources:", ", ".join(unverified) or "none")
    for p in validate():
        print("PROBLEM:", p)
