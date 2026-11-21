"""Optional Gemini helper. Standard library only, so it adds no dependencies and stays fast on Vercel.

When GEMINI_API_KEY is set, Gemini answers open-ended conversation first (questions, follow-ups, "give me a
fun fact", small talk, off-topic questions), grounded in the whole cited knowledge base. Every function here
returns None on any problem (no key, quota used up, bad key, timeout, network error, odd response, invented
citation), and the caller silently uses the rule-based reply instead. The learner never sees the difference.

Settings (environment variables, or a local .env file that is never committed):
  GEMINI_API_KEY   free key from Google AI Studio; empty or unset means rule-based replies only
  GEMINI_MODEL     default gemini-2.5-flash
  GEMINI_ENABLED   0 / false / no / off turns Gemini off even with a key (the tests do this)
"""
import json
import logging
import os
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from .knowledge import cite, glossary, references, topics

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / ".env"
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
DEFAULT_MODEL = "gemini-2.5-flash"
TIMEOUT = 15             # seconds; slower than this falls back to the rule-based reply
COOLDOWN_SECONDS = 300   # after a quota (429) or key (401/403) error, skip Gemini for this long
MAX_REPLY_CHARS = 1500
HISTORY_TURNS = 6        # recent messages sent along so follow-ups ("explain it simply") make sense

log = logging.getLogger(__name__)
_cooldown_until = 0.0
_thinking_config_ok = True   # set False if this model rejects thinkingConfig, so it is not sent again
_last_error = ""             # for /api/meta only, never shown in the chat; the key is redacted
_last_success = ""


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
    """A key is set and Gemini has not been switched off."""
    off = os.environ.get("GEMINI_ENABLED", "1").strip().lower() in ("0", "false", "no", "off")
    return bool(api_key()) and not off


def cooling_down() -> bool:
    return time.time() < _cooldown_until


def available() -> bool:
    """Gemini will be tried on the next open-ended turn."""
    return enabled() and not cooling_down()


def status() -> dict:
    """Diagnostics for /api/meta. Contains no key."""
    return {"enabled": enabled(), "available": available(), "model": model() if enabled() else None,
            "cooldown_seconds": max(0, round(_cooldown_until - time.time())) if cooling_down() else 0,
            "last_error": _last_error, "last_success": _last_success}


def reset() -> None:
    """Clears the cooldown and diagnostics (used by the tests)."""
    global _cooldown_until, _thinking_config_ok, _last_error, _last_success
    _cooldown_until, _thinking_config_ok, _last_error, _last_success = 0.0, True, "", ""


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _fail(message: str, cooldown: bool = False) -> None:
    """Records why Gemini was not used (key redacted) and optionally pauses it."""
    global _last_error, _cooldown_until
    key = api_key()
    safe = message.replace(key, "***") if key else message
    _last_error = f"{_now()}: {safe[:300]}"
    if cooldown:
        _cooldown_until = time.time() + COOLDOWN_SECONDS
        log.warning("Gemini %s; using the rule-based engine for %d seconds", safe[:200], COOLDOWN_SECONDS)
    else:
        log.warning("Gemini %s; using the rule-based reply", safe[:200])


# ---------- the API call ----------
def _request(body: dict) -> urllib.request.Request:
    return urllib.request.Request(
        API_URL.format(model=model()),
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key()},  # key in a header, never the URL
        method="POST",
    )


def _error_detail(err: urllib.error.HTTPError) -> tuple[str, str]:
    try:
        e = json.loads(err.read() or b"{}").get("error", {})
        return str(e.get("status", "")), str(e.get("message", ""))
    except Exception:
        return "", ""


def generate(system: str, prompt: str, temperature: float = 0.6, max_tokens: int = 1024) -> str | None:
    """One Gemini call. Returns the reply text, or None on any failure (never raises)."""
    global _thinking_config_ok, _last_success
    if not available():
        return None
    config = {"temperature": temperature, "maxOutputTokens": max_tokens}
    if _thinking_config_ok and model().startswith("gemini-2.5-flash"):
        config["thinkingConfig"] = {"thinkingBudget": 0}  # short replies need no thinking; much faster
    body = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": config,
    }
    for attempt in (1, 2):
        try:
            with urllib.request.urlopen(_request(body), timeout=TIMEOUT) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as err:
            status_name, message = _error_detail(err)
            if err.code == 400 and attempt == 1 and "thinkingConfig" in config:
                # some models or API versions reject thinkingConfig: retry once without it, and stop sending it
                _thinking_config_ok = False
                del config["thinkingConfig"]
                _fail(f"HTTP 400 {status_name} with thinkingConfig, retrying without it: {message}")
                continue
            if err.code == 429 or status_name == "RESOURCE_EXHAUSTED":
                _fail(f"HTTP {err.code} {status_name} quota or rate limit: {message}", cooldown=True)
            elif err.code in (401, 403):
                _fail(f"HTTP {err.code} {status_name} API key rejected: {message}", cooldown=True)
            else:
                _fail(f"HTTP {err.code} {status_name}: {message}")
            return None
        except Exception as err:  # timeout, DNS, connection reset, invalid JSON...
            _fail(f"call failed: {type(err).__name__}: {err}")
            return None
    try:
        cand = data["candidates"][0]
        text = "".join(p.get("text", "") for p in cand["content"]["parts"] if not p.get("thought")).strip()
    except (KeyError, IndexError, TypeError, AttributeError):
        _fail(f"unexpected response: {json.dumps(data)[:200]}")
        return None
    if cand.get("finishReason") not in (None, "STOP"):  # cut off, blocked or recited: don't show it
        _fail(f"finished with {cand.get('finishReason')}")
        return None
    if not text:
        _fail("returned an empty reply")
        return None
    _last_success = _now()
    return text


# ---------- grounding ----------
@lru_cache(maxsize=1)
def _allowed_citations() -> frozenset:
    """(author word, year) pairs of our references, e.g. ('saputra', '2019'), ('tourism', 'n.d.')."""
    pairs = set()
    for r in references().values():
        name, year = r["short"].rsplit(",", 1)
        pairs.add((name.replace("et al.", "").split()[-1].lower(), year.strip()))
    return frozenset(pairs)


# "(Saputra, 2019)", "Saputra (2019)", "Saputra 2019", "Markarma et al., 2022", "Tourism, n.d."
_AUTHOR_YEAR = re.compile(r"\b([A-Z][A-Za-z'\-]+)(?:\s+et\s+al\.?)?,?\s*\(?\s*((?:19|20)\d{2}|n\.\s?d\.)")


def grounded(reply: str) -> bool:
    """False if the reply cites a source or year that is not one of our references (an invented citation).

    Replies without citations (greetings, off-topic refusals) are fine.
    """
    allowed = _allowed_citations()
    for author, year in _AUTHOR_YEAR.findall(reply):
        if (author.lower(), year.replace(" ", "")) not in allowed:
            return False
    return True


@lru_cache(maxsize=1)
def knowledge_text() -> str:
    """The whole cited knowledge base in compact form (about 2k tokens)."""
    parts = []
    for t in topics():
        parts.append(f"## {t['title']}")
        parts += [f"- {f['text']} {cite(f['sources'])}" for f in t["facts"]]
    parts.append("## Glossary")
    parts += [f"- {term}: {e['meaning']} {cite(e['sources'])}" for term, e in sorted(glossary().items())]
    parts.append("## References (Harvard)")
    parts += [f"- {r['full']}" for r in sorted(references().values(), key=lambda r: r["full"])]
    return "\n".join(parts)


SYSTEM = """You are Guru Beleq ("Big Teacher"; 'guru' is Indonesian for teacher and 'beleq' is Sasak for big), a warm,
encouraging teacher who teaches only about the Gendang Beleq, the traditional drum ensemble of the Sasak people of
Lombok, Indonesia. You are talking to {name}.

How to reply:
- Use ONLY the facts in the KNOWLEDGE BASE below. Never add names, dates, numbers, places or claims that are not there.
- After each fact you use, give its exact in-text citation as written, for example (Saputra, 2019). Never invent a source.
- If something is not covered by the knowledge base, say you don't have that in your sources rather than guessing.
- Things the knowledge base calls uncertain (such as its exact origins) must stay uncertain.
- Requests like "give me a fun fact" or "surprise me": share one interesting fact, ideally one not mentioned yet.
- Follow-ups such as "explain it simply" or "tell me more" refer to the recent conversation.
- Greetings, thanks and small talk: reply warmly in one or two sentences and invite a question. If the learner says
  good morning, good afternoon or good evening, use the same greeting back.
- Questions not about the Gendang Beleq or Sasak culture: do not answer them. Say kindly that it is outside what
  you teach, and suggest something about the Gendang Beleq instead.
- Keep it to 2 to 4 short sentences of plain text: no markdown, lists, headings or emoji.

KNOWLEDGE BASE:
{knowledge}"""


def converse(message: str, name: str, history: list[tuple[str, str]] | None = None, note: str = "") -> str | None:
    """Gemini's reply to an open-ended message, grounded in the knowledge base, or None.

    history: earlier (speaker, text) pairs, oldest first, speaker "learner" or "guru".
    note: extra context for this turn, e.g. the lesson question the learner will be brought back to.
    """
    if not available():
        return None
    system = SYSTEM.format(name=name, knowledge=knowledge_text())
    lines = []
    for speaker, text in (history or [])[-HISTORY_TURNS:]:
        who = name if speaker == "learner" else "Guru Beleq"
        lines.append(f"{who}: {text.strip()[:600]}")
    prompt = ("Recent conversation:\n" + "\n".join(lines) + "\n\n") if lines else ""
    if note:
        prompt += f"({note})\n"
    prompt += f"{name}'s new message: \"{message.strip()[:500]}\"\nReply as Guru Beleq:"
    reply = generate(system, prompt)
    if reply is None:
        return None
    reply = re.sub(r"^\s*Guru Beleq:\s*", "", reply)
    if len(reply) > MAX_REPLY_CHARS:
        _fail(f"reply too long ({len(reply)} characters)")
        return None
    if not grounded(reply):
        _fail(f"reply cited a source that is not in the knowledge base: {reply[:160]}")
        return None
    return reply
