from typing import Literal
from pydantic import BaseModel, Field
from ..context import gather
from ..llm import get_llm
from ..store import get_class, norm, save
from .pdf import quiz_to_pdf


class Question(BaseModel):
    type: Literal["mcq", "short", "long"]
    question: str
    options: list[str] = Field(default_factory=list, description="4 options for mcq, else empty")
    answer: str = Field(description="for mcq start with the letter, e.g. 'B) text'; short/long: a model answer")
    marks: int


class Paper(BaseModel):
    title: str
    questions: list[Question]


def build_quiz(class_name: str, topics: list[str], num_questions: int, instructions: str) -> dict:
    cls = get_class(class_name)
    ppt, reading = cls.get("ppt"), cls.get("reading")
    if not topics:
        topics = (ppt or reading or {}).get("topics") or [class_name]
    context, sources = gather(topics)
    material = ""
    if ppt:
        material += "Presentation:\n" + "\n".join(f"- {s['title']}: " + "; ".join(s["bullets"]) for s in ppt["slides"]) + "\n\n"
    if reading:
        material += "Reading material:\n" + reading["text"][:3500] + "\n\n"
    paper = get_llm(0.4).with_structured_output(Paper).invoke(
        f"Create a question paper for {class_name} on {', '.join(topics)} with exactly {num_questions} questions. "
        "Mix: mostly MCQ, some short answer, 1-2 long answer. Each with an answer and marks. "
        "No duplicates; only ask what the material covers.\n"
        f"Teacher instructions: {instructions or 'none'}\n\n{material}Book/web material:\n{context or '(none)'}"
    )
    fname = quiz_to_pdf(paper, class_name.title(), f"{norm(class_name)}-quiz.pdf")
    save(class_name, "quiz", {"file": fname, "topics": topics, "questions": [q.model_dump() for q in paper.questions]})
    return {"file": fname, "questions": len(paper.questions), "sources": sources}
