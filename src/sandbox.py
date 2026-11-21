"""Stations of the Sasak Village Sandbox (web/sandbox.html), served by GET /api/sandbox.

Each station picks its facts from data/knowledge/topics.json by a short English phrase, so the game shows the
same cited facts as the chatbot. If a phrase stops matching exactly one fact, the tests fail. In Bahasa Malaysia
the station shows the Malay text of the same facts (same position, same citations).
"""
from src.knowledge import cite, glossary, references, topics

# station name, subtitle and "Tell me more" question in Bahasa Malaysia
MALAY = {
    "drums": ("Gendang Mame & Gendang Nine", "Dua gendang besar yang mengetuai", "ceritakan lagi tentang gendang"),
    "petuq": ("Petuq / Oncer", "Penjaga tempo", "apa fungsi petuq"),
    "gong": ("Gong Beleq & Kempur", "Menutup dan mengisi frasa", "ceritakan lagi tentang gong"),
    "melody": ("Reyong & Suling", "Sudut melodi", "ceritakan lagi tentang suling dan reyong"),
    "cymbals": ("Kenceng & Rincik", "Simbal", "ceritakan lagi tentang simbal"),
    "costume": ("Tempat Pakaian Sasak", "Sapuk, dodot dan bebet", "apakah pakaian pemain"),
    "mural": ("Gerbang Nyongkolan & Mural Sejarah", "Perkahwinan, upacara dan asal usul", "ceritakan lagi tentang sejarah"),
    "guru": ("Guru Beleq", "Guru anda di pentas", "ceritakan lagi tentang gendang beleq"),
}

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


def _localised_fact(topic_id: str, fact: dict, lang: str) -> dict:
    """The same fact (same position in its topic) in another language."""
    if lang == "en":
        return fact
    english = next(t for t in topics() if t["id"] == topic_id)["facts"]
    mine = next(t for t in topics(lang) if t["id"] == topic_id)["facts"]
    return mine[english.index(fact)]


def station_payload(spec: dict, lang: str = "en") -> dict:
    facts, keys = [], []
    for topic_id, phrase in spec["facts"]:
        for f in find_facts(topic_id, phrase)[:1]:
            facts.append({"text": _localised_fact(topic_id, f, lang)["text"], "cite": cite(f["sources"])})
            keys += [k for k in f["sources"] if k not in keys]
    terms = []
    for term in spec["terms"]:
        entry = glossary(lang).get(term)
        if entry:
            terms.append({"term": term, "meaning": entry["meaning"], "cite": cite(entry["sources"])})
            keys += [k for k in entry["sources"] if k not in keys]
    name, subtitle, ask = MALAY[spec["id"]] if lang == "ms" else (spec["name"], spec["subtitle"], spec["ask"])
    return {
        "id": spec["id"], "name": name, "subtitle": subtitle, "sound": spec["sound"],
        "ask": ask, "facts": facts, "terms": terms,
        "references": [references()[k]["full"] for k in keys],
    }


def sandbox_payload(lang: str = "en") -> dict:
    stations = [station_payload(s, lang) for s in STATIONS]
    return {"stations": stations, "total": len(stations), "lang": lang}
