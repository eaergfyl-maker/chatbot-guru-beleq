"""Serves the Guru Beleq chat web page. Run: python server.py  then open http://localhost:8000"""
import json
import mimetypes
import socket
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from eval import cuq
from src import persona
from src.graph import ask, build_graph, start, state_of
from src.knowledge import cite, glossary, topics
from src.semantic_net import load_edges

ROOT = Path(__file__).parent
STATIC = {"/": ROOT / "web" / "index.html", "/avatar.png": ROOT / "assets" / "avatar.png"}
graph = build_graph()
PORT = 8000


def progress_of(tid: str) -> dict | None:
    p = state_of(graph, tid).get("progress")
    if not p:
        return None
    return {
        "badge": persona.badge(p),
        "done": len(p["lessons_done"]),
        "lessons_done": p["lessons_done"],
        "total": len(topics()),
        "quiz_right": p["quiz_right"],
        "quiz_total": p["quiz_total"],
    }


def meta_payload() -> dict:
    return {
        "topics": [{"id": t["id"], "title": t["title"], "summary": t["summary"]} for t in topics()],
        "glossary": [
            {"term": k, "meaning": v["meaning"], "cite": cite(v["sources"])}
            for k, v in sorted(glossary().items())
        ],
        "edges": [
            {"s": e["s"], "r": e["r"].replace("_", " "), "o": e["o"], "cite": cite(e["sources"])}
            for e in load_edges()
        ],
    }


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
        if self.path == "/api/cuq":
            return self._json({"items": cuq.ITEMS, "scale": cuq.SCALE})
        if self.path == "/api/meta":
            return self._json(meta_payload())
        path = STATIC.get(self.path.split("?")[0])
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
                reply = start(graph, tid)
                st = state_of(graph, tid)
                return self._json({"thread_id": tid, "reply": reply, "progress": None, "stage": st.get("stage", "ask_name")})
            if self.path == "/api/cuq":
                answers = [int(a) for a in data["answers"]]
                comments = str(data.get("comments", ""))[:1000]
                return self._json({"score": round(cuq.save(answers, comments), 1)})
            if self.path == "/api/chat":
                tid, text = str(data["thread_id"]), str(data.get("message", ""))
                reply = ask(graph, text, tid)
                st = state_of(graph, tid)
                return self._json({"reply": reply, "progress": progress_of(tid), "stage": st.get("stage", "menu")})
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
