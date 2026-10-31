import re
import uuid
from pathlib import Path

import streamlit as st

from eval import cuq
from src import persona
from src.graph import ask, build_graph, start, state_of
from src.knowledge import cite, glossary, topics
from src.semantic_net import load_edges, to_mermaid

ASSETS = Path(__file__).parent / "assets"
avatar = next((str(p) for p in (ASSETS / "avatar.png", ASSETS / "avatar.svg") if p.exists()), "🥁")

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


def send_user_message(graph, tid: str, message: str):
    st.session_state.history.append(("user", message))
    st.session_state.history.append(("assistant", ask(graph, message, tid)))


def build_transcript(history: list[tuple[str, str]], progress: dict | None) -> str:
    lines = ["Guru Beleq - Learning Transcript"]
    if progress:
        done, total = len(progress["lessons_done"]), len(topics())
        lines.append(
            f"Status: {persona.badge(progress)} | Lessons: {done}/{total} | "
            f"Quiz: {progress['quiz_right']}/{progress['quiz_total']}"
        )
    lines.append("=" * 50 + "\n")
    for role, text in history:
        speaker = persona.BOT_NAME if role == "assistant" else "You"
        lines.append(f"[{speaker}]\n{text}\n")
    return "\n".join(lines)


@st.dialog("Explore Gendang Beleq knowledge", width="large")
def explore_knowledge_dialog(graph, tid: str, progress: dict | None):
    st.caption("Browse lessons, search the 17-term Sasak glossary, or inspect the cited semantic network.")
    tab_lessons, tab_glossary, tab_net = st.tabs(
        ["Lessons (6)", "Sasak glossary (17)", "Semantic network (24)"]
    )
    done_set = set((progress or {}).get("lessons_done", []))

    with tab_lessons:
        for idx, t in enumerate(topics(), start=1):
            with st.container(border=True):
                status = ":green-badge[Completed]" if t["id"] in done_set else ":orange-badge[To learn]"
                st.markdown(f"**Lesson {idx}: {t['title']}** {status}")
                st.caption(t["summary"])
                if st.button(
                    "Start lesson",
                    key=f"dlg_lesson_{t['id']}",
                    icon=":material/school:",
                ):
                    send_user_message(graph, tid, f"teach me about {t['title'].lower()}")
                    st.rerun()

    with tab_glossary:
        query = st.text_input(
            "Search Sasak or musical terms",
            placeholder="e.g. petuq, nyongkolan, sapuk...",
            label_visibility="collapsed",
        ).lower()
        for term, entry in sorted(glossary().items()):
            if query and query not in term.lower() and query not in entry["meaning"].lower():
                continue
            with st.container(border=True):
                col_text, col_btn = st.columns([4, 1], vertical_alignment="center")
                with col_text:
                    st.markdown(f"**{term}** — {entry['meaning']} `{cite(entry['sources'])}`")
                with col_btn:
                    if st.button("Ask", key=f"dlg_term_{term}", width="stretch"):
                        send_user_message(graph, tid, f"what is {term}?")
                        st.rerun()

    with tab_net:
        st.caption("One-hop semantic network used by Guru Beleq for spreading-activation search expansion.")
        for e in load_edges():
            rel = e["r"].replace("_", " ")
            st.markdown(f"- **{e['s']}** → *{rel}* → **{e['o']}** `{cite(e['sources'])}`")
        with st.expander("View Mermaid diagram source"):
            st.code(to_mermaid(), language="mermaid")


@st.dialog("Rate this chatbot", width="large")
def rate_chatbot_dialog():
    st.caption(f"{cuq.SCALE}. Your answers are anonymous.")
    with st.form("cuq", clear_on_submit=True, border=False):
        answers = [
            st.segmented_control(
                f"{i}. {item}",
                options=[1, 2, 3, 4, 5],
                default=3,
                key=f"cuq_q_{i}",
            )
            for i, item in enumerate(cuq.ITEMS, start=1)
        ]
        comments = st.text_area("Comments (optional)", placeholder="Comments (optional)")
        if st.form_submit_button("Submit", type="primary", width="stretch"):
            if any(a is None for a in answers):
                st.error("Please answer every question from 1 to 5.")
            else:
                score = cuq.save([int(a) for a in answers], comments)
                st.success(f"Thank you! Your score: {score:.1f} out of 100.")


graph = get_graph()

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
    # the chatbot speaks first
    st.session_state.history = [("assistant", start(graph, st.session_state.thread_id))]

tid = st.session_state.thread_id
current_state = state_of(graph, tid)
progress = current_state.get("progress")
stage = current_state.get("stage", "ask_name")

with st.sidebar:
    if avatar == "🥁":
        st.markdown("# 🥁")
    else:
        st.image(avatar, width=96, alt="Guru Beleq avatar")
    st.subheader(persona.BOT_NAME)
    st.caption("Your Gendang Beleq teacher")

    if progress:
        done, total = len(progress["lessons_done"]), len(topics())
        quiz_text = (
            f" · Quiz {progress['quiz_right']}/{progress['quiz_total']}"
            if progress["quiz_total"]
            else ""
        )
        st.markdown(f"**{persona.badge(progress)}** · Lessons {done}/{total}{quiz_text}")
        st.progress(done / total)

    if st.button("Explore knowledge", icon=":material/menu_book:", width="stretch"):
        explore_knowledge_dialog(graph, tid, progress)

    st.download_button(
        "Export chat",
        data=build_transcript(st.session_state.history, progress),
        file_name="guru-beleq-transcript.txt",
        mime="text/plain",
        icon=":material/download:",
        width="stretch",
    )

    if st.button("Rate this chatbot", icon=":material/rate_review:", width="stretch"):
        rate_chatbot_dialog()

    if st.button("Start over", icon=":material/restart_alt:", width="stretch"):
        del st.session_state["thread_id"]
        st.rerun()

st.title(persona.BOT_NAME)
st.caption("Your Gendang Beleq teacher")

for role, text in st.session_state.history:
    with st.chat_message(role, avatar=avatar if role == "assistant" else None):
        st.markdown(render(text))

# Context-aware interactive quick-action menu bar
if stage == "lesson":
    with st.container(horizontal=True):
        if st.button("Hint", icon=":material/lightbulb:", type="primary"):
            send_user_message(graph, tid, "hint")
            st.rerun()
        if st.button("Repeat step", icon=":material/replay:"):
            send_user_message(graph, tid, "repeat")
            st.rerun()
        if st.button("Skip question", icon=":material/skip_next:"):
            send_user_message(graph, tid, "skip")
            st.rerun()
        if st.button("Leave lesson", icon=":material/stop_circle:"):
            send_user_message(graph, tid, "stop")
            st.rerun()
elif stage == "quiz":
    with st.container(horizontal=True):
        if st.button("Hint", icon=":material/lightbulb:", type="primary"):
            send_user_message(graph, tid, "hint")
            st.rerun()
        if st.button("Skip question", icon=":material/skip_next:"):
            send_user_message(graph, tid, "skip")
            st.rerun()
        if st.button("Stop quiz", icon=":material/stop_circle:"):
            send_user_message(graph, tid, "stop")
            st.rerun()
elif stage == "menu":
    with st.container(horizontal=True):
        if st.button("1. Lesson", icon=":material/school:", type="primary"):
            send_user_message(graph, tid, "1")
            st.rerun()
        if st.button("2. Ask", icon=":material/help:"):
            send_user_message(graph, tid, "2")
            st.rerun()
        if st.button("3. Quiz", icon=":material/quiz:"):
            send_user_message(graph, tid, "3")
            st.rerun()
        if st.button("4. Recommend", icon=":material/explore:"):
            send_user_message(graph, tid, "4")
            st.rerun()
        if st.button("5. Progress", icon=":material/insights:"):
            send_user_message(graph, tid, "5")
            st.rerun()
        if st.button("6. Help", icon=":material/info:"):
            send_user_message(graph, tid, "6")
            st.rerun()
        if st.button("7. Sources", icon=":material/library_books:"):
            send_user_message(graph, tid, "7")
            st.rerun()
        if st.button("8. Glossary", icon=":material/dictionary:"):
            send_user_message(graph, tid, "8")
            st.rerun()

if prompt := st.chat_input("Type here...", submit_mode="disable"):
    send_user_message(graph, tid, prompt)
    st.rerun()
