"""Serves the Guru Beleq chat web page. Run: python server.py  then open http://localhost:8000"""
import json
import mimetypes
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from src import persona
from src.graph import ask, build_graph, start, state_of
from src.knowledge import topics

ROOT = Path(__file__).parent
STATIC = {"/": ROOT / "web" / "index.html", "/avatar.png": ROOT / "assets" / "avatar.png"}
graph = build_graph()


def progress_of(tid: str) -> dict | None:
    p = state_of(graph, tid).get("progress")
    if not p:
        return None
    return {"badge": persona.badge(p), "done": len(p["lessons_done"]), "total": len(topics()),
            "quiz_right": p["quiz_right"], "quiz_total": p["quiz_total"]}


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
                return self._json({"thread_id": tid, "reply": start(graph, tid), "progress": None})
            if self.path == "/api/chat":
                tid, text = str(data["thread_id"]), str(data.get("message", ""))
                return self._json({"reply": ask(graph, text, tid), "progress": progress_of(tid)})
            self._json({"error": "not found"}, 404)
        except (ValueError, KeyError):
            self._json({"error": "bad request"}, 400)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    print("Guru Beleq is running at http://localhost:8000  (Ctrl+C to stop)")
    ThreadingHTTPServer(("127.0.0.1", 8000), Handler).serve_forever()
