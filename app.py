import re
import uuid
from pathlib import Path

import streamlit as st

from eval import cuq
from src import persona
from src.graph import ask, build_graph, start, state_of
from src.knowledge import topics

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
    """Keep the bot's line breaks, and stop Markdown renumbering the menu (it would show option 0 as 8)."""
    return re.sub(r"(?m)^\s*(\d+)\.", r"\1\\.", text).replace("\n", "  \n")


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
progress = state_of(graph, tid).get("progress")

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

if prompt := st.chat_input("Type here...", submit_mode="disable"):
    st.session_state.history.append(("user", prompt))
    st.session_state.history.append(("assistant", ask(graph, prompt, tid)))
    st.rerun()
