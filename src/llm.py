"""Optional Gemini helper. Standard library only, so it adds no dependencies and stays fast on Vercel.

Smart Mode is on only when GEMINI_API_KEY is set. Every function here returns None on any problem
(no key, quota used up, bad key, timeout, network error, odd response, ungrounded reply), and the caller
then uses the rule-based reply it already computed. The chatbot never depends on Gemini.

Settings (environment variables, or a local .env file that is never committed):
  GEMINI_API_KEY   free key from Google AI Studio; empty or unset means Classic (rule-based) Mode
  GEMINI_MODEL     default gemini-2.5-flash
  GEMINI_ENABLED   0 / false / no / off turns Smart Mode off even with a key (the tests do this)
"""
import json
import logging
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

from .knowledge import cite, glossary, references

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / ".env"
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
DEFAULT_MODEL = "gemini-2.5-flash"
TIMEOUT = 6              # seconds; a slow reply falls back instead of keeping the learner waiting
COOLDOWN_SECONDS = 300   # after a quota (429) or key (401/403) error, skip Gemini for this long
MAX_REPLY_CHARS = 1200

log = logging.getLogger(__name__)
_cooldown_until = 0.0


def load_env(path: Path = ENV_FILE) -> None:
    """Reads KEY=VALUE lines from a .env file. Variables already set in the environment win."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip().removeprefix("export ").strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        if key:
            os.environ.setdefault(key, value)


load_env()


# ---------- configuration and status ----------
def api_key() -> str:
    return os.environ.get("GEMINI_API_KEY", "").strip()


def model() -> str:
    return os.environ.get("GEMINI_MODEL", "").strip() or DEFAULT_MODEL


def enabled() -> bool:
    """A key is set and Smart Mode has not been switched off."""
    off = os.environ.get("GEMINI_ENABLED", "1").strip().lower() in ("0", "false", "no", "off")
    return bool(api_key()) and not off


def cooling_down() -> bool:
    return time.time() < _cooldown_until


def available() -> bool:
    """Gemini will be tried on the next turn."""
    return enabled() and not cooling_down()


def status() -> dict:
    return {"enabled": enabled(), "available": available(), "model": model() if enabled() else None,
            "cooldown_seconds": max(0, round(_cooldown_until - time.time())) if cooling_down() else 0}


def reset() -> None:
    """Clears the cooldown (used by the tests)."""
    global _cooldown_until
    _cooldown_until = 0.0


def _start_cooldown(reason: str) -> None:
    global _cooldown_until
    _cooldown_until = time.time() + COOLDOWN_SECONDS
    log.warning("Gemini %s; using the rule-based engine for %d seconds", reason, COOLDOWN_SECONDS)


# ---------- the API call ----------
def generate(system: str, prompt: str, temperature: float = 0.4, max_tokens: int = 400) -> str | None:
    """One Gemini call. Returns the reply text, or None on any failure (never raises)."""
    if not available():
        return None
    config = {"temperature": temperature, "maxOutputTokens": max_tokens}
    if model().startswith("gemini-2.5-flash"):
        config["thinkingConfig"] = {"thinkingBudget": 0}  # short grounded answers need no thinking; keeps it fast
    body = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": config,
    }
    req = urllib.request.Request(
        API_URL.format(model=model()),
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key()},  # key in a header, never in the URL
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        detail = ""
        try:
            detail = json.loads(err.read() or b"{}").get("error", {}).get("status", "")
        except Exception:
            pass
        if err.code == 429 or detail == "RESOURCE_EXHAUSTED":
            _start_cooldown("quota or rate limit reached (HTTP 429)")
        elif err.code in (401, 403):
            _start_cooldown(f"rejected the API key (HTTP {err.code})")
        else:
            log.warning("Gemini HTTP %s %s; using the rule-based reply", err.code, detail)
        return None
    except Exception as err:  # timeout, DNS, connection reset, invalid JSON...
        log.warning("Gemini call failed (%s); using the rule-based reply", type(err).__name__)
        return None
    try:
        cand = data["candidates"][0]
        if cand.get("finishReason") not in (None, "STOP"):  # cut off, blocked or recited: don't show it
            log.warning("Gemini finished with %s; using the rule-based reply", cand.get("finishReason"))
            return None
        text = "".join(p.get("text", "") for p in cand["content"]["parts"]).strip()
    except (KeyError, IndexError, TypeError, AttributeError):
        log.warning("Gemini returned an unexpected response; using the rule-based reply")
        return None
    return text or None


# ---------- grounding ----------
_CITATION = re.compile(r"\(([^()]*?(?:\d{4}|n\.d\.)[^()]*)\)")

PERSONA = (
    "You are Guru Beleq ('Big Teacher'), a warm, encouraging teacher who teaches only about the Gendang Beleq, "
    "the traditional drum ensemble of the Sasak people of Lombok, Indonesia. You are talking to {name}. "
    "Reply in plain English text: no markdown, no lists, no headings, no emoji."
)

ANSWER_RULES = """
Rules:
- Use ONLY the facts in KNOWLEDGE. Never add names, dates, numbers, places or claims that are not there.
- After each fact you use, copy its exact in-text citation, for example (Saputra, 2019). Never invent or change a citation.
- If the facts only partly answer the question, say so honestly and share only what they support.
- Things the facts call uncertain (such as its exact origins) must stay uncertain.
- If the question is not about the Gendang Beleq or Sasak culture, politely say it is outside what you teach.
- Answer in 2 to 4 short sentences. Do not end with a question; the app adds its own follow-up.
"""


def _knowledge_block(facts: list[dict], question: str) -> tuple[str, set[str]]:
    """Facts, matching glossary entries and their Harvard references, plus the set of allowed citation parts."""
    keys, lines = [], []
    for f in facts:
        lines.append(f"- {f['text']} {cite(f['sources'])}")
        keys += [k for k in f["sources"] if k not in keys]
    low = f"{question} {' '.join(f['text'] for f in facts)}".lower()
    terms = []
    for term, entry in sorted(glossary().items()):
        if re.search(rf"\b{re.escape(term)}\b", low):
            terms.append(f"- {term}: {entry['meaning']} {cite(entry['sources'])}")
            keys += [k for k in entry["sources"] if k not in keys]
    refs = references()
    block = "KNOWLEDGE:\n" + "\n".join(lines)
    if terms:
        block += "\n\nGLOSSARY:\n" + "\n".join(terms)
    block += "\n\nREFERENCES (Harvard):\n" + "\n".join(f"- {refs[k]['full']}" for k in keys)
    return block, {refs[k]["short"] for k in keys}


def grounded(reply: str, allowed: set[str], need_citation: bool = True) -> bool:
    """Every citation in the reply is one we supplied, and (for answers) there is at least one."""
    found = _CITATION.findall(reply)
    parts = [p.strip() for group in found for p in group.split(";")]
    if any(p not in allowed for p in parts):
        return False
    return bool(parts) or not need_citation


def grounded_answer(question: str, name: str, facts: list[dict], partial: bool = False) -> str | None:
    """A natural answer written only from the retrieved facts, keeping their citations, or None."""
    if not facts or not available():
        return None
    block, allowed = _knowledge_block(facts, question)
    system = PERSONA.format(name=name) + "\n" + ANSWER_RULES + "\n" + block
    prompt = f"{name} asks: \"{question.strip()[:500]}\""
    if partial:
        prompt += "\n(The knowledge may only partly answer this. Say so, then share what it does say.)"
    reply = generate(system, prompt)
    if reply is None:
        return None
    if len(reply) > MAX_REPLY_CHARS or not grounded(reply, allowed):
        log.warning("Gemini answer was not grounded in the supplied citations; using the rule-based reply")
        return None
    return reply


def in_character(message: str, name: str, draft: str, must_include: str = "") -> str | None:
    """Rewrites a rule-based small-talk or off-topic reply warmly in character, or None.

    No facts are supplied, so a reply that cites anything is rejected. `must_include` keeps a phrase
    the classic reply relies on (such as a mirrored 'Good morning').
    """
    if not available():
        return None
    system = PERSONA.format(name=name) + """
Rewrite the DRAFT reply so it sounds natural and warm, in 1 to 3 short sentences. Keep its meaning and its invitation.
Do not state any facts about the Gendang Beleq, and do not answer anything outside the Gendang Beleq: if the draft
declines a topic, decline it too and steer gently back to the Gendang Beleq."""
    reply = generate(system, f"{name} said: \"{message.strip()[:300]}\"\nDRAFT reply: {draft}", temperature=0.7, max_tokens=200)
    if reply is None:
        return None
    if len(reply) > 500 or not grounded(reply, set(), need_citation=False):
        return None
    if must_include and must_include.lower() not in reply.lower():
        return None
    return reply
