import re
import uuid
from pathlib import Path

import streamlit as st

from eval import cuq
from src import i18n, persona
from src.graph import ask, build_graph, start, state_of, switch_language
from src.knowledge import cite, glossary, topics
from src.semantic_net import label, load_edges, relation_label, to_mermaid

ASSETS = Path(__file__).parent / "assets"
avatar = next((str(p) for p in (ASSETS / "avatar.png", ASSETS / "avatar.svg") if p.exists()), "🥁")

# Every label on the page, in English and Bahasa Malaysia (the bot's own words come from src/i18n.py)
UI = {
    "en": {
        "page_title": "Gendang Beleq Teacher", "subtitle": "Your Gendang Beleq teacher", "language": "Language",
        "thinking": "Guru Beleq is thinking...", "transcript": "Guru Beleq - Learning Transcript",
        "status": "Status: {badge} | Lessons: {done}/{total} | Quiz: {right}/{qtotal}", "you": "You",
        "file": "guru-beleq-transcript.txt",
        "explore_title": "Explore Gendang Beleq knowledge",
        "explore_hint": "Browse lessons, search the 17-term Sasak glossary, or inspect the cited semantic network.",
        "tabs": ["Lessons (6)", "Sasak glossary (17)", "Semantic network (24)"],
        "completed": "Completed", "to_learn": "To learn", "lesson_n": "Lesson {n}: {title}",
        "start_lesson": "Start lesson", "teach_about": "teach me about {title}",
        "search": "Search Sasak or musical terms", "search_ph": "e.g. petuq, nyongkolan, sapuk...",
        "ask": "Ask", "what_is": "what is {term}?",
        "net_hint": "One-hop semantic network used by Guru Beleq for spreading-activation search expansion.",
        "mermaid": "View Mermaid diagram source",
        "rate": "Rate this chatbot", "anon": "Your answers are anonymous.", "comments": "Comments (optional)",
        "submit": "Submit", "answer_all": "Please answer every question from 1 to 5.",
        "thanks": "Thank you! Your score: {score:.1f} out of 100.",
        "not_saved": "Thank you! Your score: {score:.1f} out of 100. (This copy cannot store responses.)",
        "ready": "🥁 Ready", "lvl": "LVL", "quiz": "Quiz",
        "explore": "Explore knowledge", "export": "Export chat", "restart": "Start over",
        "hint": "Hint", "repeat": "Repeat step", "skip": "Skip question", "leave": "Leave lesson", "stop_quiz": "Stop quiz",
        "cmd_hint": "hint", "cmd_repeat": "repeat", "cmd_skip": "skip", "cmd_stop": "stop",
        "menu": ["1. Lesson", "2. Ask", "3. Quiz", "4. Recommend", "5. Progress", "6. Help", "7. Sources", "8. Glossary"],
        "type_here": "Type here...",
        "reactions": {"greeting": "👋 Greeting you", "teaching": "🥁 Explaining...", "celebrate": "🎉 Spot on!",
                      "thinking": "💡 Hint & clue", "comfort": "💛 Taking it slow", "six_seven": "🤲 67!"},
    },
    "ms": {
        "page_title": "Guru Gendang Beleq", "subtitle": "Guru Gendang Beleq anda", "language": "Bahasa",
        "thinking": "Guru Beleq sedang berfikir...", "transcript": "Guru Beleq - Transkrip Pembelajaran",
        "status": "Status: {badge} | Pelajaran: {done}/{total} | Kuiz: {right}/{qtotal}", "you": "Anda",
        "file": "guru-beleq-transkrip.txt",
        "explore_title": "Terokai pengetahuan Gendang Beleq",
        "explore_hint": "Layari pelajaran, cari dalam glosari Sasak 17 istilah, atau lihat rangkaian semantik yang bersumber.",
        "tabs": ["Pelajaran (6)", "Glosari Sasak (17)", "Rangkaian semantik (24)"],
        "completed": "Selesai", "to_learn": "Belum dipelajari", "lesson_n": "Pelajaran {n}: {title}",
        "start_lesson": "Mula pelajaran", "teach_about": "ajar saya tentang {title}",
        "search": "Cari istilah Sasak atau muzik", "search_ph": "cth. petuq, nyongkolan, sapuk...",
        "ask": "Tanya", "what_is": "apa itu {term}?",
        "net_hint": "Rangkaian semantik satu langkah yang digunakan Guru Beleq untuk meluaskan carian.",
        "mermaid": "Lihat sumber rajah Mermaid",
        "rate": "Nilai chatbot ini", "anon": "Jawapan anda tanpa nama.", "comments": "Komen (pilihan)",
        "submit": "Hantar", "answer_all": "Sila jawab setiap soalan dari 1 hingga 5.",
        "thanks": "Terima kasih! Skor anda: {score:.1f} daripada 100.",
        "not_saved": "Terima kasih! Skor anda: {score:.1f} daripada 100. (Salinan ini tidak dapat menyimpan jawapan.)",
        "ready": "🥁 Sedia", "lvl": "TAHAP", "quiz": "Kuiz",
        "explore": "Terokai pengetahuan", "export": "Eksport sembang", "restart": "Mula semula",
        "hint": "Petunjuk", "repeat": "Ulang langkah", "skip": "Langkau soalan", "leave": "Tinggalkan pelajaran",
        "stop_quiz": "Hentikan kuiz",
        "cmd_hint": "petunjuk", "cmd_repeat": "ulang", "cmd_skip": "langkau", "cmd_stop": "berhenti",
        "menu": ["1. Pelajaran", "2. Tanya", "3. Kuiz", "4. Cadangan", "5. Kemajuan", "6. Bantuan", "7. Sumber",
                 "8. Glosari"],
        "type_here": "Taip di sini...",
        "reactions": {"greeting": "👋 Menyapa anda", "teaching": "🥁 Menerangkan...", "celebrate": "🎉 Tepat sekali!",
                      "thinking": "💡 Petunjuk & klu", "comfort": "💛 Perlahan-lahan", "six_seven": "🤲 67!"},
    },
}
LANG_NAMES = {"en": "English", "ms": "Bahasa Malaysia"}

st.set_page_config(
    page_title=f"{persona.BOT_NAME} - Gendang Beleq Teacher",
    page_icon=avatar,
    layout="centered",
)


@st.cache_resource
def get_graph():
    return build_graph()


def render(text: str) -> str:
    """Keep the bot's line breaks, and stop Markdown renumbering the menu (it would show option 0 as 9)."""
    return re.sub(r"(?m)^\s*(\d+)\.", r"\1\\.", text).replace("\n", "  \n")


def current_lang() -> str:
    return i18n.norm(st.session_state.get("lang"))


def send_user_message(graph, tid: str, message: str):
    st.session_state.history.append(("user", message))
    with st.spinner(UI[current_lang()]["thinking"]):
        reply = ask(graph, message, tid, current_lang())
    st.session_state.history.append(("assistant", reply))


def on_language_change():
    """The bot confirms the switch and repeats its current question or the menu in the new language."""
    if "thread_id" in st.session_state:
        reply = switch_language(get_graph(), st.session_state.thread_id, current_lang())
        st.session_state.history.append(("assistant", reply))


def build_transcript(history: list[tuple[str, str]], progress: dict | None, lang: str) -> str:
    ui = UI[lang]
    lines = [ui["transcript"]]
    if progress:
        lines.append(ui["status"].format(
            badge=persona.badge(progress, lang), done=len(progress["lessons_done"]), total=len(topics()),
            right=progress["quiz_right"], qtotal=progress["quiz_total"],
        ))
    lines.append("=" * 50 + "\n")
    for role, text in history:
        speaker = persona.BOT_NAME if role == "assistant" else ui["you"]
        lines.append(f"[{speaker}]\n{text}\n")
    return "\n".join(lines)


def explore_knowledge_dialog(graph, tid: str, progress: dict | None, lang: str):
    ui = UI[lang]

    @st.dialog(ui["explore_title"], width="large")
    def dialog():
        st.caption(ui["explore_hint"])
        tab_lessons, tab_glossary, tab_net = st.tabs(ui["tabs"])
        done_set = set((progress or {}).get("lessons_done", []))

        with tab_lessons:
            for idx, t in enumerate(topics(lang), start=1):
                with st.container(border=True):
                    status = f":green-badge[{ui['completed']}]" if t["id"] in done_set else f":orange-badge[{ui['to_learn']}]"
                    st.markdown(f"**{ui['lesson_n'].format(n=idx, title=t['title'])}** {status}")
                    st.caption(t["summary"])
                    if st.button(ui["start_lesson"], key=f"dlg_lesson_{t['id']}", icon=":material/school:"):
                        send_user_message(graph, tid, ui["teach_about"].format(title=t["title"].lower()))
                        st.rerun()

        with tab_glossary:
            query = st.text_input(ui["search"], placeholder=ui["search_ph"], label_visibility="collapsed").lower()
            for term, entry in sorted(glossary(lang).items()):
                if query and query not in term.lower() and query not in entry["meaning"].lower():
                    continue
                with st.container(border=True):
                    col_text, col_btn = st.columns([4, 1], vertical_alignment="center")
                    with col_text:
                        st.markdown(f"**{term}** — {entry['meaning']} `{cite(entry['sources'])}`")
                    with col_btn:
                        if st.button(ui["ask"], key=f"dlg_term_{term}", width="stretch"):
                            send_user_message(graph, tid, ui["what_is"].format(term=term))
                            st.rerun()

        with tab_net:
            st.caption(ui["net_hint"])
            for e in load_edges():
                st.markdown(
                    f"- **{label(e['s'], lang)}** → *{relation_label(e['r'], lang)}* → **{label(e['o'], lang)}** "
                    f"`{cite(e['sources'])}`"
                )
            with st.expander(ui["mermaid"]):
                st.code(to_mermaid(), language="mermaid")

    dialog()


def rate_chatbot_dialog(lang: str):
    ui, form = UI[lang], cuq.questionnaire(lang)

    @st.dialog(ui["rate"], width="large")
    def dialog():
        st.caption(f"{form['scale']}. {ui['anon']}")
        with st.form("cuq", clear_on_submit=True, border=False):
            answers = [
                st.segmented_control(f"{i}. {item}", options=[1, 2, 3, 4, 5], default=3, key=f"cuq_q_{i}")
                for i, item in enumerate(form["items"], start=1)
            ]
            comments = st.text_area(ui["comments"], placeholder=ui["comments"])
            if st.form_submit_button(ui["submit"], type="primary", width="stretch"):
                if any(a is None for a in answers):
                    st.error(ui["answer_all"])
                else:
                    values = [int(a) for a in answers]
                    try:
                        st.success(ui["thanks"].format(score=cuq.save(values, comments)))
                    except OSError:  # read-only disk, as on Streamlit Community Cloud
                        st.success(ui["not_saved"].format(score=cuq.score(values)))

    dialog()


graph = get_graph()

if "lang" not in st.session_state:
    st.session_state.lang = i18n.norm(st.query_params.get("lang"))  # ?lang=ms opens the app in Bahasa Malaysia
with st.sidebar:
    st.segmented_control(
        ":material/translate: Language / Bahasa",
        options=list(LANG_NAMES),
        format_func=LANG_NAMES.get,
        required=True,
        key="lang",
        on_change=on_language_change,
        width="stretch",
    )
lang = current_lang()
ui = UI[lang]

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
    # the chatbot speaks first
    st.session_state.history = [("assistant", start(graph, st.session_state.thread_id, lang))]

tid = st.session_state.thread_id
current_state = state_of(graph, tid)
progress = current_state.get("progress")
stage = current_state.get("stage", "ask_name")
last_reply = st.session_state.history[-1][1] if st.session_state.history else ""
reaction = persona.reaction_of(current_state, last_reply)

with st.sidebar:
    if avatar == "🥁":
        st.markdown("# 🥁")
    else:
        st.image(avatar, width=140, alt="Guru Beleq avatar")
    st.subheader(persona.BOT_NAME)
    st.caption(f"{ui['subtitle']} · {ui['reactions'].get(reaction, ui['ready'])}")

    if progress:
        done, total = len(progress["lessons_done"]), len(topics())
        lvl = persona.level_of(progress)
        quiz_text = (
            f" · {ui['quiz']} {progress['quiz_right']}/{progress['quiz_total']}"
            if progress["quiz_total"]
            else ""
        )
        st.markdown(f"**{ui['lvl']} {lvl} · {persona.badge(progress, lang)}** ({done}/{total}{quiz_text})")
        st.progress(done / total)
    else:
        st.markdown(f"**{ui['lvl']} 1 · {i18n.get(lang, 'badges')[0]}**")

    if st.button(ui["explore"], icon=":material/menu_book:", width="stretch"):
        explore_knowledge_dialog(graph, tid, progress, lang)

    st.download_button(
        ui["export"],
        data=build_transcript(st.session_state.history, progress, lang),
        file_name=ui["file"],
        mime="text/plain",
        icon=":material/download:",
        width="stretch",
    )

    if st.button(ui["rate"], icon=":material/rate_review:", width="stretch"):
        rate_chatbot_dialog(lang)

    if st.button(ui["restart"], icon=":material/restart_alt:", width="stretch"):
        del st.session_state["thread_id"]
        st.rerun()

st.title(persona.BOT_NAME)
st.caption(ui["subtitle"])

for role, text in st.session_state.history:
    with st.chat_message(role, avatar=avatar if role == "assistant" else None):
        st.markdown(render(text))

# Context-aware quick-action bar; each button sends the command word in the current language
if stage == "lesson":
    actions = [(ui["hint"], ":material/lightbulb:", ui["cmd_hint"]), (ui["repeat"], ":material/replay:", ui["cmd_repeat"]),
               (ui["skip"], ":material/skip_next:", ui["cmd_skip"]), (ui["leave"], ":material/stop_circle:", ui["cmd_stop"])]
elif stage == "quiz":
    actions = [(ui["hint"], ":material/lightbulb:", ui["cmd_hint"]), (ui["skip"], ":material/skip_next:", ui["cmd_skip"]),
               (ui["stop_quiz"], ":material/stop_circle:", ui["cmd_stop"])]
elif stage == "menu":
    icons = [":material/school:", ":material/help:", ":material/quiz:", ":material/explore:",
             ":material/insights:", ":material/info:", ":material/library_books:", ":material/dictionary:"]
    actions = [(name, icon, str(n)) for n, (name, icon) in enumerate(zip(ui["menu"], icons), start=1)]
else:
    actions = []
if actions:
    with st.container(horizontal=True):
        for i, (name, icon, message) in enumerate(actions):
            if st.button(name, icon=icon, type="primary" if i == 0 else "secondary", key=f"qa_{stage}_{i}"):
                send_user_message(graph, tid, message)
                st.rerun()

if prompt := st.chat_input(ui["type_here"], submit_mode="disable"):
    send_user_message(graph, tid, prompt)
    st.rerun()
