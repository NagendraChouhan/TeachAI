"""Chat history for the UI (SQLite file data/chats.db): chats + the messages shown on screen."""
import json
import sqlite3
import time
from contextlib import closing

from .config import DATA

DB = DATA / "chats.db"


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c


with closing(_conn()) as c, c:
    c.execute("CREATE TABLE IF NOT EXISTS chats (id TEXT PRIMARY KEY, title TEXT, updated REAL)")
    c.execute("""CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id TEXT, role TEXT, text TEXT,
        files TEXT, approval TEXT, ts REAL)""")


def add_message(chat_id: str, role: str, text: str, files: list | None = None, approval: dict | None = None) -> None:
    now = time.time()
    with closing(_conn()) as c, c:
        if not c.execute("SELECT 1 FROM chats WHERE id=?", (chat_id,)).fetchone():
            c.execute("INSERT INTO chats VALUES (?,?,?)", (chat_id, text[:45] or "New chat", now))
        c.execute("UPDATE chats SET updated=? WHERE id=?", (now, chat_id))
        c.execute("INSERT INTO messages (chat_id, role, text, files, approval, ts) VALUES (?,?,?,?,?,?)",
                  (chat_id, role, text, json.dumps(files or []), json.dumps(approval) if approval else None, now))


def clear_approval(chat_id: str) -> None:
    with closing(_conn()) as c, c:
        c.execute("UPDATE messages SET approval=NULL WHERE chat_id=?", (chat_id,))


def list_chats() -> list[dict]:
    with closing(_conn()) as c:
        return [dict(r) for r in c.execute("SELECT id, title, updated FROM chats ORDER BY updated DESC")]


def get_messages(chat_id: str) -> list[dict]:
    with closing(_conn()) as c:
        rows = c.execute("SELECT role, text, files, approval FROM messages WHERE chat_id=? ORDER BY id", (chat_id,))
        return [{"role": r["role"], "text": r["text"], "files": json.loads(r["files"] or "[]"),
                 "approval": json.loads(r["approval"]) if r["approval"] else None} for r in rows]


def delete_chat(chat_id: str) -> None:
    with closing(_conn()) as c, c:
        c.execute("DELETE FROM messages WHERE chat_id=?", (chat_id,))
        c.execute("DELETE FROM chats WHERE id=?", (chat_id,))
