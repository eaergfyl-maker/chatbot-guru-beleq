import functools
import logging

from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from . import nodes
from .state import State

log = logging.getLogger(__name__)


def safe(fn, **on_error):
    """Exception handling: if a node raises, log it and apologise so the chat carries on."""

    @functools.wraps(fn)
    def wrapper(state: State) -> dict:
        try:
            return fn(state)
        except Exception:
            log.exception("node %s failed", fn.__name__)
            return {"messages": [AIMessage(content=nodes.ERROR_MESSAGE)], **on_error}

    return wrapper


# intent -> node that handles it
INTENT_NODES = {
    "qa": "answer", "menu": "menu", "leave": "leave", "invite": "invite", "help": "help", "smalltalk": "smalltalk",
    "offtopic": "offtopic", "bye": "bye", "progress": "progress", "recommend": "recommend", "sources": "sources",
    "glossary": "glossary", "lesson_start": "lesson_start", "lesson_reply": "lesson_reply",
    "quiz_start": "quiz_start", "quiz_reply": "quiz_reply",
}


def build_graph():
    g = StateGraph(State)

    g.add_node("greet", nodes.greet)
    g.add_node("validate", nodes.validate)
    g.add_node("reject", nodes.reject)
    g.add_node("route_stage", lambda state: {})  # junction: decides between name capture and normal handling
    g.add_node("take_name", safe(nodes.take_name))
    g.add_node("normalize", safe(nodes.normalize))
    g.add_node("classify", safe(nodes.classify, intent="error"))  # already apologised, so the turn ends there
    for node_name, fn in (
        ("answer", nodes.answer), ("menu", nodes.menu), ("leave", nodes.leave), ("invite", nodes.invite),
        ("help", nodes.help_node), ("smalltalk", nodes.smalltalk), ("offtopic", nodes.offtopic), ("bye", nodes.bye),
        ("progress", nodes.progress_node), ("recommend", nodes.recommend), ("sources", nodes.sources),
        ("glossary", nodes.glossary_node), ("lesson_start", nodes.lesson_start),
        ("lesson_reply", nodes.lesson_reply), ("quiz_start", nodes.quiz_start), ("quiz_reply", nodes.quiz_reply),
    ):
        g.add_node(node_name, safe(fn))

    # the bot speaks first on the boot turn, afterwards every message is validated
    g.add_conditional_edges(START, nodes.route_start, {"greet": "greet", "validate": "validate"})
    g.add_conditional_edges("validate", nodes.route_valid, {"reject": "reject", "route_stage": "route_stage"})
    g.add_conditional_edges("route_stage", nodes.route_stage, {"take_name": "take_name", "normalize": "normalize"})
    g.add_edge("normalize", "classify")
    g.add_conditional_edges("classify", nodes.route_intent, {**INTENT_NODES, "error": END})
    for end_node in ["greet", "reject", "take_name", *INTENT_NODES.values()]:
        g.add_edge(end_node, END)

    # MemorySaver keeps per-thread state in RAM. Learner progress is also saved by name in data/profiles.json.
    return g.compile(checkpointer=MemorySaver())


def _config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


def start(graph, thread_id: str = "default") -> str:
    """The bot speaks first."""
    return graph.invoke({"boot": True}, config=_config(thread_id))["messages"][-1].content


def ask(graph, text: str, thread_id: str = "default") -> str:
    try:
        out = graph.invoke({"boot": False, "messages": [("user", text)]}, config=_config(thread_id))
        return out["messages"][-1].content
    except Exception:
        log.exception("graph invocation failed")
        return nodes.ERROR_MESSAGE


def state_of(graph, thread_id: str = "default") -> dict:
    return graph.get_state(_config(thread_id)).values


if __name__ == "__main__":
    graph = build_graph()
    print(start(graph))
    while True:
        try:
            print("\n" + ask(graph, input("\nYou: ")))
        except (KeyboardInterrupt, EOFError):
            break
        if state_of(graph).get("intent") == "bye":
            break
