import uuid
from pathlib import Path

import streamlit as st

from src import persona
from src.graph import ask, build_graph, start, state_of
from src.knowledge import topics

st.set_page_config(page_title=persona.BOT_NAME, page_icon="🥁")

ASSETS = Path(__file__).parent / "assets"
avatar = next((str(p) for p in (ASSETS / "avatar.png", ASSETS / "avatar.svg") if p.exists()), "🥁")


@st.cache_resource
def get_graph():
    return build_graph()


graph = get_graph()

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
    # the chatbot speaks first
    st.session_state.history = [("assistant", start(graph, st.session_state.thread_id))]

tid = st.session_state.thread_id

with st.sidebar:
    st.image(avatar, width=120) if avatar != "🥁" else st.markdown("# 🥁")
    st.subheader(persona.BOT_NAME)
    st.caption("Your Gendang Beleq teacher")
    progress = state_of(graph, tid).get("progress")
    if progress:
        st.markdown(f"**Title:** {persona.badge(progress)}")
        st.progress(len(progress["lessons_done"]) / len(topics()), text=f"Lessons {len(progress['lessons_done'])}/{len(topics())}")
        if progress["quiz_total"]:
            st.write(f"Quiz: {progress['quiz_right']}/{progress['quiz_total']} correct")
    if st.button("Start over"):
        del st.session_state["thread_id"]
        st.rerun()

st.title(persona.BOT_NAME)

for role, text in st.session_state.history:
    with st.chat_message(role, avatar=avatar if role == "assistant" else None):
        st.markdown(text.replace("\n", "  \n"))

if prompt := st.chat_input("Type here..."):
    st.session_state.history.append(("user", prompt))
    st.session_state.history.append(("assistant", ask(graph, prompt, tid)))
    st.rerun()
