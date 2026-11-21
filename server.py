"""Serves the Guru Beleq web app. Run: python server.py  then open http://localhost:8000

Pages: / (choose a mode), /chat (companion chat), /sandbox (Sasak Village Sandbox game).
"""
import json
import mimetypes
import socket
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from eval import cuq
from src import i18n, llm, persona
from src.sandbox import sandbox_payload
from src.graph import ask, build_graph, start, state_of, switch_language
from src.knowledge import cite, glossary, topics
from src.semantic_net import label, load_edges, relation_label

ROOT = Path(__file__).parent
STATIC = {
    "/": ROOT / "web" / "landing.html",
    "/chat": ROOT / "web" / "index.html",
    "/sandbox": ROOT / "web" / "sandbox.html",
    "/lang.js": ROOT / "web" / "lang.js",
    "/avatar.png": ROOT / "assets" / "avatar.png",
}
graph = build_graph()
PORT = 8000


def progress_of(tid: str) -> dict | None:
    st = state_of(graph, tid)
    p = st.get("progress")
    if not p:
        return None
    return {
        "badge": persona.badge(p, i18n.norm(st.get("lang"))),
        "level": persona.level_of(p),
        "done": len(p["lessons_done"]),
        "lessons_done": p["lessons_done"],
        "total": len(topics()),
        "quiz_right": p["quiz_right"],
        "quiz_total": p["quiz_total"],
    }


def meta_payload(lang: str = "en") -> dict:
    return {
        "lang": lang,
        "topics": [{"id": t["id"], "title": t["title"], "summary": t["summary"]} for t in topics(lang)],
        "glossary": [
            {"term": k, "meaning": v["meaning"], "cite": cite(v["sources"])}
            for k, v in sorted(glossary(lang).items())
        ],
        "edges": [
            {"s": label(e["s"], lang), "r": relation_label(e["r"], lang), "o": label(e["o"], lang),
             "cite": cite(e["sources"])}
            for e in load_edges()
        ],
        "llm": llm.status(),
    }


def turn_payload(tid: str, reply: str) -> dict:
    """What the pages need after any bot turn."""
    st = state_of(graph, tid)
    return {
        "reply": reply,
        "progress": progress_of(tid),
        "stage": st.get("stage", "menu"),
        "lang": i18n.norm(st.get("lang")),
        "reaction": persona.reaction_of(st, reply),
        "engine": st.get("engine", "python"),  # who wrote this reply: "gemini" or "python"
        "smart": llm.available(),              # will Gemini be tried next turn (key set, no cooldown)
    }


def submit_cuq(answers: list[int], comments: str) -> dict:
    """Scores and saves a CUQ response. Vercel's disk is read-only, so there the score is returned unsaved."""
    try:
        return {"score": round(cuq.save(answers, comments), 1), "saved": True}
    except OSError:
        return {"score": round(cuq.score(answers), 1), "saved": False}


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: bytes, ctype: str):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, data: dict, code: int = 200):
        self._send(code, json.dumps(data).encode("utf-8"), "application/json; charset=utf-8")

    def do_GET(self):
        url = urlsplit(self.path)
        lang = i18n.norm(parse_qs(url.query).get("lang", ["en"])[0])  # ?lang=ms for Bahasa Malaysia
        if url.path == "/api/cuq":
            return self._json(cuq.questionnaire(lang))
        if url.path == "/api/meta":
            return self._json(meta_payload(lang))
        if url.path == "/api/sandbox":
            return self._json(sandbox_payload(lang))
        route = url.path.rstrip("/") or "/"  # /chat/ works like /chat
        path = STATIC.get(route)
        if path and path.exists():
            ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            return self._send(200, path.read_bytes(), f"{ctype}; charset=utf-8" if ctype.startswith("text") else ctype)
        self._send(404, b"Not found", "text/plain")

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
            data = json.loads(self.rfile.read(length) or b"{}")
            if self.path == "/api/start":
                tid = str(uuid.uuid4())
                reply = start(graph, tid, i18n.norm(data.get("lang")))
                return self._json({"thread_id": tid, **turn_payload(tid, reply), "progress": None})
            if self.path == "/api/cuq":
                answers = [int(a) for a in data["answers"]]
                comments = str(data.get("comments", ""))[:1000]
                return self._json(submit_cuq(answers, comments))
            if self.path == "/api/chat":
                tid, text = str(data["thread_id"]), str(data.get("message", ""))
                reply = ask(graph, text, tid, i18n.opt(data.get("lang")))  # no lang: keep the conversation's
                return self._json(turn_payload(tid, reply))
            if self.path == "/api/language":
                tid = str(data["thread_id"])
                if not state_of(graph, tid):
                    return self._json({"error": "unknown thread"}, 404)
                reply = switch_language(graph, tid, i18n.norm(data.get("lang")))
                return self._json(turn_payload(tid, reply))
            self._json({"error": "not found"}, 404)
        except (ValueError, KeyError, TypeError):
            self._json({"error": "bad request"}, 400)

    def log_message(self, *args):
        pass


class DualStackServer(ThreadingHTTPServer):
    """Listens on IPv4 and IPv6, so http://localhost:8000 works however the browser resolves 'localhost'."""
    address_family = socket.AF_INET6
    allow_reuse_address = False  # on Windows this would let two servers share the port

    def server_bind(self):
        self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        super().server_bind()


if __name__ == "__main__":
    try:
        httpd = DualStackServer(("::", PORT), Handler)
    except OSError as err:
        if err.errno in (98, 48) or getattr(err, "winerror", None) == 10048:  # port busy
            raise SystemExit(f"Port {PORT} is already in use. Close the other copy of server.py and try again.")
        ThreadingHTTPServer.allow_reuse_address = False
        httpd = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)  # no IPv6 on this machine
    print(f"Guru Beleq is running. Open http://localhost:{PORT}  (Ctrl+C to stop)", flush=True)
    httpd.serve_forever()
