"""Semantic network of the domain (knowledge representation).

Nodes are concepts, edges are labelled relations. The chatbot uses it to widen a search with
related concepts (spreading activation, one hop). Print it for the report with:
    python -m src.semantic_net
"""
import json
from functools import lru_cache
from pathlib import Path

NET_FILE = Path(__file__).resolve().parent.parent / "data" / "knowledge" / "semantic_net.json"


@lru_cache(maxsize=1)
def load_edges() -> tuple:
    if not NET_FILE.exists():
        return ()
    return tuple(json.loads(NET_FILE.read_text(encoding="utf-8")).get("edges", []))


def label(concept: str, lang: str = "en") -> str:
    """A concept's name in a language (proper names such as 'petuq' are the same in every language)."""
    from .knowledge import network_labels

    return network_labels(lang)[0].get(concept, concept) if lang != "en" else concept


def relation_label(relation: str, lang: str = "en") -> str:
    from .knowledge import network_labels

    plain = relation.replace("_", " ")
    return network_labels(lang)[1].get(relation, plain) if lang != "en" else plain


def related_concepts(text: str, limit: int = 4, lang: str = "en") -> list[str]:
    """Concepts one hop away from any node mentioned in the text, named in the learner's language.

    Gendang Beleq itself is skipped as a starting point: every concept connects to it, so spreading from it
    would pull the whole network into the search and drown out what was actually asked.
    """
    low = text.lower()
    out: list[str] = []
    for e in load_edges():
        for here, other in ((e["s"], e["o"]), (e["o"], e["s"])):
            if here.lower() == "gendang beleq":
                continue
            names = {here.lower(), label(here, lang).lower()}
            name = label(other, lang)
            if any(n in low for n in names) and name.lower() not in low and name not in out:
                out.append(name)
    return out[:limit]


def to_mermaid() -> str:
    lines = ["graph LR"]
    for e in load_edges():
        lines.append(f'    {_id(e["s"])}["{e["s"]}"] -->|{e["r"]}| {_id(e["o"])}["{e["o"]}"]')
    return "\n".join(lines)


def _id(label: str) -> str:
    return "n_" + "".join(c if c.isalnum() else "_" for c in label)


if __name__ == "__main__":
    print(to_mermaid())
