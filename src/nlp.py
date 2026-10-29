"""Lightweight NLP layer: input validation, spelling correction, synonyms, keywords, answer matching.

Plain Python, no models and no network.
"""
import difflib
import re
from functools import lru_cache

MAX_LEN = 500

# canonical term -> variants a user might type. A hit adds the canonical term to the search query.
SYNONYMS = {
    "gendang beleq": ["gendang belek", "gendang belaq", "gendang beleg", "big drum", "giant drum", "drum ensemble"],
    "history": ["origin", "origins", "background", "heritage", "past", "began", "started"],
    "instrument": ["instruments", "gong", "drums", "cymbal", "cymbals", "equipment", "music tools"],
    "ceremony": ["ritual", "rituals", "festival", "celebration", "event", "occasion", "wedding"],
    "performance": ["perform", "performed", "play", "played", "playing", "show", "parade"],
    "warrior": ["war", "battle", "fighting", "soldier", "soldiers"],
    "costume": ["clothing", "clothes", "attire", "dress", "outfit", "uniform"],
    "meaning": ["significance", "symbolism", "symbol", "purpose", "function", "role"],
    "sasak": ["lombok people", "sasak people", "lombok tribe"],
    "lombok": ["west nusa tenggara", "ntb"],
}

STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "do", "does", "did", "of", "to", "in", "on", "at", "and", "or",
    "what", "who", "when", "where", "why", "how", "which", "can", "could", "would", "should", "me", "i", "you",
    "tell", "about", "please", "it", "its", "this", "that", "these", "those", "for", "with", "be", "have", "has",
    "my", "your", "some", "any", "there", "they", "them", "their", "from", "also",
}

# names users are most likely to mistype; matched loosely
_BASE_VOCAB = {
    "gendang", "beleq", "belek", "sasak", "lombok", "indonesia", "drum", "drums", "gong", "ensemble",
    "ceremony", "instrument", "instruments", "history", "performance", "traditional", "culture", "quiz",
    "lesson", "nyongkolan", "wedding", "costume",
}


@lru_cache(maxsize=1)
def load_vocab() -> frozenset:
    from .knowledge import vocabulary  # lazy import: knowledge does not depend on nlp

    return frozenset(_BASE_VOCAB | vocabulary())


def validate_input(text: str) -> str | None:
    """Return a reason code if the input can't be processed, else None."""
    if not text or not text.strip():
        return "empty"
    if len(text) > MAX_LEN:
        return "too_long"
    if re.fullmatch(r"\s*\d{1,2}\s*", text):  # a menu number
        return None
    letters = sum(c.isalpha() for c in text)
    if letters < 2 or letters / len(text) < 0.4:
        return "gibberish"
    if re.search(r"(.)\1{9,}", text):
        return "gibberish"
    return None


def correct_spelling(text: str) -> str:
    """Fix near-miss spellings of domain words (e.g. 'gendnag' -> 'gendang')."""
    vocab = load_vocab()
    candidates = sorted(vocab)
    core = sorted(_BASE_VOCAB)

    def fix(match: re.Match) -> str:
        word = match.group(0)
        low = word.lower()
        n = len(low)
        if n < 4 or low in vocab or low in STOPWORDS:
            return word
        # looser match against the short core list, stricter and only for longer words against the full vocabulary,
        # so ordinary words such as 'long' or 'mean' are left alone
        close = difflib.get_close_matches(low, core, n=1, cutoff=0.79 if n <= 5 else 0.72)
        if not close and n >= 6:
            close = difflib.get_close_matches(low, candidates, n=1, cutoff=0.84)
        return close[0] if close else word

    return re.sub(r"[A-Za-z]+", fix, text)


def expand_synonyms(text: str) -> list[str]:
    """Canonical terms whose variants appear in the text and that the text doesn't already contain."""
    low = text.lower()
    found = []
    for canonical, variants in SYNONYMS.items():
        if canonical in low:
            continue
        if any(re.search(rf"\b{re.escape(v)}\b", low) for v in variants):
            found.append(canonical)
    return found


def stem(word: str) -> str:
    return word[:-1] if len(word) > 3 and word.endswith("s") and not word.endswith("ss") else word


def extract_keywords(text: str) -> list[str]:
    words = re.findall(r"[a-z]+", text.lower())
    seen, out = set(), []
    for w in words:
        if len(w) > 2 and w not in STOPWORDS and w not in seen:
            seen.add(w)
            out.append(w)
    return out


def concept_hit(text: str, variants: list[str]) -> bool:
    """Does the learner's answer mention this concept? Tolerates plurals and small typos."""
    low = text.lower()
    tokens = re.findall(r"[a-z]+", low)
    for v in (x.lower() for x in variants):
        if " " in v:
            if v in low:
                return True
            continue
        for t in tokens:
            if t == v:
                return True
            if len(v) >= 4 and (t.startswith(v) or difflib.SequenceMatcher(None, t, v).ratio() >= 0.8):
                return True
    return False
