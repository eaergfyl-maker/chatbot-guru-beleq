"""Knowledge base: lessons, quiz questions, cited facts, glossary and references in data/knowledge/topics.json.

Other languages: data/knowledge/topics_<lang>.json holds only the wording (titles, facts, lesson and quiz text,
glossary meanings). It is laid over the English base by position, so every translated fact keeps the English
fact's sources and citation. Translated keywords and answer words are added to the English ones, so a learner
in Bahasa Malaysia mode can still answer in English.

Check it with:  python -m src.knowledge
"""
import copy
import json
import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KB_FILE = ROOT / "data" / "knowledge" / "topics.json"


def _translation_file(lang: str) -> Path:
    return ROOT / "data" / "knowledge" / f"topics_{lang}.json"


@lru_cache(maxsize=1)
def load_kb() -> dict:
    return json.loads(KB_FILE.read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def load_translation(lang: str) -> dict:
    """The translated wording for a language, or {} for English or a language without a file."""
    f = _translation_file(lang)
    if lang == "en" or not f.exists():
        return {}
    return json.loads(f.read_text(encoding="utf-8"))


def _merge_words(first: list, then: list) -> list:
    return list(first) + [w for w in then if w not in first]


def _localise(topic: dict, tr: dict) -> dict:
    t = copy.deepcopy(topic)
    t["title"], t["summary"] = tr.get("title", t["title"]), tr.get("summary", t["summary"])
    t["keywords"] = _merge_words(tr.get("keywords", []), t["keywords"])
    for fact, text in zip(t["facts"], tr.get("facts", [])):
        fact["text"] = text
    for kind in ("lesson", "quiz"):
        for step, ts in zip(t.get(kind, []), tr.get(kind, [])):
            for field in ("teach", "question", "hint", "explain"):
                if ts.get(field):
                    step[field] = ts[field]
            if ts.get("answer"):
                step["answer"] = [_merge_words(mine, base) for mine, base in zip(ts["answer"], step["answer"])]
    return t


@lru_cache(maxsize=None)
def _topics(lang: str) -> tuple:
    base = load_kb()["topics"]
    tr = load_translation(lang).get("topics", {})
    return tuple(_localise(t, tr[t["id"]]) if t["id"] in tr else t for t in base)


def topics(lang: str = "en") -> list[dict]:
    return list(_topics(lang))


def get_topic(topic_id: str, lang: str = "en") -> dict:
    return next(t for t in _topics(lang) if t["id"] == topic_id)


@lru_cache(maxsize=None)
def _glossary(lang: str) -> dict:
    base = load_kb().get("glossary", {})
    tr = load_translation(lang).get("glossary", {})
    return {term: ({**entry, "meaning": tr[term]} if term in tr else entry) for term, entry in base.items()}


def glossary(lang: str = "en") -> dict:
    return _glossary(lang)


def network_labels(lang: str = "en") -> tuple[dict, dict]:
    """Translated semantic-network labels: (concepts, relations), each English -> translation."""
    net = load_translation(lang).get("network", {})
    return net.get("concepts", {}), net.get("relations", {})


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


def quiz_items(lang: str = "en") -> list[dict]:
    """Every lesson check question plus the extra quiz questions, in one pool. Keys are the same in every language."""
    items = []
    for t in topics(lang):
        for i, s in enumerate(t.get("lesson", [])):
            items.append({"key": f"{t['id']}:lesson:{i}", "topic": t["id"], "level": 1,
                          "question": s["question"], "answer": s["answer"], "hint": s["hint"], "explain": s["explain"]})
        for i, q in enumerate(t.get("quiz", [])):
            items.append({"key": f"{t['id']}:quiz:{i}", "topic": t["id"], "level": q.get("level", 1),
                          "question": q["question"], "answer": q["answer"], "hint": q["hint"], "explain": q["explain"]})
    return items


def vocabulary(lang: str = "en") -> set[str]:
    """Words in the knowledge base, used by the spelling corrector. Other languages also keep the English words."""
    text = []
    for code in {"en", lang}:
        for t in topics(code):
            text += [t["title"], t["summary"], *t["keywords"], *(f["text"] for f in t["facts"])]
        for term, entry in glossary(code).items():
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
    return problems + validate_translation("ms")


def validate_translation(lang: str) -> list[str]:
    """A translation must cover every topic, fact, lesson step, quiz item and glossary term, position by position,
    with the same number of answer groups, so no fact can lose its citation."""
    tr = load_translation(lang)
    if not tr:
        return [f"{lang}: translation file {_translation_file(lang).name} is missing"]
    problems = []
    for t in topics():
        tt = tr.get("topics", {}).get(t["id"])
        if not tt:
            problems.append(f"{lang}: topic '{t['id']}' is not translated")
            continue
        for field in ("title", "summary", "keywords"):
            if not tt.get(field):
                problems.append(f"{lang}/{t['id']}: missing {field}")
        if len(tt.get("facts", [])) != len(t["facts"]):
            problems.append(f"{lang}/{t['id']}: {len(tt.get('facts', []))} facts, English has {len(t['facts'])}")
        for kind in ("lesson", "quiz"):
            base, mine = t.get(kind, []), tt.get(kind, [])
            if len(mine) != len(base):
                problems.append(f"{lang}/{t['id']}: {len(mine)} {kind} items, English has {len(base)}")
            for i, (b, m) in enumerate(zip(base, mine)):
                for field in ("question", "answer", "hint", "explain", *(["teach"] if kind == "lesson" else [])):
                    if not m.get(field):
                        problems.append(f"{lang}/{t['id']} {kind} {i}: missing {field}")
                if len(m.get("answer", [])) != len(b["answer"]):
                    problems.append(f"{lang}/{t['id']} {kind} {i}: answer groups differ from English")
    missing = set(glossary()) - set(tr.get("glossary", {}))
    problems += [f"{lang}: glossary term '{term}' is not translated" for term in sorted(missing)]
    return problems


if __name__ == "__main__":
    facts = sum(len(t["facts"]) for t in topics())
    print(f"{len(topics())} topics, {facts} cited facts, {len(quiz_items())} quiz questions, "
          f"{len(glossary())} glossary terms, {len(references())} references")
    problems = validate()
    for p in problems:
        print("PROBLEM:", p)
    print("Problems:", len(problems))
