from ddgs import DDGS


def web_search(query: str, n: int = 5) -> list[dict]:
    try:
        return [
            {"title": r["title"], "url": r["href"], "text": r["body"]}
            for r in DDGS().text(query, max_results=n)
        ]
    except Exception:
        return []
