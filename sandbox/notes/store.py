import json
import os
import tempfile

MAX_LEN = 200


class NoteError(Exception):
    pass


def _path(path: str | None) -> str:
    return path or os.environ.get("SANDBOX_NOTES_FILE") or "./notes.json"


def validate(text: str) -> str:
    text = text.strip()
    if not text:
        raise NoteError("text is empty")
    if len(text) > MAX_LEN:
        raise NoteError(f"text is longer than {MAX_LEN} characters")
    if any(c in text for c in "\t\r\n"):
        raise NoteError("text must not contain tabs or newlines")
    return text


def load(path: str | None = None) -> list[dict]:
    path = _path(path)
    try:
        with open(path, encoding="utf-8") as f:
            raw = f.read()
    except FileNotFoundError:
        return []
    if not raw.strip():
        return []
    try:
        return json.loads(raw)["notes"]
    except (ValueError, KeyError, TypeError) as err:
        raise NoteError(f"cannot read {path}: {err}") from err


def add(text: str, path: str | None = None) -> int:
    path = _path(path)
    text = validate(text)
    notes = load(path)
    new_id = max((n["id"] for n in notes), default=0) + 1
    notes.append({"id": new_id, "text": text})
    folder = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(dir=folder, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({"notes": notes}, f)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
    return new_id
