"""The chatbot's character: name, time-based greetings, teacher phrases, menu, badges."""
import random
import re
from datetime import datetime

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
    return datetime.now()  # separate function so tests can fix the time


def time_greeting() -> str:
    hour = now().hour
    if hour < 12:
        return "Good morning"
    if hour < 18:
        return "Good afternoon"
    return "Good evening"


def time_period() -> str:
    return time_greeting().replace("Good ", "")


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
