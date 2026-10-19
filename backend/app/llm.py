from langchain_groq import ChatGroq
from .config import GROQ_MODEL


def get_llm(temperature: float = 0.3) -> ChatGroq:
    return ChatGroq(model=GROQ_MODEL, temperature=temperature)
