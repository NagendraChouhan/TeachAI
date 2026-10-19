"""Shared helper: gather material for a topic from books, and from the web only if books are thin."""
from . import rag
from .web import web_search

MAX_CHARS = 6000  # keep prompts small for Groq's free-tier token limits


def gather(topics: list[str]) -> tuple[str, list[str]]:
    """Returns (context_text, source_notes)."""
    parts, sources, hits = [], [], 0
    for t in topics:
        chunks = rag.relevant(rag.search(t, k=4))
        hits += len(chunks)
        for c in chunks:
            parts.append(f"[Book: {c['book']} p.{c['page']}] {c['text']}")
            sources.append(f"{c['book']} p.{c['page']}")
    used_web = False
    if hits < 3 * len(topics):  # coverage check: books are not enough -> web
        used_web = True
        for t in topics:
            for r in web_search(t, 3):
                parts.append(f"[Web: {r['url']}] {r['text']}")
                sources.append(r["url"])
    text = "\n\n".join(parts)[:MAX_CHARS]
    note = ["Books + web search" if used_web and hits else "Web search" if used_web else "Books only"]
    return text, note + sorted(set(sources))
