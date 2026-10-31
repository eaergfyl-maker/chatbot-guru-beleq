"""Graph nodes. Every node is plain Python: it reads the State and returns the fields it changes."""
import copy
import random
import re

from langchain_core.messages import AIMessage, HumanMessage

from . import nlp, persona, profiles, search
from .knowledge import cite, get_topic, quiz_items, references, topic_sources, topics
from .semantic_net import related_concepts
from .state import State

QUIZ_LENGTH = 5

REJECT_MESSAGES = {
    "empty": "I didn't catch anything there. Could you type your message again?",
    "too_long": "That message is a bit long for me. Could you shorten it to one or two sentences?",
    "gibberish": "I couldn't make sense of that. Could you rephrase it in a sentence?",
}
ERROR_MESSAGE = "Sorry, something went wrong on my side. Could you try that again?"

# ---------- patterns ----------
_GREETING = re.compile(r"^\s*(hi|hello|hey|hai|halo|selamat\s+\w+|good\s+(morning|afternoon|evening|day))\b", re.I)
_THANKS = re.compile(r"\b(thanks|thank you|terima kasih|cheers|appreciate)\b", re.I)
_BYE = re.compile(r"\b(bye|goodbye|see you|exit|quit|good night)\b", re.I)
_MENU = re.compile(r"\b(menu|options|main menu)\b", re.I)
_PROGRESS = re.compile(r"\b(progress|score|report card|how am i doing|my results|badge)\b", re.I)
_HELP = re.compile(r"^\s*(help|how do i use|what can you do|commands)\b", re.I)
_RECOMMEND = re.compile(r"\b(recommend|suggest|what should i|where (do|should) i (start|begin)|next topic|what next)\b", re.I)
_QUIZ = re.compile(r"\b(quiz|test me|test my|exam|question me)\b", re.I)
_LESSON = re.compile(r"\b(lessons?|teach|tutorial|class|study)\b|\b(want|like|love|help me|let'?s|start|begin) (to )?learn\b|^\s*learn\b", re.I)
_SOURCES = re.compile(r"\b(sources?|references?|citations?|bibliography|where did you (get|learn))\b", re.I)
_IDENTITY = re.compile(r"\b(who are you|what are you|your name|about you|are you a (bot|robot|person|human))\b", re.I)
_CONTINUE = re.compile(r"^\s*(next|continue|yes|yeah|yep|sure|ok|okay|ready|go on|go ahead|let'?s go)\b", re.I)
_DECLINE = re.compile(r"^\s*(no|nope|not now|not yet|nah|maybe later|later)\b", re.I)
_LEAVE = re.compile(r"^\s*(stop|quit|exit|menu|leave|cancel|main menu)\b|\b(stop|quit) (the )?(lesson|quiz)\b", re.I)
_HINT = re.compile(r"^\s*(hint|clue|help)\b", re.I)
_SKIP = re.compile(r"\b(skip|pass|i don'?t know|dunno|no idea|give up|tell me the answer)\b", re.I)
_REPEAT = re.compile(r"\b(repeat|again|re-?explain)\b", re.I)
_QUESTION = re.compile(r"^\s*(what|who|when|where|why|how|which|can|could|does|do|is|are|tell me)\b", re.I)
_DOMAIN = re.compile(r"\b(gendang|beleq|belek|sasak|lombok|drum|drums|gong|ensemble|nyongkolan)", re.I)
_STRUGGLING = re.compile(r"(confus|don'?t understand|do not understand|too hard|difficult|stuck|lost|frustrat|boring)", re.I)
_HAPPY = re.compile(r"\b(great|awesome|love|fun|cool|amazing|nice|interesting)\b", re.I)
_SUBJECT_NAMES = re.compile(r"\b(gendang bel(ek|aq|eg)|big drums?( ensemble)?|giant drums?|drum ensemble)\b", re.I)
_MORE = re.compile(r"\b(more|else|another|other|further)\b", re.I)
_MENU_NUMBERS = {"1": "lesson_start", "2": "invite", "3": "quiz_start", "4": "recommend", "5": "progress", "6": "help",
                 "7": "sources", "0": "bye"}


# ---------- helpers ----------
def _msg(text: str, **fields) -> dict:
    return {"messages": [AIMessage(content=text)], **fields}


def _raw(state: State) -> str:
    for m in reversed(state.get("messages", [])):
        if isinstance(m, HumanMessage):
            return m.content
    return ""


def _previous_raw(state: State) -> str:
    seen = 0
    for m in reversed(state.get("messages", [])):
        if isinstance(m, HumanMessage):
            seen += 1
            if seen == 2:
                return m.content
    return ""


def _text(state: State) -> str:
    return state.get("clean_text") or _raw(state)


def _name(state: State) -> str:
    return state.get("user_name") or "friend"


def _progress(state: State) -> dict:
    return copy.deepcopy(state.get("progress") or profiles.new_progress())


def _save(state: State, progress: dict) -> None:
    if state.get("user_name"):
        profiles.save(state["user_name"], progress)


def _grade(text: str, groups: list) -> tuple[int, int]:
    return sum(nlp.concept_hit(text, g) for g in groups), len(groups)


def _stat(progress: dict, topic_id: str, correct: bool) -> None:
    s = progress["topic_stats"].setdefault(topic_id, {"right": 0, "total": 0})
    s["total"] += 1
    s["right"] += int(correct)


def _current_answer(state: State) -> list:
    """Accepted answer groups for the question the learner is on."""
    if state.get("stage") == "lesson" and state.get("lesson"):
        L = state["lesson"]
        return get_topic(L["topic"])["lesson"][L["step"]]["answer"]
    if state.get("stage") == "quiz" and state.get("quiz", {}).get("current"):
        return next(i["answer"] for i in quiz_items() if i["key"] == state["quiz"]["current"])
    return []


def _next_unfinished(progress: dict):
    done = set(progress["lessons_done"])
    return next((t for t in topics() if t["id"] not in done), None)


# ---------- opening and input handling ----------
def greet(state: State) -> dict:
    return _msg(
        f"{persona.time_greeting()}! I'm {persona.BOT_NAME}, your Gendang Beleq teacher. "
        f"({persona.BOT_MEANING}.) Before we begin, what should I call you?",
        stage="ask_name", boot=False,
    )


def route_start(state: State) -> str:
    return "greet" if state.get("boot") else "validate"


def validate(state: State) -> dict:
    return {"invalid_reason": nlp.validate_input(_raw(state)) or ""}


def route_valid(state: State) -> str:
    return "reject" if state.get("invalid_reason") else "route_stage"


def reject(state: State) -> dict:
    return _msg(REJECT_MESSAGES[state["invalid_reason"]])


def route_stage(state: State) -> str:
    return "take_name" if state.get("stage") == "ask_name" else "normalize"


def take_name(state: State) -> dict:
    name = persona.extract_name(_raw(state))  # raw text: spelling correction would damage names
    if not name:
        return _msg("Sorry, I didn't catch your name. What should I call you? Just your first name is fine.")
    saved = profiles.load(name)
    progress = saved or profiles.new_progress()
    total = len(topics())
    if saved and saved["lessons_done"]:
        hello = f"Welcome back, {name}! You have completed {len(saved['lessons_done'])} of {total} lessons so far."
    else:
        hello = f"Nice to meet you, {name}!"
    return _msg(f"{hello}\n\n{persona.menu_text(name)}", user_name=name, progress=progress, stage="menu")


def normalize(state: State) -> dict:
    """Spelling-correct the message and build the search query (synonyms, related concepts, previous turn)."""
    raw = _raw(state)
    clean = nlp.correct_spelling(raw)
    canon = _SUBJECT_NAMES.sub("gendang beleq", clean)  # one name for matching
    cues = nlp.question_cues(canon, search.mentions_domain(canon))
    extras = [s for s in (*nlp.expand_synonyms(canon), *related_concepts(canon)) if s.lower() != "gendang beleq"]
    parts = [canon, *cues, *extras]  # "gendang beleq" is the subject of every topic, so it is no clue and is left out
    keywords = nlp.extract_keywords(clean)
    if not cues and len(keywords) < 2 and (not keywords or _MORE.search(clean)):  # a follow-up such as "tell me more"
        parts.insert(0, _previous_raw(state))
    changed = re.sub(r"\W+", "", clean.lower()) != re.sub(r"\W+", "", raw.lower())
    mood = "struggling" if _STRUGGLING.search(raw) else "happy" if _HAPPY.search(raw) else ""
    return {"clean_text": clean, "heard": clean if changed else "", "search_query": " ".join(p for p in parts if p),
            "mood": mood, "cued": bool(cues)}


# ---------- intent ----------
def classify(state: State) -> dict:
    text = _text(state).strip()
    low = text.lower()
    stage = state.get("stage", "menu")

    if stage in ("lesson", "quiz"):
        if _LEAVE.search(low):
            return {"intent": "leave"}
        # a question only interrupts if it doesn't also answer what was asked ("is it a wedding?" is an answer)
        is_question = _QUESTION.match(low) or low.endswith("?")
        if is_question and not _SKIP.search(low) and not _HINT.match(low) and not _grade(text, _current_answer(state))[0]:
            return {"intent": "qa"}
        return {"intent": "lesson_reply" if stage == "lesson" else "quiz_reply"}

    if re.fullmatch(r"\d{1,2}", low):
        return {"intent": _MENU_NUMBERS.get(low, "menu")}  # menu node explains a number that isn't on the menu
    if _GREETING.match(low) and len(low.split()) <= 4:
        return {"intent": "smalltalk"}
    if _CONTINUE.match(low) and len(low.split()) <= 4:
        return {"intent": "lesson_start"}
    if _DECLINE.match(low) and len(low.split()) <= 4:
        return {"intent": "smalltalk"}
    for pattern, intent in (
        (_BYE, "bye"), (_THANKS, "smalltalk"), (_IDENTITY, "smalltalk"), (_MENU, "menu"), (_PROGRESS, "progress"),
        (_HELP, "help"), (_SOURCES, "sources"), (_RECOMMEND, "recommend"), (_QUIZ, "quiz_start"), (_LESSON, "lesson_start"),
    ):
        if pattern.search(low):
            return {"intent": intent}
    if state.get("mood") == "struggling" and not _QUESTION.match(low):
        return {"intent": "smalltalk"}
    if _DOMAIN.search(low) or search.mentions_domain(low) or search.search(state.get("search_query", text), question=text):
        return {"intent": "qa"}
    return {"intent": "offtopic"}


def route_intent(state: State) -> str:
    return state["intent"]


# ---------- menu, help, small talk ----------
def menu(state: State) -> dict:
    wrong_number = "That number isn't on the menu.\n\n" if _text(state).strip().isdigit() else ""
    return _msg(wrong_number + persona.menu_text(_name(state)), stage="menu")


def leave(state: State) -> dict:
    _save(state, _progress(state))
    return _msg(f"No problem, {_name(state)}. We can pick it up whenever you like.\n\n{persona.menu_text(_name(state))}",
                stage="menu", lesson={}, quiz={})


def sources(state: State) -> dict:
    lines = "\n".join(f"  - {r['full']}" for r in sorted(references().values(), key=lambda r: r["full"]))
    return _msg(f"Everything I teach comes from these sources, {_name(state)}:\n{lines}\n\nWhat would you like to explore?")


def invite(state: State) -> dict:
    return _msg(
        f"Ask away, {_name(state)}! You can ask about the name, the instruments, when it is played, its history "
        "or the players. What would you like to know?"
    )


def help_node(state: State) -> dict:
    return _msg(
        "Just talk to me like you would to a teacher. I understand small typos and different wordings. "
        "Say 'lesson' to learn step by step, 'quiz' to test yourself, 'progress' for your report card, "
        "'sources' for my references, or ask any question. Inside a lesson or quiz you can say 'hint', 'skip', 'repeat' or 'stop'. "
        "Type 'menu' at any time to see the options."
    )


def smalltalk(state: State) -> dict:
    name, low = _name(state), _raw(state).lower()
    if state.get("mood") == "struggling":
        return _msg(f"{persona.pick(persona.COMFORT)} We can go slowly, {name}. Say 'lesson' and I will explain one small "
                    "step at a time, with hints whenever you want them.")
    if _IDENTITY.search(low):
        return _msg(f"I'm {persona.BOT_NAME}, a teaching chatbot built to explain the Gendang Beleq. "
                    f"{persona.BOT_MEANING[0].upper()}{persona.BOT_MEANING[1:]}. What would you like to learn, {name}?")
    if _DECLINE.match(low):
        return _msg(f"That's fine, {name}. Ask me anything when you're ready, or say 'menu' to see the options.")
    if _THANKS.search(low):
        return _msg(f"You're very welcome, {name}! What would you like to explore next?")
    if _GREETING.match(low):
        return _msg(f"{persona.time_greeting()}, {name}! Good to see you. What would you like to learn about the Gendang Beleq today?")
    return _msg(f"Glad you're enjoying it, {name}! What would you like to explore next?")


def offtopic(state: State) -> dict:
    return _msg(
        f"That's outside what I teach, {_name(state)}. I'm here for the Gendang Beleq drum ensemble of Lombok. "
        "What would you like to know about its history, instruments or ceremonies?"
    )


def bye(state: State) -> dict:
    progress = _progress(state)
    _save(state, progress)
    done = len(progress["lessons_done"])
    return _msg(
        f"Goodbye, {_name(state)}! You have completed {done} of {len(topics())} lessons and earned the title "
        f"'{persona.badge(progress)}'. Have a lovely {persona.time_period()}, and come back soon!",
        stage="menu",
    )


# ---------- question answering ----------
def _reprompt(state: State) -> str:
    """When a question interrupts a lesson or quiz, bring the learner back to where they were."""
    if state.get("stage") == "lesson" and state.get("lesson"):
        L = state["lesson"]
        return f"\n\nNow, back to our lesson: {get_topic(L['topic'])['lesson'][L['step']]['question']}"
    if state.get("stage") == "quiz" and state.get("quiz", {}).get("current"):
        item = {i["key"]: i for i in quiz_items()}[state["quiz"]["current"]]
        return f"\n\nNow, back to the quiz: {item['question']}"
    return ""


def answer(state: State) -> dict:
    progress = _progress(state)
    hits = search.search(state.get("search_query") or _text(state), question=_text(state))
    note = f"(I read that as: \"{state['heard']}\")\n" if state.get("heard") else ""
    if not hits:
        titles = ", ".join(t["title"].lower() for t in topics()[:4])
        return _msg(
            f"{note}I'm not sure about that one, {_name(state)}, and I'd rather not guess. "
            f"I can teach you about topics like {titles}. What would you like to look at?{_reprompt(state)}"
        )
    question = _text(state)
    told = state.get("told") or []
    good = [h for h in hits if h["score"] >= 0.6 * hits[0]["score"]]
    # when the learner asks for more, move on to facts they haven't heard yet
    ranked = ([h for h in good if h["text"] not in told] or good) if _MORE.search(question) else good
    best = ranked[0]

    def fits(h: dict) -> bool:
        # a second fact must read as one thought with the first: same topic, or something the question actually asked
        if best["topic"] == "glossary":
            return search.coverage(question, h["text"]) > 0
        return h["topic"] == best["topic"] and h["score"] >= 0.75 * best["score"]

    second = next((h for h in ranked[1:] if fits(h)), None)
    chosen = [best, second] if second else [best]
    if second and best["topic"] == "glossary" and state.get("cued"):
        chosen = [second]  # "what does the petuq do?" wants the fact; a definition on top only repeats it
    answer_text = " ".join(f"{h['text']} {cite(h['sources'])}" for h in chosen)
    topic_id = next((h["topic"] for h in chosen if h["topic"] != "glossary"), "glossary")
    follow = "What else would you like to know?"
    if topic_id != "glossary":
        if topic_id not in progress["topics_seen"]:
            progress["topics_seen"].append(topic_id)
        related = [f"'{get_topic(r)['title']}'" for r in get_topic(topic_id).get("related", [])]
        follow = f"Related lessons: {', '.join(related)}. What would you like to explore next?" if related else follow
    canon_q = _SUBJECT_NAMES.sub("gendang beleq", question)
    partial = (not state.get("cued") and not nlp.expand_synonyms(canon_q)
               and len(nlp.extract_keywords(canon_q)) >= 2
               and search.coverage(canon_q, " ".join(h["text"] for h in chosen)) <= 0.5)
    lead = "I don't have an exact answer to that, but this is the closest I can tell you: " if partial else ""
    return _msg(f"{note}{lead}{answer_text}\n\n{follow}{_reprompt(state)}", progress=progress,
                told=told + [h["text"] for h in chosen])


# ---------- teacher: lessons ----------
def _present(topic: dict, i: int) -> str:
    step = topic["lesson"][i]
    return f"Step {i + 1} of {len(topic['lesson'])}\n{step['teach']}\n\nNow it's your turn: {step['question']}"


def _pick_topic(state: State, progress: dict):
    text = _text(state).lower()
    best, top = None, 0
    for t in topics():
        score = sum(1 for k in t["keywords"] if search.keyword_hit(k, text))
        if score > top:
            best, top = t, score
    return best or _next_unfinished(progress)


def lesson_start(state: State) -> dict:
    progress = _progress(state)
    topic = _pick_topic(state, progress)
    if topic is None:
        return _msg(f"You have finished every lesson, {_name(state)}! Say 'quiz' to test everything you have learned, "
                    "or ask me any question.", stage="menu")
    number = [t["id"] for t in topics()].index(topic["id"]) + 1
    return _msg(
        f"Let's begin, {_name(state)}! Lesson {number}: {topic['title']}\n"
        "I'll teach a little, then ask you a question. Say 'hint' if you need a clue.\n\n" + _present(topic, 0),
        stage="lesson", lesson={"topic": topic["id"], "step": 0, "attempts": 0},
    )


def _advance_lesson(state: State, progress: dict, lesson: dict, topic: dict, feedback: str) -> dict:
    nxt = lesson["step"] + 1
    if nxt < len(topic["lesson"]):
        return _msg(f"{feedback}\n\n{_present(topic, nxt)}", lesson={**lesson, "step": nxt, "attempts": 0}, progress=progress)
    if topic["id"] not in progress["lessons_done"]:
        progress["lessons_done"].append(topic["id"])
    _save(state, progress)
    upcoming = _next_unfinished(progress)
    onward = (f"When you're ready, say 'lesson' to continue with '{upcoming['title']}', or 'quiz' to test yourself."
              if upcoming else "You have now finished all the lessons! Say 'quiz' to test everything you learned.")
    return _msg(
        f"{feedback}\n\nLesson complete, {_name(state)}! Quick recap: {topic['summary']} {cite(topic_sources(topic))}\n{onward}",
        stage="menu", lesson={}, progress=progress,
    )


def lesson_reply(state: State) -> dict:
    progress, lesson = _progress(state), dict(state["lesson"])
    topic = get_topic(lesson["topic"])
    step = topic["lesson"][lesson["step"]]
    text = _text(state)
    if _REPEAT.search(text):
        return _msg(f"Of course! Here it is again.\n\n{_present(topic, lesson['step'])}")
    if _HINT.match(text):
        return _msg(f"Here's a clue: {step['hint']}")
    skipped = bool(_SKIP.search(text))
    hit, total = _grade(text, step["answer"])

    if not skipped and hit == total:
        progress["lesson_total"] += 1
        if lesson["attempts"] == 0:
            progress["lesson_right"] += 1
        return _advance_lesson(state, progress, lesson, topic, f"{persona.pick(persona.PRAISE)} {step['explain']}")
    if not skipped and lesson["attempts"] == 0:
        tone = persona.pick(persona.COMFORT if state.get("mood") == "struggling" else persona.GENTLE)
        if hit and hit < total:
            tone = f"You've got part of it, {_name(state)}."
        return _msg(f"{tone} Here's a clue: {step['hint']}\nTry again in your own words.", lesson={**lesson, "attempts": 1})
    progress["lesson_total"] += 1
    return _advance_lesson(state, progress, lesson, topic, f"No problem, let's learn it together. {step['explain']}")


# ---------- teacher: quiz ----------
def _pick_quiz(quiz: dict, progress: dict):
    level = 2 if quiz["right"] >= 2 else 1
    pool = [i for i in quiz_items() if i["key"] not in quiz["asked"]]
    allowed = [i for i in pool if i["level"] <= level] or pool
    learned = [i for i in allowed if i["topic"] in progress["lessons_done"]]
    return random.choice(learned or allowed) if allowed else None


def quiz_start(state: State) -> dict:
    progress = _progress(state)
    quiz = {"n": 0, "right": 0, "asked": [], "current": None, "attempts": 0}
    item = _pick_quiz(quiz, progress)
    quiz.update(current=item["key"], asked=[item["key"]])
    return _msg(
        f"Quiz time, {_name(state)}! I'll ask up to {QUIZ_LENGTH} questions. Answer in your own words. "
        f"Say 'hint' for a clue, 'skip' to pass, or 'stop' to quit.\n\nQuestion 1: {item['question']}",
        stage="quiz", quiz=quiz,
    )


def quiz_reply(state: State) -> dict:
    progress, quiz = _progress(state), dict(state["quiz"])
    item = {i["key"]: i for i in quiz_items()}[quiz["current"]]
    text = _text(state)
    if _HINT.match(text):
        return _msg(f"Here's a clue: {item['hint']}")
    skipped = bool(_SKIP.search(text))
    hit, total = _grade(text, item["answer"])
    correct = not skipped and hit == total

    if not correct and not skipped and quiz["attempts"] == 0:
        tone = f"You've got part of it, {_name(state)}." if hit else persona.pick(persona.GENTLE)
        return _msg(f"{tone} Here's a clue: {item['hint']}\nGive it one more try.", quiz={**quiz, "attempts": 1})

    progress["quiz_total"] += 1
    _stat(progress, item["topic"], correct and quiz["attempts"] == 0)
    if correct:
        progress["quiz_right"] += 1
        quiz["right"] += 1
        feedback = f"{persona.pick(persona.PRAISE)} {item['explain']}"
    else:
        feedback = f"The answer was: {item['explain']}"
    quiz["n"] += 1
    quiz["attempts"] = 0
    _save(state, progress)

    nxt = _pick_quiz(quiz, progress) if quiz["n"] < QUIZ_LENGTH else None
    if nxt is None:
        ratio = quiz["right"] / quiz["n"]
        comment = ("Fantastic work!" if ratio >= 0.8 else "Good progress!" if ratio >= 0.5
                   else "Keep practising, a lesson will help.")
        return _msg(
            f"{feedback}\n\nQuiz finished! You got {quiz['right']} out of {quiz['n']}. {comment} "
            f"Your title is now '{persona.badge(progress)}'.",
            stage="menu", quiz={}, progress=progress,
        )
    quiz.update(current=nxt["key"], asked=quiz["asked"] + [nxt["key"]])
    return _msg(f"{feedback}\n\nQuestion {quiz['n'] + 1}: {nxt['question']}", quiz=quiz, progress=progress)


# ---------- teacher: progress and recommendations ----------
def progress_node(state: State) -> dict:
    p = _progress(state)
    titles = [get_topic(t)["title"] for t in p["lessons_done"]]
    acc = f"{100 * p['quiz_right'] // p['quiz_total']}%" if p["quiz_total"] else "no quiz taken yet"
    upcoming = _next_unfinished(p)
    nxt = f"Next up: {upcoming['title']}." if upcoming else "You have finished every lesson!"
    return _msg(
        f"Report card for {_name(state)}\n"
        f"  Lessons completed: {len(titles)} of {len(topics())}" + (f" ({'; '.join(titles)})" if titles else "") + "\n"
        f"  Lesson questions right first time: {p['lesson_right']} of {p['lesson_total']}\n"
        f"  Quiz: {p['quiz_right']} of {p['quiz_total']} correct ({acc})\n"
        f"  Title: {persona.badge(p)}\n{nxt}"
    )


def recommend(state: State) -> dict:
    """Rule-based consultant. Score = +3 not yet learned, +2 per interest keyword in the message,
    +2 if quiz accuracy on the topic is below 60%, +1 if the learner has asked about it."""
    p = _progress(state)
    text = _text(state).lower()
    scored = []
    for t in topics():
        score, reasons = 0, []
        if t["id"] not in p["lessons_done"]:
            score += 3
            reasons.append("you haven't done this lesson yet")
        hits = [k for k in t["keywords"] if search.keyword_hit(k, text)]
        if hits:
            score += 2 * len(hits)
            reasons.append(f"it matches your interest in {hits[0]}")
        s = p["topic_stats"].get(t["id"])
        if s and s["right"] / s["total"] < 0.6:
            score += 2
            reasons.append("the quiz showed it needs more practice")
        if t["id"] in p["topics_seen"]:
            score += 1
            reasons.append("you asked about it earlier")
        scored.append((score, t, reasons))
    scored.sort(key=lambda x: x[0], reverse=True)
    top = [x for x in scored if x[0] > 0][:2]
    if not top:
        return _msg(f"You've covered everything, {_name(state)}! A quiz is the best way to keep it fresh. "
                    "Is there any part you'd like to revisit?")
    lines = [f"  - {t['title']}: {reasons[0]}." for _, t, reasons in top]
    return _msg(f"Based on what you've done so far, I recommend:\n" + "\n".join(lines) +
                "\n\nTell me which one appeals to you, or what you're curious about, and I'll start from there.")
