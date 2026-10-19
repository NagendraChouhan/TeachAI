"""LangGraph agent: intent router -> (qa | ppt | reading | quiz | email) -> END.
Email uses interrupt() so nothing is sent until the teacher approves."""
from typing import Annotated, Literal, Optional
from typing_extensions import TypedDict
from pydantic import BaseModel, Field
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.types import interrupt

from . import rag
from .config import DATA, STUDENT_EMAILS
from .context import gather
from .llm import get_llm
from .pipelines.email import send_email
from .pipelines.ppt import build_ppt
from .pipelines.quiz import build_quiz
from .pipelines.reading import build_reading
from .store import get_class


class State(TypedDict, total=False):
    messages: Annotated[list, add_messages]
    plan: dict
    files: list[str]
    draft: dict


class Draft(BaseModel):
    subject: str
    body: str = Field(description="complete plain-text email, greeting to sign-off")


class Plan(BaseModel):
    intent: Literal["qa", "ppt", "reading", "quiz", "email", "chat"] = Field(
        description="qa=ANY question about a subject, concept, fact or 'why/how/what' (even short ones) - answered from the books; "
        "ppt=make presentation; "
        "reading=make reading material; quiz=make question paper; email=send an email/announcement to students; chat=ONLY greetings, thanks, or questions about the assistant itself")
    class_name: str = Field(default="general", description="e.g. 'class 1'")
    topics: list[str] = Field(default_factory=list)
    num_items: int = Field(default=8, description="slides for ppt, questions for quiz")
    file_kind: Literal["ppt", "reading", "quiz", "none"] = Field(
        default="none", description="for email only: attach the ppt/reading/quiz ONLY if the teacher explicitly asks "
        "to send that document; for a plain message/announcement use 'none'")
    email_message: str = Field(default="", description="for email: what the teacher wants to tell the students, "
                               "in their own words (e.g. 'class tomorrow at 10 am')")
    emails: list[str] = Field(default_factory=list)
    instructions: str = ""


def classify(history: list) -> Plan:
    """Ask the LLM what the teacher wants. Raises on failure (the evaluation scripts call this directly)."""
    msgs = [SystemMessage(content="Classify the teacher's latest request and extract parameters. Always answer by "
                          "calling the function, even for greetings or small talk (use intent 'chat'). "
                          "Use earlier messages to resolve things like 'it' or 'same class'.")] + history[-6:]
    return get_llm(0).with_structured_output(Plan).invoke(msgs)


def router(state: State) -> dict:
    plan = None
    for _ in range(2):  # the model occasionally replies in plain text instead of calling the tool
        try:
            plan = classify(state["messages"])
            break
        except Exception:
            continue
    plan = plan or Plan(intent="chat")
    return {"plan": plan.model_dump(), "files": [], "draft": {}}


def route(state: State) -> str:
    i = state["plan"]["intent"]
    return {"email": "email_draft"}.get(i, i)


def chat(state: State) -> dict:
    ans = get_llm(0.5).invoke(
        [SystemMessage(content="You are TeachAI, a friendly assistant for teachers. Never say you are ChatGPT or made by "
                       "OpenAI. Reply briefly (1-3 sentences). If asked who you are or what you can do, say you can answer "
                       "questions from the teacher's uploaded books, and create PPTs, reading material (PDF) and quiz "
                       "papers, and email students with the teacher's approval.")] + state["messages"][-6:]
    ).content
    return {"messages": [AIMessage(content=ans)]}


def qa(state: State) -> dict:
    question = state["messages"][-1].content
    context, sources = gather([question])
    ans = get_llm(0.3).invoke(
        [SystemMessage(content="You are a helpful teaching assistant. Explain clearly using the source material "
                       "when relevant; say if it came from the books or the web.\n"
                       "Format the answer in clean markdown: '##' headings, short paragraphs, bullet lists, **bold** key terms, "
                       "proper markdown tables (header row + |---| separator row, each row on its own line), '>' for source "
                       "quotes. Put any diagram or flow in a fenced code block (```) using simple ASCII boxes and arrows.\n\nSources:\n" + (context or "(none)"))]
        + state["messages"][-6:]
    ).content
    return {"messages": [AIMessage(content=ans)]}


def _topics(p: dict) -> list[str]:
    return p["topics"]


def ppt(state: State) -> dict:
    p = state["plan"]
    if not _topics(p):
        return {"messages": [AIMessage(content="Which topics should the presentation cover, and how many slides?")]}
    r = build_ppt(p["class_name"], _topics(p), p["num_items"], p["instructions"])
    msg = f"Created a {r['slides']}-slide presentation for **{p['class_name']}**. Source: {r['sources'][0]}."
    return {"messages": [AIMessage(content=msg)], "files": [r["file"]]}


def reading(state: State) -> dict:
    p = state["plan"]
    r = build_reading(p["class_name"], _topics(p), p["instructions"])
    msg = f"Created reading material for **{p['class_name']}**" + (
        " based on the class presentation." if r["used_ppt"] else " (no presentation found for that class, so I used books/web).")
    return {"messages": [AIMessage(content=msg)], "files": [r["file"]]}


def quiz(state: State) -> dict:
    p = state["plan"]
    r = build_quiz(p["class_name"], _topics(p), p["num_items"], p["instructions"])
    msg = f"Created a {r['questions']}-question paper for **{p['class_name']}** (answer key on the last page)."
    return {"messages": [AIMessage(content=msg)], "files": [r["file"]]}


def email_draft(state: State) -> dict:
    p = state["plan"]
    attachment = None
    if p["file_kind"] != "none":
        rec = get_class(p["class_name"]).get(p["file_kind"])
        if not rec:
            return {"messages": [AIMessage(content=f"I haven't created a {p['file_kind']} for {p['class_name']} yet, so there is nothing to attach.")]}
        attachment = rec["file"]
    to = p["emails"] or STUDENT_EMAILS
    if not to:
        return {"messages": [AIMessage(content="Which email addresses should I send it to?")]}
    d = get_llm(0.3).with_structured_output(Draft).invoke(
        "Write a short, friendly, professional email from a teacher to their students.\n"
        f"Teacher's request: {state['messages'][-1].content}\n"
        f"Message to convey: {p['email_message'] or state['messages'][-1].content}\n"
        f"Attachment: {attachment or 'none'} (mention it in the body only if there is one)\n"
        "Use only facts the teacher gave; do not invent dates, times or links. Sign off as 'Your teacher'.")
    return {"draft": {"to": to, "subject": d.subject, "body": d.body, "attachment": attachment}}


def after_draft(state: State) -> str:
    return "email_send" if state.get("draft") else END


def email_send(state: State) -> dict:
    draft = state["draft"]
    approved = interrupt(draft)  # pauses here until the teacher clicks Approve / Cancel
    if not approved:
        return {"messages": [AIMessage(content="Okay, I did not send the email.")], "draft": {}}
    try:
        send_email(**draft)
    except Exception as e:
        return {"messages": [AIMessage(content=f"Email failed: {e}")], "draft": {}}
    return {"messages": [AIMessage(content=f"Email sent to {len(draft['to'])} student(s).")], "draft": {}}


def build_graph():
    g = StateGraph(State)
    for name, fn in [("router", router), ("chat", chat), ("qa", qa), ("ppt", ppt), ("reading", reading), ("quiz", quiz),
                     ("email_draft", email_draft), ("email_send", email_send)]:
        g.add_node(name, fn)
    g.add_edge(START, "router")
    g.add_conditional_edges("router", route, ["chat", "qa", "ppt", "reading", "quiz", "email_draft"])
    for n in ["chat", "qa", "ppt", "reading", "quiz", "email_send"]:
        g.add_edge(n, END)
    g.add_conditional_edges("email_draft", after_draft, ["email_send", END])
    return g.compile(checkpointer=checkpointer)


# the agent's own memory (conversation + paused email approvals) survives restarts
checkpointer = SqliteSaver(sqlite3.connect(DATA / "checkpoints.db", check_same_thread=False))
graph = build_graph()
