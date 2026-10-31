"""Knowledge base: lessons, quiz questions, cited facts, glossary and references in data/knowledge/topics.json.

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


def references() -> dict:
    return load_kb().get("references", {})


def topic_sources(topic: dict) -> list[str]:
    """Every source cited by a topic's facts, in first-cited order."""
    keys = []
    for fact in topic["facts"]:
        keys += [k for k in fact["sources"] if k not in keys]
    return keys


def cite(keys: list[str]) -> str:
    """In-text Harvard citation, e.g. '(Saputra, 2019; Keen, 2015)'."""
    return "(" + "; ".join(references()[k]["short"] for k in keys) + ")"


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
        text += [t["title"], t["summary"], *t["keywords"], *(f["text"] for f in t["facts"])]
    for term, entry in glossary().items():
        text += [term, entry["meaning"]]
    return {w for w in re.findall(r"[a-z]{4,}", " ".join(text).lower())}


def validate() -> list[str]:
    problems = []
    ids = {t["id"] for t in topics()}
    refs = references()
    for t in topics():
        for field in ("id", "title", "keywords", "summary", "facts", "lesson"):
            if not t.get(field):
                problems.append(f"{t.get('id', '?')}: missing {field}")
        for r in t.get("related", []):
            if r not in ids:
                problems.append(f"{t['id']}: related topic '{r}' does not exist")
        for fact in t.get("facts", []):
            if not fact.get("sources"):
                problems.append(f"{t['id']}: fact has no source: {fact.get('text', '')[:40]}")
            problems += [f"{t['id']}: unknown source '{k}'" for k in fact.get("sources", []) if k not in refs]
        for s in [*t.get("lesson", []), *t.get("quiz", [])]:
            for field in ("question", "answer", "hint", "explain"):
                if not s.get(field):
                    problems.append(f"{t['id']}: question missing {field}")
    for term, entry in glossary().items():
        if not entry.get("sources"):
            problems.append(f"glossary '{term}' has no source")
        problems += [f"glossary '{term}': unknown source '{k}'" for k in entry.get("sources", []) if k not in refs]
    return problems


if __name__ == "__main__":
    facts = sum(len(t["facts"]) for t in topics())
    print(f"{len(topics())} topics, {facts} cited facts, {len(quiz_items())} quiz questions, "
          f"{len(glossary())} glossary terms, {len(references())} references")
    problems = validate()
    for p in problems:
        print("PROBLEM:", p)
    print("Problems:", len(problems))
