from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class State(TypedDict, total=False):
    messages: Annotated[list, add_messages]  # conversation history
    boot: bool           # True only for the opening turn, when the bot speaks first
    stage: str           # "ask_name" | "menu" | "lesson" | "quiz"
    user_name: str
    invalid_reason: str  # set by validate: "empty" | "too_long" | "gibberish"
    clean_text: str      # user text after spelling correction
    heard: str           # corrected text, shown back to the user when it differs from what they typed
    search_query: str    # clean text + synonyms + semantic-net neighbours (+ previous turn for follow-ups)
    cued: bool           # the question type was recognised (how many, when, where...)
    mood: str            # "struggling" | "happy" | ""
    intent: str          # which branch of the graph handled the message
    lesson: dict         # {"topic": id, "step": n, "attempts": n} while a lesson is running
    quiz: dict           # {"n", "right", "asked", "current", "attempts"} while a quiz is running
    progress: dict       # see profiles.new_progress()
    told: list           # facts already given in this conversation, so "tell me more" moves on
