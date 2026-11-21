"""Stations of the Sasak Village Sandbox (web/sandbox.html), served by GET /api/sandbox.

Each station picks its facts from data/knowledge/topics.json by a short phrase, so the game shows the
same cited facts as the chatbot. If a phrase stops matching exactly one fact, the tests fail.
"""
from src.knowledge import cite, glossary, references, topics

# facts: (topic id, phrase that appears in exactly one fact of that topic)
# ask: what "Tell me more" sends to the chatbot once the station's own facts have all been shown
STATIONS = [
    {
        "id": "drums", "name": "Gendang Mame & Gendang Nine", "subtitle": "The two big lead drums", "sound": "drum",
        "facts": [("instruments", "two big drums lead"), ("instruments", "drum body is wood"),
                  ("instruments", "94 cm"), ("instruments", "pemantok")],
        "terms": ["gendang mame", "gendang nine", "pemantok"],
        "ask": "tell me more about the drums",
    },
    {
        "id": "petuq", "name": "Petuq / Oncer", "subtitle": "The tempo keeper", "sound": "chime",
        "facts": [("instruments", "also called oncer"), ("players", "cohesion")],
        "terms": ["petuq", "oncer"],
        "ask": "what does the petuq do",
    },
    {
        "id": "gong", "name": "Gong Beleq & Kempur", "subtitle": "Closing and filling the phrases", "sound": "gong",
        "facts": [("instruments", "gong closes"), ("players", "four men")],
        "terms": ["kempur"],
        "ask": "tell me more about the gong",
    },
    {
        "id": "melody", "name": "Reyong & Suling", "subtitle": "The melody corner", "sound": "melody",
        "facts": [("instruments", "melody comes from the suling")],
        "terms": ["reyong", "suling"],
        "ask": "tell me more about the suling and reyong",
    },
    {
        "id": "cymbals", "name": "Kenceng & Rincik", "subtitle": "The cymbals", "sound": "shimmer",
        "facts": [("instruments", "rhythm section is"), ("instruments", "exact set can differ")],
        "terms": ["kenceng", "rincik"],
        "ask": "tell me more about the cymbals",
    },
    {
        "id": "costume", "name": "Sasak Costume Stand", "subtitle": "Sapuk, dodot and bebet", "sound": "procession",
        "facts": [("players", "traditional sasak dress"), ("players", "on their shoulders"),
                  ("players", "march and dance")],
        "terms": ["sapuk"],
        "ask": "what do the players wear",
    },
    {
        "id": "mural", "name": "Nyongkolan Arch & History Mural", "subtitle": "Weddings, ceremonies and origins",
        "sound": "procession",
        "facts": [("occasions", "accompanies the nyongkolan"), ("occasions", "circumcisions"),
                  ("history", "royal soldiers"), ("history", "exact history is uncertain"),
                  ("history", "from war to celebration")],
        "terms": ["nyongkolan"],
        "ask": "tell me more about the history",
    },
    {
        "id": "guru", "name": "Guru Beleq", "subtitle": "Your teacher on the stage", "sound": "drum",
        "facts": [("overview", "traditional art of the sasak"), ("name", "beleq' is the sasak word for big"),
                  ("overview", "found across lombok"), ("overview", "worry about its decline")],
        "terms": ["gendang", "beleq", "sasak"],
        "ask": "tell me more about the gendang beleq",
    },
]


def find_facts(topic_id: str, phrase: str) -> list[dict]:
    """Facts of one topic whose text contains the phrase (case-insensitive)."""
    topic = next((t for t in topics() if t["id"] == topic_id), None)
    if topic is None:
        return []
    return [f for f in topic["facts"] if phrase.lower() in f["text"].lower()]


def station_payload(spec: dict) -> dict:
    facts, keys = [], []
    for topic_id, phrase in spec["facts"]:
        for f in find_facts(topic_id, phrase)[:1]:
            facts.append({"text": f["text"], "cite": cite(f["sources"])})
            keys += [k for k in f["sources"] if k not in keys]
    terms = []
    for term in spec["terms"]:
        entry = glossary().get(term)
        if entry:
            terms.append({"term": term, "meaning": entry["meaning"], "cite": cite(entry["sources"])})
            keys += [k for k in entry["sources"] if k not in keys]
    return {
        "id": spec["id"], "name": spec["name"], "subtitle": spec["subtitle"], "sound": spec["sound"],
        "ask": spec["ask"], "facts": facts, "terms": terms,
        "references": [references()[k]["full"] for k in keys],
    }


def sandbox_payload() -> dict:
    stations = [station_payload(s) for s in STATIONS]
    return {"stations": stations, "total": len(stations)}
