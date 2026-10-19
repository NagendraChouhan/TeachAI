import re
from ..context import gather
from ..images import fetch_many
from ..llm import get_llm
from ..store import get_class, norm, save
from .pdf import markdown_to_pdf

IMG_RE = re.compile(r"!\[(.*?)\]\(IMAGE:\s*(.*?)\)")

FORMAT_GUIDE = """Write like a polished study guide / blog article, in markdown:
- '# ' one title only, at the top.
- A short engaging intro paragraph, then 4-6 '## ' sections (each with clear explanation, simple language, a worked example or analogy).
- Use '### ' sub-headings, '- ' bullet lists and '1. ' numbered steps where useful.
- **Bold** important terms and ==highlight== the 1-2 most crucial phrases per section.
- Add 2-3 callout boxes using lines that start with '> ' (e.g. '> **Key idea:** ...', '> **Remember:** ...', '> **Did you know?** ...').
- Add exactly 3 images as: ![Short caption](IMAGE: visual description for an illustration, 6-12 words) placed on their own line between sections.
- End with '## Key Takeaways' (bullets) and '## Quick Check' (3-4 self-test questions, numbered).
Do not use tables, emojis or HTML."""


def build_reading(class_name: str, topics: list[str], instructions: str) -> dict:
    ppt = get_class(class_name).get("ppt")
    if not topics and ppt:
        topics = ppt["topics"]
    if not topics:
        topics = [class_name]
    context, sources = gather(topics)
    slides = ""
    if ppt:
        slides = "\n".join(f"- {s['title']}: " + "; ".join(s["bullets"]) for s in ppt["slides"])
    md = get_llm(0.4).invoke(
        f"Write student reading material for {class_name} on: {', '.join(topics)}.\n{FORMAT_GUIDE}\n"
        f"Teacher instructions: {instructions or 'none'}\n\n"
        f"Class presentation outline (follow its structure):\n{slides or '(no presentation yet)'}\n\n"
        f"Extra source material:\n{context or '(none)'}"
    ).content
    found = IMG_RE.findall(md)[:4]
    paths = fetch_many([desc for _, desc in found])
    it = iter(zip(found, paths))

    def swap(m):
        try:
            (cap, _), path = next(it)
        except StopIteration:
            return ""
        return f"![{cap}]({path})" if path else ""

    md = IMG_RE.sub(swap, md)
    fname = markdown_to_pdf(md, f"{norm(class_name)}-reading-material.pdf", f"Reading Material  |  {class_name.title()}")
    save(class_name, "reading", {"file": fname, "topics": topics, "text": IMG_RE.sub("", md)})
    return {"file": fname, "sources": sources, "used_ppt": bool(ppt), "images": sum(p is not None for p in paths)}
