import json
import os
from pathlib import Path

from filelock import FileLock

from backend.config import BASE_DIR

SESSIONS_DIR = BASE_DIR / "sessions"
SESSIONS_DIR.mkdir(exist_ok=True)


def _session_path(user_id: int, session_id: str) -> Path:
    d = SESSIONS_DIR / str(user_id)
    d.mkdir(parents=True, exist_ok=True)
    os.chmod(d, 0o700)
    p = (d / f"{session_id}.json").resolve()
    if not p.is_relative_to(SESSIONS_DIR.resolve()):
        raise ValueError("Path traversal detected")
    return p


def load_messages(user_id: int, session_id: str) -> list[dict]:
    path = _session_path(user_id, session_id)
    if not path.exists():
        return []
    with FileLock(str(path) + ".lock"):
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return []


def save_messages(user_id: int, session_id: str, messages: list[dict]) -> None:
    path = _session_path(user_id, session_id)
    tmp = path.with_suffix(".tmp")
    with FileLock(str(path) + ".lock"):
        tmp.write_text(
            json.dumps(messages, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        os.chmod(tmp, 0o600)
        tmp.replace(path)


def delete_session_files(user_id: int, session_id: str) -> None:
    path = _session_path(user_id, session_id)
    if path.exists():
        path.unlink()
    lock_path = str(path) + ".lock"
    if os.path.exists(lock_path):
        os.unlink(lock_path)


def trim_messages(messages: list[dict], max_rounds: int) -> list[dict]:
    if max_rounds <= 0:
        return messages
    system_msgs = [m for m in messages if m.get("role") == "system"]
    other_msgs = [m for m in messages if m.get("role") != "system"]
    keep = other_msgs[-max_rounds * 2 :]
    return system_msgs + keep
