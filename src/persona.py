"""The chatbot's character: name, time-based greetings, teacher phrases, menu, badges (English and Malay)."""
import os
import random
import re
from datetime import datetime, timedelta, timezone

from . import i18n

BOT_NAME = "Guru Beleq"
BOT_MEANING = i18n.get("en", "bot_meaning")

PRAISE = i18n.get("en", "praise")
GENTLE = i18n.get("en", "gentle")
COMFORT = i18n.get("en", "comfort")

_NAME_STOP = {
    "hi", "hello", "hey", "yes", "no", "ok", "okay", "what", "who", "why", "how", "when", "where", "menu",
    "help", "quiz", "lesson", "bye", "thanks", "none", "nothing", "skip", "stop", "good", "morning", "afternoon",
    "evening", "fine", "here", "nice", "sorry", "ready", "not", "going", "confused", "tired", "the", "from",
    # Bahasa Malaysia
    "hai", "helo", "halo", "salam", "selamat", "pagi", "petang", "malam", "tengah", "terima", "kasih", "ya", "tak",
    "tidak", "nak", "mahu", "suka", "baik", "okey", "apa", "siapa", "bila", "mana", "kenapa", "bagaimana", "nama",
    "saya", "aku", "awak", "kamu", "anda", "bukan", "sedang", "sudah", "dah", "belum", "boleh", "keliru", "penat",
    "kuiz", "pelajaran", "bantuan", "tolong", "maaf", "sini", "dari", "dan", "tiada", "entah", "sedia", "jom",
}
_NAME = r"[^\W\d_][^\W\d_'\-]*(?:['\-][^\W\d_]+)*"  # letters in any alphabet, allowing O'Brien and Anne-Marie


def now() -> datetime:
    # Separate function so tests can fix the time. Vercel's clock is UTC, so online greetings use UTC+8 (Lombok time).
    return datetime.now(timezone(timedelta(hours=8))) if os.getenv("VERCEL") else datetime.now()


def _part_of_day() -> int:
    """0 = morning, 1 = afternoon, 2 = evening."""
    hour = now().hour
    return 0 if hour < 12 else 1 if hour < 18 else 2


def time_greeting(lang: str = "en") -> str:
    return i18n.get(lang, "greetings")[_part_of_day()]


def time_period(lang: str = "en") -> str:
    return i18n.get(lang, "periods")[_part_of_day()]


def reply_greeting(text: str = "", lang: str = "en") -> str:
    """Match an explicit time greeting ('good morning', 'selamat petang', etc.), or fall back to the clock."""
    low = text.lower()
    greetings = i18n.get(lang, "greetings")
    if re.search(r"\b(morning|pagi)\b", low):
        return greetings[0]
    if re.search(r"\b(afternoon|siang|sore|petang|tengah hari)\b", low):
        return greetings[1]
    if re.search(r"\b(evening|malam)\b", low):
        return greetings[2]
    return time_greeting(lang)


def pick(options: list[str]) -> str:
    return random.choice(options)


def extract_name(text: str) -> str | None:
    """Pull a first name out of text like 'I'm Budi' or just 'Budi'. Returns None if it doesn't look like a name."""
    t = text.strip().rstrip(".!")
    m = re.search(rf"\b(?:my name is|my name's|i am|i'm|im|call me|this is|it's|its|nama saya|nama aku|"
                  rf"panggil saya|panggil aku|saya ialah|saya adalah|saya|aku)\s+({_NAME})", t, re.I)
    if m:
        name = m.group(1)
    elif re.fullmatch(rf"{_NAME}(?: {_NAME})?", t):
        name = t.split()[0]
    else:
        return None
    if name.lower() in _NAME_STOP or len(name) > 25:
        return None
    return name[0].upper() + name[1:]


def menu_text(name: str, lang: str = "en") -> str:
    return i18n.t(lang, "menu", name=name)


def badge(progress: dict, lang: str = "en") -> str:
    return i18n.get(lang, "badges")[level_of(progress) - 1]


def level_of(progress: dict | None) -> int:
    if not progress:
        return 1
    points = 10 * len(progress["lessons_done"]) + 3 * progress["quiz_right"]
    if points < 10:
        return 1
    if points < 30:
        return 2
    if points < 55:
        return 3
    return 4


# phrases that show how a turn went, in every language (the reply text is all the avatar gets to see)
_MISSED_NAME = ("didn't catch your name", "tidak menangkap nama anda")
_CELEBRATE = ("Lesson complete", "Quiz finished!", "Pelajaran selesai", "Kuiz tamat!")
_THINKING = ("Here's a clue:", "You've got part of it", "I don't have an exact answer", "I'm not sure about that one",
             "Ini petunjuknya:", "Anda betul sebahagiannya", "Saya tiada jawapan yang tepat",
             "Saya kurang pasti tentang itu")
_GREETING_WORDS = (*i18n.all_values("greetings"), "You're very welcome", "Sama-sama")
_HELLO = ("Nice to meet you", "Welcome back", "Gembira berkenalan", "Selamat kembali")


def reaction_of(state: dict, reply: str = "") -> str:
    """Visual reaction state for the side avatar based on the turn outcome."""
    intent = state.get("intent", "")
    mood = state.get("mood", "")
    if intent == "six_seven" or reply.startswith("🤲 67"):
        return "six_seven"
    if state.get("invalid_reason") or intent == "offtopic" or any(m in reply for m in _MISSED_NAME):
        return "comfort"
    if mood == "struggling" or any(reply.startswith(c) for c in i18n.all_values("comfort")):
        return "comfort"
    if any(reply.startswith(p) for p in i18n.all_values("praise")) or any(c in reply for c in _CELEBRATE) or mood == "happy":
        return "celebrate"
    if any(c in reply for c in _THINKING) or any(reply.startswith(g) for g in i18n.all_values("gentle")):
        return "thinking"
    if (
        state.get("stage") == "ask_name"
        or intent == "bye"
        or (intent == "smalltalk" and any(w in reply for w in _GREETING_WORDS))
        or reply.startswith(_HELLO)
    ):
        return "greeting"
    return "teaching"
