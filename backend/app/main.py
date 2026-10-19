import shutil
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from langchain_core.messages import HumanMessage
from langgraph.types import Command
from pydantic import BaseModel

from . import chats, rag
from .config import OUTPUTS, UPLOADS
from .graph import checkpointer, graph

app = FastAPI(title="Teacher Assistant")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class ChatIn(BaseModel):
    thread_id: str
    message: str


class ApproveIn(BaseModel):
    thread_id: str
    approved: bool


def _result(thread_id: str, out: dict) -> dict:
    cfg = {"configurable": {"thread_id": thread_id}}
    state = graph.get_state(cfg)
    if state.next:  # paused on interrupt
        draft = state.tasks[0].interrupts[0].value
        return {"reply": "I've drafted this email. Please review and approve.", "files": [], "approval": draft}
    last = out["messages"][-1].content
    return {"reply": last, "files": out.get("files", []), "approval": None}


@app.post("/api/chat")
def chat(body: ChatIn):
    cfg = {"configurable": {"thread_id": body.thread_id}}
    chats.add_message(body.thread_id, "user", body.message)
    try:
        out = graph.invoke({"messages": [HumanMessage(content=body.message)]}, cfg)
    except Exception as e:
        raise HTTPException(500, f"{type(e).__name__}: {e}")
    res = _result(body.thread_id, out)
    chats.add_message(body.thread_id, "bot", res["reply"], res["files"], res["approval"])
    return res


@app.post("/api/approve")
def approve(body: ApproveIn):
    cfg = {"configurable": {"thread_id": body.thread_id}}
    chats.clear_approval(body.thread_id)
    try:
        out = graph.invoke(Command(resume=body.approved), cfg)
    except Exception as e:
        raise HTTPException(500, f"{type(e).__name__}: {e}")
    res = _result(body.thread_id, out)
    chats.add_message(body.thread_id, "bot", res["reply"], res["files"], res["approval"])
    return res


@app.post("/api/upload")
async def upload(files: list[UploadFile] = File(...)):
    done = []
    for f in files:
        path = UPLOADS / f.filename
        with open(path, "wb") as out:
            shutil.copyfileobj(f.file, out)
        done.append({"name": f.filename, "chunks": rag.ingest(str(path), f.filename)})
    return done


@app.get("/api/books")
def books():
    return rag.list_books()


@app.delete("/api/books/{name}")
def delete_book(name: str):
    rag.remove(name)
    return {"ok": True}


@app.get("/api/files/{name}")
def download(name: str):
    path = OUTPUTS / name
    if not path.resolve().parent == OUTPUTS.resolve() or not path.exists():
        raise HTTPException(404)
    return FileResponse(path, filename=name)


@app.get("/api/chats")
def list_chats():
    return chats.list_chats()


@app.get("/api/chats/{chat_id}")
def get_chat(chat_id: str):
    return chats.get_messages(chat_id)


@app.delete("/api/chats/{chat_id}")
def delete_chat(chat_id: str):
    chats.delete_chat(chat_id)
    try:
        checkpointer.delete_thread(chat_id)
    except Exception:
        pass
    return {"ok": True}
