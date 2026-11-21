"""Graph nodes. Every node is plain Python: it reads the State and returns the fields it changes.

Language: state["lang"] is "en" (default) or "ms" (Bahasa Malaysia). Replies come from src/i18n.py and the
knowledge base in that language; the intent patterns below understand both languages either way.
"""
import copy
import random
import re

from langchain_core.messages import AIMessage, HumanMessage

from . import i18n, llm, nlp, persona, profiles, search
from .knowledge import cite, get_topic, glossary, quiz_items, references, topic_sources, topics
from .semantic_net import related_concepts
from .state import State

QUIZ_LENGTH = 5
SIX_SEVEN = "67"
SIX_SEVEN_REPLY = "🤲 67"

REJECT_MESSAGES = {k: i18n.get("en", f"reject.{k}") for k in ("empty", "too_long", "gibberish")}
ERROR_MESSAGE = i18n.get("en", "error")

# ---------- patterns (English | Bahasa Malaysia) ----------
_GREETING = re.compile(r"^\s*(hi|hello|hey|hai|helo|halo|salam|assalamualaikum|selamat\s+(?!tinggal|jalan)\w+"
                       r"|(good\s+)?(morning|afternoon|evening|day))\b", re.I)
_THANKS = re.compile(r"\b(thanks|thank you|terima kasih|cheers|appreciate|tq|thx)\b", re.I)
_BYE = re.compile(r"\b(bye|goodbye|see you|exit|quit|good night|selamat tinggal|selamat jalan|jumpa lagi|babai)\b", re.I)
_MENU = re.compile(r"\b(menu|options|main menu|pilihan|menu utama)\b", re.I)
_PROGRESS = re.compile(r"\b(progress|score|report card|how am i doing|my results|badge"
                       r"|kemajuan|markah|prestasi|kad laporan|keputusan saya|lencana|pencapaian)\b", re.I)
_HELP = re.compile(r"^\s*(help|how do i use|what can you do|commands|bantuan|cara guna|macam mana nak guna"
                   r"|apa (yang )?(awak|kamu|anda) boleh (buat|lakukan))\b", re.I)
_RECOMMEND = re.compile(r"\b(recommend|suggest|what should i|where (do|should) i (start|begin)|next topic|what next"
                        r"|cadang|cadangkan|cadangan|syor|apa (yang )?(patut|perlu) saya|nak mula dari mana"
                        r"|topik seterusnya|apa seterusnya)\b", re.I)
_QUIZ = re.compile(r"\b(quiz|test me|test my|exam|question me|kuiz|uji saya|soal saya|ujian)\b", re.I)
_LESSON = re.compile(r"\b(lessons?|teach|tutorial|class|study|pelajaran|ajar|ajarkan|ajari|belajar|pelajari|kelas)\b"
                     r"|\b(want|like|love|help me|let'?s|start|begin) (to )?learn\b|^\s*learn\b", re.I)
_SOURCES = re.compile(r"\b(sources?|references?|citations?|bibliography|where did you (get|learn)"
                      r"|sumber|rujukan|bibliografi)\b", re.I)
_GLOSSARY = re.compile(r"\b(glossary|dictionary|vocabulary|word list|all terms|sasak terms|musical terms"
                       r"|glosari|kamus|senarai (kata|istilah)|istilah sasak|istilah muzik)\b", re.I)
_IDENTITY = re.compile(r"\b(who are you|what are you|your name|about you|are you a (bot|robot|person|human)"
                       r"|siapa(kah)? (awak|kamu|anda)|nama (awak|kamu|anda)|tentang (diri )?(awak|kamu|anda)"
                       r"|(awak|kamu|anda) (ni |ini )?(bot|robot|manusia))\b", re.I)
_CONTINUE = re.compile(r"^\s*(next|continue|yes|yeah|yep|sure|ok|okay|ready|go on|go ahead|let'?s go"
                       r"|ya|ye|yup|baik|baiklah|okey|teruskan|seterusnya|sedia|jom|mari)\b", re.I)
_DECLINE = re.compile(r"^\s*(no|nope|not now|not yet|nah|maybe later|later"
                      r"|tidak|tak|bukan sekarang|belum|nanti|lain kali)\b", re.I)
_LEAVE = re.compile(r"^\s*(stop|quit|exit|menu|leave|cancel|main menu|berhenti|keluar|batal|menu utama)\b"
                    r"|\b(stop|quit) (the )?(lesson|quiz)\b|\b(berhenti|keluar) (dari |daripada )?(pelajaran|kuiz)\b", re.I)
_HINT = re.compile(r"^\s*(hint|clue|help|petunjuk|klu|bantuan|bantu)\b", re.I)
_SKIP = re.compile(r"\b(skip|pass|i don'?t know|dunno|no idea|give up|tell me the answer"
                   r"|langkau|tak tahu|tidak tahu|tak pasti|entah|menyerah|beritahu (saya )?jawapan(nya)?)\b", re.I)
_REPEAT = re.compile(r"\b(repeat|again|re-?explain|ulang|ulangi|sekali lagi|terangkan semula)\b", re.I)
_QUESTION = re.compile(r"^\s*(what|who|when|where|why|how|which|can|could|does|do|is|are|tell me"
                       r"|apa|apakah|siapa|siapakah|bila|bilakah|di ?mana|manakah|kenapa|mengapa|bagaimana"
                       r"|bagaimanakah|macam mana|berapa|adakah|boleh|bolehkah|ceritakan|terangkan|beritahu)\b", re.I)
_DOMAIN = re.compile(r"\b(gendang|beleq|belek|sasak|lombok|drum|drums|gong|ensemble|nyongkolan|ensembel)", re.I)
_STRUGGLING = re.compile(r"(confus|don'?t understand|do not understand|too hard|difficult|stuck|lost|frustrat|boring"
                         r"|keliru|tak faham|tidak faham|kurang faham|susah|sukar|tersekat|buntu|bosan|pening)", re.I)
_HAPPY = re.compile(r"\b(great|awesome|love|fun|cool|amazing|nice|interesting"
                    r"|best|hebat|bagus|seronok|menarik|syok|mantap|terbaik)\b", re.I)
_SUBJECT_NAMES = re.compile(r"\b(gendang bel(ek|aq|eg)|big drums?( ensemble)?|giant drums?|drum ensemble)\b", re.I)
_MORE = re.compile(r"\b(more|else|another|other|further|lagi|lain|tambahan|selanjutnya|lanjut)\b", re.I)
_FUN_FACT = re.compile(r"\b(fun|interesting|random|cool|surprising) facts?\b|\bsurprise me\b|\btrivia\b|\bdid you know\b"
                       r"|\bfakta (yang )?(menarik|rawak|best|seronok|unik|pelik)\b|\bkejutkan saya\b"
                       r"|\btahukah (anda|awak|kamu)\b", re.I)
_ANOTHER = re.compile(r"\b(another|more|again|one more|next|lagi|satu lagi|seterusnya)\b", re.I)
_MENU_NUMBERS = {"1": "lesson_start", "2": "invite", "3": "quiz_start", "4": "recommend", "5": "progress", "6": "help",
                 "7": "sources", "8": "glossary", "0": "bye"}


# ---------- helpers ----------
def _msg(text: str, **fields) -> dict:
    """A reply. `engine` records who wrote it, for diagnostics only: "python" (rule-based, the default) or "gemini"."""
    return {"messages": [AIMessage(content=text)], "engine": "python", **fields}


def _lang(state: State) -> str:
    return i18n.norm(state.get("lang"))


def _t(state: State, key: str, **values) -> str:
    return i18n.t(_lang(state), key, **values)


def _history(state: State) -> list[tuple[str, str]]:
    """Earlier turns as (speaker, text), oldest first, without the message being answered now."""
    msgs = state.get("messages", [])
    if msgs and isinstance(msgs[-1], HumanMessage):
        msgs = msgs[:-1]
    return [("learner" if isinstance(m, HumanMessage) else "guru", m.content) for m in msgs]


def _gemini(state: State) -> dict | None:
    """Gemini-first handling of an open-ended turn: its reply (plus the way back into a lesson or quiz), or None
    when Gemini is off or fails, in which case the caller gives its rule-based reply. The learner can't tell which."""
    if not llm.available():
        return None
    lang = _lang(state)
    back = _reprompt(state)
    note = ""
    if back:
        note = ("The learner is in the middle of a lesson or quiz and will be asked this question again right after "
                f"your reply, so do not give away its answer: {back.split(': ', 1)[1]}")
    reply = llm.converse(_raw(state), _name(state), _history(state), note, lang=lang)
    if not reply:
        return None
    progress = _progress(state)
    hit = next(iter(search.search(state.get("search_query") or _text(state), k=1, question=_text(state), lang=lang)), None)
    if hit and hit["topic"] != "glossary" and hit["topic"] not in progress["topics_seen"]:
        progress["topics_seen"].append(hit["topic"])  # keeps "you asked about it earlier" in recommendations
    return _msg(f"{reply}{back}", engine="gemini", progress=progress)


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
    return state.get("user_name") or ("kawan" if _lang(state) == "ms" else "friend")


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


def _quiz_item(state: State, key: str) -> dict:
    return next(i for i in quiz_items(_lang(state)) if i["key"] == key)


def _current_answer(state: State) -> list:
    """Accepted answer groups for the question the learner is on."""
    if state.get("stage") == "lesson" and state.get("lesson"):
        L = state["lesson"]
        return get_topic(L["topic"], _lang(state))["lesson"][L["step"]]["answer"]
    if state.get("stage") == "quiz" and state.get("quiz", {}).get("current"):
        return _quiz_item(state, state["quiz"]["current"])["answer"]
    return []


def _next_unfinished(progress: dict, lang: str = "en"):
    done = set(progress["lessons_done"])
    return next((t for t in topics(lang) if t["id"] not in done), None)


# ---------- opening and input handling ----------
def greet(state: State) -> dict:
    lang = _lang(state)
    return _msg(
        i18n.t(lang, "greet", greeting=persona.time_greeting(lang), bot=persona.BOT_NAME,
               meaning=i18n.get(lang, "bot_meaning")),
        stage="ask_name", boot=False,
    )


def route_start(state: State) -> str:
    if state.get("switch_lang"):
        return "relang"
    return "greet" if state.get("boot") else "validate"


def relang(state: State) -> dict:
    """The learner switched language mid-conversation: confirm, then repeat where they were in the new language."""
    head = _t(state, "switched")
    if state.get("stage", "ask_name") == "ask_name":
        return _msg(f"{head} {_t(state, 'ask_name')}", switch_lang=False)
    back = _reprompt(state)
    if back:
        return _msg(head + back, switch_lang=False)
    return _msg(f"{head}\n\n{persona.menu_text(_name(state), _lang(state))}", switch_lang=False, stage="menu")


def validate(state: State) -> dict:
    return {"invalid_reason": nlp.validate_input(_raw(state)) or ""}


def route_valid(state: State) -> str:
    return "reject" if state.get("invalid_reason") else "route_stage"


def reject(state: State) -> dict:
    return _msg(_t(state, f"reject.{state['invalid_reason']}"))


def route_stage(state: State) -> str:
    return "take_name" if state.get("stage") == "ask_name" else "normalize"


def take_name(state: State) -> dict:
    raw, lang = _raw(state), _lang(state)
    if raw.strip() == SIX_SEVEN:
        return _msg(f"{SIX_SEVEN_REPLY}\n\n{_t(state, 'ask_name')}")
    name = persona.extract_name(raw)  # raw text: spelling correction would damage names
    if not name:
        if _GREETING.match(raw):
            return _msg(f"{persona.reply_greeting(raw, lang)}! {_t(state, 'name_retry')}")
        return _msg(_t(state, "name_retry"))
    saved = profiles.load(name)
    progress = saved or profiles.new_progress()
    total = len(topics())
    if saved and saved["lessons_done"]:
        hello = _t(state, "welcome_back", name=name, done=len(saved["lessons_done"]), total=total)
    else:
        hello = _t(state, "nice_to_meet", name=name)
    return _msg(f"{hello}\n\n{persona.menu_text(name, lang)}", user_name=name, progress=progress, stage="menu")


def normalize(state: State) -> dict:
    """Spelling-correct the message and build the search query (synonyms, related concepts, previous turn)."""
    raw, lang = _raw(state), _lang(state)
    clean = nlp.correct_spelling(raw, lang)
    canon = _SUBJECT_NAMES.sub("gendang beleq", clean)  # one name for matching
    cues = nlp.question_cues(canon, search.mentions_domain(canon, lang), lang)
    extras = [s for s in (*nlp.expand_synonyms(canon, lang), *related_concepts(canon, lang=lang))
              if s.lower() != "gendang beleq"]
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
    lang = _lang(state)

    if low == SIX_SEVEN:
        return {"intent": "six_seven"}
    # "give me a fun fact", or "another one" straight after a fun fact
    wants_fact = _FUN_FACT.search(low) or _FUN_FACT.search(_raw(state)) or (
        state.get("intent") == "fun_fact" and _ANOTHER.search(low) and len(low.split()) <= 5)
    if stage in ("lesson", "quiz"):
        if _LEAVE.search(low):
            return {"intent": "leave"}
        if wants_fact:
            return {"intent": "fun_fact"}
        # a question only interrupts if it doesn't also answer what was asked ("is it a wedding?" is an answer)
        is_question = _QUESTION.match(low) or low.endswith("?")
        if is_question and not _SKIP.search(low) and not _HINT.match(low) and not _grade(text, _current_answer(state))[0]:
            return {"intent": "qa"}
        return {"intent": "lesson_reply" if stage == "lesson" else "quiz_reply"}

    if re.fullmatch(r"\d{1,2}", low):
        return {"intent": _MENU_NUMBERS.get(low, "menu")}  # menu node explains a number that isn't on the menu
    if wants_fact:
        return {"intent": "fun_fact"}
    if _GREETING.match(low) and len(low.split()) <= 4:
        return {"intent": "smalltalk"}
    if _CONTINUE.match(low) and len(low.split()) <= 4:
        return {"intent": "lesson_start"}
    if _DECLINE.match(low) and len(low.split()) <= 4:
        return {"intent": "smalltalk"}
    for pattern, intent in (
        (_BYE, "bye"), (_THANKS, "smalltalk"), (_IDENTITY, "smalltalk"), (_MENU, "menu"), (_PROGRESS, "progress"),
        (_HELP, "help"), (_SOURCES, "sources"), (_GLOSSARY, "glossary"), (_RECOMMEND, "recommend"),
        (_QUIZ, "quiz_start"), (_LESSON, "lesson_start"),
    ):
        if pattern.search(low):
            return {"intent": intent}
    if state.get("mood") == "struggling" and not _QUESTION.match(low):
        return {"intent": "smalltalk"}
    if (_DOMAIN.search(low) or search.mentions_domain(low, lang)
            or search.search(state.get("search_query", text), question=text, lang=lang)):
        return {"intent": "qa"}
    return {"intent": "offtopic"}


def route_intent(state: State) -> str:
    return state["intent"]


# ---------- menu, help, small talk ----------
def menu(state: State) -> dict:
    wrong_number = _t(state, "wrong_number") if _text(state).strip().isdigit() else ""
    return _msg(wrong_number + persona.menu_text(_name(state), _lang(state)), stage="menu")


def leave(state: State) -> dict:
    _save(state, _progress(state))
    return _msg(_t(state, "leave", name=_name(state), menu=persona.menu_text(_name(state), _lang(state))),
                stage="menu", lesson={}, quiz={})


def sources(state: State) -> dict:
    lines = "\n".join(f"  - {r['full']}" for r in sorted(references().values(), key=lambda r: r["full"]))
    return _msg(_t(state, "sources", name=_name(state), lines=lines))


def glossary_node(state: State) -> dict:
    lines = "\n".join(
        f"  - {term}: {entry['meaning']} {cite(entry['sources'])}"
        for term, entry in sorted(glossary(_lang(state)).items())
    )
    return _msg(_t(state, "glossary", name=_name(state), lines=lines))


def invite(state: State) -> dict:
    return _msg(_t(state, "invite", name=_name(state)))


def help_node(state: State) -> dict:
    return _msg(_t(state, "help"))


def smalltalk(state: State) -> dict:
    smart = _gemini(state)
    if smart:
        return smart
    name, low, lang = _name(state), _raw(state).lower(), _lang(state)
    if state.get("mood") == "struggling":
        return _msg(_t(state, "struggling", comfort=persona.pick(i18n.get(lang, "comfort")), name=name))
    if _IDENTITY.search(low):
        meaning = i18n.get(lang, "bot_meaning")
        return _msg(_t(state, "identity", bot=persona.BOT_NAME, meaning=meaning[0].upper() + meaning[1:], name=name))
    if _DECLINE.match(low):
        return _msg(_t(state, "decline", name=name))
    if _THANKS.search(low):
        return _msg(_t(state, "thanks", name=name))
    if _GREETING.match(low):
        return _msg(_t(state, "hello", greeting=persona.reply_greeting(low, lang), name=name))
    return _msg(_t(state, "enjoying", name=name))


def offtopic(state: State) -> dict:
    # Gemini first: the keyword router can't tell "explain it simply" or a comparison from a truly off-topic question
    return _gemini(state) or _msg(_t(state, "offtopic", name=_name(state)))


def fun_fact(state: State) -> dict:
    """'Give me a fun fact' / 'surprise me': Gemini first, otherwise a random cited fact not given yet."""
    smart = _gemini(state)
    if smart:
        return smart
    told = state.get("told") or []
    facts = [(t, f) for t in topics(_lang(state)) for f in t["facts"]]
    fresh = [tf for tf in facts if tf[1]["text"] not in told] or facts
    topic, fact = random.choice(fresh)
    progress = _progress(state)
    if topic["id"] not in progress["topics_seen"]:
        progress["topics_seen"].append(topic["id"])
    return _msg(
        _t(state, "fun_fact", name=_name(state), fact=fact["text"], cite=cite(fact["sources"])) + _reprompt(state),
        progress=progress, told=told + [fact["text"]],
    )


def bye(state: State) -> dict:
    progress = _progress(state)
    _save(state, progress)
    lang = _lang(state)
    return _msg(
        _t(state, "bye", name=_name(state), done=len(progress["lessons_done"]), total=len(topics()),
           badge=persona.badge(progress, lang), period=persona.time_period(lang)),
        stage="menu",
    )


# ---------- question answering ----------
def _reprompt(state: State) -> str:
    """When a question interrupts a lesson or quiz, bring the learner back to where they were."""
    if state.get("stage") == "lesson" and state.get("lesson"):
        L = state["lesson"]
        return _t(state, "back_lesson", question=get_topic(L["topic"], _lang(state))["lesson"][L["step"]]["question"])
    if state.get("stage") == "quiz" and state.get("quiz", {}).get("current"):
        return _t(state, "back_quiz", question=_quiz_item(state, state["quiz"]["current"])["question"])
    return ""


def six_seven(state: State) -> dict:
    """Echo the meme, then return to the current lesson or quiz question (or the menu). Does not count as an attempt."""
    back = _reprompt(state) or f"\n\n{persona.menu_text(_name(state), _lang(state))}"
    return _msg(f"{SIX_SEVEN_REPLY}{back}")


def answer(state: State) -> dict:
    smart = _gemini(state)  # Gemini first; the rule-based answer below is the silent fallback
    if smart:
        return smart
    lang = _lang(state)
    progress = _progress(state)
    hits = search.search(state.get("search_query") or _text(state), question=_text(state), lang=lang)
    note = _t(state, "heard", heard=state["heard"]) if state.get("heard") else ""
    if not hits:
        titles = ", ".join(t["title"].lower() for t in topics(lang)[:4])
        return _msg(f"{note}{_t(state, 'not_sure', name=_name(state), titles=titles)}{_reprompt(state)}")
    question = _text(state)
    told = state.get("told") or []
    good = [h for h in hits if h["score"] >= 0.6 * hits[0]["score"]]
    # when the learner asks for more, move on to facts they haven't heard yet
    ranked = ([h for h in good if h["text"] not in told] or good) if _MORE.search(question) else good
    best = ranked[0]

    def covered(q: str, h: dict) -> float:  # in Malay mode the question may be in English, so check both texts
        return max(search.coverage(q, h["text"]), search.coverage(q, h["alt"]) if h.get("alt") else 0)

    def fits(h: dict) -> bool:
        # a second fact must read as one thought with the first: same topic, or something the question actually asked
        if best["topic"] == "glossary":
            return covered(question, h) > 0
        return h["topic"] == best["topic"] and h["score"] >= 0.75 * best["score"]

    second = next((h for h in ranked[1:] if fits(h)), None)
    chosen = [best, second] if second else [best]
    if second and best["topic"] == "glossary" and state.get("cued"):
        chosen = [second]  # "what does the petuq do?" wants the fact; a definition on top only repeats it
    answer_text = " ".join(f"{h['text']} {cite(h['sources'])}" for h in chosen)
    topic_id = next((h["topic"] for h in chosen if h["topic"] != "glossary"), "glossary")
    follow = _t(state, "what_else")
    if topic_id != "glossary":
        if topic_id not in progress["topics_seen"]:
            progress["topics_seen"].append(topic_id)
        related = [f"'{get_topic(r, lang)['title']}'" for r in get_topic(topic_id).get("related", [])]
        follow = _t(state, "related", related=", ".join(related)) if related else follow
    canon_q = _SUBJECT_NAMES.sub("gendang beleq", question)
    joined = {"text": " ".join(h["text"] for h in chosen), "alt": " ".join(h.get("alt", "") for h in chosen).strip()}
    partial = (not state.get("cued") and not nlp.expand_synonyms(canon_q, lang)
               and len(nlp.extract_keywords(canon_q)) >= 2
               and covered(canon_q, joined) <= 0.5)
    lead = _t(state, "partial") if partial else ""
    return _msg(f"{note}{lead}{answer_text}\n\n{follow}{_reprompt(state)}", progress=progress,
                told=told + [h["text"] for h in chosen])


# ---------- teacher: lessons ----------
def _present(state: State, topic: dict, i: int) -> str:
    step = topic["lesson"][i]
    return _t(state, "present", n=i + 1, total=len(topic["lesson"]), teach=step["teach"], question=step["question"])


def _pick_topic(state: State, progress: dict):
    text, lang = _text(state).lower(), _lang(state)
    # a lesson title in either language picks that lesson ("teach me about the instruments", "ajar saya tentang ...")
    for code in dict.fromkeys((lang, "en")):
        for t in topics(code):
            if t["title"].lower().rstrip("?") in text:
                return get_topic(t["id"], lang)
    best, top = None, 0
    for t in topics(lang):
        score = sum(1 for k in t["keywords"] if search.keyword_hit(k, text))
        if score > top:
            best, top = t, score
    return best or _next_unfinished(progress, lang)


def lesson_start(state: State) -> dict:
    progress = _progress(state)
    topic = _pick_topic(state, progress)
    if topic is None:
        return _msg(_t(state, "all_lessons_done", name=_name(state)), stage="menu")
    number = [t["id"] for t in topics()].index(topic["id"]) + 1
    return _msg(
        _t(state, "lesson_start", name=_name(state), number=number, title=topic["title"]) + _present(state, topic, 0),
        stage="lesson", lesson={"topic": topic["id"], "step": 0, "attempts": 0},
    )


def _advance_lesson(state: State, progress: dict, lesson: dict, topic: dict, feedback: str) -> dict:
    nxt = lesson["step"] + 1
    if nxt < len(topic["lesson"]):
        return _msg(f"{feedback}\n\n{_present(state, topic, nxt)}", lesson={**lesson, "step": nxt, "attempts": 0},
                    progress=progress)
    if topic["id"] not in progress["lessons_done"]:
        progress["lessons_done"].append(topic["id"])
    _save(state, progress)
    upcoming = _next_unfinished(progress, _lang(state))
    onward = _t(state, "onward_next", title=upcoming["title"]) if upcoming else _t(state, "onward_done")
    return _msg(
        _t(state, "lesson_complete", feedback=feedback, name=_name(state), summary=topic["summary"],
           cite=cite(topic_sources(topic)), onward=onward),
        stage="menu", lesson={}, progress=progress,
    )


def lesson_reply(state: State) -> dict:
    progress, lesson, lang = _progress(state), dict(state["lesson"]), _lang(state)
    topic = get_topic(lesson["topic"], lang)
    step = topic["lesson"][lesson["step"]]
    text = _text(state)
    if _REPEAT.search(text):
        return _msg(_t(state, "repeat", step=_present(state, topic, lesson["step"])))
    if _HINT.match(text):
        return _msg(_t(state, "clue", hint=step["hint"]))
    skipped = bool(_SKIP.search(text))
    hit, total = _grade(text, step["answer"])

    if not skipped and hit == total:
        progress["lesson_total"] += 1
        if lesson["attempts"] == 0:
            progress["lesson_right"] += 1
        return _advance_lesson(state, progress, lesson, topic, f"{persona.pick(i18n.get(lang, 'praise'))} {step['explain']}")
    if not skipped and lesson["attempts"] == 0:
        tone = persona.pick(i18n.get(lang, "comfort" if state.get("mood") == "struggling" else "gentle"))
        if hit and hit < total:
            tone = _t(state, "partly", name=_name(state))
        return _msg(_t(state, "lesson_retry", tone=tone, hint=step["hint"]), lesson={**lesson, "attempts": 1})
    progress["lesson_total"] += 1
    return _advance_lesson(state, progress, lesson, topic, _t(state, "learn_together", explain=step["explain"]))


# ---------- teacher: quiz ----------
def _pick_quiz(quiz: dict, progress: dict, lang: str = "en"):
    level = 2 if quiz["right"] >= 2 else 1
    pool = [i for i in quiz_items(lang) if i["key"] not in quiz["asked"]]
    allowed = [i for i in pool if i["level"] <= level] or pool
    learned = [i for i in allowed if i["topic"] in progress["lessons_done"]]
    return random.choice(learned or allowed) if allowed else None


def quiz_start(state: State) -> dict:
    progress = _progress(state)
    quiz = {"n": 0, "right": 0, "asked": [], "current": None, "attempts": 0}
    item = _pick_quiz(quiz, progress, _lang(state))
    quiz.update(current=item["key"], asked=[item["key"]])
    return _msg(_t(state, "quiz_start", name=_name(state), n=QUIZ_LENGTH, question=item["question"]),
                stage="quiz", quiz=quiz)


def quiz_reply(state: State) -> dict:
    progress, quiz, lang = _progress(state), dict(state["quiz"]), _lang(state)
    item = _quiz_item(state, quiz["current"])
    text = _text(state)
    if _HINT.match(text):
        return _msg(_t(state, "clue", hint=item["hint"]))
    skipped = bool(_SKIP.search(text))
    hit, total = _grade(text, item["answer"])
    correct = not skipped and hit == total

    if not correct and not skipped and quiz["attempts"] == 0:
        tone = _t(state, "partly", name=_name(state)) if hit else persona.pick(i18n.get(lang, "gentle"))
        return _msg(_t(state, "quiz_retry", tone=tone, hint=item["hint"]), quiz={**quiz, "attempts": 1})

    progress["quiz_total"] += 1
    _stat(progress, item["topic"], correct and quiz["attempts"] == 0)
    if correct:
        progress["quiz_right"] += 1
        quiz["right"] += 1
        feedback = f"{persona.pick(i18n.get(lang, 'praise'))} {item['explain']}"
    else:
        feedback = _t(state, "answer_was", explain=item["explain"])
    quiz["n"] += 1
    quiz["attempts"] = 0
    _save(state, progress)

    nxt = _pick_quiz(quiz, progress, lang) if quiz["n"] < QUIZ_LENGTH else None
    if nxt is None:
        ratio = quiz["right"] / quiz["n"]
        comment = _t(state, "quiz_high" if ratio >= 0.8 else "quiz_mid" if ratio >= 0.5 else "quiz_low")
        return _msg(
            _t(state, "quiz_done", feedback=feedback, right=quiz["right"], n=quiz["n"], comment=comment,
               badge=persona.badge(progress, lang)),
            stage="menu", quiz={}, progress=progress,
        )
    quiz.update(current=nxt["key"], asked=quiz["asked"] + [nxt["key"]])
    return _msg(_t(state, "quiz_next", feedback=feedback, n=quiz["n"] + 1, question=nxt["question"]),
                quiz=quiz, progress=progress)


# ---------- teacher: progress and recommendations ----------
def progress_node(state: State) -> dict:
    p, lang = _progress(state), _lang(state)
    titles = [get_topic(t, lang)["title"] for t in p["lessons_done"]]
    acc = f"{100 * p['quiz_right'] // p['quiz_total']}%" if p["quiz_total"] else _t(state, "no_quiz")
    upcoming = _next_unfinished(p, lang)
    nxt = _t(state, "next_up", title=upcoming["title"]) if upcoming else _t(state, "finished_all")
    return _msg(_t(
        state, "report", name=_name(state), done=len(titles), total=len(topics()),
        titles=f" ({'; '.join(titles)})" if titles else "", lesson_right=p["lesson_right"],
        lesson_total=p["lesson_total"], quiz_right=p["quiz_right"], quiz_total=p["quiz_total"], acc=acc,
        badge=persona.badge(p, lang), next=nxt,
    ))


def recommend(state: State) -> dict:
    """Rule-based consultant. Score = +3 not yet learned, +2 per interest keyword in the message,
    +2 if quiz accuracy on the topic is below 60%, +1 if the learner has asked about it."""
    p, lang = _progress(state), _lang(state)
    text = _text(state).lower()
    scored = []
    for t in topics(lang):
        score, reasons = 0, []
        if t["id"] not in p["lessons_done"]:
            score += 3
            reasons.append(_t(state, "why_new"))
        hits = [k for k in t["keywords"] if search.keyword_hit(k, text)]
        if hits:
            score += 2 * len(hits)
            reasons.append(_t(state, "why_interest", keyword=hits[0]))
        s = p["topic_stats"].get(t["id"])
        if s and s["right"] / s["total"] < 0.6:
            score += 2
            reasons.append(_t(state, "why_practice"))
        if t["id"] in p["topics_seen"]:
            score += 1
            reasons.append(_t(state, "why_asked"))
        scored.append((score, t, reasons))
    scored.sort(key=lambda x: x[0], reverse=True)
    top = [x for x in scored if x[0] > 0][:2]
    if not top:
        return _msg(_t(state, "covered_all", name=_name(state)))
    lines = "\n".join(f"  - {t['title']}: {reasons[0]}." for _, t, reasons in top)
    return _msg(_t(state, "recommend", lines=lines))
