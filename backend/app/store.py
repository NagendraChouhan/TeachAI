"""Tiny JSON store: remembers the PPT / reading material / quiz made for each class."""
import json
import re
from .config import DATA

_FILE = DATA / "classes.json"


def norm(class_name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (class_name or "general").lower()).strip("-") or "general"


def _load() -> dict:
    return json.loads(_FILE.read_text()) if _FILE.exists() else {}


def get_class(class_name: str) -> dict:
    return _load().get(norm(class_name), {})


def save(class_name: str, kind: str, record: dict) -> None:
    data = _load()
    data.setdefault(norm(class_name), {})[kind] = record
    _FILE.write_text(json.dumps(data, indent=2))
