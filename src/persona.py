"""The chatbot's character: name, time-based greetings, teacher phrases, menu, badges."""
import os
import random
import re
from datetime import datetime, timedelta, timezone

BOT_NAME = "Guru Beleq"
BOT_MEANING = "'Guru' is Indonesian for teacher and 'beleq' is Sasak for big, so I am the Big Teacher"

PRAISE = ["Excellent!", "Well done!", "Spot on!", "That's right!", "Great job!", "Exactly!"]
GENTLE = ["Not quite, but you're on the right track.", "Close! Keep thinking.", "Good effort, let's refine it."]
COMFORT = ["No worries, everyone learns at their own pace.", "That's okay, we'll take it slowly."]

_NAME_STOP = {
    "hi", "hello", "hey", "yes", "no", "ok", "okay", "what", "who", "why", "how", "when", "where", "menu",
    "help", "quiz", "lesson", "bye", "thanks", "none", "nothing", "skip", "stop", "good", "morning", "afternoon",
    "evening", "fine", "here", "nice", "sorry", "ready", "not", "going", "confused", "tired", "the", "from",
}
_NAME = r"[^\W\d_][^\W\d_'\-]*(?:['\-][^\W\d_]+)*"  # letters in any alphabet, allowing O'Brien and Anne-Marie


def now() -> datetime:
    # Separate function so tests can fix the time. Vercel's clock is UTC, so online greetings use UTC+8 (Lombok time).
    return datetime.now(timezone(timedelta(hours=8))) if os.getenv("VERCEL") else datetime.now()


def time_greeting() -> str:
    hour = now().hour
    if hour < 12:
        return "Good morning"
    if hour < 18:
        return "Good afternoon"
    return "Good evening"


def time_period() -> str:
    return time_greeting().replace("Good ", "")


def reply_greeting(text: str = "") -> str:
    """Match an explicit time greeting ('good morning', 'good evening', etc.), or fall back to the clock."""
    low = text.lower()
    if re.search(r"\b(morning|pagi)\b", low):
        return "Good morning"
    if re.search(r"\b(afternoon|siang|sore)\b", low):
        return "Good afternoon"
    if re.search(r"\b(evening|malam)\b", low):
        return "Good evening"
    return time_greeting()


def pick(options: list[str]) -> str:
    return random.choice(options)


def extract_name(text: str) -> str | None:
    """Pull a first name out of text like 'I'm Budi' or just 'Budi'. Returns None if it doesn't look like a name."""
    t = text.strip().rstrip(".!")
    m = re.search(rf"\b(?:my name is|my name's|i am|i'm|im|call me|this is|it's|its)\s+({_NAME})", t, re.I)
    if m:
        name = m.group(1)
    elif re.fullmatch(rf"{_NAME}(?: {_NAME})?", t):
        name = t.split()[0]
    else:
        return None
    if name.lower() in _NAME_STOP or len(name) > 25:
        return None
    return name[0].upper() + name[1:]


def menu_text(name: str) -> str:
    return (
        f"Here is what we can do together, {name}:\n"
        "  1. Start a lesson (I teach you step by step)\n"
        "  2. Ask me anything about the Gendang Beleq\n"
        "  3. Take a quiz\n"
        "  4. Get a recommendation on what to learn next\n"
        "  5. See your progress\n"
        "  6. Help\n"
        "  7. See the sources behind what I teach\n"
        "  8. Browse the Sasak glossary\n"
        "  0. Say goodbye\n"
        "Type a number, or simply tell me in your own words what you would like."
    )


def badge(progress: dict) -> str:
    points = 10 * len(progress["lessons_done"]) + 3 * progress["quiz_right"]
    if points < 10:
        return "Curious Listener"
    if points < 30:
        return "Apprentice Drummer"
    if points < 55:
        return "Gong Keeper"
    return "Master of the Big Drum"


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


def reaction_of(state: dict, reply: str = "") -> str:
    """Visual reaction state for the side avatar based on the turn outcome."""
    intent = state.get("intent", "")
    mood = state.get("mood", "")
    if intent == "six_seven" or reply.startswith("🤲 67"):
        return "six_seven"
    if state.get("invalid_reason") or intent == "offtopic" or "didn't catch your name" in reply:
        return "comfort"
    if mood == "struggling" or any(reply.startswith(c) for c in COMFORT):
        return "comfort"
    if (
        any(reply.startswith(p) for p in PRAISE)
        or "Lesson complete" in reply
        or "Quiz finished!" in reply
        or mood == "happy"
    ):
        return "celebrate"
    if (
        "Here's a clue:" in reply
        or any(reply.startswith(g) for g in GENTLE)
        or "You've got part of it" in reply
        or "I don't have an exact answer" in reply
        or "I'm not sure about that one" in reply
    ):
        return "thinking"
    if (
        state.get("stage") == "ask_name"
        or intent == "bye"
        or (
            intent == "smalltalk"
            and any(w in reply for w in ("Good morning", "Good afternoon", "Good evening", "You're very welcome"))
        )
        or reply.startswith(("Nice to meet you", "Welcome back"))
    ):
        return "greeting"
    return "teaching"
