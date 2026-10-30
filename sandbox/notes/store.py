import json
import os
import tempfile
import unicodedata

MAX_LEN = 200


_BAD_CATEGORIES = ("Cc", "Cf", "Cs", "Co", "Zl", "Zp")
_JOINERS = {0x200C, 0x200D}


class NoteError(Exception):
    pass


def _path(path: str | None) -> str:
    return path or os.environ.get("SANDBOX_NOTES_FILE") or "./notes.json"


def _noncharacter(cp: int) -> bool:
    return 0xFDD0 <= cp <= 0xFDEF or cp & 0xFFFF in (0xFFFE, 0xFFFF)


def _bad_text(value: str) -> bool:
    return any(
        _noncharacter(ord(c))
        or (unicodedata.category(c) in _BAD_CATEGORIES and ord(c) not in _JOINERS)
        for c in value
    )


def validate(text: str) -> str:
    text = text.strip()
    if not text:
        raise NoteError("text is empty")
    if len(text) > MAX_LEN:
        raise NoteError(f"text is longer than {MAX_LEN} characters")
    if any(c in text for c in "\t\r\n"):
        raise NoteError("text must not contain tabs or newlines")
    if _bad_text(text):
        raise NoteError("text must not contain control or invisible characters")
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
        if note_id < 1:
            raise ValueError("note ids must be 1 or more")
        if not isinstance(text, str):
            raise TypeError("each note needs a text string")
        if _bad_text(text):
            raise ValueError("note text has control or invisible characters")
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
    tmp = None
    try:
        fd, tmp = tempfile.mkstemp(dir=folder, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({"notes": notes}, f)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except OSError as err:
        _discard(tmp)
        raise NoteError(f"cannot write {path}: {err.strerror or err}") from err
    except BaseException:
        _discard(tmp)
        raise
    return new_id


def _discard(tmp: str | None) -> None:
    if tmp and os.path.exists(tmp):
        os.unlink(tmp)
