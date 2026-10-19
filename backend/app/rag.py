"""Book ingestion + retrieval (PyMuPDF -> chunks -> Chroma with its built-in local embeddings)."""
import pymupdf as fitz
import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter
from .config import CHROMA

_client = chromadb.PersistentClient(path=str(CHROMA))
_col = _client.get_or_create_collection("books", metadata={"hnsw:space": "cosine"})
_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)

RELEVANT_DISTANCE = 0.6  # cosine distance; lower = closer


def _read(path: str) -> list[tuple[int, str]]:
    if path.lower().endswith(".pdf"):
        with fitz.open(path) as doc:
            return [(i + 1, page.get_text()) for i, page in enumerate(doc)]
    with open(path, encoding="utf-8", errors="ignore") as f:
        return [(1, f.read())]


def ingest(path: str, name: str) -> int:
    remove(name)
    ids, docs, metas = [], [], []
    for page_no, text in _read(path):
        for j, chunk in enumerate(_splitter.split_text(text)):
            ids.append(f"{name}-{page_no}-{j}")
            docs.append(chunk)
            metas.append({"book": name, "page": page_no})
    for i in range(0, len(docs), 100):
        _col.add(ids=ids[i:i + 100], documents=docs[i:i + 100], metadatas=metas[i:i + 100])
    return len(docs)


def remove(name: str) -> None:
    _col.delete(where={"book": name})


def list_books() -> list[str]:
    got = _col.get(include=["metadatas"])
    return sorted({m["book"] for m in got["metadatas"]})


def search(query: str, k: int = 6) -> list[dict]:
    if _col.count() == 0:
        return []
    res = _col.query(query_texts=[query], n_results=min(k, _col.count()))
    return [
        {"text": d, "book": m["book"], "page": m["page"], "distance": dist}
        for d, m, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0])
    ]


def relevant(chunks: list[dict]) -> list[dict]:
    return [c for c in chunks if c["distance"] <= RELEVANT_DISTANCE]
