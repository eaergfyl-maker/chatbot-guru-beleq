import re
import uuid
from pathlib import Path

import streamlit as st

from eval import cuq
from src import persona
from src.graph import ask, build_graph, start, state_of
from src.knowledge import topics

st.set_page_config(page_title=persona.BOT_NAME, page_icon="🥁")

ASSETS = Path(__file__).parent / "assets"
avatar = next((str(p) for p in (ASSETS / "avatar.png", ASSETS / "avatar.svg") if p.exists()), "🥁")


@st.cache_resource
def get_graph():
    return build_graph()


def render(text: str) -> str:
    """Keep the bot's line breaks, and stop Markdown renumbering the menu (it would show option 0 as 8)."""
    return re.sub(r"(?m)^\s*(\d+)\.", r"\1\\.", text).replace("\n", "  \n")


graph = get_graph()

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
    # the chatbot speaks first
    st.session_state.history = [("assistant", start(graph, st.session_state.thread_id))]

tid = st.session_state.thread_id

with st.sidebar:
    if avatar == "🥁":
        st.markdown("# 🥁")
    else:
        st.image(avatar, width=120)
    st.subheader(persona.BOT_NAME)
    st.caption("Your Gendang Beleq teacher")
    progress = state_of(graph, tid).get("progress")
    if progress:
        done, total = len(progress["lessons_done"]), len(topics())
        st.markdown(f"**Title:** {persona.badge(progress)}")
        st.progress(done / total, text=f"Lessons {done}/{total}")
        if progress["quiz_total"]:
            st.write(f"Quiz: {progress['quiz_right']}/{progress['quiz_total']} correct")
    if st.button("Start over"):
        del st.session_state["thread_id"]
        st.rerun()

    with st.expander("Rate this chatbot"):
        st.caption(f"Chatbot Usability Questionnaire. {cuq.SCALE}. Your answers are anonymous.")
        with st.form("cuq", clear_on_submit=True):
            answers = [st.slider(f"{i}. {item}", 1, 5, 3) for i, item in enumerate(cuq.ITEMS, start=1)]
            comments = st.text_area("Comments (optional)")
            if st.form_submit_button("Submit"):
                st.success(f"Thank you! Your score: {cuq.save(answers, comments):.1f} out of 100.")

st.title(persona.BOT_NAME)

for role, text in st.session_state.history:
    with st.chat_message(role, avatar=avatar if role == "assistant" else None):
        st.markdown(render(text))

if prompt := st.chat_input("Type here..."):
    st.session_state.history.append(("user", prompt))
    st.session_state.history.append(("assistant", ask(graph, prompt, tid)))
    st.rerun()
