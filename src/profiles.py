"""Saves each learner's progress by name so returning users are remembered."""
import json
import logging
import os
from pathlib import Path

log = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parent.parent


def _file() -> Path:
    return Path(os.getenv("PROFILES_FILE", ROOT / "data" / "profiles.json"))


def new_progress() -> dict:
    return {
        "lessons_done": [],
        "lesson_right": 0,   # lesson checks answered correctly first time
        "lesson_total": 0,
        "quiz_right": 0,
        "quiz_total": 0,
        "topic_stats": {},   # topic id -> {"right": n, "total": n}
        "topics_seen": [],   # topics the learner asked about
    }


def _read() -> dict:
    try:
        return json.loads(_file().read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (ValueError, OSError):
        log.exception("profiles file unreadable; starting empty")
        return {}


def load(name: str) -> dict | None:
    entry = _read().get(name.lower())
    return {**new_progress(), **entry["progress"]} if entry else None


def save(name: str, progress: dict) -> None:
    try:
        data = _read()
        data[name.lower()] = {"name": name, "progress": progress}
        f = _file()
        f.parent.mkdir(parents=True, exist_ok=True)
        tmp = f.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp.replace(f)  # a crash mid-write can't corrupt the existing file
    except OSError:
        log.exception("could not save profile")
