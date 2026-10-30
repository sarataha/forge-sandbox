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
    except (OSError, UnicodeDecodeError) as err:
        raise _unreadable(path, err) from err
    if not raw.strip():
        return []
    try:
        notes = _check(json.loads(raw))
    except (ValueError, TypeError) as err:
        raise _unreadable(path, err) from err
    return notes


def _unreadable(path: str, err: object) -> NoteError:
    detail = " ".join(str(err).split())
    return NoteError(f"cannot read {path}: {detail}")


def _check(data: object) -> list[dict]:
    if not isinstance(data, dict) or "notes" not in data:
        raise TypeError('expected an object with a "notes" list')
    notes = data["notes"]
    if not isinstance(notes, list):
        raise TypeError('"notes" must be a list')
    seen = set()
    for note in notes:
        if not isinstance(note, dict):
            raise TypeError("each note must be an object")
        note_id, text = note.get("id"), note.get("text")
        if not isinstance(note_id, int) or isinstance(note_id, bool):
            raise TypeError("each note needs an integer id")
        if not isinstance(text, str):
            raise TypeError("each note needs a text string")
        if note_id in seen:
            raise ValueError(f"duplicate id {note_id}")
        seen.add(note_id)
    return notes


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
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
    return new_id
